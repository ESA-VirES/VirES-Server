#-------------------------------------------------------------------------------
#
# Models parser - tests
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
#pylint: disable=missing-docstring,too-many-public-methods,invalid-name

from unittest import TestCase, main
from vires.parsers.exceptions import ParserError
from vires.parsers.models_parser import get_models_parser
from vires.parsers.models_lexer import get_models_lexer


class TestModelsParser(TestCase):

    def _test_parser(self, input_, output):
        lexer = get_models_lexer()
        parser = get_models_parser()
        raw_result = parser.parse(input_, lexer=lexer)
        result = [
            (id_, [(comp_id, dict(params)) for comp_id, params in components])
            for id_, components in raw_result
        ]
        self.assertEqual(result, output)

    def _test_parser_error(self, input_):
        lexer = get_models_lexer()
        parser = get_models_parser()
        with self.assertRaises(ParserError):
            parser.parse(input_, lexer=lexer)
            list(lexer)

    def test_empty_list(self):
        self._test_parser("\t\r\n ", [])

    def test_one_model_id(self):
        self._test_parser("MODEL-1", [("MODEL-1", [("MODEL-1", {})])])

    def test_one_model_id_quoted_single(self):
        self._test_parser("'MODEL-1'", [("MODEL-1", [("MODEL-1", {})])])

    def test_one_model_id_quoted_double(self):
        self._test_parser('"MODEL-1"', [("MODEL-1", [("MODEL-1", {})])])

    def test_many_model_ids(self):
        self._test_parser(
            "MODEL-1, 'MODEL-2', \"MODEL-3\", MODEL-4",
            [
                ("MODEL-1", [("MODEL-1", {})]),
                ("MODEL-2", [("MODEL-2", {})]),
                ("MODEL-3", [("MODEL-3", {})]),
                ("MODEL-4", [("MODEL-4", {})]),
            ]
        )

    def test_empty_list_invalid_extra_comma(self):
        self._test_parser_error(",")

    def test_empty_list_invalid_extra_commas(self):
        self._test_parser_error(",,")

    def test_non_model_invalid_extra_comma_before(self):
        self._test_parser_error(",MODEL-1")

    def test_non_model_invalid_extra_commas_before(self):
        self._test_parser_error(",,MODEL-1")

    def test_non_model_invalid_extra_comma_after(self):
        self._test_parser_error("MODEL-1,")

    def test_invalid_list_extra_commas_after(self):
        self._test_parser_error("MODEL-1, MODEL-2,,")

    def test_invalid_list_extra_comma_middle(self):
        self._test_parser_error("MODEL-1,,MODEL-2")

    def test_invalid_list_extra_commas_middle(self):
        self._test_parser_error("MODEL-1,,,MODEL-2")

    def test_invalid_list_no_comma(self):
        self._test_parser_error("MODEL-1 MODEL-2")

    def test_invalid_list_no_comma_first(self):
        self._test_parser_error("MODEL-1 MODEL-2, MODEL-3")

    def test_invalid_list_no_comma_last(self):
        self._test_parser_error("MODEL-1 MODEL-2, MODEL-3")

    def test_invalid_list_no_comma_middle(self):
        self._test_parser_error("MODEL-1, MODEL-2 MODEL-3, MODEL-4")

    def test_assigned_model_simple(self):
        self._test_parser('MODEL-1=MODEL', [('MODEL-1', [('MODEL', {})])])

    def test_assigned_model_simple_single_quoted(self):
        self._test_parser("MODEL-1='MODEL-2'", [('MODEL-1', [('MODEL-2', {})])])

    def test_assigned_model_simple_double_quoted(self):
        self._test_parser('MODEL-1="MODEL-2"', [('MODEL-1', [('MODEL-2', {})])])

    def test_assigned_model_simple_empty_params(self):
        self._test_parser('MODEL-1=MODEL()', [('MODEL-1', [('MODEL', {})])])

    def test_assigned_model_simple_with_params(self):
        self._test_parser(
            'MODEL-1=MODEL(max_degree=10, min_degree=20)',
            [('MODEL-1', [('MODEL', {'max_degree': 10, 'min_degree': 20})])]
        )

    def test_invalid_assigned_model_simple_with_params_trailing_comma(self):
        self._test_parser_error(
            'MODEL-1=MODEL(max_degree=10, min_degree=20,)'
        )

    def test_invalid_assigned_model_simple_with_params_duplicate(self):
        self._test_parser_error(
            'MODEL-1=MODEL(max_degree=10, max_degree=20)'
        )

    def test_invalid_assigned_model_simple_with_params_no_id(self):
        self._test_parser_error('MODEL-1=MODEL(=10)')

    def test_invalid_assigned_model_simple_with_params_invalid_id(self):
        self._test_parser_error('MODEL-1=MODEL(a=10)')

    def test_invalid_assigned_model_simple_with_params_double_assign(self):
        self._test_parser_error('MODEL-1=MODEL(max_degree ==10)')

    def test_invalid_assigned_model_simple_with_params_no_assign(self):
        self._test_parser_error('MODEL-1=MODEL(max_degree 10)')

    def test_assigned_model_composed_with_params(self):
        self._test_parser(
            'MODEL1_NEW = MODEL1(min_degree=10, max_degree=20) '
            '+ "MODEL2"(max_degree=1) - \'MODEL3\'(min_degree=1), '
            'MODEL2_NEW = MODEL1 - "MODEL2" + \'MODEL3\'',
            [
                ('MODEL1_NEW', [
                    ('MODEL1', {'min_degree': 10, 'max_degree': 20}),
                    ('MODEL2', {'max_degree': 1}),
                    ('MODEL3', {'min_degree': 1, 'scale': -1}),
                ]),
                ('MODEL2_NEW', [
                    ('MODEL1', {}),
                    ('MODEL2', {'scale': -1}),
                    ('MODEL3', {}),
                ]),
            ]
        )


if __name__ == "__main__":
    main()
