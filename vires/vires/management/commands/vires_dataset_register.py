#-------------------------------------------------------------------------------
#
# Products management - product registration
#
# Project: VirES
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------
# pylint: disable=fixme, import-error, no-self-use
# pylint: disable=missing-docstring,too-many-arguments,unused-argument
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
# pylint: disable=too-few-public-methods

import numpy as np
from django.contrib.gis import geos
from django.core.management import call_command
from django.core.management.base import CommandError, BaseCommand
from django.utils.dateparse import parse_datetime
from eoxserver.core import env
from eoxserver.backends import models as backends
from eoxserver.backends.component import BackendComponent
from eoxserver.backends.cache import CacheContext
from eoxserver.backends.access import connect
from eoxserver.resources.coverages import models
from eoxserver.resources.coverages.metadata.component import MetadataComponent
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from vires.models import Product
from vires.cdf_util import cdf_open, cdf_rawtime_to_datetime
from vires.time_util import naive_to_utc


class Command(CommandOutputMixIn, BaseCommand):

    help = """
        Registers a Dataset.
        A dataset is a collection of data and metadata items. When being
        registered, as much metadata as possible is extracted from the supplied
        (meta-)data items. If some metadata is still missing, it needs to be
        supplied via the specific override options.

        By default, datasets are not "visible" which means that they are not
        advertised in the GetCapabilities sections of the various services.
        This needs to be overruled via the `--visible` switch.

        The registered dataset can optionally be directly inserted one or more
        collections.
    """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "-i", "--identifier", "--coverage-id", dest="identifier",
            action="store", default=None, help=(
                "Optional custom product identifier overriding the default "
                " identifier of the dataset."
            )
        )
        parser.add_argument(
            "-d", "--data", dest="data", required=True, action="append", help=(
                "One or more data items of the dataset. The format is: "
                "[storage_type:url] [package_type:location]* format:location"
            )
        )
        parser.add_argument(
            "-s", "--semantic", dest="semantics", action="append",
            help=(
                "Optional band semantics. If given, one band "
                "semantics 'band[*]' must be present for each data item."
            )
        )
        parser.add_argument(
            "-m", "--meta-data", dest="metadata", default=[], action="append",
            help=(
                "One or more metadata items of the dataset. The format is: "
                "[storage_type:url] [package_type:location]* format:location"
            )
        )
        parser.add_argument(
            "-r", "--range-type", dest="range_type_name", required=True,
            help="Mandatory range type name."
        )
        parser.add_argument(
            "--size", dest="size", action="store", default=None,
            help="Custom dataset size encoded as <size-x>,<size-y>"
        )
        parser.add_argument(
            "--begin-time", dest="begin_time", action="store", default=None,
            help="Custom begin time encoded as ISO8601 datetime strings."
        )
        parser.add_argument(
            "--end-time", dest="end_time", action="store", default=None,
            help="Custom end time. Format is ISO8601 datetime strings."
        )
        parser.add_argument(
            "--visible", dest="visible", action="store_true", default=False,
            help=(
                "Set the dataset to be 'visible', i.e, to be advertised "
                "in OWS capabilities."
            )
        )
        parser.add_argument(
            "--collection", dest="collection_ids", action="append",
            help="Optional list of collection the dataset should be linked to."
        )
        parser.add_argument(
            '--ignore-missing-collection', dest='ignore_missing_collection',
            action="store_true", default=False,
            help=(
                "This flag indicates that the registration should proceed "
                "even if the linked collection does not exist ."
                "By default a missing collection will result in an error."
            )
        )

    args = (
        "-d [<storage>:][<package>:]<location> [-d ... ] "
        "-r <range-type-name> "
        "[-m [<storage>:][<package>:]<location> [-m ... ]] "
        "[-s <semantic> [-s <semantic>]] "
        "[--identifier <identifier>] "
        "[-e <minx>,<miny>,<maxx>,<maxy>] "
        "[--size <size-x> <size-y>] "
        "[--srid <srid> | --projection <projection-def>] "
        "[--footprint <footprint-wkt>] "
        "[--begin-time <begin-time>] [--end-time <end-time>] "
        "[--coverage-type <coverage-type-name>] "
        "[--visible] [--collection <collection-id> [--collection ... ]] "
        "[--ignore-missing-collection]"
    )

    @nested_commit_on_success
    def handle(self, *args, **kwargs):
        with CacheContext() as cache:
            self.handle_with_cache(cache, *args, **kwargs)

    def handle_with_cache(self, cache, *args, **kwargs):
        metadata_component = MetadataComponent(env)
        datas = kwargs["data"]
        semantics = kwargs.get("semantics")
        metadatas = kwargs["metadata"]
        range_type_name = kwargs["range_type_name"]

        range_type = models.RangeType.objects.get(name=range_type_name)

        metadata_keys = set((
            "identifier", "extent", "size",
            "footprint", "begin_time", "end_time",
        ))

        all_data_items = []
        retrieved_metadata = {}

        retrieved_metadata.update(
            self._get_overrides(**kwargs)
        )

        for metadata in metadatas:
            storage, package, format_, location = self._get_location_chain(
                metadata
            )
            data_item = backends.DataItem(
                location=location, format=format_ or "", semantic="metadata",
                storage=storage, package=package,
            )
            data_item.full_clean()
            data_item.save()
            all_data_items.append(data_item)

            with open(connect(data_item, cache)) as fobj:
                content = fobj.read()

            reader = metadata_component.get_reader_by_test(content)
            if reader:
                values = reader.read(content)

                format_ = values.pop("format", None)
                if format_:
                    data_item.format = format_
                    data_item.full_clean()
                    data_item.save()

                for key, value in values.items():
                    if key in metadata_keys:
                        retrieved_metadata.setdefault(key, value)

        if semantics is None:
            # TODO: check corner cases.
            # e.g: only one data item given but multiple bands in range type
            # --> bands[1:<bandnum>]
            if len(datas) == 1:
                if len(range_type) == 1:
                    semantics = ["bands[1]"]
                else:
                    semantics = ["bands[1:%d]" % len(range_type)]

            else:
                semantics = ["bands[%d]" % i for i in range(len(datas))]

        for data, semantic in zip(datas, semantics):
            storage, package, format_, location = self._get_location_chain(data)
            data_item = backends.DataItem(
                location=location, format=format_ or "", semantic=semantic,
                storage=storage, package=package,
            )
            data_item.full_clean()
            data_item.save()
            all_data_items.append(data_item)

            # TODO: read XML meta-data
            with cdf_open(connect(data_item, cache)) as dataset:
                values = VirESMetadataReader.read(dataset)
                format_ = values.pop("format", None)
                if format_:
                    data_item.format = format_
                    data_item.full_clean()
                    data_item.save()
                for key, value in values.items():
                    if key in metadata_keys:
                        retrieved_metadata.setdefault(key, value)

        if metadata_keys - set(retrieved_metadata.keys()):
            raise CommandError(
                "Missing metadata keys %s."
                % ", ".join(metadata_keys - set(retrieved_metadata.keys()))
            )

        try:
            coverage = Product()
            coverage.range_type = range_type
            coverage.srid = 4326
            coverage.extent = (-180, -90, 180, 90)

            for key, value in retrieved_metadata.items():
                setattr(coverage, key, value)

            coverage.visible = kwargs["visible"]

            coverage.full_clean()
            coverage.save()

            for data_item in all_data_items:
                data_item.dataset = coverage
                data_item.full_clean()
                data_item.save()

            # link with collection(s)
            if kwargs["collection_ids"]:
                ignore_missing_collection = kwargs["ignore_missing_collection"]
                call_command(
                    "eoxs_collection_link",
                    collection_ids=kwargs["collection_ids"],
                    add_ids=[coverage.identifier],
                    ignore_missing_collection=ignore_missing_collection
                )

        except Exception as exc:
            self.print_traceback(exc, kwargs)
            raise CommandError("Dataset registration failed: %s" % exc)

        self.print_msg(
            "Dataset with ID '%s' registered successfully."
            % coverage.identifier
        )

    def _get_overrides(self, identifier=None, size=None, extent=None,
                       begin_time=None, end_time=None, footprint=None,
                       projection=None, coverage_type=None, **kwargs):

        overrides = {}

        if coverage_type:
            overrides["coverage_type"] = coverage_type

        if identifier:
            overrides["identifier"] = identifier

        if extent:
            overrides["extent"] = [float(v) for v in extent.split(",")]

        if size:
            overrides["size"] = int(size)

        if begin_time:
            overrides["begin_time"] = parse_datetime(begin_time)

        if end_time:
            overrides["end_time"] = parse_datetime(end_time)

        if footprint:
            footprint = geos.GEOSGeometry(footprint)
            if footprint.hasz:
                raise CommandError(
                    "Invalid footprint geometry! 3D geometry is not supported!"
                )
            if footprint.geom_type == "MultiPolygon":
                overrides["footprint"] = footprint
            elif footprint.geom_type == "Polygon":
                overrides["footprint"] = geos.MultiPolygon(footprint)
            else:
                raise CommandError(
                    "Invalid footprint geometry type '%s'!"
                    % (footprint.geom_type)
                )

        if projection:
            try:
                overrides["projection"] = int(projection)
            except ValueError:
                overrides["projection"] = projection

        return overrides

    def _get_location_chain(self, items):
        """ Returns the tuple
        """
        component = BackendComponent(env)
        storage = None
        package = None

        storage_type, url = self._split_location(items[0])
        if storage_type:
            storage_component = component.get_storage_component(storage_type)
        else:
            storage_component = None

        if storage_component:
            storage, _ = backends.Storage.objects.get_or_create(
                url=url, storage_type=storage_type
            )

        # packages
        for item in items[1 if storage else 0:-1]:
            type_or_format, location = self._split_location(item)
            package_component = component.get_package_component(type_or_format)
            if package_component:
                package, _ = backends.Package.objects.get_or_create(
                    location=location, format=format,
                    storage=storage, package=package
                )
                storage = None  # override here
            else:
                raise Exception(
                    "Could not find package component for format '%s'"
                    % type_or_format
                )

        format_, location = self._split_location(items[-1])
        return storage, package, format_, location

    def _split_location(self, item):
        """ Splits string as follows: <format>:<location> where format can be
            None.
        """
        idx = item.find(":")
        return (None, item) if idx == -1 else (item[:idx], item[idx + 1:])


def save(model):
    model.full_clean()
    model.save()
    return model


class VirESMetadataReader(object):

    LATLON_KEYS = [
        ("Longitude", "Latitude"),
        ("longitude", "latitude"),
    ]

    TIME_KEYS = [
        "Timestamp",
        "timestamp",
        "Epoch"
    ]

    @classmethod
    def get_time_range_and_size(cls, data):
        # iterate possible time keys and try to extract the values
        for time_key in cls.TIME_KEYS:
            try:
                times = data.raw_var(time_key)
            except KeyError:
                continue
            else:
                break
        else:
            raise KeyError("Temporal variable not found!")

        if len(times.shape) != 1:
            raise ValueError("Incorrect dimension of the time-stamp array!")

        return (
            naive_to_utc(cdf_rawtime_to_datetime(times[0], times.type())),
            naive_to_utc(cdf_rawtime_to_datetime(times[-1], times.type())),
            times.shape[0]
        )

    @classmethod
    def get_coords(cls, data):
        # iterate possible lat/lon keys and try to extract the values
        for lat_key, lon_key in cls.LATLON_KEYS:
            try:
                lat_data = data[lat_key][:]
                lon_data = data[lon_key][:]
            except KeyError:
                continue
            else:
                coords = np.empty((len(lon_data), 2))
                coords[:, 0] = lon_data
                coords[:, 1] = lat_data
                break
        else:
            # values not extracted assume global product
            coords = np.array([(-180.0, -90.0), (+180.0, +90.0)])

        return coords

    @classmethod
    def coords_to_bounding_box(cls, coords):
        coords = coords[~np.isnan(coords).any(1)]
        if coords.size:
            lon_min, lat_min = np.floor(np.amin(coords, 0))
            lon_max, lat_max = np.ceil(np.amax(coords, 0))
        else:
            lon_min, lat_min, lon_max, lat_max = -180, -90, 180, 90
        return (lon_min, lat_min, lon_max, lat_max)

    @classmethod
    def bounding_box_to_geometry(cls, bbox):
        return geos.MultiPolygon(
            geos.Polygon((
                (bbox[0], bbox[1]), (bbox[2], bbox[1]),
                (bbox[2], bbox[3]), (bbox[0], bbox[3]), (bbox[0], bbox[1]),
            ))
        )

    @classmethod
    def read(cls, data):
        # NOTE: For sake of simplicity we take geocentric (ITRF) coordinates
        #       as geodetic coordinates.
        begin_time, end_time, n_times = cls.get_time_range_and_size(data)
        coords = cls.get_coords(data)
        bbox = cls.coords_to_bounding_box(coords)
        footprint = cls.bounding_box_to_geometry(bbox)

        return {
            "format": "CDF",
            "size": (n_times, 0),
            "extent": bbox,
            "footprint": footprint,
            "begin_time": begin_time,
            "end_time": end_time,
        }
