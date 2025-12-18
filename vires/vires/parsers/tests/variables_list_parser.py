#-------------------------------------------------------------------------------
#
# Variables list parser - tests
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
#pylint: disable=missing-docstring,too-many-public-methods,invalid-name

from unittest import TestCase, main
from vires.parsers.exceptions import ParserError
from vires.parsers.variables_list_parser import (
    get_variables_list_parser,
    Variable,
    SourceVariable,
)
from vires.parsers.variables_list_lexer import get_variables_list_lexer

class TestVariablesListParser(TestCase):

    def _test_parser(self, input_, output):
        lexer = get_variables_list_lexer()
        parser = get_variables_list_parser()
        raw_result = parser.parse(input_, lexer=lexer)
        result = raw_result
        self.assertEqual(result, output)

    def _test_parser_error(self, input_):
        lexer = get_variables_list_lexer()
        parser = get_variables_list_parser()
        with self.assertRaises(ParserError):
            parser.parse(input_, lexer=lexer)

    def test_one_variable_name_invalid_too_long(self):
        self._test_parser_error("X"*129)

    def test_one_variable_incomplete_assignment(self):
        self._test_parser_error("Var_01 = ")

    def test_one_variable_trailing_comma(self):
        self._test_parser_error("Var_01 = Src_01 , ")

    def test_multiple_variables_incomplete_assignment(self):
        self._test_parser_error("Var_01 = , Var_02")

    def test_no_variable(self):
        self._test_parser("  ", [])

    def test_one_variable_name(self):
        self._test_parser("_Var_01", [
            Variable("_Var_01", SourceVariable("_Var_01",)),
        ])

    def test_one_variable_alias(self):
        self._test_parser("Var_01 = Src_01", [
            Variable(name='Var_01', source=SourceVariable(name='Src_01'))
        ])

    def test_multiple_variable_names(self):
        self._test_parser("Var_01 , Var_02 , Var_03", [
            Variable(name='Var_01', source=SourceVariable(name='Var_01')),
            Variable(name='Var_02', source=SourceVariable(name='Var_02')),
            Variable(name='Var_03', source=SourceVariable(name='Var_03')),
        ])

    def test_multiple_variable_aliases(self):
        self._test_parser("Var_01 = Src_01 , Var_02 = Src_02 , Var_03 = Src_03", [
            Variable(name='Var_01', source=SourceVariable(name='Src_01')),
            Variable(name='Var_02', source=SourceVariable(name='Src_02')),
            Variable(name='Var_03', source=SourceVariable(name='Src_03')),
        ])

    def test_multiple_variable_names_and_aliases(self):
        self._test_parser("Var_01, Var_02 = Src_02 , Var_03 = Src_03, Var_04", [
            Variable(name='Var_01', source=SourceVariable(name='Var_01')),
            Variable(name='Var_02', source=SourceVariable(name='Src_02')),
            Variable(name='Var_03', source=SourceVariable(name='Src_03')),
            Variable(name='Var_04', source=SourceVariable(name='Var_04')),
        ])


if __name__ == "__main__":
    main()
