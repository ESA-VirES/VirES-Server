#-------------------------------------------------------------------------------
#
# VirES specific Djnago DB models.
#
# Project: VirES
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
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

#pylint: disable=missing-docstring,fixme,unused-argument
#pylint: disable=old-style-class,no-init,too-few-public-methods

from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db.models import (
    Model, ForeignKey, CharField, DateTimeField,
)
from django.contrib.gis import geos
from django.contrib.gis.db.models import (
    GeoManager, MultiLineStringField,
)
from django.contrib.auth.models import User

from eoxserver.resources.coverages.models import (
    collect_eo_metadata, Collection, Coverage, EO_OBJECT_TYPE_REGISTRY
)
from vires.util import get_total_seconds


class Job(Model):
    """ VirES WPS asynchronous job.
    """
    owner = ForeignKey(User, related_name='jobs', null=False, blank=False)
    identifier = CharField(max_length=256, null=False, blank=False)
    process_id = CharField(max_length=256, null=False, blank=False)
    response_url = CharField(max_length=512, null=False, blank=False)
    created = DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "WPS Job"
        verbose_name_plural = "WPS Jobs"

    def __unicode__(self):
        return "%s:%s" % (self.process_id, self.identifier)


class Product(Coverage):
    objects = GeoManager()
    ground_path = MultiLineStringField(null=True, blank=True)

    # TODO: Get rid of the incorrect resolution time
    @property
    def resolution_time(self):
        return (self.end_time - self.begin_time) / self.size_x

    @property
    def sampling_period(self):
        if self.size_x > 1:
            return (self.end_time - self.begin_time) / (self.size_x - 1)
        else:
            return timedelta(0)

    @property
    def duration(self):
        return self.end_time - self.begin_time

EO_OBJECT_TYPE_REGISTRY[201] = Product


class ProductCollection(Product, Collection):
    objects = GeoManager()

    class Meta:
        verbose_name = "Product Collection"
        verbose_name_plural = "Product Collections"

    def perform_insertion(self, eo_object, through=None):
        if eo_object.real_type != Product:
            raise ValidationError("In a %s only %s can be inserted." % (
                ProductCollection._meta.verbose_name,
                Product._meta.verbose_name_plural
            ))

        product = eo_object.cast()

        if len(self):
            # TODO: needs to be reviewed
            #if self.resolution_time != product.resolution_time:
            #    raise ValidationError(
            #        "%s has a different temporal resolution as %s" % (
            #            self, product
            #        )
            #    )
            sampling_period = self.sampling_period
            #ground_path = self.ground_path.union(product.ground_path)
        else:
            sampling_period = product.sampling_period
            #ground_path = product.ground_path

        if self.begin_time and self.end_time and self.footprint:
            self.begin_time = min(self.begin_time, product.begin_time)
            self.end_time = max(self.end_time, product.end_time)
            footprint = self.footprint.union(product.footprint)
            self.footprint = geos.MultiPolygon(
                geos.Polygon.from_bbox(footprint.extent)
            )
        else:
            self.begin_time, self.end_time, self.footprint = collect_eo_metadata(
                self.eo_objects.all(), insert=[eo_object], bbox=True
            )
        self.size_x = 1 + int(round(
            get_total_seconds(self.duration) /
            get_total_seconds(sampling_period)
        ))
        #self.ground_path = ground_path
        self.save()

EO_OBJECT_TYPE_REGISTRY[210] = ProductCollection


class ForwardModel(Coverage):
    objects = GeoManager()

EO_OBJECT_TYPE_REGISTRY[250] = ForwardModel
