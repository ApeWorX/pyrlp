from rlp import (
    decode,
    decode_lazy,
    encode,
)


def test_memoryview():
    e = encode(b"abc")
    expected = decode(e)
    actual = decode(memoryview(e))
    assert actual == expected


def test_memoryview_lazy():
    e = encode(b"abc")
    expected = decode(e)
    actual = decode_lazy(memoryview(e))
    assert expected == actual


def test_memoryview_nested_list():
    e = encode([b"cat", b"dog", [b"nested", b""]])
    assert decode(memoryview(e)) == decode(e)
