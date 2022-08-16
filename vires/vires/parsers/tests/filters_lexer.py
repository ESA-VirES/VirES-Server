#-------------------------------------------------------------------------------
#
# Filters lexer - tests
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2022 EOX IT Services GmbH
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
from numpy import inf, nan
from numpy.testing import assert_equal
from vires.parsers.exceptions import ParserError
from vires.parsers.filters_lexer import get_filters_lexer


class TestModelExpressionLexer(TestCase):

    def _test_lexer(self, input_, output):
        lexer = get_filters_lexer()
        lexer.input(input_)
        tokens = [(token.type, token.value) for token in lexer]
        # Note that self.assertEqual(tokens, output) does not handle NaN.
        try:
            assert_equal(tokens, output)
        except AssertionError as error:
            raise AssertionError(f"{error}\n\n{tokens} != {output}") from None

    def _test_lexer_error(self, input_):
        lexer = get_filters_lexer()
        lexer.input(input_)
        with self.assertRaises(ParserError):
            list(lexer)

    def test_identifier_simple(self):
        self._test_lexer(
            "simple_Id A42 __main__",
            [
                ("identifier", "simple_Id"),
                ('identifier', 'A42'),
                ('identifier', '__main__'),
            ]
        )

    def test_identifier_escaped(self):
        self._test_lexer(
            r"\-A A\-B \42A",
            [
                ("identifier", "-A"),
                ('identifier', 'A-B'),
                ('identifier', '42A'),
            ]
        )

    def test_identifier_too_long(self):
        self._test_lexer_error("A"*129)

    def test_identifier_escaped_long(self):
        self._test_lexer(r"\-"*128, [("identifier", "-"*128)])

    def test_identifier_escaped_too_long(self):
        self._test_lexer_error(r"\-"*129)

    def test_reserved_words(self):
        self._test_lexer(
            r"and Inf NaN True false",
            [
                ("logical_and", "AND"),
                ('float', inf),
                ('float', nan),
                ('bool', True),
                ('bool', False),
            ]
        )

    def test_escaped_reserved_words(self):
        self._test_lexer(
            r"\and \Inf \NaN \True \false",
            [
                ("identifier", "and"),
                ("identifier", "Inf"),
                ("identifier", "NaN"),
                ("identifier", "True"),
                ("identifier", "false"),
            ]
        )

    def test_string_squoted(self):
        self._test_lexer(
            "'ABC' 'A''B''C' ''''",
            [
                ("string", "ABC"),
                ("string", "A'B'C"),
                ("string", "'"),
            ]
        )

    def test_string_squoted_too_long(self):
        self._test_lexer_error("'" + "A"*129 + "'")

    def test_string_squoted_with_quotes_long(self):
        self._test_lexer("'" + "''"*128 + "'", [("string", "'"*128)])

    def test_string_squoted_with_quotes_too_long(self):
        self._test_lexer_error("'" + "''"*129 + "'")

    def test_string_squoted_unfinished(self):
        self._test_lexer_error("'''")

    def test_string_dquoted(self):
        self._test_lexer(
            '"ABC" "A""B""C" """"',
            [
                ("string", 'ABC'),
                ("string", 'A"B"C'),
                ("string", '"'),
            ]
        )

    def test_string_dquoted_unfinished(self):
        self._test_lexer_error('"""')

    def test_string_dquoted_too_long(self):
        self._test_lexer_error('"' + "A"*129 + '"')

    def test_string_dquoted_with_quotes_long(self):
        self._test_lexer('"' + '""'*128 + '"', [("string", '"'*128)])

    def test_string_dquoted_with_quotes_too_long(self):
        self._test_lexer_error('"' + '""'*129 + '"')

    def test_integer(self):
        self._test_lexer(
            "0 +0 -0 5 +400 -245 001 -002 +003",
            [
                ("integer", 0),
                ("integer", 0),
                ("integer", 0),
                ("integer", 5),
                ("integer", 400),
                ("integer", -245),
                ("integer", 1),
                ("integer", -2),
                ("integer", 3),
            ]
        )

    def test_float_decimal(self):
        self._test_lexer(
            "0.0 +0.0 -0.0 5.1 +40.000 -245.123 001.0 -002.0 +003.0",
            [
                ("float", 0.0),
                ("float", +0.0),
                ("float", -0.0),
                ("float", 5.1),
                ("float", 40.0),
                ("float", -245.123),
                ("float", 1.),
                ("float", -2.),
                ("float", 3.),
            ]
        )

    def test_float_traling_dot(self):
        self._test_lexer(
            "0. +0. -0. 5. +400. -245. 001.0 -002.0 +003.0",
            [
                ("float", 0.0),
                ("float", +0.0),
                ("float", -0.0),
                ("float", 5.0),
                ("float", 400.0),
                ("float", -245.0),
                ("float", 1.),
                ("float", -2.),
                ("float", 3.),
            ]
        )

    def test_float_leading_dot(self):
        self._test_lexer(
            ".0 +.0 -.0 .5 +.400 -.245",
            [
                ("float", 0.0),
                ("float", +0.0),
                ("float", -0.0),
                ("float", 0.5),
                ("float", 0.400),
                ("float", -0.2450),
            ]
        )

    def test_float_exponential(self):
        self._test_lexer(
            "1E3 1.e3 +1E+3 +1.0E+3 0e0 -.1E-1 1e300 1E500 "
            "001e3 -002.E-3 +003e+3",
            [
                ("float", 1000.0),
                ("float", 1000.0),
                ("float", 1000.0),
                ("float", 1000.0),
                ("float", 0),
                ("float", -0.01),
                ("float", 1e300),
                ("float", float('inf')),
                ("float", 1000.0),
                ("float", -0.002),
                ("float", 3000.0),
            ]
        )

    def test_non_finite(self):
        self._test_lexer(
            "NaN nan NAN Inf inf INF"
            "+NaN +nan +NAN +Inf +inf +INF"
            "-NaN -nan -NAN -Inf -inf -INF",
            [
                ('float', nan),
                ('float', nan),
                ('float', nan),
                ('float', inf),
                ('float', inf),
                ('float', inf),
                ('float', nan),
                ('float', nan),
                ('float', nan),
                ('float', inf),
                ('float', inf),
                ('float', inf),
                ('float', nan),
                ('float', nan),
                ('float', nan),
                ('float', -inf),
                ('float', -inf),
                ('float', -inf),
            ]
        )

    def test_number_too_long(self):
        self._test_lexer_error("1"*129)

    def test_number_invalid(self):
        self._test_lexer_error("1e3X")

    def test_number_invalid_nan(self):
        self._test_lexer_error("+nanX")

    def test_number_invalid_inf(self):
        self._test_lexer_error("-infX")

    def test_operators(self):
        self._test_lexer(
            "== != < > <= >= & AND OR NOT",
            [
                ('equal', '=='),
                ('not_equal', '!='),
                ('less_than', '<'),
                ('greater_than', '>'),
                ('less_than_or_equal', '<='),
                ('greater_than_or_equal', '>='),
                ('bitwise_and', '&'),
                ('logical_and', 'AND'),
                ('logical_or', 'OR'),
                ('logical_not', 'NOT'),
            ]
        )

    def test_delimiters(self):
        self._test_lexer(
            ": ; , ( )",
            [
                ('colon', ':'),
                ('semicolon', ';'),
                ('comma', ','),
                ('left_round_bracket', '('),
                ('right_round_bracket', ')')
            ]
        )

    def test_array_index(self):
        self._test_lexer(
            "[] [0] [1,2] [3,40,500]",
            [
                ('left_square_bracket', '['),
                ('right_square_bracket', ']'),
                ('left_square_bracket', '['),
                ('index', 0),
                ('right_square_bracket', ']'),
                ('left_square_bracket', '['),
                ('index', 1),
                ('comma', ','),
                ('index', 2),
                ('right_square_bracket', ']'),
                ('left_square_bracket', '['),
                ('index', 3),
                ('comma', ','),
                ('index', 40),
                ('comma', ','),
                ('index', 500),
                ('right_square_bracket', ']')
            ]
        )

    def test_array_index_too_long(self):
        self._test_lexer(
            "[" + "9"*9 + "]",
            [
                ('left_square_bracket',
                '['), ('index', 999999999),
                ('right_square_bracket', ']'),
            ]
        )
        self._test_lexer_error("[" + "9"*10 + "]")

    def test_array_index_missing_closing_square_bracket(self):
        self._test_lexer_error("[")

    def test_array_index_missing_opening_square_bracket(self):
        self._test_lexer_error("]")


if __name__ == "__main__":
    main()
