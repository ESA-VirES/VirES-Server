#-------------------------------------------------------------------------------
#
# VirES HAPI - time-series reader
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021-2023 EOX IT Services GmbH
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
# pylint: disable=too-few-public-methods

from vires.data.vires_settings import DEFAULT_MISSION
from vires.processes.util import VariableResolver
from vires.processes.util.models import generate_magnetic_model_sources
from vires.processes.util.time_series import ProductTimeSeries
from vires.cdf_util import CDF_TIME_TYPES, cdf_rawtime_to_datetime64
from .data_type import parse_data_type, TIME_PRECISION
from .magnetic_model import parse_model_list


class TimeSeries:
    """ Product time-series class - wrapper around the WPS TimeSeries """
    CHUNK_SIZE = 10800 # equivalent of 3h of 1Hz data

    def __init__(self, collection, dataset_id, options, logger=None):

        self.master = ProductTimeSeries(
            collection=collection,
            dataset_id=dataset_id,
            logger=logger
        )

        spacecraft = (
            collection.metadata.get("mission") or DEFAULT_MISSION,
            collection.metadata.get("spacecraft")
        )

        # magnetic models and residuals
        requested_models, source_models = self._parse_models(
            options.get("magneticModels") or []
        )

        self.models = list(generate_magnetic_model_sources(
            *spacecraft, requested_models, source_models,
            no_cache=False, master=self.master,
        ))

    def subset(self, start, stop, parameters):
        """ Iterate chunks of the extracted data. """
        resolver = self._resolve_variables(list(parameters))

        datasets = resolver.master.subset(start, stop, resolver.required)
        datasets = self._interpolate_slave_datasets(datasets, resolver)
        datasets = self._split_datasets_to_chunks(datasets)
        datasets = self._evaluate_model_datasets(datasets, resolver)

        yield from self._finalize_datasets(datasets, parameters)

    def _resolve_variables(self, variables):
        resolver = VariableResolver()
        resolver.add_master(self.master)
        for model in self.models:
            resolver.add_consumer(model)
        resolver.add_output_variables(variables)
        resolver.reduce()
        return resolver

    @classmethod
    def _finalize_datasets(cls, datasets, parameters):
        output_variables = list(parameters)
        for dataset in datasets:
            dataset = dataset.extract(output_variables)
            dataset = cls._convert_data_types(dataset, parameters)
            yield dataset

    @staticmethod
    def _interpolate_slave_datasets(datasets, resolver):
        time_variable = resolver.master.time_variable
        variables = resolver.required
        for dataset in datasets:
            for slave in resolver.slaves:
                dataset.merge(
                    slave.interpolate(
                        times=dataset[time_variable],
                        variables=variables,
                        interp1d_kinds={},
                        cdf_type=dataset.cdf_type[time_variable],
                    )
                )
            yield dataset

    @staticmethod
    def _evaluate_model_datasets(datasets, resolver):
        variables = resolver.required
        for dataset in datasets:
            for model in resolver.models:
                dataset.merge(model.eval(dataset, variables))
            yield dataset

    @staticmethod
    def _parse_models(models):
        if not models:
            return [], []
        model_list = ", ".join(
            "{name} = {expression}".format(**model) for model in models
        )
        return parse_model_list(model_list)

    @classmethod
    def _split_datasets_to_chunks(cls, datasets):
        """ Yield chunks of the datasets from the passed iterator. """
        for dataset in datasets:
            yield from cls._split_dataset_to_chunks(dataset)

    @classmethod
    def _split_dataset_to_chunks(cls, dataset):
        """ Yield chunks of the passed dataset. """
        size = dataset.length
        for idx_start in range(0, dataset.length, cls.CHUNK_SIZE):
            idx_stop = min(idx_start + cls.CHUNK_SIZE, size)
            yield dataset.subset(slice(idx_start, idx_stop))

    @classmethod
    def _convert_data_types(cls, dataset, parameters):
        for variable, data in dataset.items():
            options = parameters[variable]
            cdf_type = dataset.cdf_type.get(variable)
            if cdf_type in CDF_TIME_TYPES:
                dataset[variable] = data = cls._convert_cdf_time(
                    data, cdf_type, options,
                )
            cls._check_declared_type(variable, data, options)
        return dataset

    @staticmethod
    def _check_declared_type(variable, data, options):
        """ Assert that the extracted data type matches the data type declared
        in parameter's metadata.
        """
        declared = parse_data_type(options)
        if data.dtype != declared.dtype:
            raise TypeError(
                f"{variable}: mismatch between the declared and extracted "
                f"data type! {declared.dtype} != {data.dtype}"
            )

    @staticmethod
    def _convert_cdf_time(data, cdf_type, options):
        """ Covert raw CDF data into the native numpy.datetim64 type. """
        unit = TIME_PRECISION[options.get("timePrecision")]
        dtype = f"datetime64[{unit}]"
        return cdf_rawtime_to_datetime64(data, cdf_type).astype(dtype)
