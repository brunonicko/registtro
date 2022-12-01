import copy
import functools

import pyrsistent
import six
from basicco import SlottedBase, runtime_final
from pyrsistent.typing import PMap, PMapEvolver
from tippo import (
    AbstractSet,
    Dict,
    Generic,
    Mapping,
    TypeVar,
    Union,
    WeakSet,
    cast,
    ref,
)

from ._exceptions import EntryNotFoundError

_ET = TypeVar("_ET")
_VT = TypeVar("_VT")
_ST = TypeVar("_ST")


@runtime_final.final
class Registry(SlottedBase, Generic[_ET, _VT]):
    """Immutable weak entry/strong value registry."""

    __slots__ = ("__previous", "__registries", "__data")

    def __init__(self, initial=None):
        # type: (Union[Mapping[_ET, _VT], None]) -> None
        self.__previous = None  # type: Union[ref[Registry[_ET, _VT]], None]
        self.__registries = WeakSet({self})  # type: WeakSet[Registry[_ET, _VT]]
        self.__data = cast(PMapEvolver[ref[_ET], _VT], pyrsistent.pmap().evolver())
        if initial is not None:
            self.__initialize(initial)

    def __contains__(self, entry):
        # type: (object) -> bool
        return ref(entry) in self.__data.persistent()

    def __reduce__(self):
        return type(self), (self.to_dict(),)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        try:
            deep_copy = memo[id(self)]
        except KeyError:
            deep_copy = memo[id(self)] = Registry(copy.deepcopy(self.to_dict(), memo))
        return deep_copy

    def __copy__(self):
        return self

    @staticmethod
    def __clean(registries, weak_key):
        # type: (AbstractSet[Registry[_ET, _VT]], ref[_ET]) -> None
        for registry in registries:
            del registry.__data[weak_key]

    def __initialize(self, initial):
        # type: (Mapping[_ET, _VT]) -> None
        temp_registry = self.update(initial)
        self.__registries = registries = temp_registry.__registries
        registries.clear()
        registries.add(self)
        self.__data = temp_registry.__data

    def update(self, updates):
        # type: (Mapping[_ET, _VT]) -> Registry[_ET, _VT]
        """Update entries."""
        if not updates:
            return self

        registry = Registry.__new__(Registry)
        registry.__previous = ref(self)
        registry.__registries = registries = WeakSet({registry})

        # Update weak references.
        weak_updates = {}
        for entry, value in updates.items():
            weak_key = ref(entry, functools.partial(Registry.__clean, registries))
            weak_updates[weak_key] = value
        if not weak_updates:
            return self

        # Update previous registries.
        previous = self  # type: Union[Registry[_ET, _VT], None]
        while previous is not None:
            previous.__registries.add(registry)
            if previous.__previous is None:
                break
            previous = previous.__previous()

        registry.__data = self.__data.persistent().update(weak_updates).evolver()

        return registry

    def query(self, entry):
        # type: (_ET) -> _VT
        """
        Query value for entry.

        :raises EntryNotFoundError: Entry not in the registry.
        """
        try:
            return self.__data[ref(entry)]
        except KeyError:
            exc = EntryNotFoundError(entry)
            six.raise_from(exc, None)
            raise exc

    def get(self, entry, fallback=None):
        # type: (_ET, Union[_VT, None]) -> Union[_VT, None]
        """Get value for entry, return fallback value if not in the registry."""
        try:
            return self.query(entry)
        except EntryNotFoundError:
            return fallback

    def to_dict(self):
        # type: () -> Dict[_ET, _VT]
        """Convert to dictionary."""
        to_dict = {}
        for weak_key, data in self.__data.persistent().items():
            entry = weak_key()
            if entry is not None:
                to_dict[entry] = data
        return to_dict

    def get_evolver(self):
        # type: () -> RegistryEvolver[_ET, _VT]
        """Get mutable evolver."""
        return RegistryEvolver(self)


@runtime_final.final
class RegistryEvolver(SlottedBase, Generic[_ET, _VT]):
    """Mutable registry evolver."""

    __slots__ = ("__registry", "__updates")

    def __init__(self, registry=None):
        # type: (Union[Registry, None]) -> None
        if registry is None:
            registry = Registry()
        self.__registry = registry  # type: Registry[_ET, _VT]
        self.__updates = pyrsistent.pmap()  # type: PMap[_ET, _VT]

    def __contains__(self, entry):
        # type: (object) -> bool
        return entry in self.__updates or entry in self.__registry

    def __reduce__(self):
        return _evolver_reducer, (self.__registry, self.__updates)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        try:
            deep_copy = memo[id(self)]
        except KeyError:
            deep_copy = memo[id(self)] = RegistryEvolver.__new__(RegistryEvolver)
            deep_copy_args_a = self.__registry, memo
            deep_copy.__registry = copy.deepcopy(*deep_copy_args_a)
            deep_copy_args_b = self.__updates, memo
            deep_copy.__updates = copy.deepcopy(*deep_copy_args_b)
        return deep_copy

    def __copy__(self):
        return self.fork()

    def update(self, updates):
        # type: (Mapping[_ET, _VT]) -> RegistryEvolver[_ET, _VT]
        """Update entries."""
        self.__updates = self.__updates.update(updates)
        return self

    def query(self, entry):
        # type: (_ET) -> _VT
        """
        Query value for entry.

        :raises EntryNotFoundError: Entry not in the registry.
        """
        try:
            return self.__updates[entry]
        except KeyError:
            try:
                return self.__registry.query(entry)
            except EntryNotFoundError:
                exc = EntryNotFoundError(entry)
                six.raise_from(exc, None)
                raise exc

    def get(self, entry, fallback=None):
        # type: (_ET, Union[_VT, None]) -> Union[_VT, None]
        """Get value for entry, return fallback value if not in the registry."""
        try:
            return self.query(entry)
        except EntryNotFoundError:
            return fallback

    def to_dict(self):
        # type: () -> Dict[_ET, _VT]
        """Convert to dictionary."""
        return self.get_registry().to_dict()

    def get_registry(self):
        # type: () -> Registry[_ET, _VT]
        """Get immutable registry."""
        return self.__registry.update(self.__updates)

    def fork(self):
        # type: () -> RegistryEvolver[_ET, _VT]
        """Fork into a new mutable evolver."""
        evolver = RegistryEvolver.__new__(RegistryEvolver)
        evolver.__registry = self.__registry
        evolver.__updates = self.__updates
        return evolver

    def is_dirty(self):
        # type: () -> bool
        """Whether has updates that were not committed."""
        return bool(self.__updates)

    def reset(self):
        """Reset updates to last commit."""
        self.__updates = pyrsistent.pmap()

    def commit(self):
        """Commit updates."""
        self.__registry = self.__registry.update(self.__updates)
        self.__updates = pyrsistent.pmap()

    @property
    def updates(self):
        # type: () -> PMap[_ET, _VT]
        """Updates."""
        return self.__updates


def _evolver_reducer(registry, updates):
    # type: (Registry[_ET, _VT], Mapping[_ET, _VT]) -> RegistryEvolver[_ET, _VT]
    evolver = RegistryEvolver(registry)  # type: RegistryEvolver[_ET, _VT]
    evolver.update(updates)
    return evolver
