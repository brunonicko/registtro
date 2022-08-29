Registtro
=========
.. image:: https://github.com/brunonicko/registtro/workflows/MyPy/badge.svg
   :target: https://github.com/brunonicko/registtro/actions?query=workflow%3AMyPy

.. image:: https://github.com/brunonicko/registtro/workflows/Lint/badge.svg
   :target: https://github.com/brunonicko/registtro/actions?query=workflow%3ALint

.. image:: https://github.com/brunonicko/registtro/workflows/Tests/badge.svg
   :target: https://github.com/brunonicko/registtro/actions?query=workflow%3ATests

.. image:: https://readthedocs.org/projects/registtro/badge/?version=stable
   :target: https://registtro.readthedocs.io/en/stable/

.. image:: https://img.shields.io/github/license/brunonicko/registtro?color=light-green
   :target: https://github.com/brunonicko/registtro/blob/main/LICENSE

.. image:: https://static.pepy.tech/personalized-badge/registtro?period=total&units=international_system&left_color=grey&right_color=brightgreen&left_text=Downloads
   :target: https://pepy.tech/project/registtro

.. image:: https://img.shields.io/pypi/pyversions/registtro?color=light-green&style=flat
   :target: https://pypi.org/project/registtro/

Overview
--------
`Registtro` provides a weak entry, strong value immutable registry data structure.
Think of it as an immutable `WeakKeyDictionary`.

Example
-------

.. code:: python

    >>> from registtro import Registry
    >>> class Entry:
    ...     pass
    ...
    >>> # Initialize registry with 2 entries.
    >>> entry_a = Entry()
    >>> entry_b = Entry()
    >>> registry = Registry({entry_a: 1, entry_b: 2})
    >>> registry.query(entry_a)
    1
    >>> # Update a value and add a new entry, retrieve new registry (immutable).
    >>> entry_c = Entry()
    >>> registry = registry.update({entry_a: 10, entry_c: 3})
    >>> registry.query(entry_a)
    10
    >>> registry.query(entry_c)
    3
    >>> # Get evolver and perform updates on it (mutable).
    >>> evolver = registry.get_evolver()
    >>> evolver.update({entry_b: 20})
    <registtro._registry.RegistryEvolver object at ...>
    >>> evolver.update({entry_c: 30})
    <registtro._registry.RegistryEvolver object at ...>
    >>> evolver.query(entry_c)
    30
    >>> # Freeze evolver into a registry (immutable).
    >>> registry = evolver.get_registry()
    >>> registry.query(entry_c)
    30
