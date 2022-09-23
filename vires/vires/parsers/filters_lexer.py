#-------------------------------------------------------------------------------
#
# Filters lexer
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

# TODO: ISO time-stamps

import re
from ply.lex import lex
from .exceptions import ParserError

RE_ESCAPE = re.compile(r"\\(.)")


def get_filters_lexer():
    """ Get clone of a compiled lexer instance. """
    return __FILTERS_LEXER.clone()


class FiltersLexer():
    """ Filters expression lexer class. """
    reserved = {
        "AND": ("logical_and", "AND"),
        "OR": ("logical_or", "OR"),
        "NOT": ("logical_not", "NOT"),
        "INF": ("float", float("inf")),
        "NAN": ("float", float("nan")),
        "TRUE": ("bool", True),
        "FALSE": ("bool", False),
    }

    tokens = [
        "single_quote",
        "double_quote",
        "identifier",
        "string",
        "bool",
        "float",
        "integer",
        "index",
        "equal",
        "not_equal",
        "greater_than",
        "less_than",
        "greater_than_or_equal",
        "less_than_or_equal",
        "bitwise_and",
        "logical_and",
        "logical_or",
        "logical_not",
        "colon",
        "semicolon",
        "comma",
        "left_square_bracket",
        "right_square_bracket",
        "left_round_bracket",
        "right_round_bracket",
    ]

    token_labels = {
        "identifier": "variable identifier",
        "string": "string literal",
        "bool": "Boolean literal",
        "float": "float number literal",
        "integer": "integer number literal",
        "index": "integer index",
        "equal": "equal",
        "not_equal": "not equal",
        "greater_than": "greater than",
        "less_than": "less than",
        "greater_than_or_equal": "greater than or equal",
        "less_than_or_equal": "less than or equal",
        "bitwise_and": "bitwise AND",
        "logical_and": "logical AND",
        "logical_or": "logical OR",
        "logical_not": "logical NOT",
        "colon": "colon",
        "semicolon": "semicolon",
        "comma": "comma",
        "left_square_bracket": "left_square_bracket",
        "right_square_bracket": "right_square_bracket",
        "left_round_bracket": "left_round_bracket",
        "right_round_bracket": "right_round_bracket",
    }

    states = (
        ("squote", "exclusive"),
        ("dquote", "exclusive"),
        ("index", "exclusive"),
    )

    @classmethod
    def build(cls, **kwargs):
        return lex(module=cls, **kwargs)

    @staticmethod
    def get_line_and_column(token):
        line_start = token.lexer.lexdata.rfind("\n", 0, token.lexpos) + 1
        return (token.lineno, token.lexpos - line_start + 1)

    @classmethod
    def t_error(cls, token):
        line, column = cls.get_line_and_column(token)
        raise ParserError(line, column, (
            f"Illegal character {token.value[0]!r}, line {line}, "
            f"column {column}!"
        ))

    #---------------------------------------------------------------------------

    t_ignore = ' \t\r'

    #---------------------------------------------------------------------------
    # parsig operators

    t_colon = ":"
    t_semicolon = ";"
    t_comma = ","
    t_equal = "=="
    t_not_equal = "!="
    t_greater_than = ">"
    t_less_than = "<"
    t_greater_than_or_equal = ">="
    t_less_than_or_equal = "<="
    t_bitwise_and = "&"
    t_left_round_bracket = r"\("
    t_right_round_bracket = r"\)"

    #---------------------------------------------------------------------------
    # parsig parse identifiers, words and non-string literals

    @staticmethod
    def _unescape(token):
        token.value = RE_ESCAPE.sub(r"\1", token.value)
        return token

    @classmethod
    def _check_token_length(cls, token, limit):
        if len(token.value) <= limit:
            return token
        line, column = cls.get_line_and_column(token)
        label = cls.token_labels.get(token.type, token.type).capitalize()
        raise ParserError(line, column, (
            f"{label} longer then {limit} characters at line {line},"
            f" column {column}!"
        ))

    @classmethod
    def t_identifier(cls, token):
        r"([a-zA-Z_]|\\[a-zA-Z0-9_ -])([a-zA-Z0-9_]|\\[ -]){0,128}"
        # handle reserved word
        type_, value = cls.reserved.get(token.value.upper(), (None, None))
        if type_:
            token.type, token.value = type_, value
            return token
        # handle identifier
        return cls._check_token_length(cls._unescape(token), 128)

    @classmethod
    def t_number(cls, token):
        r"(?i)[+-]?((\.[0-9]+|[0-9]+(\.[0-9]*)?)(e[+-]?([1-9][0-9]*|0))?|nan|inf)\w{0,128}"

        cls._check_token_length(token, 128)

        # try to parse the number as an integer
        try:
            token.value, token.type = int(token.value), "integer"
            return token
        except ValueError:
            pass

        # try to parse the number as a float
        try:
            # default to float
            token.value, token.type = float(token.value), "float"
            return token
        except ValueError:
            pass

        line, column = cls.get_line_and_column(token)
        raise ParserError(line, column, (
            f"Not a valid number literal {token.value} at line {line},"
            f" column {column}!"
        ))

    #---------------------------------------------------------------------------
    # single quoted string parsing

    @classmethod
    def _quoted_string_error(cls, token):
        line, column = cls.get_line_and_column(token)
        raise ParserError(line, column, (
            f"Illegal character {token.value[0]!r} in a string literal"
            f"at line {line}, column {column}!"
        ))

    t_squote_ignore = ''
    t_squote_error = _quoted_string_error

    @staticmethod
    def t_single_quote(token):
        r"'"
        token.lexer.push_state('squote')

    @classmethod
    def t_squote_string(cls, token):
        r"([^']|''){1,129}"
        token.value = token.value.replace("''", "'")
        return cls._check_token_length(token, 128)

    @staticmethod
    def t_squote_single_quote(token):
        r"'"
        token.lexer.pop_state()

    @classmethod
    def t_squote_eof(cls, token):
        line, column = cls.get_line_and_column(token)
        raise ParserError(line, column, "Missing closing single quote!")

    #---------------------------------------------------------------------------
    # double quoted model string parsing

    t_dquote_ignore = ''
    t_dquote_error = _quoted_string_error

    @staticmethod
    def t_double_quote(token):
        r'"'
        token.lexer.push_state('dquote')

    @classmethod
    def t_dquote_string(cls, token):
        r'([^"]|""){1,129}'
        token.value = token.value.replace('""', '"')
        return cls._check_token_length(token, 128)

    @staticmethod
    def t_dquote_double_quote(token):
        r'"'
        token.lexer.pop_state()

    @classmethod
    def t_dquote_eof(cls, token):
        line, column = cls.get_line_and_column(token)
        raise ParserError(line, column, "Missing closing double quote!")

    #---------------------------------------------------------------------------
    # vector index parsing

    t_index_ignore = t_ignore
    t_index_error = t_error
    t_index_comma = r','

    @staticmethod
    def t_left_square_bracket(token):
        r'\['
        token.lexer.push_state('index')
        return token

    @staticmethod
    def t_index_right_square_bracket(token):
        r'\]'
        token.lexer.pop_state()
        return token

    @classmethod
    def t_index_index(cls, token):
        r'\d{1,10}'
        cls._check_token_length(token, 9)
        token.value = int(token.value)
        return token

    @classmethod
    def t_index_eof(cls, token):
        line, column = cls.get_line_and_column(token)
        raise ParserError(line, column, "Missing closing square bracket!")


#--------------------------------------------------------------------------------
# Main compiled model lexer do not use directly for parsing
# but its clone created by get_models_lexer() factory function.
__FILTERS_LEXER = FiltersLexer.build()
