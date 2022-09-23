#-------------------------------------------------------------------------------
#
# Filters parser - tests
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
#pylint: disable=missing-docstring,too-many-public-methods,invalid-name

from unittest import TestCase, main
from numpy import nan, inf
from numpy.testing import assert_equal
from vires.parsers.exceptions import ParserError
from vires.parsers.filters_parser import get_filters_parser
from vires.parsers.filters_lexer import get_filters_lexer


class TestModelExpressionParser(TestCase):

    def _test_parser(self, input_, output, has_nan=False):
        lexer = get_filters_lexer()
        parser = get_filters_parser()
        result = parser.parse(input_, lexer=lexer)
        # Note that self.assertEqual does not handle NaN and
        # numpy.testing.assert_equal does not handle well nested lists
        try:
            if has_nan:
                assert_equal(result, output)
            else:
                self.assertEqual(result, output)
        except AssertionError as error:
            raise AssertionError(f"{error}\n\n{result} != {output}") from None

    def _test_parser_error(self, input_):
        lexer = get_filters_lexer()
        parser = get_filters_parser()
        with self.assertRaises(ParserError):
            parser.parse(input_, lexer=lexer)

    def test_empty_string(self):
        self._test_parser("", None)

    def test_predicate_conjunction(self):
        self._test_parser(
            "variable1 == 1 AND variable2 != 2",
            ("conjunction", [
                ("equal", ("variable1", ()), 1),
                ("not_equal", ("variable2", ()), 2),
            ])
        )

    def test_nested_predicate_conjunction(self):
        self._test_parser(
            "( variable1 == 1 ) AND ( variable2 != 2 AND variable3 > 3)",
            ("conjunction", [
                ("equal", ("variable1", ()), 1),
                ("not_equal", ("variable2", ()), 2),
                ('greater_than', ('variable3', ()), 3)
            ])
        )

    def test_predicate_conjunction_with_nested_disjunction(self):
        self._test_parser(
            "( variable1 == 1 AND ( variable2 != 2 OR variable3 > 3))",
            ('conjunction', [
                ('equal', ('variable1', ()), 1),
                ('disjunction', [
                    ('not_equal', ('variable2', ()), 2),
                    ('greater_than', ('variable3', ()), 3)
                ])
            ])
        )

    def test_predicate_disjunction(self):
        self._test_parser(
            "variable1 == 1 OR variable2 != 2",
            ("disjunction", [
                ("equal", ("variable1", ()), 1),
                ("not_equal", ("variable2", ()), 2),
            ])
        )

    def test_nested_predicate_disjunction(self):
        self._test_parser(
            "( variable1 == 1 ) OR ( variable2 != 2 OR variable3 > 3)",
            ("disjunction", [
                ("equal", ("variable1", ()), 1),
                ("not_equal", ("variable2", ()), 2),
                ('greater_than', ('variable3', ()), 3)
            ])
        )

    def test_predicate_disjunction_with_nested_conjunction(self):
        self._test_parser(
            "( variable1 == 1 ) OR ( variable2 != 2 AND variable3 > 3)",
            ('disjunction', [
                ('equal', ('variable1', ()), 1),
                ('conjunction', [
                    ('not_equal', ('variable2', ()), 2),
                    ('greater_than', ('variable3', ()), 3)
                ])
            ])
        )

    def test_mixed_conjunction_and_disjunction(self):
        self._test_parser_error("A == 0 AND B == 1 OR C == 2")

    def test_mixed_disjunction_and_conjunction(self):
        self._test_parser_error("A == 0 OR B == 1 AND C == 2")

    def test_negated_simple_predicate(self):
        self._test_parser(
            "NOT variable != 0",
            ('not',
                 ('not_equal', ('variable', ()), 0)
            )
        )

    def test_double_negated_simple_predicate(self):
        self._test_parser(
            "NOT NOT variable != 0",
             ('not_equal', ('variable', ()), 0)
        )

    def test_negated_simple_predicate_with_brackets(self):
        self._test_parser(
            "NOT (variable != 0)",
            ('not',
                 ('not_equal', ('variable', ()), 0)
            )
        )

    def test_negated_conjunction(self):
        self._test_parser(
            "NOT (variable1 != 1 AND variable1 != 2)",
            ('not',
                ('conjunction', [
                    ('not_equal', ('variable1', ()), 1),
                    ('not_equal', ('variable1', ()), 2),
                ])
            )
        )

    def test_negated_disjunction(self):
        self._test_parser(
            "NOT (variable1 == 1 OR variable1 == 2)",
            ('not',
                ('disjunction', [
                    ('equal', ('variable1', ()), 1),
                    ('equal', ('variable1', ()), 2),
                ])
            )
        )

    def test_conjunction_of_negations(self):
        self._test_parser(
            "NOT variable1 == 1 AND NOT variable1 == 2",
            ('conjunction', [
                ('not', ('equal', ('variable1', ()), 1)),
                ('not', ('equal', ('variable1', ()), 2)),
            ])
        )

    def test_disjunction_of_negations(self):
        self._test_parser(
            "NOT variable1 != 1 OR NOT variable1 != 2",
            ('disjunction', [
                ('not', ('not_equal', ('variable1', ()), 1)),
                ('not', ('not_equal', ('variable1', ()), 2)),
            ])
        )

    def test_single_predicate_with_1d_index(self):
        self._test_parser("variable[0] == 1", ("equal", ("variable", (0,)), 1))

    def test_single_predicate_with_2d_index(self):
        self._test_parser("variable[1, 2] == -3", ("equal", ("variable", (1, 2)), -3))

    def test_single_predicate_equal_bool(self):
        self._test_parser("variable == True", ("equal", ("variable", ()), True))

    def test_single_predicate_equal_integer(self):
        self._test_parser("variable == +123", ("equal", ("variable", ()), 123))

    def test_single_predicate_equal_float(self):
        self._test_parser("variable == 1e3", ("equal", ("variable", ()), 1000.0))

    def test_single_predicate_equal_nan(self):
        self._test_parser("variable == NaN", ("equal", ("variable", ()), nan), has_nan=True)

    def test_single_predicate_equal_inf(self):
        self._test_parser("variable == inf", ("equal", ("variable", ()), inf))

    def test_single_predicate_equal_string(self):
        self._test_parser("variable == 'ABC'", ("equal", ("variable", ()), "ABC"))

    def test_single_predicate_not_equal_integer(self):
        self._test_parser("variable != -123", ("not_equal", ("variable", ()), -123))

    def test_single_predicate_not_equal_bool(self):
        self._test_parser("variable != False", ("not_equal", ("variable", ()), False))

    def test_single_predicate_not_equal_float(self):
        self._test_parser("variable != +1.5e-3", ("not_equal", ("variable", ()), 0.0015))

    def test_single_predicate_not_equal_nan(self):
        self._test_parser("variable != NaN", ("not_equal", ("variable", ()), nan), has_nan=True)

    def test_single_predicate_not_equal_inf(self):
        self._test_parser("variable != -inf", ("not_equal", ("variable", ()), -inf))

    def test_single_predicate_not_equal_string(self):
        self._test_parser('variable != "ABC"', ("not_equal", ("variable", ()), "ABC"))

    def test_single_predicate_less_than_bool(self):
        self._test_parser("variable < True", ("less_than", ("variable", ()), True))

    def test_single_predicate_less_than_integer(self):
        self._test_parser("variable < +123", ("less_than", ("variable", ()), 123))

    def test_single_predicate_less_than_float(self):
        self._test_parser("variable < 1e3", ("less_than", ("variable", ()), 1000.0))

    def test_single_predicate_less_than_nan(self):
        self._test_parser("variable < NaN", ("less_than", ("variable", ()), nan), has_nan=True)

    def test_single_predicate_less_than_inf(self):
        self._test_parser("variable < inf", ("less_than", ("variable", ()), inf))

    def test_single_predicate_less_than_string(self):
        self._test_parser_error("variable < 'ABC'")

    def test_single_predicate_less_than_identifier(self):
        self._test_parser_error("variable1 < variable2")

    def test_single_predicate_greater_than_bool(self):
        self._test_parser("variable > False", ("greater_than", ("variable", ()), False))

    def test_single_predicate_greater_than_integer(self):
        self._test_parser("variable > -123", ("greater_than", ("variable", ()), -123))

    def test_single_predicate_greater_than_float(self):
        self._test_parser("variable > -1e+3", ("greater_than", ("variable", ()), -1000.0))

    def test_single_predicate_greater_than_nan(self):
        self._test_parser("variable > -NaN", ("greater_than", ("variable", ()), nan), has_nan=True)

    def test_single_predicate_greater_than_inf(self):
        self._test_parser("variable > -inf", ("greater_than", ("variable", ()), -inf))

    def test_single_predicate_greater_than_string(self):
        self._test_parser_error("variable > 'ABC'")

    def test_single_predicate_greater_than_variable(self):
        self._test_parser_error("variable1 > variable2")

    def test_single_predicate_less_than_or_equal_bool(self):
        self._test_parser("variable <= True", ("less_than_or_equal", ("variable", ()), True))

    def test_single_predicate_less_than_or_equal_integer(self):
        self._test_parser("variable <= +123", ("less_than_or_equal", ("variable", ()), 123))

    def test_single_predicate_less_than_or_equal_float(self):
        self._test_parser("variable <= 1e3", ("less_than_or_equal", ("variable", ()), 1000.0))

    def test_single_predicate_less_than_or_equal_nan(self):
        self._test_parser("variable <= NaN", ("less_than_or_equal", ("variable", ()), nan), has_nan=True)

    def test_single_predicate_less_than_or_equal_inf(self):
        self._test_parser("variable <= inf", ("less_than_or_equal", ("variable", ()), inf))

    def test_single_predicate_less_than_or_equal_string(self):
        self._test_parser_error("variable <= 'ABC'")

    def test_single_predicate_less_than_or_equal_variable(self):
        self._test_parser_error("variable1 <= variable2")

    def test_single_predicate_greater_than_or_equal_bool(self):
        self._test_parser("variable >= False", ("greater_than_or_equal", ("variable", ()), False))

    def test_single_predicate_greater_than_or_equal_integer(self):
        self._test_parser("variable >= -123", ("greater_than_or_equal", ("variable", ()), -123))

    def test_single_predicate_greater_than_or_equal_float(self):
        self._test_parser("variable >= -1e+3", ("greater_than_or_equal", ("variable", ()), -1000.0))

    def test_single_predicate_greater_than_or_equal_nan(self):
        self._test_parser("variable >= -NaN", ("greater_than_or_equal", ("variable", ()), nan), has_nan=True)

    def test_single_predicate_greater_than_or_equal_inf(self):
        self._test_parser("variable >= -inf", ("greater_than_or_equal", ("variable", ()), -inf))

    def test_single_predicate_greater_than_or_equal_string(self):
        self._test_parser_error("variable >= 'ABC'")

    def test_single_predicate_greater_than_or_equal_variable(self):
        self._test_parser_error("variable1 >= variable2")

    def test_single_bitmask_equal(self):
        self._test_parser("variable & 127 == 65", ("bitmask_equal", ("variable", ()), 127, 65))

    def test_single_bitmask_not_equal(self):
        self._test_parser("variable & 127 != 65", ("bitmask_not_equal", ("variable", ()), 127, 65))

    def test_single_bitmask_equal_with_float(self):
        self._test_parser_error("variable & 127.0 == 65")

    def test_single_bitmask_not_equal_with_float(self):
        self._test_parser_error("variable & 127 != 65.0")

    def test_legacy_range_filter(self):
        self._test_parser(
            "variable: 1, 2",
            ('conjunction', [
                ('greater_than_or_equal', ('variable', ()), 1),
                ('less_than_or_equal', ('variable', ()), 2),
            ])
        )

    def test_legacy_range_filter_with_index(self):
        self._test_parser(
            "variable[0]: 1, 2",
            ('conjunction', [
                ('greater_than_or_equal', ('variable', (0,)), 1),
                ('less_than_or_equal', ('variable', (0,)), 2),
            ])

        )

    def test_legacy_range_filter_list(self):
        self._test_parser(
            "variable1:1,2;variable2:2.0,3e2",
            ('conjunction', [
                ('greater_than_or_equal', ('variable1', ()), 1),
                ('less_than_or_equal', ('variable1', ()), 2),
                ('greater_than_or_equal', ('variable2', ()), 2.0),
                ('less_than_or_equal', ('variable2', ()), 300.0),
            ])
        )

    def test_invalid_mixed_old_and_new_syntax_01(self):
        self._test_parser_error("variable1:1,2;variable2>2.0")

    def test_invalid_mixed_old_and_new_syntax_02(self):
        self._test_parser_error("variable2>2.0 AND variable:1,2")

    def test_missing_array_index(self):
        self._test_parser_error("variable[] == 0")

    def test_array_index_too_long(self):
        self._test_parser(
            "variable[%s] == 0" % ",".join("0"*32),
            ('equal', ('variable', (0,)*32), 0)
        )
        self._test_parser_error("variable[%s] == 0" % ",".join("0"*33))

    def test_too_many_conjunction_predicates(self):
        self._test_parser(
            " AND ".join(["variable == 0"]*4096),
            ("conjunction", [('equal', ('variable', ()), 0)]*4096),
            has_nan=True
        )
        self._test_parser_error(
            " AND ".join(["variable == 0"]*4097),
        )

    def test_too_many_disjunction_predicates(self):
        self._test_parser(
            " OR ".join(["variable == 0"]*4096),
            ("disjunction", [('equal', ('variable', ()), 0)]*4096),
            has_nan=True
        )
        self._test_parser_error(
            " OR ".join(["variable == 0"]*4097),
        )

    def test_too_many_range_filters(self):
        self._test_parser(
            ";".join(["variable:0,1"]*2048),
            ('conjunction', [
                ('greater_than_or_equal', ('variable', ()), 0),
                ('less_than_or_equal', ('variable', ()), 1),
            ]*2048),
            has_nan=True
        )
        self._test_parser_error(
            ";".join(["variable:0,1"]*2049)
        )


if __name__ == "__main__":
    main()
