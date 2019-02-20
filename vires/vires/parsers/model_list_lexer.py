#-------------------------------------------------------------------------------
#
# Model list lexer
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
#pylint: disable=missing-docstring

from ply.lex import lex
from .exceptions import ParserError


def get_model_list_lexer():
    """ Get clone of a compiled lexer instance. """
    return __MODEL_LIST_LEXER.clone()


class ModelListLexer(object):
    """ Models lexer class. """
    tokens = [
        "model_id",
        "parameter_id",
        "integer",
        "comma",
        "assign",
        "plus",
        "minus",
        "left_parenthesis",
        "right_parenthesis",
        "single_quote",
        "double_quote",
    ]

    token_labels = {
        "model_id": "model identifier",
        "parameter_id": "parameter identifier",
        "integer": "integer value",
        "comma": "comma separator",
        "assign": "assignment",
        "plus": "plus operator",
        "minus": "minus operator",
        "left_parenthesis": "left parenthesis",
        "right_parenthesis": "right parenthesis",
    }

    states = (
        ('expression', 'exclusive'),
        ('squote', 'exclusive'),
        ('dquote', 'exclusive'),
        ('params', 'exclusive'),
    )

    @classmethod
    def build(cls, **kwargs):
        return lex(module=cls, **kwargs)

    #---------------------------------------------------------------------------
    # models list parsing

    t_comma = r","
    t_ignore = ' \t\r'

    @staticmethod
    def t_model_id(token):
        r"[a-zA-Z][a-zA-Z0-9_-]{0,128}"
        return ModelListLexer._check_id_length(token, 128)

    @staticmethod
    def t_newline(token):
        r'\n+'
        token.lexer.lineno += len(token.value)

    @staticmethod
    def t_error(token):
        line, column = ModelListLexer.get_line_and_column(token)
        raise ParserError(
            line, column, "Illegal character %r, line %d, column %d!"
            % (token.value[0], line, column)
        )

    @staticmethod
    def _check_id_length(token, limit):
        if len(token.value) <= limit:
            return token
        line, column = ModelListLexer.get_line_and_column(token)
        raise ParserError(
            line, column,
            "Identifier longer then %d characters at line %d, column %d!"
            % (limit, line, column)
        )

    @staticmethod
    def get_line_and_column(token):
        line_start = token.lexer.lexdata.rfind('\n', 0, token.lexpos) + 1
        return (token.lineno, token.lexpos - line_start + 1)


    #---------------------------------------------------------------------------
    # model expression parsing

    t_expression_plus = r"\+"
    t_expression_minus = r"-"
    t_expression_ignore = t_ignore
    t_expression_error = t_error
    t_expression_newline = t_newline

    @staticmethod
    def t_expression_model_id(token):
        r"[a-zA-Z][a-zA-Z0-9_]{0,128}"
        return ModelListLexer._check_id_length(token, 128)

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

    #---------------------------------------------------------------------------
    # model parameters parsing

    t_params_newline = t_newline
    t_params_ignore = t_ignore
    t_params_error = t_error
    t_params_assign = r'='
    t_params_comma = t_comma

    @staticmethod
    def t_expression_left_parenthesis(token):
        r'\('
        token.lexer.push_state('params')
        return token

    @staticmethod
    def t_params_right_parenthesis(token):
        r'\)'
        token.lexer.pop_state()
        return token

    @staticmethod
    def t_params_integer(token):
        r'[-+]?\d{1,10}'
        limit = 9
        digits = token.value[1:] if token.value[0] in "+-" else token.value
        if len(digits) > limit:
            line, column = ModelListLexer.get_line_and_column(token)
            raise ParserError(
                line, column,
                "Integer value has more then %d digits at line %d, column %d!"
                % (limit, line, column)
            )
        token.value = int(token.value)
        return token

    @staticmethod
    def t_params_parameter_id(token):
        r"[a-z][a-z0-9_]{0,128}"
        return ModelListLexer._check_id_length(token, 128)

    @staticmethod
    def t_params_eof(token):
        line, column = ModelListLexer.get_line_and_column(token)
        raise ParserError(line, column, "Missing closing parenthesis!")

    #---------------------------------------------------------------------------
    # single quoted model identifier parsing

    @staticmethod
    def _quoted_id_error(token):
        line, column = ModelListLexer.get_line_and_column(token)
        raise ParserError(
            line, column,
            "Illegal character %r in a quoted identifier at line %d, column %d!"
            % (token.value[0], line, column)
        )

    t_squote_model_id = t_model_id
    t_squote_ignore = ''
    t_squote_error = _quoted_id_error

    @staticmethod
    def t_single_quote(token):
        r"'"
        token.lexer.push_state('squote')

    t_expression_single_quote = t_single_quote

    @staticmethod
    def t_squote_single_quote(token):
        r"'"
        token.lexer.pop_state()

    @staticmethod
    def t_squote_eof(token):
        line, column = ModelListLexer.get_line_and_column(token)
        raise ParserError(line, column, "Missing closing single quote!")

    #---------------------------------------------------------------------------
    # double quoted model identifier parsing

    t_dquote_model_id = t_model_id
    t_dquote_ignore = ''
    t_dquote_error = _quoted_id_error

    @staticmethod
    def t_double_quote(token):
        r'"'
        token.lexer.push_state('dquote')

    t_expression_double_quote = t_double_quote

    @staticmethod
    def t_dquote_double_quote(token):
        r'"'
        token.lexer.pop_state()

    @staticmethod
    def t_dquote_eof(token):
        line, column = ModelListLexer.get_line_and_column(token)
        raise ParserError(line, column, "Missing closing double quote!")


#--------------------------------------------------------------------------------
# Main compiled model lexer do not use directly for parsing
# but its clone created by get_models_lexer() factory function.
__MODEL_LIST_LEXER = ModelListLexer.build()
