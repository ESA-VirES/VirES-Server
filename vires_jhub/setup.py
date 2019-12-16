#-------------------------------------------------------------------------------
#
# VirES Jupyter Hub integration
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from os import walk
from os.path import join, abspath, relpath, dirname
from setuptools import setup, find_packages
import vires_jhub


def collect_data_files(path, base_dir):
    def _pack_item(directory, filenames):
        rdir = relpath(directory, base_dir)
        return (rdir, [join(rdir, file_) for file_ in filenames])
    return [
        _pack_item(directory, filenames)
        for directory, _, filenames in walk(path) if filenames
    ]


VERSION = vires_jhub.__version__
CURRENT_DIR = abspath(dirname(__file__))
SHARE_DIR = join(CURRENT_DIR, 'share', 'vires_jhub')

DATA_FILES = collect_data_files(SHARE_DIR, CURRENT_DIR)


setup(
    name='vires-jhub',
    version=VERSION,
    packages=find_packages(),
    data_files=DATA_FILES,
    include_package_data=True,
    package_data={},
    scripts=[],
    install_requires=[
        "oauthenticator",
        "jupyterhub",
        "tornado",
    ],
    zip_safe=False,

    # Metadata
    author="EOX IT Services GmbH",
    author_email="office@eox.at",
    maintainer="EOX IT Services GmbH",
    maintainer_email="packages@eox.at",

    description="VirES JupyterHub integration.",
    #long_description=read("README.rst"),

    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Other Audience',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Multimedia :: Graphics',
    ],

    license="EOxServer Open License (MIT-style)",
    keywords="JupyterHub, User Management, VirES, OAuth2",
    url="https://github.com/ESA-VirES/VirES-Server/",
)
