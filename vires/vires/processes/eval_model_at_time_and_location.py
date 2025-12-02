#-------------------------------------------------------------------------------
#
# Evaluate magnetic model at user provided times and locations
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments
# pylint: disable=too-few-public-methods

#from datetime import datetime
#from io import StringIO
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData,
    FormatText, FormatBinaryRaw, FormatBinaryBase64, FormatJSON,
    CDObject, CDFileWrapper, CDFile,
)
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.config import SystemConfigReader
from vires.model_eval.common import (
    FORMAT_SPECIFIC_TIME_FORMAT,
)
from vires.model_eval.input_data import (
    INPUT_TIME_FORMATS,
    convert_json_input,
    convert_msgpack_input,
    convert_csv_input,
    convert_cdf_input,
    convert_hdf_input,
)
from vires.model_eval.output_data import (
    OUTPUT_TIME_FORMATS,
    enforce_1d_data_shape,
    write_json_output,
    write_msgpack_output,
    write_csv_output,
    write_cdf_output,
    write_hdf_output,
    write_sources,
)
from vires.model_eval.calculation import calculate_model_values
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_model_list,
    get_extra_model_parameters,
)

DEFAULT_FORMAT = FORMAT_SPECIFIC_TIME_FORMAT

DEFAULT_OUTPUT_TIME_FORMAT = DEFAULT_FORMAT
OUTPUT_TIME_FORMATS = [
    "ISO date-time",
    "MJD2000",
    "Unix epoch",
    "Decimal year",
    "CDF_EPOCH",
    "CDF_TIME_TT2000",
    "datetime64[s]",
    "datetime64[ms]",
    "datetime64[us]",
    "datetime64[ns]",
    DEFAULT_FORMAT,
]


class EvalModelAtTimeAndLocation(WPSProcess):
    """ This process evaluates composed magnetic models at user-provided
    times and locations.
    """
    identifier = "vires:eval_model_at_time_and_location"
    tmp_filename_prefix = identifier.replace(":", "_")
    title = "Evaluate model at user provide times and locations"
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("model_ids", LiteralData(
            "model_ids", str, optional=True, default="",
            title="Model identifiers",
            abstract="List of the evaluate geo-magnetic field models.",
        )),
        ("shc", ComplexData(
            "shc", title="SHC file data", optional=True,
            formats=(FormatText("text/plain"),),
            abstract="The custom model coefficients encoded in the SHC format.",
        )),
        ("input_", ComplexData(
            "input", title="Input times and locations.", formats=(
                FormatJSON(),
                FormatText("text/csv"),
                FormatBinaryBase64("application/msgpack"),
                FormatBinaryRaw("application/msgpack"),
                FormatBinaryBase64("application/x-msgpack"),
                FormatBinaryRaw("application/x-msgpack"),
                FormatBinaryBase64("application/cdf"),
                FormatBinaryRaw("application/cdf"),
                FormatBinaryBase64("application/x-cdf"),
                FormatBinaryRaw("application/x-cdf"),
                FormatBinaryBase64("application/x-hdf5"),
                FormatBinaryRaw("application/x-hdf5"),
            )
        )),
        ("input_time_format", LiteralData(
            "input_time_format", str, optional=True, title="input time format",
            abstract="Optional input time format.",
            allowed_values=INPUT_TIME_FORMATS,
            default=FORMAT_SPECIFIC_TIME_FORMAT,
        )),
        ("output_time_format", LiteralData(
            "output_time_format", str, optional=True, title="output time format",
            abstract="Optional output time format.",
            allowed_values=OUTPUT_TIME_FORMATS,
            default=FORMAT_SPECIFIC_TIME_FORMAT,
        )),
    ]

    outputs = [
        ("output", ComplexData(
            "output", title="Calculated output values.", formats=(
                FormatJSON(),
                FormatText("text/csv"),
                FormatBinaryRaw("application/msgpack"),
                FormatBinaryRaw("application/x-msgpack"),
                FormatBinaryRaw("application/cdf"),
                FormatBinaryRaw("application/x-cdf"),
                FormatBinaryRaw("application/x-hdf5"),
            )
        )),
        ("sources", ComplexData(
            "sources", title="Calculated output values.", formats=(
                FormatText("text/plain"),
            )
        )),
    ]

    def execute(self, model_ids, shc,
                input_, output, sources,
                input_time_format,
                output_time_format,
                **kwargs):
        """ Execute process """

        access_logger = self.get_access_logger(**kwargs)

        requested_models, source_models = parse_model_list(
            "model_ids", model_ids, shc
        )

        access_logger.info(
            "request: model: %s,request-format: %s, response-format: %s"
            ", ".join(
                f"{model.name} = {model.expression}"
                for model in requested_models
            ),
            input_.mime_type, output['mime_type']
        )

        try:
            data, input_time_format = self._read_input_data(input_, input_time_format)
        except Exception as error:
            raise InvalidInputValueError(
                "input", f"Failed to read the input data! {error}"
            ) from None

        # some of the output formats support only 1D data
        if output["mime_type"] in (
            "text/csv",
            "application/cdf",
            "application/x-cdf",
        ):
            try:
                data = enforce_1d_data_shape(data)
            except ValueError as error:
                raise InvalidInputValueError(
                    "input", f"Failed to read the input data! {error}"
                ) from None

        data, info = calculate_model_values(
            data, requested_models, source_models,
            get_extra_model_parameters,
        )

        return {
            "output": self._write_output_data(
                data, output, output_time_format, input_time_format, info
            ),
            "sources": self._write_sources(info, sources),
        }

    def _write_sources(self, model_info, sources):
        return CDFileWrapper(
            write_sources(model_info), filename="sources.txt", **sources
        )

    def _read_input_data(self, input_, input_time_format):

        if input_.mime_type == "application/json":
            return convert_json_input(input_.data, input_time_format)

        if input_.mime_type == "text/csv":
            return convert_csv_input(input_, input_time_format)

        if input_.mime_type in ("application/msgpack", "application/x-msgpack"):
            return convert_msgpack_input(input_, input_time_format)

        if input_.mime_type in ("application/cdf", "application/x-cdf"):
            return convert_cdf_input(
                input_, input_time_format,
                filename_prefix=f"{self.tmp_filename_prefix}_input",
                temp_path=SystemConfigReader().path_temp,
            )

        if input_.mime_type == "application/x-hdf5":
            return convert_hdf_input(
                input_, input_time_format,
                filename_prefix=f"{self.tmp_filename_prefix}_input",
                temp_path=SystemConfigReader().path_temp,
            )

        raise ValueError(f"Unexpected input file format! {input_.mime_type}")

    def _write_output_data(self, data, output, output_time_format, input_time_format, model_info):

        output_mime_type = output["mime_type"]
        if output_mime_type == "application/json":
            return CDObject(
                write_json_output(
                    data, output_time_format, input_time_format, model_info
                ),
                filename="output.json", **output
            )

        if output_mime_type == "text/csv":
            return CDFileWrapper(
                write_csv_output(
                    data, output_time_format, input_time_format, model_info
                ),
                filename="output.json", **output
            )

        if output_mime_type in ("application/msgpack", "application/x-msgpack"):
            return CDObject(
                write_msgpack_output(
                    data, output_time_format, input_time_format, model_info
                ),
                filename="output.mp", **output
            )

        if output_mime_type in ("application/cdf", "application/x-cdf"):
            return CDFile(
                write_cdf_output(
                    data, output_time_format, input_time_format, model_info,
                    filename_prefix=f"{self.tmp_filename_prefix}_output",
                    temp_path=SystemConfigReader().path_temp,
                ),
                filename="output.cdf", **output
            )

        if output_mime_type == "application/x-hdf5":
            return CDFile(
                write_hdf_output(
                    data, output_time_format, input_time_format, model_info,
                    filename_prefix=f"{self.tmp_filename_prefix}_output",
                    temp_path=SystemConfigReader().path_temp,
                ),
                filename="output.hdf5", **output
            )

        raise ValueError(f"Unexpected output file format! {output_mime_type}")
