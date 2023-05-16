#-------------------------------------------------------------------------------
#
# VirES HAPI views - landing page
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

from django.template.defaulttags import register
from django.shortcuts import render
from vires.time_util import format_datetime, parse_duration
from ..dataset import list_public_datasets
from .common import HapiResponse, parse_datetime
from .info import parse_dataset, get_info_response, sort_dataset_definition

TEMPLATE_NAME = "vires/hapi/landing_page.html"

PREFERED_EXAMPLE_DATASET = "SW_OPER_MAGA_LR_1B"
PREFERED_EXAMPLE_PARAMETERS = [
    'Latitude', 'Longitude', 'Radius', 'B_NEC', 'Flags_B',
]

DEFAULT_ORDER = 1000

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


def landing_page(request):
    """ HAPI landing page view. """
    datasets = _get_dataset_infos(list_public_datasets())
    dataset_groups = _group_datasets_by_type(datasets)

    return render(request, TEMPLATE_NAME, dict(
        version=HapiResponse.VERSION,
        datasets=datasets,
        type_groups=dataset_groups,
        example=_get_example_selection(datasets),
    ))


def _get_info(hapi_dataset_id):
    collection, dataset_id, dataset_def = parse_dataset(hapi_dataset_id)
    dataset_def = sort_dataset_definition(dataset_def)
    return {
        **get_info_response(collection, dataset_id, dataset_def),
        "x_dataTypeOrder": collection.type.definition.get("_order", DEFAULT_ORDER),
    }


def _get_dataset_infos(datasets):
    return {dataset: _get_info(dataset) for dataset in datasets}


def _group_datasets_by_type(dataset_infos):
    groups = {}
    order = {}
    for dataset, info in dataset_infos.items():
        type_ = info["x_datasetType"]
        order[type_] = info["x_dataTypeOrder"]
        group = groups.get(type_)
        if not group:
            groups[type_] = group = {}
        group[dataset] = info
    return _order_groups(groups, order)


def _order_groups(groups, order):
    return dict(sorted(groups.items(), key=lambda item: (order[item[0]], item[0])))


def _get_example_selection(datasets):
    if not datasets:
        return None

    dataset = None
    parameters = None

    if PREFERED_EXAMPLE_DATASET in datasets:
        dataset = PREFERED_EXAMPLE_DATASET
        parameters = ",".join(PREFERED_EXAMPLE_PARAMETERS or [])
    elif datasets:
        dataset = next(iter(datasets))

    start = datasets[dataset]["startDate"]
    stop = format_datetime(
        parse_datetime(start) +
        parse_duration(datasets[dataset]["cadence"]) * 10
    )

    return dict(dataset=dataset, parameters=parameters, start=start, stop=stop)
