#-------------------------------------------------------------------------------
#
# Filters parser
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
#pylint: disable=missing-docstring

from collections import namedtuple
from ply.yacc import yacc
from .exceptions import ParserError
from .filters_lexer import FiltersLexer

MAX_NUMBER_OF_PREDICATES = 4096
MAX_NUMBER_OF_DIMENSIONS = 32

#
# Filters grammar:
#
# filters : filter_expresison | range_filter_list | <empty>
#
# range_filter_list : range_filter_list ; range_filter
#                   | range_filter
#
# range_filter : variable : ordinal_literal , ordinal_literal
#
# filter_expression : filter_conjunction
#                   | filter_disjunction
#
# filter_conjunction : filter_conjunction AND filter_predicate
#                    | filter_predicate
#
# filter_disjunction : filter_conjunction OR filter_predicate
#                    | filter_predicate
#
# filter_predicate: variable == literal
#                 | variable != literal
#                 | variable > ordinal_literal
#                 | variable < ordinal_literal
#                 | variable <= ordinal_literal
#                 | variable >= ordinal_literal
#                 | variable & integer == integer
#                 | variable & integer != integer
#                 | ( filter_disjunction )
#                 | ( filter_conjunction )
#
# variable : indetifier [ array_index ]
#          | indetifier
#
# array_index : array_index , index
#             | index
#
# literal: ordinal_literal | string
#
# ordinal_literal: bool | integer | float
#
# ---
# NOTES:
#
# Simple predicates in parenthesis as treated as wihout them, i.e.,
# "(<predicate>)" is parsed as "<predicate>" and the parenthesis
# are effectively used only for the composed conjunctions and disjunctions.
#
# Nested conjunctions and disjunctions are flattened, i.e.,
# "<predictate1> AND (<predicate2> AND <predicate3>)" are parsed as
# "<predictate1> AND <predicate2> AND <predicate3>" and
# "<predictate1> OR (<predicate2> OR <predicate3>)" are parsed as
# "<predictate1> OR <predicate2> OR <predicate3>".
#
# Double negation are canceled, i.e., "NOT NOT <predicate>" as parsed as
# "<predicate>".
#
# The parsed filters are currently a list of single-variable predicates
# cupled with the logical conjunction (AND). Mutiple predicates for the
# same variable may appear.
#
# For sake of the backward compatibility the legacy range filters are
# also supported. These are expande to a conjunction of a paier of simple
# predicates, e.g., "<variable>:0,1" is expanded as
# "variable >= 0 AND variable <= 1"
#


def get_filters_parser():
    """ Get compiled parser. """
    return FILTERS_PARSER


def get_line_and_column(lexer, token):
    position = token.lexpos if token else len(lexer.lexdata)
    line_start = lexer.lexdata.rfind("\n", 0, position) + 1
    return (lexer.lineno, position - line_start + 1)


def check_number_of_composed_predicates(param, type_, *args):
    if type_ not in ("conjunction", "disjunction"):
        return
    if len(args[0]) > MAX_NUMBER_OF_PREDICATES:
        line, column = get_line_and_column(param.lexer, param.parser.token())
        raise ParserError(line, column, (
            f"The {type_} exceeds the maximum allowed number "
            f"of predicates ({MAX_NUMBER_OF_PREDICATES}), at line {line}, "
            f"column {column}!"
        ))

def join_composed_predicates(composed_type, old, new):
    return (composed_type, [
        *(old[1] if old[0] == composed_type else [old]),
        *(new[1] if new[0] == composed_type else [new]),
    ])


class FiltersParser():

    tokens = list(FiltersLexer.token_labels)

    @classmethod
    def build(cls, write_tables=False, debug=False, **kwargs):
        return yacc(module=cls, write_tables=write_tables, debug=debug, **kwargs)

    @staticmethod
    def p_error(token):
        if token is not None:
            line, column = FiltersLexer.get_line_and_column(token)
            raise ParserError(
                line, column, "Unexpected %s %r at line %d, column %d!" % (
                    FiltersLexer.token_labels[token.type],
                    token.value, line, column
                )
            )
        raise ParserError(-1, -1, "Syntax error!")

    @staticmethod
    def p_filters_from_expression(param):
        'filters : filter_expression'
        param[0] = param[1]

    @staticmethod
    def p_filters_from_range_filter_list(param):
        'filters : range_filter_list'
        param[0] = param[1]

    @staticmethod
    def p_filters_empty(param):
        'filters : '
        param[0] = None

    @staticmethod
    def p_legacy_range_filter_list_from_list(param):
        "range_filter_list : range_filter_list semicolon range_filter"
        predicate = join_composed_predicates("conjunction", param[1], param[3])
        check_number_of_composed_predicates(param, *predicate)
        param[0] = predicate

    @staticmethod
    def p_legacy_range_filter_from_single_predicate(param):
        'range_filter_list : range_filter'
        param[0] = param[1]

    @staticmethod
    def p_legacy_range_filter(param):
        'range_filter : variable colon ordinal_literal comma ordinal_literal'
        param[0] = ("conjunction", [
            ("greater_than_or_equal", param[1], param[3]),
            ("less_than_or_equal", param[1], param[5]),
        ])

    @staticmethod
    def p_filter_expression_from_conjunction(param):
        "filter_expression : filter_conjunction"
        param[0] = param[1]

    @staticmethod
    def p_filter_expression_from_disjunction(param):
        "filter_expression : filter_disjunction"
        param[0] = param[1]

    @staticmethod
    def p_filter_conjunction_from_composed_predicates(param):
        "filter_conjunction : filter_conjunction logical_and filter_predicate"
        predicate = join_composed_predicates("conjunction", param[1], param[3])
        check_number_of_composed_predicates(param, *predicate)
        param[0] = predicate

    @staticmethod
    def p_filter_conjunction_from_single_predicate(param):
        "filter_conjunction : filter_predicate"
        param[0] = param[1]

    @staticmethod
    def p_filter_disjunction_from_composed_predicates(param):
        "filter_disjunction : filter_disjunction logical_or filter_predicate"
        predicate = join_composed_predicates("disjunction", param[1], param[3])
        check_number_of_composed_predicates(param, *predicate)
        param[0] = predicate

    @staticmethod
    def p_filter_disjunction_from_single_predicate(param):
        "filter_disjunction : filter_predicate"
        param[0] = param[1]

    @staticmethod
    def p_filter_predicate_negated(param):
        "filter_predicate : logical_not filter_predicate"
        param[0] = param[2][1] if param[2][0] == "not" else ("not", param[2])

    @staticmethod
    def p_filter_predicate_nested_cojunction(param):
        "filter_predicate : left_round_bracket filter_conjunction right_round_bracket"
        param[0] = param[2]

    @staticmethod
    def p_filter_predicate_nested_disjunction(param):
        "filter_predicate : left_round_bracket filter_disjunction right_round_bracket"
        param[0] = param[2]

    @staticmethod
    def p_filter_predicate_equal(param):
        "filter_predicate : variable equal literal"
        param[0] = ("equal", param[1], param[3])

    @staticmethod
    def p_filter_predicate_not_equal(param):
        "filter_predicate : variable not_equal literal"
        param[0] = ("not_equal", param[1], param[3])

    @staticmethod
    def p_filter_predicate_greater_than(param):
        "filter_predicate : variable greater_than ordinal_literal"
        param[0] = ("greater_than", param[1], param[3])

    @staticmethod
    def p_filter_predicate_less_than(param):
        "filter_predicate : variable less_than ordinal_literal"
        param[0] = ("less_than", param[1], param[3])

    @staticmethod
    def p_filter_predicate_greater_than_or_equal(param):
        "filter_predicate : variable greater_than_or_equal ordinal_literal"
        param[0] = ("greater_than_or_equal", param[1], param[3])

    @staticmethod
    def p_filter_predicate_less_than_or_equal(param):
        "filter_predicate : variable less_than_or_equal ordinal_literal"
        param[0] = ("less_than_or_equal", param[1], param[3])

    @staticmethod
    def p_filter_predicate_bitmask_equal(param):
        "filter_predicate : variable bitwise_and integer equal integer"
        param[0] = ("bitmask_equal", param[1], param[3], param[5])

    @staticmethod
    def p_filter_predicate_bitmask_not_equal(param):
        "filter_predicate : variable bitwise_and integer not_equal integer"
        param[0] = ("bitmask_not_equal", param[1], param[3], param[5])

    @staticmethod
    def p_literal_from_ordinal_literal(param):
        "literal : ordinal_literal"
        param[0] = param[1]

    @staticmethod
    def p_literal_from_string(param):
        "literal : string"
        param[0] = param[1]

    @staticmethod
    def p_ordinal_from_bool(param):
        "ordinal_literal : bool"
        param[0] = param[1]

    @staticmethod
    def p_ordinal_from_integer(param):
        "ordinal_literal : integer"
        param[0] = param[1]

    @staticmethod
    def p_ordinal_from_float(param):
        "ordinal_literal : float"
        param[0] = param[1]

    @staticmethod
    def p_filter_variable_with_array_index(param):
        "variable : identifier left_square_bracket array_index right_square_bracket"
        param[0] = (param[1], param[3])

    @staticmethod
    def p_filter_variable_without_array_index(param):
        "variable : identifier"
        param[0] = (param[1], ())

    @staticmethod
    def p_array_index_list(param):
        "array_index : array_index comma index"
        if len(param[1]) == MAX_NUMBER_OF_DIMENSIONS:
            line, column = get_line_and_column(param.lexer, param.parser.token())
            raise ParserError(line, column, (
                "The array index exceeds the maximum allowed number "
                f"of dimensions ({MAX_NUMBER_OF_DIMENSIONS}), at line {line}, "
                f"column {column}!"
            ))
        param[0] = (*param[1], param[3])

    @staticmethod
    def p_array_index_single_index(param):
        "array_index : index"
        param[0] = (param[1],)


FILTERS_PARSER = FiltersParser.build()
