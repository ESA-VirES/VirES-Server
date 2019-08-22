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
#pylint: disable=old-style-class,no-init,too-few-public-methods,too-many-ancestors

from django.core.exceptions import ValidationError
from django.db.models import (
    Model, ForeignKey, BooleanField, CharField, DateTimeField, BigIntegerField,
    TextField,
)
from django.contrib.gis import geos
from django.contrib.gis.db.models import GeoManager
from django.contrib.auth.models import User

from eoxserver.resources.coverages.models import (
    collect_eo_metadata, Collection, Coverage, EO_OBJECT_TYPE_REGISTRY
)


class Job(Model):
    """ VirES WPS asynchronous job.
    """
    ACCEPTED = 'A'  # Accepted, enqueued for processing
    STARTED = 'R'   # Running, processing in progress
    SUCCEEDED = 'S'  # Successfully finished without errors
    ABORTED = 'T'   # Terminated on user request (reserved for future use)
    FAILED = 'F'    # Failed, an error occurred
    UNDEFINED = 'U' # Unknown undefined state

    STATUS_CHOICES = (
        (ACCEPTED, "ACCEPTED"),
        (STARTED, "STARTED"),
        (SUCCEEDED, "SUCCEEDED"),
        (ABORTED, "ABORTED"),
        (FAILED, "FAILED"),
        (UNDEFINED, "UNDEFINED"),
    )

    owner = ForeignKey(User, related_name='jobs', null=True, blank=True)
    identifier = CharField(max_length=256, null=False, blank=False)
    process_id = CharField(max_length=256, null=False, blank=False)
    response_url = CharField(max_length=512, null=False, blank=False)
    created = DateTimeField(auto_now_add=True)
    started = DateTimeField(null=True)
    stopped = DateTimeField(null=True)
    status = CharField(max_length=1, choices=STATUS_CHOICES, default=UNDEFINED)

    class Meta:
        verbose_name = "WPS Job"
        verbose_name_plural = "WPS Jobs"

    def __unicode__(self):
        return "%s:%s:%s" % (self.process_id, self.identifier, self.status)


class UploadedFile(Model):
    """ Model describing user uploaded file. """
    is_valid = BooleanField(default=True)
    created = DateTimeField(auto_now_add=True)
    identifier = CharField(max_length=64, null=False, blank=False, unique=True)
    filename = CharField(max_length=255, null=False, blank=False)
    location = CharField(max_length=4096, null=False, blank=False)
    size = BigIntegerField(null=False, blank=False)
    content_type = CharField(max_length=64, null=False, blank=False)
    checksum = CharField(max_length=64, null=False, blank=False)
    info = TextField(null=True, blank=True) # optional additional info in JSON

    class Meta:
        abstract = True


class CustomDataset(UploadedFile):
    """ Model describing user uploaded custom dataset. """
    owner = ForeignKey(User, null=True, blank=True)
    start = DateTimeField(null=False, blank=False)
    end = DateTimeField(null=False, blank=False)


class CustomModel(UploadedFile):
    """ Model describing user uploaded custom model. """
    owner = ForeignKey(User, null=True, blank=True)
    start = DateTimeField(null=False, blank=False)
    end = DateTimeField(null=False, blank=False)


class ClientState(Model):
    """ Model describing saved client state. """
    owner = ForeignKey(User, related_name='client_states', null=True, blank=True)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    identifier = CharField(max_length=64, null=False, blank=False, unique=True)
    name = CharField(max_length=256, null=False, blank=False)
    description = TextField(null=True, blank=True)
    state = TextField(null=False, blank=False) # stored JSON


class Product(Coverage):
    objects = GeoManager()

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
        self.save()

EO_OBJECT_TYPE_REGISTRY[210] = ProductCollection
