import pickle
import copy
import gc

import pytest

from registtro import Registry, RegistryEvolver


@pytest.mark.parametrize("abstract_registry_cls", (Registry, Evolver))
def test_common(abstract_registry_cls):
    class Obj(object):
        pass

    obj_a = Obj()
    obj_b = Obj()
    abstract_registry = abstract_registry_cls()

    abstract_registry = abstract_registry.update({obj_a: 1})
    assert abstract_registry.query(obj_a) == 1
    assert abstract_registry.get(obj_b) is None

    abstract_registry = abstract_registry.update({obj_b: 2})
    assert abstract_registry.query(obj_a) == 1
    assert abstract_registry.query(obj_b) == 2

    assert len(abstract_registry.to_dict()) == 2
    assert abstract_registry.to_dict() == {obj_a: 1, obj_b: 2}


def test_registry_garbage_collection():
    class Obj(object):
        pass

    obj_a = Obj()
    obj_b = Obj()
    obj_c = Obj()
    registry_a = Registry({obj_a: 1})
    registry_b = registry_a.update({obj_b: 2})
    registry_c = registry_b.update({obj_c: 3})

    del obj_a
    collect()

    assert registry_a.to_dict() == {}
    assert registry_b.to_dict() == {obj_b: 2}
    assert registry_c.to_dict() == {obj_b: 2, obj_c: 3}

    del obj_b
    collect()

    assert registry_a.to_dict() == {}
    assert registry_b.to_dict() == {}
    assert registry_c.to_dict() == {obj_c: 3}

    del obj_c
    collect()

    assert registry_a.to_dict() == {}
    assert registry_b.to_dict() == {}
    assert registry_c.to_dict() == {}


def test_evolver_garbage_collection():
    class Obj(object):
        pass

    obj_a = Obj()
    obj_b = Obj()
    obj_c = Obj()
    registry = Registry({obj_a: 1})

    evolver = registry.evolver()
    evolver.update({obj_b: 2, obj_c: 3})
    assert evolver.is_dirty()

    del obj_a, obj_b, obj_c
    collect()

    assert len(evolver.to_dict()) == 2

    evolver.commit()
    collect()

    assert not evolver.is_dirty()
    assert not evolver.to_dict()


def test_registry_evolver_roundtrip():
    class Obj(object):
        pass

    obj_a = Obj()
    obj_b = Obj()
    obj_c = Obj()
    registry = Registry({obj_a: 1, obj_b: 2})

    evolver = Evolver(registry)
    assert registry.to_dict() == evolver.to_dict()

    evolver.update({obj_c: 3})
    assert registry.to_dict() != evolver.to_dict()

    new_evolver = evolver.fork()
    evolver.reset()
    assert registry.to_dict() == evolver.to_dict()

    new_registry = new_evolver.registry()
    assert new_registry.to_dict() == new_evolver.to_dict()
    assert new_registry.to_dict() == {obj_a: 1, obj_b: 2, obj_c: 3}


@pytest.mark.parametrize("deep_copier", (copy.deepcopy, lambda s: pickle.loads(pickle.dumps(s))))
def test_deep_copy_and_pickle_registry(deep_copier):
    class _Obj(object):
        __name__ = __qualname__ = "_Obj"

        def __init__(self, name):
            self.name = name

        def __hash__(self):
            return hash(self.name)

        def __eq__(self, other):
            return other.name == self.name

    globals()[_Obj.__name__] = _Obj

    obj_a = _Obj("a")
    obj_b = _Obj("b")
    obj_c = _Obj("c")
    obj_d = _Obj("d")
    objects = obj_a, obj_b, obj_c
    registry = Registry({obj_a: 1, obj_b: 2, obj_c: 3, obj_d: 4})

    copied_objects, copied_registry = deep_copier((objects, registry))
    truth_dict = registry.to_dict()
    del truth_dict[obj_d]
    assert copied_registry.to_dict() == truth_dict


@pytest.mark.parametrize("deep_copier", (copy.deepcopy, lambda s: pickle.loads(pickle.dumps(s))))
def test_deep_copy_and_pickle_evolver(deep_copier):
    class _Obj(object):
        __name__ = __qualname__ = "_Obj"

        def __init__(self, name):
            self.name = name

        def __hash__(self):
            return hash(self.name)

        def __eq__(self, other):
            return other.name == self.name

    globals()[_Obj.__name__] = _Obj

    obj_a = _Obj("a")
    obj_b = _Obj("b")
    obj_c = _Obj("c")
    obj_d = _Obj("d")
    objects = obj_a,
    evolver = Registry({obj_a: 1, obj_d: 4}).evolver().update({obj_b: 2, obj_c: 3})

    copied_objects, copied_evolver = deep_copier((objects, evolver))
    assert len(copied_evolver.to_dict()) == 3
    truth_dict = evolver.to_dict()
    del truth_dict[obj_d]
    assert copied_evolver.to_dict() == truth_dict


def test_shallow_copy_registry():
    class Obj(object):
        pass

    obj_a = Obj()
    registry = Registry({obj_a: 1})

    assert copy.copy(registry) is registry


def test_shallow_copy_evolver():
    class Obj(object):
        pass

    obj_a = Obj()
    evolver = Registry({obj_a: 1}).evolver()
    evolver_copy = copy.copy(evolver)
    evolver_forked = evolver.fork()

    assert evolver_copy is not evolver is not evolver_forked
    assert evolver_copy.to_dict() == evolver.to_dict() == evolver_forked.to_dict()


if __name__ == "__main__":
    pytest.main()
