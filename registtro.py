from typing import Dict, Optional, Mapping, Generic, TypeVar, cast
from weakref import ReferenceType, WeakSet, ref
from functools import partial
from copy import deepcopy

from basicco import final
from pyrsistent import pmap
from pyrsistent.typing import PMap, PMapEvolver

from ._base import Base

__all__ = ["Registry", "Evolver"]


KT = TypeVar("KT")
VT = TypeVar("VT")


@final
class Registry(Base, Generic[KT, VT]):
    __slots__ = ("__previous", "__registries", "__data")

    def __init__(self, initial: Optional[Mapping[KT, VT]] = None) -> None:
        self.__previous: Optional[ReferenceType[Registry[KT, VT]]] = None
        self.__registries: WeakSet[Registry[KT, VT]] = WeakSet({self})
        self.__data = cast(PMapEvolver[ReferenceType[KT], VT], pmap().evolver())
        if initial is not None:
            self.__initialize(initial)

    def __contains__(self, key: KT) -> bool:
        return ref(key) in self.__data.persistent()

    def __reduce__(self):
        return type(self), (self.to_dict(),)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        try:
            deep_copy = memo[id(self)]
        except KeyError:
            deep_copy_args = self.to_dict(), memo
            deep_copy = memo[id(self)] = Registry(deepcopy(*deep_copy_args))
        return deep_copy

    def __copy__(self):
        return self

    @staticmethod
    def __clean(registries: WeakSet[Registry[KT, VT]], weak_key: ReferenceType[KT]) -> None:
        for registry in registries:
            del registry.__data[weak_key]

    def __initialize(self, initial: Mapping[KT, VT]) -> None:
        temp_registry = self.update(initial)
        self.__registries = registries = temp_registry.__registries
        registries.clear()
        registries.add(self)
        self.__data = temp_registry.__data

    def update(self, updates: Mapping[KT, VT]) -> Registry[KT, VT]:
        if not updates:
            return self

        registry = Registry.__new__(Registry)
        registry.__previous = ref(self)
        registry.__registries = registries = WeakSet({registry})

        # Update weak references.
        weak_updates = {}
        for key, entry in updates.items():
            weak_key = ref(key, partial(Registry.__clean, registries))
            weak_updates[weak_key] = entry
        if not weak_updates:
            return self

        # Update previous registries.
        previous: Optional[Registry[KT, VT]] = self
        while previous is not None:
            previous.__registries.add(registry)
            if previous.__previous is None:
                break
            previous = previous.__previous()

        registry.__data = self.__data.persistent().update(weak_updates).evolver()

        return registry

    def query(self, key: KT) -> VT:
        return self.__data[ref(key)]

    def to_dict(self) -> Dict[KT, VT]:
        to_dict = {}
        for weak_key, data in self.__data.persistent().items():
            key = weak_key()
            if key is not None:
                to_dict[key] = data
        return to_dict

    def get_evolver(self) -> Evolver[KT, VT]:
        return Evolver(self)


@final
class Evolver(Base, Generic[KT, VT]):

    __slots__ = ("__registry", "__updates")

    def __init__(self, registry: Optional[Registry] = None) -> None:
        if registry is None:
            registry = Registry()
        self.__registry: Registry[KT, VT] = registry
        self.__updates: PMap[KT, VT] = pmap()

    def __contains__(self, key: KT) -> bool:
        return key in self.__updates or key in self.__registry

    def __reduce__(self):
        return _evolver_reducer, (self.__registry, self.__updates)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        try:
            deep_copy = memo[id(self)]
        except KeyError:
            deep_copy = memo[id(self)] = Evolver.__new__(Evolver)
            deep_copy_args_a = self.__registry, memo
            deep_copy.__registry = deepcopy(*deep_copy_args_a)
            deep_copy_args_b = self.__updates, memo
            deep_copy.__updates = deepcopy(*deep_copy_args_b)
        return deep_copy

    def __copy__(self):
        return self.fork()

    def update(self, updates: Mapping[KT, VT]) -> Evolver[KT, VT]:
        self.__updates = self.__updates.update(updates)
        return self

    def query(self, key: KT) -> VT:
        try:
            return self.__updates[key]
        except KeyError:
            return self.__registry.query(key)

    def to_dict(self) -> Dict[KT, VT]:
        return self.get_registry().to_dict()

    def get_registry(self) -> Registry[KT, VT]:
        return self.__registry.update(self.__updates)

    def fork(self) -> Evolver[KT, VT]:
        evolver = Evolver.__new__(Evolver)
        evolver.__registry = self.__registry
        evolver.__updates = self.__updates
        return evolver

    def is_dirty(self) -> bool:
        return bool(self.__updates)

    def reset(self):
        self.__updates = pmap()

    def commit(self):
        self.__registry = self.__registry.update(self.__updates)
        self.__updates = pmap()

    @property
    def updates(self) -> PMap[KT, VT]:
        return self.__updates


def _evolver_reducer(registry: Registry[KT, VT], updates: Mapping[KT, VT]) -> Evolver:
    evolver: Evolver[KT, VT] = Evolver(registry)
    evolver.update(updates)
    return evolver
