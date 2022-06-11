import functools
import copy
import weakref
from typing import Dict, Optional, Mapping, Generic, TypeVar, Protocol, runtime_checkable, cast, final

import pyrsistent
from pyrsistent.typing import PMap, PMapEvolver

__all__ = ["RegistryProtocol", "Registry", "RegistryEvolver"]


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


@final
@runtime_checkable
class RegistryProtocol(Protocol[_KT, _VT]):
    def update(self, updates: Mapping[_KT, _VT]) -> "RegistryProtocol[_KT, _VT]":
        ...

    def query(self, key: _KT) -> _VT:
        ...

    def get(self, key: _KT, fallback: Optional[_VT] = None) -> Optional[_VT]:
        ...

    def to_dict(self) -> Dict[_KT, _VT]:
        ...


@final
class Registry(Generic[_KT, _VT]):
    __slots__ = ("__weakref__", "__previous", "__registries", "__data")

    def __init__(self, initial: Optional[Mapping[_KT, _VT]] = None) -> None:
        self.__previous: Optional[weakref.ReferenceType[Registry[_KT, _VT]]] = None
        self.__registries: weakref.WeakSet[Registry[_KT, _VT]] = weakref.WeakSet({self})
        self.__data = cast(PMapEvolver[weakref.ReferenceType[_KT], _VT], pyrsistent.pmap().evolver())
        if initial is not None:
            self.__initialize(initial)

    def __contains__(self, key: _KT) -> bool:
        return weakref.ref(key) in self.__data.persistent()

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
    def __clean(registries: weakref.WeakSet["Registry[_KT, _VT]"], weak_key: weakref.ReferenceType[_KT]) -> None:
        for registry in registries:
            del registry.__data[weak_key]

    def __initialize(self, initial: Mapping[_KT, _VT]) -> None:
        temp_registry = self.update(initial)
        self.__registries = registries = temp_registry.__registries
        registries.clear()
        registries.add(self)
        self.__data = temp_registry.__data

    def update(self, updates: Mapping[_KT, _VT]) -> "Registry[_KT, _VT]":
        if not updates:
            return self

        registry = Registry.__new__(Registry)
        registry.__previous = weakref.ref(self)
        registry.__registries = registries = weakref.WeakSet({registry})

        # Update weak references.
        weak_updates = {}
        for key, entry in updates.items():
            weak_key = weakref.ref(key, functools.partial(Registry.__clean, registries))
            weak_updates[weak_key] = entry
        if not weak_updates:
            return self

        # Update previous registries.
        previous: Optional[Registry[_KT, _VT]] = self
        while previous is not None:
            previous.__registries.add(registry)
            if previous.__previous is None:
                break
            previous = previous.__previous()

        registry.__data = self.__data.persistent().update(weak_updates).evolver()

        return registry

    def query(self, key: _KT) -> _VT:
        return self.__data[weakref.ref(key)]

    def get(self, key: _KT, fallback: Optional[_VT] = None) -> Optional[_VT]:
        try:
            return self.query(key)
        except KeyError:
            return fallback

    def to_dict(self) -> Dict[_KT, _VT]:
        to_dict = {}
        for weak_key, data in self.__data.persistent().items():
            key = weak_key()
            if key is not None:
                to_dict[key] = data
        return to_dict

    def get_evolver(self) -> "RegistryEvolver[_KT, _VT]":
        return RegistryEvolver(self)


@final
class RegistryEvolver(Generic[_KT, _VT]):

    __slots__ = ("__weakref__", "__registry", "__updates")

    def __init__(self, registry: Optional[Registry] = None) -> None:
        if registry is None:
            registry = Registry()
        self.__registry: Registry[_KT, _VT] = registry
        self.__updates: PMap[_KT, _VT] = pyrsistent.pmap()

    def __contains__(self, key: _KT) -> bool:
        return key in self.__updates or key in self.__registry

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

    def update(self, updates: Mapping[_KT, _VT]) -> "RegistryEvolver[_KT, _VT]":
        self.__updates = self.__updates.update(updates)
        return self

    def query(self, key: _KT) -> _VT:
        try:
            return self.__updates[key]
        except KeyError:
            return self.__registry.query(key)

    def get(self, key: _KT, fallback: Optional[_VT] = None) -> Optional[_VT]:
        try:
            return self.query(key)
        except KeyError:
            return fallback

    def to_dict(self) -> Dict[_KT, _VT]:
        return self.get_registry().to_dict()

    def get_registry(self) -> Registry[_KT, _VT]:
        return self.__registry.update(self.__updates)

    def fork(self) -> "RegistryEvolver[_KT, _VT]":
        evolver = RegistryEvolver.__new__(RegistryEvolver)
        evolver.__registry = self.__registry
        evolver.__updates = self.__updates
        return evolver

    def is_dirty(self) -> bool:
        return bool(self.__updates)

    def reset(self):
        self.__updates = pyrsistent.pmap()

    def commit(self):
        self.__registry = self.__registry.update(self.__updates)
        self.__updates = pyrsistent.pmap()

    @property
    def updates(self) -> PMap[_KT, _VT]:
        return self.__updates


def _evolver_reducer(registry: Registry[_KT, _VT], updates: Mapping[_KT, _VT]) -> RegistryEvolver[_KT, _VT]:
    evolver: RegistryEvolver[_KT, _VT] = RegistryEvolver(registry)
    evolver.update(updates)
    return evolver
