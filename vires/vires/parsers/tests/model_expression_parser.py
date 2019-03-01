#-------------------------------------------------------------------------------
#
# Model expression parser - tests
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
from vires.parsers.model_expression_parser import get_model_expression_parser
from vires.parsers.model_expression_lexer import get_model_expression_lexer


class TestModelExpressionParser(TestCase):

    def _test_parser(self, input_, output):
        lexer = get_model_expression_lexer()
        parser = get_model_expression_parser()
        raw_result = parser.parse(input_, lexer=lexer)
        result = [(comp_id, dict(params)) for comp_id, params in raw_result]
        self.assertEqual(result, output)

    def _test_parser_error(self, input_):
        lexer = get_model_expression_lexer()
        parser = get_model_expression_parser()
        with self.assertRaises(ParserError):
            parser.parse(input_, lexer=lexer)

    def test_invalid_empty_string(self):
        self._test_parser_error("\t\r\n ")

    def test_model_id(self):
        self._test_parser("MODEL1", [("MODEL1", {})])

    def test_model_id_with_leading_plus(self):
        self._test_parser("+MODEL1", [("MODEL1", {})])

    def test_model_id_with_leading_minus(self):
        self._test_parser("-MODEL1", [("MODEL1", {'scale': -1})])

    def test_model_id_quoted_single(self):
        self._test_parser("'MODEL-1'", [("MODEL-1", {})])

    def test_model_id_quoted_double(self):
        self._test_parser('"MODEL-1"', [("MODEL-1", {})])

    def test_invalid_many_model_ids(self):
        self._test_parser_error("MODEL-1, 'MODEL-2', \"MODEL-3\", MODEL-4")

    def test_invalid_space_in_id(self):
        self._test_parser_error("MODEL ID")

    def test_invalid_assigned_model(self):
        self._test_parser_error('MODEL-1=MODEL')

    def test_model_with_params(self):
        self._test_parser(
            'MODEL(max_degree=10, min_degree=20)',
            [('MODEL', {'max_degree': 10, 'min_degree': 20})]
        )

    def test_invalid_model_with_params_trailing_comma(self):
        self._test_parser_error('MODEL(max_degree=10, min_degree=20,)')

    def test_invalid_model_with_params_duplicate(self):
        self._test_parser_error('MODEL(max_degree=10, max_degree=20)')

    def test_invalid_model_with_params_no_id(self):
        self._test_parser_error('MODEL(=10)')

    def test_invalid_model_with_params_invalid_id(self):
        self._test_parser_error('MODEL(a=10)')

    def test_invalid_model_with_params_double_assign(self):
        self._test_parser_error('MODEL(max_degree ==10)')

    def test_invalid_model_with_params_no_assign(self):
        self._test_parser_error('MODEL(max_degree 10)')

    def test_model_composed_with_leading_plus(self):
        self._test_parser(
            "+MODEL1-MODEL2+MODEL3",
            [
                ("MODEL1", {}),
                ("MODEL2", {'scale': -1}),
                ("MODEL3", {}),
            ]
        )

    def test_model_composed_with_leading_minus(self):
        self._test_parser(
            "-MODEL1+MODEL2-MODEL3",
            [
                ("MODEL1", {'scale': -1}),
                ("MODEL2", {}),
                ("MODEL3", {'scale': -1}),
            ]
        )

    def test_model_composed_with_params(self):
        self._test_parser(
            'MODEL1(min_degree=10, max_degree=20) '
            '+ "MODEL2"(max_degree=1) - \'MODEL3\'(min_degree=1)',
            [
                ('MODEL1', {'min_degree': 10, 'max_degree': 20}),
                ('MODEL2', {'max_degree': 1}),
                ('MODEL3', {'min_degree': 1, 'scale': -1}),
            ]
        )


if __name__ == "__main__":
    main()
