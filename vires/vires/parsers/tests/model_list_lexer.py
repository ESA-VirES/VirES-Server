#-------------------------------------------------------------------------------
#
# Models lexer - tests
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
#pylint: disable=missing-docstring,invalid-name,too-many-public-methods

from unittest import TestCase, main
from vires.parsers.exceptions import ParserError
from vires.parsers.model_list_lexer import get_model_list_lexer


class TestModelListLexer(TestCase):

    def _test_lexer(self, input_, output):
        lexer = get_model_list_lexer()
        lexer.input(input_)
        tokens = [(token.type, token.value) for token in lexer]
        self.assertEqual(tokens, output)

    def _test_lexer_error(self, input_):
        lexer = get_model_list_lexer()
        lexer.input(input_)
        with self.assertRaises(ParserError):
            list(lexer)

    def test_one_model_id(self):
        self._test_lexer("_MODEL-1", [('model_id', '_MODEL-1')])

    def test_one_model_id_invalid_too_long(self):
        self._test_lexer_error("X"*129)

    def test_one_model_id_quoted_single(self):
        self._test_lexer("'_MODEL-1'", [('model_id', '_MODEL-1')])

    def test_one_model_id_quoted_single_invalid(self):
        self._test_lexer_error("'MODEL 1'")

    def test_one_model_id_quoted_single_invalid_too_long(self):
        self._test_lexer_error("'" + "X"*129 + "'")

    def test_one_model_id_quoted_single_missing_end_quote(self):
        self._test_lexer_error("'MODEL-1")

    def test_one_model_id_quoted_double(self):
        self._test_lexer('"MODEL-1"', [('model_id', 'MODEL-1')])

    def test_one_model_id_quoted_double_invalid(self):
        self._test_lexer_error('"MODEL 1"')

    def test_one_model_id_quoted_double_invalid_too_long(self):
        self._test_lexer_error('"' + "X"*129 + '"')

    def test_one_model_id_quoted_double_missing_end_quote(self):
        self._test_lexer_error('"MODEL-1')

    def test_one_model_id_assigned_one_model_simple(self):
        self._test_lexer(
            "MODEL = _MODEL1",
            [
                ('model_id', 'MODEL'),
                ('assign', '='),
                ('model_id', '_MODEL1'),
            ]
        )

    def test_one_model_id_assigned_one_model_quoted_single(self):
        self._test_lexer(
            "MODEL = '_MODEL-1'",
            [
                ('model_id', 'MODEL'),
                ('assign', '='),
                ('model_id', '_MODEL-1'),
            ]
        )

    def test_one_model_id_assigned_one_model_quoted_double(self):
        self._test_lexer(
            'MODEL = "_MODEL-1"',
            [
                ('model_id', 'MODEL'),
                ('assign', '='),
                ('model_id', '_MODEL-1'),
            ]
        )

    def test_one_model_id_assigned_invalid_too_long(self):
        self._test_lexer_error("MODEL = " + "X"*129)

    def test_one_model_id_assigned_invalid_id(self):
        self._test_lexer_error("MODEL = MODEL-1")

    def test_one_model_id_assigned_invalid_id_single_quote(self):
        self._test_lexer_error("MODEL = 'MODEL-1")

    def test_one_model_id_assigned_invalid_id_double_quote(self):
        self._test_lexer_error('MODEL = "MODEL-1')

    def test_one_model_id_assigned_quoted_single_invalid_too_long(self):
        self._test_lexer_error("MODEL = " + "'" + "X"*129 + "'")

    def test_one_model_id_assigned_quoted_double_invalid_too_long(self):
        self._test_lexer_error("MODEL = " + '"' + "X"*129 + '"')

    def test_one_model_id_assigned_one_model(self):
        self._test_lexer(
            "MODEL = 'MODEL-1'",
            [
                ('model_id', 'MODEL'),
                ('assign', '='),
                ('model_id', 'MODEL-1'),
            ]
        )

    def test_one_model_id_assigned_model_with_params(self):
        self._test_lexer(
            "MODEL = 'MODEL-1'( abc_01 = 0 , b = +123456789, c = -123456789)",
            [
                ('model_id', 'MODEL'),
                ('assign', '='),
                ('model_id', 'MODEL-1'),
                ('left_parenthesis', '('),
                ('parameter_id', 'abc_01'),
                ('assign', '='),
                ('integer', 0),
                ('comma', ','),
                ('parameter_id', 'b'),
                ('assign', '='),
                ('integer', 123456789),
                ('comma', ','),
                ('parameter_id', 'c'),
                ('assign', '='),
                ('integer', -123456789),
                ('right_parenthesis', ')')
            ]
        )

    def test_one_model_id_assigned_model_with_params_unclosed(self):
        self._test_lexer_error("MODEL = 'MODEL-1'( abc_01 = 1, ")

    def test_one_model_id_assigned_model_with_params_invalid(self):
        self._test_lexer_error("MODEL = 'MODEL-1'(abc - abc)")

    def test_one_model_id_assigned_model_with_params_int_too_long(self):
        self._test_lexer_error("MODEL = 'MODEL-1'(a = 1234567890)")

    def test_one_model_id_assigned_invalid_param_id_too_long(self):
        self._test_lexer_error("MODEL = M(" + "x"*129 + "= 1)")

    def test_one_model_id_assigned_model_expression(self):
        self._test_lexer(
            "MODEL = MODEL1 + 'MODEL-2' - \"MODEL-3\"",
            [
                ('model_id', 'MODEL'),
                ('assign', '='),
                ('model_id', 'MODEL1'),
                ('plus', '+'),
                ('model_id', 'MODEL-2'),
                ('minus', '-'),
                ('model_id', 'MODEL-3'),
            ]
        )

    def test_one_model_id_assigned_model_expression_dash(self):
        self._test_lexer(
            "MODEL = MODEL-TEST",
            [
                ('model_id', 'MODEL'),
                ('assign', '='),
                ('model_id', 'MODEL'),
                ('minus', '-'),
                ('model_id', 'TEST'),
            ]
        )



    def test_multiple_model_ids(self):
        self._test_lexer(
            "MODEL-1, MODEL-2, MODEL-3",
            [
                ('model_id', 'MODEL-1'),
                ('comma', ','),
                ('model_id', 'MODEL-2'),
                ('comma', ','),
                ('model_id', 'MODEL-3'),
            ]
        )

    def test_multiple_model_ids_quoted(self):
        self._test_lexer(
            "MODEL-1, 'MODEL-2', \"MODEL-3\"",
            [
                ('model_id', 'MODEL-1'),
                ('comma', ','),
                ('model_id', 'MODEL-2'),
                ('comma', ','),
                ('model_id', 'MODEL-3'),
            ]
        )

    def test_multiple_model_ids_complex(self):
        self._test_lexer(",\n".join([
            "MODEL-3 = 'MODEL-2' - 'MODEL-2'(a=2, b=3)",
            "MODEL-2 = 'MODEL-1' + 'MODEL-2'(a=2, b=3)",
            "MODEL-1 = 'MODEL-0'(a=1, b=2)",
        ]), [
            ('model_id', 'MODEL-3'),
            ('assign', '='),
            ('model_id', 'MODEL-2'),
            ('minus', '-'),
            ('model_id', 'MODEL-2'),
            ('left_parenthesis', '('),
            ('parameter_id', 'a'),
            ('assign', '='),
            ('integer', 2),
            ('comma', ','),
            ('parameter_id', 'b'),
            ('assign', '='),
            ('integer', 3),
            ('right_parenthesis', ')'),
            ('comma', ','),
            ('model_id', 'MODEL-2'),
            ('assign', '='),
            ('model_id', 'MODEL-1'),
            ('plus', '+'),
            ('model_id', 'MODEL-2'),
            ('left_parenthesis', '('),
            ('parameter_id', 'a'),
            ('assign', '='),
            ('integer', 2),
            ('comma', ','),
            ('parameter_id', 'b'),
            ('assign', '='),
            ('integer', 3),
            ('right_parenthesis', ')'),
            ('comma', ','),
            ('model_id', 'MODEL-1'),
            ('assign', '='),
            ('model_id', 'MODEL-0'),
            ('left_parenthesis', '('),
            ('parameter_id', 'a'),
            ('assign', '='),
            ('integer', 1),
            ('comma', ','),
            ('parameter_id', 'b'),
            ('assign', '='),
            ('integer', 2),
            ('right_parenthesis', ')'),
        ])

if __name__ == "__main__":
    main()
