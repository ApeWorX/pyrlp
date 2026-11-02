import pytest
import binascii

from eth_utils import (
    int_to_big_endian,
)

import rlp
from rlp import (
    DeserializationError,
    SerializationError,
)
from rlp.sedes import (
    BigEndianInt,
    List,
    big_endian_int,
    binary,
)
from rlp.utils import (
    ALL_BYTES,
)

valid_data = (
    (256, b"\x01\x00"),
    (1024, b"\x04\x00"),
    (65535, b"\xff\xff"),
)

single_bytes = ((n, ALL_BYTES[n]) for n in range(1, 256))

random_integers = (
    256,
    257,
    4839,
    849302,
    483290432,
    483290483290482039482039,
    48930248348219540325894323584235894327865439258743754893066,
)
assert random_integers[-1] < 2**256

negative_ints = (-1, -100, -255, -256, -2342423)


def test_neg():
    for n in negative_ints:
        with pytest.raises(SerializationError):
            big_endian_int.serialize(n)


@pytest.mark.parametrize("value", [True, False])
def test_rejects_bool(value):
    with pytest.raises(SerializationError):
        big_endian_int.serialize(value)


def test_serialization():
    for n in random_integers:
        serial = big_endian_int.serialize(n)
        deserialized = big_endian_int.deserialize(serial)
        assert deserialized == n
        if n != 0:
            assert serial[0] != b"\x00"  # is not checked


def test_single_byte():
    for n, s in single_bytes:
        serial = big_endian_int.serialize(n)
        assert serial == s
        deserialized = big_endian_int.deserialize(serial)
        assert deserialized == n


def test_valid_data():
    for n, serial in valid_data:
        serialized = big_endian_int.serialize(n)
        deserialized = big_endian_int.deserialize(serial)
        assert serialized == serial
        assert deserialized == n


def test_fixedlength():
    s = BigEndianInt(4)
    for i in (0, 1, 255, 256, 256**3, 256**4 - 1):
        assert len(s.serialize(i)) == 4
        assert s.deserialize(s.serialize(i)) == i
    for i in (256**4, 256**4 + 1, 256**5, -1, -256, "asdf"):
        with pytest.raises(SerializationError):
            s.serialize(i)


@pytest.mark.parametrize("serial", [[], (), [b""], [b"\x05"], [[]], [b"\x01", b"\x02"]])
@pytest.mark.parametrize("sedes", [big_endian_int, BigEndianInt(1), BigEndianInt(2)])
def test_deserialize_rejects_lists(sedes, serial):
    with pytest.raises(DeserializationError, match="cannot be deserialized"):
        sedes.deserialize(serial)


@pytest.mark.parametrize(
    "encoded",
    [
        b"\xc1\xc0",  # [[]]: an empty list where an integer is expected
        b"\xc2\xc1\x05",  # [[0x05]]
        b"\xc2\xc1\x80",  # [[b""]]
    ],
)
def test_decode_rejects_list_in_integer_field(encoded):
    with pytest.raises(DeserializationError):
        rlp.decode(encoded, List([big_endian_int]))


def test_decode_serializable_rejects_list_in_integer_field():
    class Tx(rlp.Serializable):
        fields = [("nonce", big_endian_int), ("to", binary)]

    canonical = rlp.encode(Tx(0, b"\x11" * 20))
    assert rlp.decode(canonical, Tx).nonce == 0

    # same payload with the nonce encoded as an empty list (0xc0) instead of 0x80
    nonce_as_list = rlp.encode([[], b"\x11" * 20])
    assert nonce_as_list != canonical
    with pytest.raises(DeserializationError):
        rlp.decode(nonce_as_list, Tx)


def packl(lnum):
    """Packs the lnum (which must be convertable to a long) into a
    byte string 0 padded to a multiple of padmultiple bytes in size. 0
    means no padding whatsoever, so that packing 0 result in an empty
    string.  The resulting byte string is the big-endian two's
    complement representation of the passed in long.
    """
    if lnum == 0:
        return b"\0"
    s = hex(lnum)[2:]
    s = s.rstrip("L")
    if len(s) & 1:
        s = "0" + s
    s = binascii.unhexlify(s)
    return s


try:
    import ctypes

    PyLong_AsByteArray = ctypes.pythonapi._PyLong_AsByteArray
    PyLong_AsByteArray.argtypes = [
        ctypes.py_object,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_int,
        ctypes.c_int,
    ]
    import sys

    long_start = sys.maxint + 1

    def packl_ctypes(lnum):
        if lnum < long_start:
            return int_to_big_endian(lnum)
        a = ctypes.create_string_buffer(lnum.bit_length() // 8 + 1)
        PyLong_AsByteArray(lnum, a, len(a), 0, 1)
        return a.raw.lstrip(b"\0")

except AttributeError:
    packl_ctypes = packl


def test_packl():
    for i in range(256):
        v = 2**i - 1
        rc = packl_ctypes(v)
        assert rc == int_to_big_endian(v)
        r = packl(v)
        assert r == int_to_big_endian(v)


def perf():
    import time

    st = time.time()
    for _ in range(100000):
        for i in random_integers:
            packl(i)
    print(f"packl elapsed {time.time() - st}")

    st = time.time()
    for _ in range(100000):
        for i in random_integers:
            packl_ctypes(i)
    print(f"ctypes elapsed {time.time() - st}")

    st = time.time()
    for _ in range(100000):
        for i in random_integers:
            int_to_big_endian(i)
    print(f"py elapsed {time.time() - st}")


if __name__ == "__main__":
    # test_packl()
    perf()
