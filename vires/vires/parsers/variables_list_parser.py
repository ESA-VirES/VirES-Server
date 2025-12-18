#-------------------------------------------------------------------------------
#
# Variables list parser
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

from collections import namedtuple
from ply.yacc import yacc
from .exceptions import ParserError
from .variables_list_lexer import VariablesListLexer

#
# Variables grammar:
#
#   variables : variables_list
#             | <empty>
#
#   variables_list : variables_list , variable
#                  | variable
#
#   variable : variable_name = variable_expression
#            | variable_name
#
#   variable_expression : variable_name
#

Variable = namedtuple('Variable', ['name', 'source'])
SourceVariable = namedtuple('SourceVariable', ['name'])


def get_variables_list_parser():
    """ Get compiled parser. """
    return VARIABLES_LIST_PARSER


class VariablesListParser():

    tokens = list(VariablesListLexer.token_labels)

    @classmethod
    def build(cls, write_tables=False, debug=False, **kwargs):
        return yacc(module=cls, write_tables=write_tables, debug=debug, **kwargs)

    @staticmethod
    def p_error(token):
        if token is not None:
            line, column = VariablesListLexer.get_line_and_column(token)
            raise ParserError(line, column, (
                 f"Unexpected {VariablesListLexer.token_labels[token.type]} "
                 f"{token.value!r} at line {line}, column {column}!"
            ))
        raise ParserError(-1, -1, "Syntax error!")

    @staticmethod
    def p_variables_as_variables_list(param):
        'variables : variables_list'
        param[0] = param[1]

    @staticmethod
    def p_variables_list_trailing_comma(param):
        'variables : variables_list comma'
        raise ParserError(-1, -1, "Unexpected trailing comma!")

    @staticmethod
    def p_variables_empty(param):
        'variables : '
        param[0] = []

    @staticmethod
    def p_variables_list_item(param):
        'variables_list : variable'
        param[0] = [param[1]]

    @staticmethod
    def p_variable_list_list(param):
        'variables_list : variables_list comma variable'
        param[0] = param[1] + [param[3]]

    @staticmethod
    def p_variable_simple(param):
        'variable : variable_name'
        param[0] = Variable(param[1], SourceVariable(param[1]))

    @staticmethod
    def p_variable_assigned_alias(param):
        'variable : variable_name assign variable_name'
        param[0] = Variable(param[1], SourceVariable(param[3]))


VARIABLES_LIST_PARSER = VariablesListParser.build()
