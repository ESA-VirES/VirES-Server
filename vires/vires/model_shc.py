#-------------------------------------------------------------------------------
#
# Multiple SHC models handling.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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

import re
from zipfile import ZipFile
from datetime import datetime, timedelta
from os.path import basename, splitext


MCO_SHA_2X_MAX_ALLOWED_TIME_GAP = timedelta(seconds=1)

RE_SWARM_SHA_PRODUCT = re.compile(
    r"^SW_OPER_(?P<type>[A-Z0-9_]{10,10})"
    r"_(?P<start>\d{8,8}T\d{6,6})_(?P<end>\d{8,8}T\d{6,6})"
    r"_(?P<baseline>\d{2,2})(?P<version>\d{2,2})$"
)


def process_zipped_files(zip_filename, process):
    """ Process zip files one-by-one and collect the outputs into a list. """
    with ZipFile(zip_filename) as archive:
        return [
            process(archive, filename)
            for filename in get_filenames_from_zip_archive(archive)
        ]


def get_filenames_from_zip_archive(archive):
    return [
        info.filename
        for info in archive.infolist()
        if not info.is_dir()
    ]


def merge_files_to_zip(sources, destination):
    """ Merge input files into a single ZIP file. """
    with ZipFile(destination, 'w') as archive:
        for source in sources:
            archive.write(source, basename(source))


def filter_mco_sha_2x(sources):
    """ Filter and sort the input MCO_SHA_2X products. """
    return filter_and_sort_sources(
        sources, "MCO_SHA_2X", MCO_SHA_2X_MAX_ALLOWED_TIME_GAP
    )


def filter_and_sort_sources(sources, product_type, max_gap):

    def _match_product(identifier):
        match = RE_SWARM_SHA_PRODUCT.match(identifier)
        return None if match is None else match.groupdict()

    def _sources_info(sources):
        for source in sources:
            product_id = filename2id(source)
            info = _match_product(product_id)
            if info and info['type'] == product_type:
                info.update({
                    'start': parse_timestamp(info['start']),
                    'end': parse_timestamp(info['end']),
                    'filename': source,
                    'identifier': product_id,
                })
                yield info

    def _sort_key(item):
        return (item['baseline'], item['version'], item['end'], item['start'])

    def _filter_sources(items):
        items = iter(items)
        try:
            item = next(items)
        except StopIteration:
            return
        previous_start = item['start']
        latest_version = (item['baseline'], item['version'])
        yield item
        for item in items:
            # pick the latest version only
            if latest_version != (item['baseline'], item['version']):
                break
            # pick sequence of consecutive products
            current_end = item['end']
            if current_end > previous_start:
                continue
            if previous_start - current_end <= max_gap:
                yield item
                previous_start = item['start']
            else:
                break

    sorted_sources = sorted(_sources_info(sources), key=_sort_key, reverse=True)
    filtered_sources = list(_filter_sources(iter(sorted_sources)))
    return [item['filename'] for item in reversed(filtered_sources)]


def parse_timestamp(datetime_str):
    """ Parse product timestamp. """
    return datetime.strptime(datetime_str, '%Y%m%dT%H%M%S')


def filename2id(filename):
    """ Turn product filename into an identifier. """
    return splitext(basename(filename))[0]
