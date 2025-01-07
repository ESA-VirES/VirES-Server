#-------------------------------------------------------------------------------
#
# WPS filename builder
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

import hashlib


def build_response_basename(template, collection_ids, start_time, end_time,
                            max_size, prefix_size=0, suffix_size=0):
    """ Build safe response filename. """

    formatted_collection_ids = "_".join(
        collection_id.replace(":", "-")
        for collection_id in collection_ids
    )

    return trim_name(
        template.format(
            collection_ids=formatted_collection_ids,
            start_time=start_time,
            end_time=end_time,
        ),
        max_size=max_size,
        prefix_size=prefix_size,
        suffix_size=suffix_size,
    )


def trim_name(name, max_size, prefix_size=0, suffix_size=0):
    """ Trim name exceeding the given size limit filling in unique hash of the
    original name while preserving the requested prefix and suffix parts. """
    assert max_size >= prefix_size + suffix_size

    if len(name) <= max_size:
        return name

    body = _get_string_hash(name)
    head_size = max(prefix_size, max_size - len(body) - suffix_size - 2)
    head, tail = name[:head_size], name[len(name) - suffix_size:]

    name = body
    if head:
        name = f"{head}_{name}"
    if tail:
        name = f"{name}_{tail}"

    return name


def _get_string_hash(string, encoding="utf-8"):
    digest = hashlib.md5()
    digest.update(string.encode(encoding))
    return digest.hexdigest()


def test_build_response_basename():
    from datetime import datetime, timedelta
    collection_ids = ["SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B"]
    options = {
        "template": (
            "{collection_ids}_{start_time:%Y%m%dT%H%M%S}_"
            "{end_time:%Y%m%dT%H%M%S}_Filtered"
        ),
        "start_time": datetime(2014, 1, 1),
        "end_time": datetime(2014, 1, 1, 23, 59, 59),
        "max_size": 225,
        "prefix_size": 2,
        "suffix_size": 40,
    }

    assert (
        build_response_basename(
            collection_ids=collection_ids*20, **options
        ) == (
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "d6669e7f0b0cb19372f17a1003f19132_"
            "20140101T000000_20140101T235959_Filtered"
        )
    )

    assert (
        build_response_basename(
            collection_ids=collection_ids*10, **options
        ) == (
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "6c2b0ce467c22e3c3bba77d07af7d595_"
            "20140101T000000_20140101T235959_Filtered"
        )
    )

    assert (
        build_response_basename(
            collection_ids=collection_ids*3, **options
        ) == (
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "SW_OPER_MAGA_LR_1B+SW_FAST_MAGA_LR_1B_"
            "20140101T000000_20140101T235959_Filtered"
        )
    )


def test_trim_name():
    assert trim_name("12345", 6, 2, 2) == "12345"
    assert trim_name("123456", 6, 2, 2) == "123456"
    assert trim_name("1234567", 6, 2, 2) == "12_fcea920f7412b5da7be0cf42b8c93759_67"
    assert trim_name("12345", 6, 0, 2) == "12345"
    assert trim_name("123456", 6, 0, 2) == "123456"
    assert trim_name("1234567", 6, 0, 2) == "fcea920f7412b5da7be0cf42b8c93759_67"
    assert trim_name("12345", 6, 2, 0) == "12345"
    assert trim_name("123456", 6, 2, 0) == "123456"
    assert trim_name("1234567", 6, 2, 0) == "12_fcea920f7412b5da7be0cf42b8c93759"


if __name__ == "__main__":
    test_build_response_basename()
    test_trim_name()
