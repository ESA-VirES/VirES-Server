#-------------------------------------------------------------------------------
#
# Inter-spacecraft difference calculation - grouping diffe
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
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

from vires.models import ProductCollection
from .time_series import ProductTimeSeries, SingleCollectionProductSource


def group_subtracted_variables(sources, residual_variables):
    """ Group subtracted variables by the spacecraft and collection. """
    result = {}

    for output_variable, item in residual_variables:
        source_variable, master_spacecraft, slave_spacecraft = item

        if master_spacecraft == slave_spacecraft:
            continue # equal spacecrafts are not allowed

        # find the master product collection providing the source variable
        for source in sources:
            if source_variable in source.variables:
                break
        else:
            source = None
            continue # no source found

        # check the spacecraft
        spacecraft = source.metadata['spacecraft']
        if master_spacecraft != spacecraft:
            continue # master spacecraft mismatch

        # find the slave collection
        try:
            slave_collection_id = (
                source.metadata['subtractableCollections'][slave_spacecraft]
            )
        except KeyError:
            continue # no reference collection found

        result_collection = result.setdefault(
            (master_spacecraft, slave_spacecraft), {}
        ).get(slave_collection_id)

        if result_collection is None:
            # find the slave data source
            try:
                slave_source = ProductTimeSeries(
                    SingleCollectionProductSource(
                        ProductCollection.objects.get(
                            identifier=slave_collection_id
                        )
                    )
                )
            except ProductCollection.DoesNotExist:
                continue # slave collection does not exist

            # create a new collection entry
            result[
                (master_spacecraft, slave_spacecraft)
            ][slave_collection_id] = result_collection = (slave_source, [])

        # add new variable entry
        result_collection[1].append(
            (output_variable, source_variable)
        )

    return result
