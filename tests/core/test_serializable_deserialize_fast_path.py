import pytest
import pickle

import rlp
from rlp.exceptions import ObjectDeserializationError
from rlp.sedes import List, Serializable, big_endian_int, binary
from rlp.sedes.serializable import BaseSerializable, SerializableBase


class Child(Serializable):
    fields = (("number", big_endian_int), ("payload", binary))


class Parent(Serializable):
    fields = (
        ("child", Child),
        ("pair", List((Child, Child))),
    )


class IntermediateOverride(Child):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class InheritedOverride(IntermediateOverride):
    pass


class NewOnlyOverride(Child):
    def __new__(cls, *, number, payload):
        return super().__new__(cls)


class RecordingNewOverride(Child):
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.call_form = (args, kwargs)
        return obj


class KeywordOnlyMeta(SerializableBase):
    def __call__(cls, **kwargs):
        return super().__call__(**kwargs)


class CustomMetaclass(Child, metaclass=KeywordOnlyMeta):
    pass


@pytest.fixture
def child_serial():
    return Child.serialize(Child(7, b"payload"))


def test_default_deserialize_preserves_object_operations(child_serial):
    decoded = Child.deserialize(child_serial)

    assert Child.__init__ is BaseSerializable.__init__
    assert decoded == Child(7, b"payload")
    assert decoded.as_dict() == {"number": 7, "payload": b"payload"}
    assert decoded.copy() == decoded
    assert hash(decoded) == hash(Child(7, b"payload"))
    assert pickle.loads(pickle.dumps(decoded)) == decoded


def test_deserialize_nested_serializable_fields():
    value = Parent(Child(1, b"one"), [Child(2, b"two"), Child(3, b"three")])
    decoded = Parent.deserialize(Parent.serialize(value))

    assert decoded == value
    assert decoded.as_dict() == value.as_dict()
    assert decoded.copy() == value


def test_intermediate_init_override_uses_compatibility_path(child_serial):
    decoded = InheritedOverride.deserialize(child_serial)

    assert decoded == InheritedOverride(7, b"payload")


def test_new_only_override_preserves_keyword_call(child_serial):
    decoded = NewOnlyOverride.deserialize(child_serial)

    assert decoded == NewOnlyOverride(number=7, payload=b"payload")


def test_custom_new_receives_fields_as_keywords(child_serial):
    decoded = RecordingNewOverride.deserialize(child_serial)

    assert decoded.call_form == ((), {"number": 7, "payload": b"payload"})


def test_custom_metaclass_preserves_keyword_call(child_serial):
    decoded = CustomMetaclass.deserialize(child_serial)

    assert decoded == CustomMetaclass(number=7, payload=b"payload")


def test_extra_kwargs_keep_existing_constructor_validation(child_serial):
    with pytest.raises(TypeError) as excinfo:
        Child.deserialize(child_serial, marker=1)

    assert str(excinfo.value) == "Unknown kwargs: ['marker']"


@pytest.mark.parametrize(
    "serial", [rlp.encode([7]), rlp.encode([7, b"payload", b"extra"])]
)
def test_wrong_field_count_keeps_error(serial):
    with pytest.raises(ObjectDeserializationError) as excinfo:
        rlp.decode(serial, Child)

    assert "Deserializing list length" in str(excinfo.value)
