#-------------------------------------------------------------------------------
#
# Special data source subtracting data acquired by different satellites.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
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
# pylint: disable=too-many-locals,too-many-instance-attributes

from logging import LoggerAdapter, getLogger
from itertools import chain
from numpy import searchsorted, zeros
from vires.orbit_counter import OrbitCounterReader
from vires.cdf_util import (
    CDF_DOUBLE_TYPE, CDF_EPOCH_TYPE,
    cdf_rawtime_to_datetime, seconds_to_cdf_rawtime, cdf_rawtime_to_seconds,
)
from vires.util import include
from vires.time_util import format_datetime, naive_to_utc
from vires.dataset import Dataset
from vires.cache_util import cache_path
from vires.data.vires_settings import ORBIT_COUNTER_FILE
from .base import Model


class SatSatSubtraction(Model):
    """ Calculation of the inter-spacecraft difference. """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            return '%s: %s' % (self.extra["residual_name"], msg), kwargs

    def __init__(self, master_spacecraft, slave_spacecraft,
                 grouped_collections, logger=None):
        super().__init__()

        if master_spacecraft not in ORBIT_COUNTER_FILE:
            raise ValueError("Invalid master spacecraft %s!" % master_spacecraft)

        if slave_spacecraft not in ORBIT_COUNTER_FILE:
            raise ValueError("Invalid slave spacecraft %s!" % slave_spacecraft)

        self._master_spacecraft = master_spacecraft
        self._slave_spacecraft = slave_spacecraft
        self._collections = grouped_collections

        self._master_orbit_counter = OrbitCounterReader(
            cache_path(ORBIT_COUNTER_FILE[self._master_spacecraft]),
            self.product_set
        )

        self._slave_orbit_counter = OrbitCounterReader(
            cache_path(ORBIT_COUNTER_FILE[self._slave_spacecraft]),
            self.product_set
        )

        self._attr_label = "%s - %s difference of" % (
            master_spacecraft, slave_spacecraft,
        )

        self._dtime_anx = "DeltaAscendingNodeTime_%s%s" % (
            master_spacecraft, slave_spacecraft
        )

        self._dtime_anx_attr = {
            'DESCRIPTION': (
                'Difference (%s - %s) of the times of the closest orbit '
                'ascending nodes used in the spacecraft residual '
                'calculation.' % (slave_spacecraft, master_spacecraft)
            ),
            'UNITS': 'sec',
        }

        self._dlat_anx = "DeltaAscendingNodeLongitude_%s%s" % (
            master_spacecraft, slave_spacecraft
        )

        self._dlat_anx_attr = {
            'DESCRIPTION': (
                'Difference (%s - %s) of the longitudes of the closest orbit '
                'ascending nodes used in the spacecraft residual '
                'calculation.' % (slave_spacecraft, master_spacecraft)
            ),
            'UNITS': 'deg',
        }

        var_pairs = tuple(chain.from_iterable(
            pairs for _, pairs in self._collections.values()
        ))

        self._output_variables = tuple(v for v, _ in var_pairs) + (
            self._dtime_anx, self._dlat_anx,
        )

        self._requiered_variables = ("Timestamp", "OrbitNumber") + tuple(
            v for _, v in var_pairs
        )

        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "residual_name": "%s%sResiduals" % (
                master_spacecraft, slave_spacecraft
            )
        })

    @property
    def required_variables(self):
        return self._requiered_variables

    @property
    def variables(self):
        return self._output_variables

    def eval(self, dataset, variables=None, **kwargs):
        output_ds = Dataset()
        variables = self.variables if variables is None else tuple(
            include(variables, self.variables)
        )
        self.logger.debug("requested dataset length %s", dataset.length)
        self.logger.debug("variables: %s", ", ".join(variables))
        if not variables:
            return output_ds # stop if no variable required
        variables = set(variables)

        # get master ANX times and longitudes
        time_master = dataset['Timestamp']
        time_cdf_type = dataset.cdf_type.get('Timestamp')

        if len(time_master) < 1:
            # empty master time line
            if self._dtime_anx in variables:
                output_ds.set(
                    self._dtime_anx, [], CDF_DOUBLE_TYPE, self._dtime_anx_attr,
                )
            if self._dlat_anx in variables:
                output_ds.set(
                    self._dlat_anx, [], CDF_DOUBLE_TYPE, self._dlat_anx_attr,
                )

            for _, (_, var_pairs) in self._collections.items():
                var_pairs = tuple((u, v) for u, v in var_pairs if u in variables)
                for output_var, source_var in var_pairs:
                    cdf_type, cdf_attr = self._delta_cdf_type(
                        dataset.cdf_type[source_var],
                        dict(dataset.cdf_attr.get(source_var, {}))
                    )
                    data = dataset[source_var]
                    output_ds.set(
                        output_var, zeros(data.shape, data.dtype),
                        cdf_type, cdf_attr
                    )
            return output_ds

        start_time = cdf_rawtime_to_datetime(time_master.min(), time_cdf_type)
        stop_time = cdf_rawtime_to_datetime(time_master.max(), time_cdf_type)
        orbcnt_master = self._master_orbit_counter.subset(
            start=start_time, stop=stop_time,
            fields=("orbit", "MJD2000", "phi_AN")
        )

        if orbcnt_master["orbit"].size == 0:
            raise RuntimeError(
                "Failed to read orbit numbers for the selected time interval "
                " %s/%s! The time interval is not covered by the spacecraft %s "
                "orbit counter file!" %
                (
                    format_datetime(naive_to_utc(start_time)),
                    format_datetime(naive_to_utc(stop_time)),
                    self._master_spacecraft
                )
            )

        # get slave ANX times and longitudes
        orbcnt_slave = self._slave_orbit_counter.interpolate(
            time=orbcnt_master["MJD2000"],
            fields=("MJD2000", "phi_AN"),
            kind="nearest",
        )

        # expand time and latitude offsets
        idx = searchsorted(orbcnt_master["orbit"], dataset["OrbitNumber"])

        assert (orbcnt_master["orbit"][idx] == dataset["OrbitNumber"]).all()

        # ANX time difference in seconds
        dtime_anx = 86400 * (orbcnt_master["MJD2000"] - orbcnt_slave["MJD2000"])

        if self._dtime_anx in variables:
            output_ds.set(
                self._dtime_anx, dtime_anx[idx],
                CDF_DOUBLE_TYPE, self._dtime_anx_attr,
            )

        if self._dlat_anx in variables:
            dlat_anx = orbcnt_master["phi_AN"] - orbcnt_slave["phi_AN"]
            dlat_anx[dlat_anx < -180.0] += 360.0
            dlat_anx[dlat_anx > +180.0] -= 360.0
            output_ds.set(
                self._dlat_anx, dlat_anx[idx],
                CDF_DOUBLE_TYPE, self._dlat_anx_attr,
            )

        # traverse the sources and collections and evaluate the residuals
        slave_times = (
            time_master - seconds_to_cdf_rawtime(dtime_anx, time_cdf_type)[idx]
        )

        for col_id, (slave_source, var_pairs) in self._collections.items():
            var_pairs = tuple((u, v) for u, v in var_pairs if u in variables)
            slave_vars = tuple(v for u, v in var_pairs)
            self.logger.debug("%s: %s", col_id, ", ".join(slave_vars))
            slave_ds = slave_source.interpolate(
                slave_times, slave_vars, cdf_type=time_cdf_type
            )
            self.product_set.update(slave_source.product_set)

            for output_var, source_var in var_pairs:
                cdf_type = dataset.cdf_type[source_var]
                data = dataset[source_var] - slave_ds[source_var]
                if cdf_type == CDF_EPOCH_TYPE:
                    data = cdf_rawtime_to_seconds(data, cdf_type)
                cdf_type, cdf_attr = self._delta_cdf_type(
                    cdf_type, dict(dataset.cdf_attr.get(source_var, {}))
                )
                output_ds.set(output_var, data, cdf_type, cdf_attr)

        return output_ds

    def _delta_cdf_type(self, cdf_type, cdf_attr):
        """ Prepare residual CDF type and attributes. """
        if cdf_attr and "DESCRIPTION" in cdf_attr:
            description = cdf_attr["DESCRIPTION"]
            cdf_attr["DESCRIPTION"] = (
                "%s %s" % (self._attr_label, description)
            )
        if cdf_type == CDF_EPOCH_TYPE:
            cdf_type = CDF_DOUBLE_TYPE
            cdf_attr["UNITS"] = "sec"
        return cdf_type, cdf_attr
