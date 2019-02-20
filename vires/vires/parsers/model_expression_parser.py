#-------------------------------------------------------------------------------
#
# single model expression parser
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
# pylint: disable=missing-docstring

from collections import namedtuple
from ply.yacc import yacc
from .exceptions import ParserError
from .model_expression_lexer import ModelExpressionLexer

#
# Model expression grammar:
#
#   model_expression : model_expression + model_definition
#                    | model_expression - model_definition
#                    | - model_definition
#                    | + model_definition
#                    | model_definition
#
#   model_definition : model_id ( model_parameters )
#
#   model_parameters : model_parameters_list
#                    | <empty>
#
#   model_parameters_list : model_parameters_list, model_parameter
#   model_parameters_list : model_parameter
#
#   model_parameter : parameter_id = integer
#
#   model_id : "[a-zA-Z][a-zA-Z0-9_-]{0,127}"
#            | '[a-zA-Z][a-zA-Z0-9_-]{0,127}'
#            | [a-zA-Z][a-zA-Z0-9_-]{0,127}
#
#   parameter_id : (max_degree|min_degree)
#
#   integer : [-+]?\d{1,9}
#
# Note: Dash (-) in a model id has a lower priority than the minus sign (-)
#       in model expressions and thus the ids containing dash must be quoted
#       in the model expressions.


ALLOWED_MODEL_PARAMETERS = {'max_degree', 'min_degree'}

ModelDefinition = namedtuple('ModelDefinition', ['id', 'parameters'])


def get_model_expression_parser():
    """ Get compiled parser. """
    return MODEL_EXPRESSION_PARSER


class ModelExpressionParser(object):

    tokens = list(ModelExpressionLexer.token_labels)

    @classmethod
    def build(cls, write_tables=False, debug=False, **kwargs):
        return yacc(module=cls, write_tables=write_tables, debug=debug, **kwargs)

    @staticmethod
    def p_error(token):
        if token is not None:
            line, column = ModelExpressionLexer.get_line_and_column(token)
            raise ParserError(
                line, column, "Unexpected %s %r at line %d, column %d!" % (
                    ModelExpressionLexer.token_labels[token.type],
                    token.value, line, column
                )
            )
        else:
            raise ParserError(-1, -1, "Syntax error!")

    @staticmethod
    def p_model_expression_item(param):
        'model_expression : model_definition'
        param[0] = [param[1]]

    @staticmethod
    def p_model_expression_item_with_leading_plus(param):
        'model_expression : plus model_definition'
        param[0] = [param[2]]

    @staticmethod
    def p_model_expression_item_with_leading_minus(param):
        'model_expression : minus model_definition'
        param[2].parameters["scale"] = -1
        param[0] = [param[2]]

    @staticmethod
    def p_model_expression_plus(param):
        'model_expression : model_expression plus model_definition'
        param[0] = param[1] + [param[3]]

    @staticmethod
    def p_model_expression_minus(param):
        'model_expression : model_expression minus model_definition'
        param[3].parameters["scale"] = -1
        param[0] = param[1] + [param[3]]

    @staticmethod
    def p_model_definition_simple(param):
        'model_definition : model_id'
        param[0] = ModelDefinition(param[1], {})

    @staticmethod
    def p_model_definition_parametrized(param):
        'model_definition : model_id left_parenthesis model_parameters right_parenthesis'
        param[0] = ModelDefinition(param[1], param[3])

    @staticmethod
    def p_model_parameters_list(param):
        'model_parameters : model_parameters_list'
        param[0] = param[1]

    @staticmethod
    def p_model_parameters_trailing_comma(param):
        'model_parameters : model_parameters_list comma'
        raise ParserError(-1, -1, "Unexpected trailing comma!")

    @staticmethod
    def p_model_parameters_empty(param):
        'model_parameters : '
        param[0] = {}

    @staticmethod
    def p_model_parameters_list_item(param):
        'model_parameters_list : model_parameter'
        param[0] = param[1]

    @staticmethod
    def p_model_parameters_list_list(param):
        'model_parameters_list : model_parameters_list comma model_parameter'
        for key in param[3]:
            if key in param[1]:
                raise ParserError(-1, -1, "Duplicate model parameter %r" % key)
        param[1].update(param[3])
        param[0] = param[1]

    @staticmethod
    def p_model_parameter(param):
        'model_parameter : parameter_id assign integer'
        if param[1] not in ALLOWED_MODEL_PARAMETERS:
            raise ParserError(-1, -1, "Invalid model parameter %r" % param[1])
        param[0] = {param[1]: param[3]}


MODEL_EXPRESSION_PARSER = ModelExpressionParser.build()
