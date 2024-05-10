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
from datetime import timedelta
from django.core.validators import RegexValidator
from django.db.models import (
    Model, ForeignKey, BooleanField, CharField, DateTimeField, BigIntegerField,
    TextField, Index, DurationField, Q,
    CASCADE as ON_DELETE_CASCADE,
    PROTECT as ON_DELETE_PROTECT,
    DO_NOTHING as ON_DELETE_DO_NOTHING,
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
DO_NOTHING = dict(on_delete=ON_DELETE_DO_NOTHING)


def get_user(username):
    """ Get the User object for the given username.
    Returns None if the username is None.
    """
    return None if username is None else User.objects.get(username=username)


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


class Spacecraft(Model):
    mission = CharField(max_length=64, **MANDATORY)
    spacecraft = CharField(max_length=32, **OPTIONAL)
    metadata = JSONField(default=dict, **MANDATORY)

    def __str__(self):
        return self.as_string

    class Meta:
        unique_together = ('mission', 'spacecraft')

    @property
    def as_tuple(self):
        """ Get mission/spacecraft tuple. """
        return (self.mission, self.spacecraft)

    @property
    def as_dict(self):
        """ Get mission/spacecraft tuple. """
        result = {"mission": self.mission}
        if self.spacecraft:
            result["spacecraft"] = self.spacecraft
        return result

    @property
    def as_string(self):
        """ Get mission/spacecraft string. """
        return (
            f"{self.mission}-{self.spacecraft}"
            if self.spacecraft else self.mission
        )


class ProductType(Model):
    identifier = CharField(max_length=64, validators=[ID_VALIDATOR], **MANDATORY, **UNIQUE)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    definition = JSONField(**MANDATORY)

    def __str__(self):
        return self.identifier

    class Meta:
        verbose_name = "Product Type"
        verbose_name_plural = "Product Types"

    @property
    def file_type(self):
        """ Get product file type. """
        return self.definition.get('fileType')

    def get_dataset_id(self, dataset_id=None):
        """ Get dataset identifier.  If the dataset_id parameter is set to None
        then the default dataset identifier is returned.
        """
        return self.default_dataset_id if dataset_id is None else dataset_id

    def get_base_dataset_id(self, dataset_id):
        """ Get base dataset identifier. The base dataset defines the product
        variables.  If the dataset_id parameters is omitted
        or set to None then the default dataset identifier is returned.
        """
        if dataset_id is not None:
            base_dataset_id, _, _ = dataset_id.partition(':')
            datasets = self.definition['datasets']
            if base_dataset_id in datasets:
                return base_dataset_id
        return self.default_dataset_id

    def is_valid_dataset_id(self, dataset_id):
        """ Return true for a valid dataset identifier. """
        return (
            not self.definition.get('strictDatasetCheck', True) or
            dataset_id in self.definition['datasets']
        )

    def get_dataset_definition(self, dataset_id):
        """ Get dataset definition matched by the given identifier. """
        datasets = self.definition['datasets']
        return datasets.get(self.get_base_dataset_id(dataset_id))

    def get_hapi_options(self, dataset_id):
        """ Get dataset definition matched by the given identifier. """
        options = self.definition.get('hapiOptions') or {}
        return options.get(self.get_base_dataset_id(dataset_id)) or {}

    @property
    def default_dataset_id(self):
        return self.definition.get('defaultDataset')


class ProductCollection(Model):
    identifier = CharField(max_length=256, validators=[ID_VALIDATOR], **MANDATORY, **UNIQUE)
    type = ForeignKey(ProductType, related_name='collections', **MANDATORY, **PROTECT)
    spacecraft = ForeignKey(Spacecraft, related_name='collections', **OPTIONAL, **PROTECT)
    grade = CharField(max_length=128, **OPTIONAL)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    max_product_duration = DurationField(default=timedelta(0), **MANDATORY)
    metadata = JSONField(default=dict, **MANDATORY)

    def __str__(self):
        return self.identifier

    @property
    def spacecraft_tuple(self):
        """ Get mission/spacecraft tuple. """
        return self.spacecraft.as_tuple if self.spacecraft else (None, None)

    @property
    def spacecraft_dict(self):
        """ Get mission/spacecraft tuple. """
        return self.spacecraft.as_dict if self.spacecraft else {}

    @property
    def spacecraft_string(self):
        """ Get mission/spacecraft string. """
        return self.spacecraft.as_string if self.spacecraft else (None, None)

    @classmethod
    def select_permitted(cls, permissions):
        query = cls.objects.prefetch_related('type')
        if permissions is None:
            return query
        return query.filter(
            Q(metadata__requiredPermission__isnull=True)|
            Q(metadata__requiredPermission__in=permissions)
        )

    @classmethod
    def select_public(cls):
        """ Select public collections allowing unauthenticated access. """
        query = cls.objects.prefetch_related('type')
        return query.filter(metadata__requiredPermission__isnull=True)

    class Meta:
        verbose_name = "Product Collection"
        verbose_name_plural = "Product Collections"


class Product(Model):
    identifier = CharField(max_length=256, **MANDATORY)
    collection = ForeignKey(ProductCollection, related_name='products', **MANDATORY, **PROTECT)
    begin_time = DateTimeField(**MANDATORY)
    end_time = DateTimeField(**MANDATORY)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    metadata = JSONField(default=dict, **MANDATORY)
    datasets = JSONField(default=dict, **MANDATORY)

    def __str__(self):
        return self.identifier

    class Meta:
        unique_together = ('collection', 'identifier')
        indexes = [
            Index(fields=['collection', 'begin_time']),
            Index(fields=['collection', 'end_time']),
        ]

    def set_location(self, dataset_id, location):
        _datasets = self.datasets or {}
        _dataset = _datasets.setdefault(dataset_id, {})
        _dataset['location'] = location
        self.datasets = _datasets

    def has_dataset(self, dataset_id):
        return dataset_id in self.datasets

    def get_dataset(self, dataset_id):
        return self.datasets.get(dataset_id) or {}

    def get_location(self, dataset_id):
        return self.get_dataset(dataset_id).get('location')

    def get_index_range(self, dataset_id):
        return self.get_dataset(dataset_id).get('indexRange') or [0, None]


class ProductLocation(Model):
    # View DB table not managed by Django. See the migrations for more details.

    id = BigIntegerField(primary_key=True)
    product = ForeignKey(Product, related_name='+', **DO_NOTHING)
    location = CharField(max_length=1024)

    def save(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    class Meta:
        managed = False
        db_table = 'vires_productlocation'


class CachedMagneticModel(Model):
    collection = ForeignKey(
        ProductCollection,
        related_name='cached_magnetic_models',
        **MANDATORY,
        **PROTECT,
    )
    name = CharField(max_length=128, **MANDATORY)
    expression = CharField(max_length=1024, **MANDATORY)
    metadata = JSONField(default=dict, **MANDATORY)

    def __str__(self):
        return f"{self.name}={self.expression}"

    class Meta:
        unique_together = ('collection', 'name')
        unique_together = ('collection', 'expression')
