#-------------------------------------------------------------------------------
#
# various file utilities - test
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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

from unittest import TestCase, main
from time import sleep
from uuid import uuid4
from os import remove
from os.path import exists
from tempfile import NamedTemporaryFile
from vires.file_util import FileChangeMonitor


SLEEP_TIME = 0.1 # seconds


class TestFileChangeMonitor(TestCase):
    CLASS = FileChangeMonitor

    def test_non_existent(self):
        obj = self.CLASS()
        with TempFilename() as filename:
            self.assertTrue(obj.changed(filename))

    def test_first_query(self):
        obj = self.CLASS()
        with TempFilename() as filename:
            change_file(filename)
            self.assertTrue(obj.changed(filename))

    def test_not_changed(self):
        obj = self.CLASS()
        with TempFilename() as filename:
            change_file(filename)
            obj.changed(filename)
            self.assertFalse(obj.changed(filename))

    def test_changed(self):
        obj = self.CLASS()
        with TempFilename() as filename:
            change_file(filename)
            obj.changed(filename)
            sleep(SLEEP_TIME)
            change_file(filename)
            self.assertTrue(obj.changed(filename))

    def test_removed(self):
        obj = self.CLASS()
        with TempFilename() as filename:
            change_file(filename)
            obj.changed(filename)
            remove(filename)
            self.assertTrue(obj.changed(filename))

    def test_after_removed(self):
        obj = self.CLASS()
        with TempFilename() as filename:
            obj.changed(filename)
            self.assertFalse(obj.changed(filename))

    def test_two_files_not_changed(self):
        obj = self.CLASS()
        with TempFilename() as filename1:
            with TempFilename() as filename2:
                change_file(filename1)
                change_file(filename2)
                obj.changed(filename1, filename2)
                self.assertFalse(obj.changed(filename1, filename2))

    def test_two_files_first_changed(self):
        obj = self.CLASS()
        with TempFilename() as filename1:
            with TempFilename() as filename2:
                change_file(filename1)
                change_file(filename2)
                obj.changed(filename1, filename2)
                sleep(SLEEP_TIME)
                change_file(filename1)
                self.assertTrue(obj.changed(filename1, filename2))

    def test_two_files_second_changed(self):
        obj = self.CLASS()
        with TempFilename() as filename1:
            with TempFilename() as filename2:
                change_file(filename1)
                change_file(filename2)
                obj.changed(filename1, filename2)
                remove(filename2)
                self.assertTrue(obj.changed(filename1, filename2))

    def test_two_files_both_changed(self):
        obj = self.CLASS()
        with TempFilename() as filename1:
            with TempFilename() as filename2:
                change_file(filename1)
                change_file(filename2)
                obj.changed(filename1, filename2)
                sleep(SLEEP_TIME)
                remove(filename1)
                change_file(filename2)
                self.assertTrue(obj.changed(filename1, filename2))


class TempFilename(object):

    def __init__(self):
        with NamedTemporaryFile() as file_:
            self.name = file_.name

    def __enter__(self):
        return self.name

    def __exit__(self, *args):
        if exists(self.name):
            remove(self.name)


def change_file(filename):
    with open(filename, "w") as file_:
        file_.write(str(uuid4()))


if __name__ == "__main__":
    main()
