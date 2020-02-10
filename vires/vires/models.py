#-------------------------------------------------------------------------------
#
# VirES specific Django DB models.
#
# Authors: Martin Paces <martin.paces@eox.at>
#          Fabian Schindler <fabian.schindler@eox.at>
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
#pylint: disable=missing-docstring,unused-argument
#pylint: disable=no-init,too-few-public-methods,too-many-ancestors

import re
from django.core.validators import RegexValidator
from django.db.models import (
    Model, ForeignKey, BooleanField, CharField, DateTimeField, BigIntegerField,
    TextField,
    CASCADE as ON_DELETE_CASCADE,
    PROTECT as ON_DELETE_PROTECT,
)
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import User


ID_VALIDATOR = RegexValidator(
    re.compile(r'^[a-zA-z_][a-zA-Z0-9_]*$'),
    message="Invalid identifier."
)


MANDATORY = dict(null=False, blank=False)
OPTIONAL = dict(null=True, blank=True)
UNIQUE = dict(unique=True)
INDEXED = dict(db_index=True)

CASCADE = dict(on_delete=ON_DELETE_CASCADE)
PROTECT = dict(on_delete=ON_DELETE_PROTECT)


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

    owner = ForeignKey(User, related_name='jobs', **OPTIONAL, **CASCADE)
    identifier = CharField(max_length=256, **MANDATORY, **UNIQUE)
    process_id = CharField(max_length=256, **MANDATORY)
    response_url = CharField(max_length=512, **MANDATORY)
    created = DateTimeField(auto_now_add=True)
    started = DateTimeField(null=True)
    stopped = DateTimeField(null=True)
    status = CharField(max_length=1, choices=STATUS_CHOICES, default=UNDEFINED)

    class Meta:
        verbose_name = "WPS Job"
        verbose_name_plural = "WPS Jobs"

    def __str__(self):
        return "%s:%s:%s" % (self.process_id, self.identifier, self.status)


class UploadedFile(Model):
    """ Model describing user uploaded file. """
    is_valid = BooleanField(default=True)
    created = DateTimeField(auto_now_add=True)
    identifier = CharField(max_length=64, **MANDATORY, **UNIQUE)
    filename = CharField(max_length=255, **MANDATORY)
    location = CharField(max_length=4096, **MANDATORY)
    size = BigIntegerField(**MANDATORY)
    content_type = CharField(max_length=64, **MANDATORY)
    checksum = CharField(max_length=64, **MANDATORY)
    info = JSONField(default=None, **MANDATORY)

    class Meta:
        abstract = True


class CustomDataset(UploadedFile):
    """ Model describing user uploaded custom dataset. """
    owner = ForeignKey(User, **OPTIONAL, **CASCADE)
    start = DateTimeField(**MANDATORY)
    end = DateTimeField(**MANDATORY)


class CustomModel(UploadedFile):
    """ Model describing user uploaded custom model. """
    owner = ForeignKey(User, **OPTIONAL, **CASCADE)
    start = DateTimeField(**MANDATORY)
    end = DateTimeField(**MANDATORY)


class ClientState(Model):
    """ Model describing saved client state. """
    owner = ForeignKey(User, related_name='client_states', **OPTIONAL, **CASCADE)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    identifier = CharField(max_length=64, **MANDATORY, **UNIQUE)
    name = CharField(max_length=256, **MANDATORY)
    description = TextField(**OPTIONAL)
    state = JSONField(**MANDATORY)


class ProductType(Model):
    identifier = CharField(max_length=64, validators=[ID_VALIDATOR], **MANDATORY, **UNIQUE)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    definition = JSONField(**MANDATORY)

    class Meta:
        verbose_name = "Product Type"
        verbose_name_plural = "Product Types"


class ProductCollection(Model):
    identifier = CharField(max_length=256, validators=[ID_VALIDATOR], **MANDATORY, **UNIQUE)
    type = ForeignKey(ProductType, related_name='collections', **MANDATORY, **PROTECT)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    metadata = JSONField(default=dict, **MANDATORY)

    class Meta:
        verbose_name = "Product Collection"
        verbose_name_plural = "Product Collections"


class Product(Model):
    identifier = CharField(max_length=256, **MANDATORY, **UNIQUE)
    collection = ForeignKey(ProductCollection, related_name='products', **MANDATORY, **PROTECT)
    begin_time = DateTimeField(**MANDATORY)
    end_time = DateTimeField(**MANDATORY)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    metadata = JSONField(default=dict, **MANDATORY)
    datasets = JSONField(default=dict, **MANDATORY)

    def set_location(self, dataset_id, location):
        _datasets = self.datasets or {}
        _dataset = _datasets.setdefault(dataset_id, {})
        _dataset['location'] = location
        self.datasets = _datasets

    def get_location(self, dataset_id=None):
        if dataset_id is None:
            dataset_id = self.collection.type.definition['defaultDatadaset']
        return self.datasets[dataset_id]['location']
