import pytest

from rlp import (
    DeserializationError,
    SerializationError,
    infer_sedes,
)
from rlp.sedes import (
    CountableList,
    List,
    big_endian_int,
    binary,
    boolean,
    text,
)


@pytest.mark.parametrize(
    "value,expected",
    (
        (5, big_endian_int),
        (0, big_endian_int),
        (-1, None),
        (True, boolean),
        (False, boolean),
        (None, None),
        (b"", binary),
        (b"asdf", binary),
        (b"\xe4\xf6\xfc\xea\xe2\xfb", binary),
        ("", text),
        ("asdf", text),
        ("\xe4\xf6\xfc\xea\xe2\xfb", text),
        ("你好世界", text),
        ("\u4f60\u597d\u4e16\u754c", text),
        ([], List()),
        ([1, 2, 3], List((big_endian_int,) * 3)),
        ([[], b"asdf"], List(([], binary))),
        ([1, "asdf"], List((big_endian_int, text))),
    ),
)
def test_inference(value, expected):
    if expected is not None:
        inferred = infer_sedes(value)
        assert inferred == expected
        expected.serialize(value)
    else:
        with pytest.raises(TypeError):
            infer_sedes(value)


@pytest.mark.parametrize("element", ["Hat", "", b"", bytearray()])
@pytest.mark.parametrize("nested", [False, True])
def test_list_sedes_rejects_string_and_binary_elements(element, nested):
    elements = [[element]] if nested else [element]
    with pytest.raises(TypeError, match="sedes objects"):
        List(elements)


def test_list_sedes():
    l1 = List()
    l2 = List((big_endian_int, big_endian_int))
    l3 = List((l1, l2, [[[]]]))

    l1.serialize([])
    l2.serialize((2, 3))
    l3.serialize([[], [5, 6], [[[]]]])

    with pytest.raises(SerializationError):
        l1.serialize([[]])
    with pytest.raises(SerializationError):
        l1.serialize([5])

    for d in ([], [1, 2, 3], [1, [2, 3], 4]):
        with pytest.raises(SerializationError):
            l2.serialize(d)
    for d in ([], [[], [], [[[]]]], [[], [5, 6], [[]]]):
        with pytest.raises(SerializationError):
            l3.serialize(d)

    c = CountableList(big_endian_int)
    assert l1.deserialize(c.serialize([])) == ()
    for s in (c.serialize(length) for length in [[1], [1, 2, 3], range(30), (4, 3)]):
        with pytest.raises(DeserializationError):
            l1.deserialize(s)

    valid = [(1, 2), (3, 4), (9, 8)]
    for s, v in ((c.serialize(v), v) for v in valid):
        assert l2.deserialize(s) == v
    invalid = [[], [1], [1, 2, 3]]
    for s in (c.serialize(i) for i in invalid):
        with pytest.raises(DeserializationError):
            l2.deserialize(s)
