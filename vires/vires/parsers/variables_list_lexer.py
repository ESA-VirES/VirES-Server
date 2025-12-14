#-------------------------------------------------------------------------------
#
# Varibles list lexer
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
#pylint: disable=missing-docstring

from ply.lex import lex
from .exceptions import ParserError


def get_variables_list_lexer():
    """ Get clone of a compiled lexer instance. """
    return __VARIABLES_LIST_LEXER.clone()


class VariablesListLexer():
    """ Variables list lexer class. """
    tokens = [
        "variable_name",
        "comma",
        "assign",
    ]

    token_labels = {
        "variable_name": "variable name",
        "comma": "comma separator",
        "assign": "assignment",
    }

    states = (
        ('expression', 'exclusive'),
    )

    @classmethod
    def build(cls, **kwargs):
        return lex(module=cls, **kwargs)

    #---------------------------------------------------------------------------
    # models list parsing

    t_comma = r","
    t_ignore = ' \t\r'

    @staticmethod
    def t_variable_name(token):
        r"[a-zA-Z_][a-zA-Z0-9_-]{0,128}"
        return VariablesListLexer._check_id_length(token, 128)

    @staticmethod
    def t_newline(token):
        r'\n+'
        token.lexer.lineno += len(token.value)

    @staticmethod
    def t_error(token):
        line, column = VariablesListLexer.get_line_and_column(token)
        raise ParserError(
            line, column,
            f"Illegal character {token.value[0]!r}, line {line}, column {column}!"
        )

    @staticmethod
    def _check_id_length(token, limit):
        if len(token.value) <= limit:
            return token
        line, column = VariablesListLexer.get_line_and_column(token)
        raise ParserError(
            line, column,
            f"Identifier longer then {limit} characters at line {line}, column {column}!"
        )

    @staticmethod
    def get_line_and_column(token):
        line_start = token.lexer.lexdata.rfind('\n', 0, token.lexpos) + 1
        return (token.lineno, token.lexpos - line_start + 1)

    #---------------------------------------------------------------------------
    # model expression parsing

    t_expression_ignore = t_ignore
    t_expression_error = t_error
    t_expression_newline = t_newline

    @staticmethod
    def t_expression_variable_name(token):
        r"[a-zA-Z_][a-zA-Z0-9_]{0,128}"
        return VariablesListLexer._check_id_length(token, 128)

    @staticmethod
    def t_assign(token):
        r'='
        token.lexer.push_state('expression')
        return token

    @staticmethod
    def t_expression_comma(token):
        r','
        token.lexer.pop_state()
        return token

    @staticmethod
    def t_expression_eof(token):
        token.lexer.pop_state()


#--------------------------------------------------------------------------------
# Main compiled model lexer do not use directly for parsing
# but its clone created by get_*_lexer() factory function.
__VARIABLES_LIST_LEXER = VariablesListLexer.build()
