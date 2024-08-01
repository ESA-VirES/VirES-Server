#-------------------------------------------------------------------------------
#
# VirES HAPI - low-level dataset/collection handling
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=missing-docstring,unused-argument

import re
from datetime import timedelta
from django.db.models import Count, Min, Max
from vires.models import ProductCollection

RE_DATASET = re.compile(
    r"^(?P<collection>[A-Za-z0-9_]{1,64})"
    r"(?::(?P<dataset>[A-Za-z0-9_]{1,64}(?::[A-Za-z0-9_]{1,64})?))?$"
)

# maximum allowed time selection period for 1 second sampled data
MAX_TIME_SELECTION = timedelta(days=5)

# maximum timedelta value
MAX_LIMIT = timedelta(days=999999999)


def get_time_limit(selection_limit, nominal_sampling):
    """ Get time-selection limit adapted to the requested data sampling. """
    return timedelta(seconds=min(
        MAX_LIMIT.total_seconds(),
        selection_limit.total_seconds() * nominal_sampling.total_seconds()
    ))


def parse_dataset(requested_dataset):
    """ Parse dataset identifier and return collection and dataset definition
    objects.
    """

    match = RE_DATASET.match(requested_dataset)
    if not match:
        raise ValueError("Invalid datasets identifier!")
    collection_id, dataset_id = match.groups()

    try:
        collection = ProductCollection.select_public().get(identifier=collection_id)
    except ProductCollection.DoesNotExist:
        raise ValueError("Invalid datasets identifier!") from None

    dataset_definition = collection.type.get_dataset_definition(dataset_id)

    if dataset_definition is None:
        raise ValueError("Invalid datasets identifier!")

    options = collection.type.get_hapi_options(dataset_id)
    dataset_definition = _extend_dataset_definition(
        dict(dataset_definition), options
    )

    return collection, dataset_id, dataset_definition, options


def get_public_collections():
    """ Get list of available collection/datasets """
    return (
        ProductCollection
        .select_public()
        .annotate(product_count=Count("products"))
        .filter(product_count__gt=0) # non-empty collections only
        .order_by("identifier")
    )


def get_dataset_time_info(collection, dataset_id):
    return {
        "cadence": collection.get_nominal_sampling(dataset_id),
        **collection.products.aggregate(
            startDate=Min("begin_time"),
            stopDate=Max("end_time"),
        )
    }


def list_public_datasets():
    """ Get list of public datasets. """
    # TODO: handle observatories
    def _public_datasets():
        for collection in get_public_collections():
            type_def = collection.type.definition
            default_dataset = type_def.get("defaultDataset")
            for dataset in type_def["datasets"]:
                if dataset == default_dataset:
                    yield collection.identifier
                else:
                    yield f"{collection.identifier}:{dataset}"
    return list(_public_datasets())


def _extend_dataset_definition(dataset_definition, options):
    """ Extend dataset definition by adding generated parameters. """
    order = len(dataset_definition)

    # resolve magnetic models and residuals
    calculate_field_intensity = options.get("calculateMagneticFieldIntensity", False)
    magnetic_models = options.get("magneticModels") or []
    residuals = options.get("magneticModelResiduals") or []

    if (
        calculate_field_intensity and
        "B_NEC" in dataset_definition and
        "F" not in dataset_definition
    ):
        order += 1
        dataset_definition["F"] = {
            "_order": order,
            "dataType": "float64",
            "attributes": {
                "UNITS": "nT",
                "DESCRIPTION": "Magnetic field intensity calculated from B_NEC",
            }
        }

    for model in magnetic_models:
        name = model["name"]
        description = model["description"]

        order += 1
        dataset_definition[f"B_NEC_{name}"] = {
            "_order": order,
            "dataType": "float64",
            "dimension": [3],
            "attributes": {
                "UNITS": "nT",
                "DESCRIPTION": description,
            }
        }

        if "F" in dataset_definition:
            order += 1
            dataset_definition[f"F_{name}"] = {
                "_order": order,
                "dataType": "float64",
                "attributes": {
                    "UNITS": "nT",
                    "DESCRIPTION": f"{description}, field intensity",
                }
            }

        for parameter in residuals:
            order += 1
            # copy metadata of the measurement record
            measurement = dataset_definition[parameter]
            measurement_description = measurement["attributes"]["DESCRIPTION"]
            residual = dict(measurement)
            residual.update({
                "_order": order,
                "attributes": {
                    "UNITS": "nT",
                    "DESCRIPTION": f"{measurement_description}, {description} residual",
                }
            })
            dataset_definition[f"{parameter}_res_{name}"] = residual

    return dataset_definition
