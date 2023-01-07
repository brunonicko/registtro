import copy
import gc
import pickle

import pytest

from registtro import Registry, RegistryEvolver, RegistryProtocol


@pytest.mark.parametrize("cls", (Registry, RegistryEvolver))
def test_protocol(cls):
    try:
        from typing import runtime_checkable
    except ImportError:
        pass
    else:
        assert issubclass(cls, RegistryProtocol)

    class Entry:
        pass

    entry_a = Entry()
    entry_b = Entry()
    self = cls()

    self = self.update({entry_a: 1})
    assert self.query(entry_a) == 1
    assert self.get(entry_b) is None

    self = self.update({entry_b: 2})
    assert self.query(entry_a) == 1
    assert self.query(entry_b) == 2

    assert len(self.to_dict()) == 2
    assert self.to_dict() == {entry_a: 1, entry_b: 2}


def test_static_protocol():
    # type: () -> None
    _reg_a = Registry()  # type: RegistryProtocol  # noqa
    _reg_b = RegistryEvolver()  # type: RegistryProtocol  # noqa


def test_registry_garbage_collection():
    class Entry:
        pass

    entry_a = Entry()
    entry_b = Entry()
    entry_c = Entry()
    registry_a = Registry({entry_a: 1})
    registry_b = registry_a.update({entry_b: 2})
    registry_c = registry_b.update({entry_c: 3})

    del entry_a
    gc.collect()

    assert registry_a.to_dict() == {}
    assert registry_b.to_dict() == {entry_b: 2}
    assert registry_c.to_dict() == {entry_b: 2, entry_c: 3}

    del entry_b
    gc.collect()

    assert registry_a.to_dict() == {}
    assert registry_b.to_dict() == {}
    assert registry_c.to_dict() == {entry_c: 3}

    del entry_c
    gc.collect()

    assert registry_a.to_dict() == {}
    assert registry_b.to_dict() == {}
    assert registry_c.to_dict() == {}


def test_evolver_garbage_collection():
    class Entry:
        pass

    entry_a = Entry()
    entry_b = Entry()
    entry_c = Entry()
    registry = Registry({entry_a: 1})

    evolver = registry.get_evolver()
    evolver.update({entry_b: 2, entry_c: 3})
    assert evolver.is_dirty()

    del entry_a, entry_b, entry_c
    gc.collect()

    assert len(evolver.to_dict()) == 2

    evolver.commit()
    gc.collect()

    assert not evolver.is_dirty()
    assert not evolver.to_dict()


def test_registry_evolver_roundtrip():
    class Entry:
        pass

    entry_a = Entry()
    entry_b = Entry()
    entry_c = Entry()
    registry = Registry({entry_a: 1, entry_b: 2})

    evolver = RegistryEvolver(registry)
    assert registry.to_dict() == evolver.to_dict()

    evolver.update({entry_c: 3})
    assert registry.to_dict() != evolver.to_dict()

    new_evolver = evolver.fork()
    evolver.reset()
    assert registry.to_dict() == evolver.to_dict()

    new_registry = new_evolver.get_registry()
    assert new_registry.to_dict() == new_evolver.to_dict()
    assert new_registry.to_dict() == {entry_a: 1, entry_b: 2, entry_c: 3}


@pytest.mark.parametrize("deep_copier", (copy.deepcopy, lambda s: pickle.loads(pickle.dumps(s))))
def test_deep_copy_and_pickle_registry(deep_copier):
    class _Entry:
        __name__ = __qualname__ = "_Entry"

        def __init__(self, name):
            self.name = name

        def __hash__(self):
            return hash(self.name)

        def __eq__(self, other):
            return other.name == self.name

    globals()[_Entry.__name__] = _Entry

    entry_a = _Entry("a")
    entry_b = _Entry("b")
    entry_c = _Entry("c")
    entry_d = _Entry("d")
    entries = entry_a, entry_b, entry_c
    registry = Registry({entry_a: 1, entry_b: 2, entry_c: 3, entry_d: 4})

    copied_entries, copied_registry = deep_copier((entries, registry))
    truth_dict = registry.to_dict()
    del truth_dict[entry_d]
    assert copied_registry.to_dict() == truth_dict


@pytest.mark.parametrize("deep_copier", (copy.deepcopy, lambda s: pickle.loads(pickle.dumps(s))))
def test_deep_copy_and_pickle_evolver(deep_copier):
    class _Entry:
        __name__ = __qualname__ = "_Entry"

        def __init__(self, name):
            self.name = name

        def __hash__(self):
            return hash(self.name)

        def __eq__(self, other):
            return other.name == self.name

    globals()[_Entry.__name__] = _Entry

    entry_a = _Entry("a")
    entry_b = _Entry("b")
    entry_c = _Entry("c")
    entry_d = _Entry("d")
    entries = (entry_a,)
    evolver = Registry({entry_a: 1, entry_d: 4}).get_evolver().update({entry_b: 2, entry_c: 3})

    copied_entries, copied_evolver = deep_copier((entries, evolver))
    assert len(copied_evolver.to_dict()) == 3
    truth_dict = evolver.to_dict()
    del truth_dict[entry_d]
    assert copied_evolver.to_dict() == truth_dict


def test_shallow_copy_registry():
    class Entry:
        pass

    entry_a = Entry()
    registry = Registry({entry_a: 1})

    assert copy.copy(registry) is registry


def test_shallow_copy_evolver():
    class Entry:
        pass

    entry_a = Entry()
    evolver = Registry({entry_a: 1}).get_evolver()
    evolver_copy = copy.copy(evolver)
    evolver_forked = evolver.fork()

    assert evolver_copy is not evolver is not evolver_forked
    assert evolver_copy.to_dict() == evolver.to_dict() == evolver_forked.to_dict()


if __name__ == "__main__":
    pytest.main()
