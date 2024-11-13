===================
pytest-run-parallel
===================

.. image:: https://img.shields.io/pypi/v/pytest-run-parallel.svg
    :target: https://pypi.org/project/pytest-run-parallel
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-run-parallel.svg
    :target: https://pypi.org/project/pytest-run-parallel
    :alt: Python versions

.. image:: https://github.com/Quansight-Labs/pytest-run-parallel/actions/workflows/main.yml/badge.svg
    :target: https://github.com/Quansight-Labs/pytest-run-parallel/actions/workflows/main.yml
    :alt: See Build Status on GitHub Actions

A simple pytest plugin to run tests concurrently

----

This `pytest`_ plugin takes a set of tests that would be normally be run
serially and execute them in parallel.

The main goal of ``pytest-run-parallel`` is to discover thread-safety issues that
could exist when using C libraries, this is of vital importance after `PEP703`_,
which provides a path for a CPython implementation without depending on the
Global Interpreter Lock (GIL), thus allowing for proper parallelism in programs
that make use of the CPython interpreter.

For more information about C thread-safety issues, please visit the
free-threaded community guide at https://py-free-threading.github.io/


Features
--------

* Two global CLI flags:
    * ``--parallel-threads`` to run a test suite in parallel
    * ``--iterations`` to run multiple times in each thread
* Three corresponding markers:
    * ``pytest.mark.parallel_threads(n)`` to mark a single test to run in
      parallel in ``n`` threads
    * ``pytest.mark.thread_unsafe`` to mark a single test to run in a single
      thread. It is equivalent to using ``pytest.mark.parallel_threads(1)``
    * ``pytest.mark.iterations(n)`` to mark a single test to run ``n`` times
      in each thread
* And the corresponding fixtures:
    * ``num_parallel_threads``: The number of threads the test will run in
    * ``num_iterations``: The number of iterations the test will run in each
      thread


Requirements
------------

``pytest-run-parallel`` depends exclusively on ``pytest``.


Installation
------------

You can install "pytest-run-parallel" via `pip`_ from `PyPI`_::

    $ pip install pytest-run-parallel


Usage
-----

This plugin has two modes of operation, one via the ``--parallel-threads`` and
``--iterations`` pytest CLI flags, which allows a whole test suite to be run
in parallel:

.. code-block:: bash

    pytest --parallel-threads=10 --iterations=10 tests

By default, the value for both flags will be 1, thus not modifying the
usual behaviour of pytest except when the flag is set.

Note that using ``pytest-xdist`` and setting ``iterations`` to a number greater
than one might cause tests to run even more times than intended.

The other mode of operation occurs at the individual test level, via the
``pytest.mark.parallel_threads`` and ``pytest.mark.iterations`` markers:

.. code-block:: python

    # test_file.py
    import pytest

    @pytest.fixture
    def my_fixture():
        ...

    @pytest.mark.parallel_threads(2)
    @pytest.mark.iterations(10)
    def test_something_1():
        # This test will be run in parallel using two concurrent threads
        # and 10 times in each thread
        ...

    @pytest.mark.parametrize('arg', [1, 2, 3])
    @pytest.mark.parallel_threads(3)
    def test_fixture(my_fixture, arg):
        # pytest markers and fixtures are supported as well
        ...

Both modes of operations are supported simultaneously, i.e.,

.. code-block:: bash

    # test_something_1 and test_fixture will be run using their set number of
    # threads; other tests will be run using 5 threads.
    pytest -x -v --parallel-threads=5 test_file.py

Additionally, ``pytest-run-parallel`` exposes the ``num_parallel_threads`` and
``num_iterations`` fixtures which enable a test to be aware of the number of
threads that are being spawned and the number of iterations each test will run:

.. code-block:: python

    # test_file.py
    import pytest

    def test_skip_if_parallel(num_parallel_threads):
        if num_parallel_threads > 1:
            pytest.skip(reason='does not work in parallel')
        ...

Finally, the ``thread_comp`` fixture allows for parallel test debugging, by providing an
instance of ``ThreadComparator``, whose ``__call__`` method allows to check if all the values
produced by all threads during an specific execution step are the same:

.. code-block:: python

    # test_file.py
    def test_same_execution_values(thread_comp):
        a = 2
        b = [3, 4, 5]
        c = None
        # Check that the values for a, b, c are the same across tests
        thread_comp(a=a, b=b, c=c)

Contributing
------------

Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-run-parallel" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`MIT`: https://opensource.org/licenses/MIT
.. _`file an issue`: https://github.com/Quansight-Labs/pytest-run-parallel/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
.. _`PEP703`: https://peps.python.org/pep-0703/
