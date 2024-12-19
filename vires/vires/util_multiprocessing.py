#-------------------------------------------------------------------------------
#
# Multi-processing utilities.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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

import multiprocessing
import concurrent.futures
from collections import namedtuple

N_CPU = multiprocessing.cpu_count()


class MultiProcessStreamExecutor:
    """ Multi-process stream executor. """

    MAX_JOB_COUNT_FACTOR = 2  # max_queued_jobs = MAX_JOB_COUNT_FACTOR * max_workers
    WAIT_TIMEOUT_SECONDS = 2

    def __init__(self, max_workers):
        self.max_workers = max_workers

    def __call__(self, records, submit_job, handle_result):
        """ Run the stream executor.

        Args:
            records: a sequence of the processed records
            submit_job: custom submit function calling the received submit
                function with parameters extracted from passed record
                and return the created future object. E.g.,
                    def submit_job(submit, record):
                        return submit(processor, *record)
            handle_result: custom function handling the finished future object
                and returning the result. E.g.,
                    def handle_result(future, record):
                        try:
                            return record, future.result()
                        except:
                            return record, None

        Yields:
            Processed results.

        """
        return self._run_executor(
            records,
            submit_job,
            handle_result,
            max_workers=self.max_workers,
            max_submitted_jobs=(self.max_workers * self.MAX_JOB_COUNT_FACTOR),
            wait_timeout=self.WAIT_TIMEOUT_SECONDS
        )

    @staticmethod
    def _run_executor(records, submit_job, handle_result,
                      max_workers, max_submitted_jobs, wait_timeout):
        """ Run multi-process executor. """

        FutureRecord = namedtuple("FutureRecord", ["future", "record"])

        def _too_many_futures(futures):
            return len(futures) >= max_submitted_jobs

        def _wait_for_first_completed(futures):
            concurrent.futures.wait(
                [item.future for item in futures],
                timeout=wait_timeout,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )

        def _handle_finished_futures(futures):
            unfished_futures = []
            results = []
            for item in futures:
                if item.future.done():
                    result = handle_result(item.future, item.record)
                    if result:
                        results.append(result)
                else:
                    unfished_futures.append(item)
            return unfished_futures, results

        # multi-process execution

        futures = []

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers,
        ) as executor:

            for record in records:

                # safeguard preventing submitting too many jobs
                while _too_many_futures(futures):
                    _wait_for_first_completed(futures)
                    futures, results = _handle_finished_futures(futures)
                    yield from results

                futures.append(
                    FutureRecord(
                        submit_job(executor.submit, record), record
                    )
                )

                futures, results = _handle_finished_futures(futures)
                yield from results

            executor.shutdown()

            # handle remaining jobs
            while futures:
                _wait_for_first_completed(futures)
                futures, results = _handle_finished_futures(futures)
                yield from results
