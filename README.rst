.. logo_start
.. raw:: html

   <p align="center">
     <a href="https://github.com/brunonicko/registtro">
         <picture>
            <object data="./_static/registtro.svg" type="image/png">
                <source srcset="./docs/source/_static/registtro_white.svg" media="(prefers-color-scheme: dark)">
                <img src="./docs/source/_static/registtro.svg" width="60%" alt="registtro" />
            </object>
         </picture>
     </a>
   </p>
.. logo_end

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
Weak entry, strong value immutable registry data structure. Think of it as an immutable `WeakKeyDictionary`.

Motivation
----------
Immutable data structures are great for when you need to implement some kind of "snapshot" of states for easy undo/redo,
time-travelling functionality. The library `pyrsistent <https://pypi.org/project/pyrsistent/>`_ is great for that, but
it lacks a map-like structure in which the keys are stored as weak references.

`Registtro` is an implementation of that structure, which allows for proper garbage collection of the keys/entries,
while still allowing to store their states in a centralized, immutable structure.

Example
-------
Simple implementation of an undoable store that keeps track of states for entries.

.. code:: python

    >>> from registtro import Registry
    >>> class Store(object):
    ...     """Keeps track of the history of states for entries."""
    ...     def __init__(self):
    ...         self._done = [Registry()]
    ...         self._undone = []
    ...     def init(self, entry, state):
    ...         self._done.append(self._done[-1].update({entry: state}))
    ...         del self._done[:-1]
    ...         del self._undone[:]
    ...     def get_state(self, entry):
    ...         return self._done[-1].query(entry)
    ...     def set_state(self, entry, state):
    ...         del self._undone[:]
    ...         self._done.append(self._done[-1].update({entry: state}))
    ...     def undo(self):
    ...         assert len(self._done) > 1, "can't undo"
    ...         self._undone.append(self._done.pop())
    ...     def redo(self):
    ...         assert self._undone, "can't redo"
    ...         self._done.append(self._undone.pop())
    ...
    >>> class Entry(object):
    ...     """Reads/sets state in a store."""
    ...     def __init__(self, store, state):
    ...         self._store = store
    ...         store.init(self, state)
    ...     def get_state(self):
    ...         return self._store.get_state(self)
    ...     def set_state(self, state):
    ...         self._store.set_state(self, state)
    ...
    >>> # Initialize entries.
    >>> global_store = Store()
    >>> entry_a = Entry(global_store, "foo")
    >>> entry_b = Entry(global_store, "bar")
    >>> (entry_a.get_state(), entry_b.get_state())
    ('foo', 'bar')
    >>> # Modify entries.
    >>> entry_a.set_state("FOO")
    >>> entry_b.set_state("BAR")
    >>> (entry_a.get_state(), entry_b.get_state())
    ('FOO', 'BAR')
    >>> # Undo modifications.
    >>> global_store.undo()
    >>> (entry_a.get_state(), entry_b.get_state())
    ('FOO', 'bar')
    >>> global_store.undo()
    >>> (entry_a.get_state(), entry_b.get_state())
    ('foo', 'bar')
    >>> # Redo modifications.
    >>> global_store.redo()
    >>> (entry_a.get_state(), entry_b.get_state())
    ('FOO', 'bar')
    >>> global_store.redo()
    >>> (entry_a.get_state(), entry_b.get_state())
    ('FOO', 'BAR')
