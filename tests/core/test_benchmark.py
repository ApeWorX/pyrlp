import pytest
from itertools import (
    chain,
    repeat,
)
import sys

import rlp
from rlp.exceptions import (
    DecodingError,
    DeserializationError,
)
from rlp.sedes import (
    CountableList,
    binary,
)

try:
    import pytest_benchmark  # noqa: F401
except ImportError:
    do_benchmark = False
else:
    do_benchmark = True


# speed up setup in case tests aren't run anyway
if do_benchmark:
    SIZE = int(1e6)
else:
    SIZE = 1


class Message(rlp.Serializable):
    fields = [
        ("field1", binary),
        ("field2", binary),
        ("field3", CountableList(binary, max_length=100)),
    ]


def lazy_test_factory(s, valid):
    @pytest.mark.benchmark(group="lazy")
    def f(benchmark):
        @benchmark
        def result():
            try:
                Message.deserialize(rlp.decode_lazy(s))
            except (DecodingError, DeserializationError):
                return not valid
            else:
                return valid

        assert result

    return f


def eager_test_factory(s, valid):
    @pytest.mark.benchmark(group="eager")
    def f(benchmark):
        @benchmark
        def result():
            try:
                rlp.decode(s, Message)
            except (DecodingError, DeserializationError):
                return not valid
            else:
                return valid

        assert result

    return f


def generate_test_functions():
    valid = {}
    invalid = {}
    long_string = bytes(bytearray(i % 256 for i in range(SIZE)))
    long_list = rlp.encode([c for c in long_string])
    invalid["long_string"] = long_string
    invalid["long_list"] = long_list

    nested_list = rlp.encode(b"\x00")
    for _ in repeat(None, SIZE):
        nested_list += rlp.codec.length_prefix(len(nested_list), 0xC0)
    invalid["nested_list"] = nested_list

    valid["long_string_object"] = rlp.encode([b"\x00", long_string, []])

    prefix = rlp.codec.length_prefix(1 + 1 + len(long_list), 0xC0)
    invalid["long_list_object"] = (
        prefix + rlp.encode(b"\x00") + rlp.encode(b"\x00") + long_list
    )

    valid["friendly"] = rlp.encode(
        Message(
            b"hello",
            b"I'm friendly",
            [b"not", b"many", b"elements"],
        )
    )

    invalid = invalid.items()
    valid = valid.items()
    rlp_strings = [i[1] for i in chain(valid, invalid)]
    valids = [True] * len(valid) + [False] * len(invalid)
    names = [i[0] for i in chain(valid, invalid)]

    current_module = sys.modules[__name__]
    for rlp_string, valid, name in zip(rlp_strings, valids, names):
        f_eager = pytest.mark.skipif("not do_benchmark")(
            eager_test_factory(rlp_string, valid)
        )
        f_lazy = pytest.mark.skipif("not do_benchmark")(
            lazy_test_factory(rlp_string, valid)
        )
        setattr(current_module, "test_eager_" + name, f_eager)
        setattr(current_module, "test_lazy_" + name, f_lazy)


generate_test_functions()


@pytest.mark.skipif(not do_benchmark, reason="pytest-benchmark is not installed")
@pytest.mark.benchmark(group="eager-wide-list")
@pytest.mark.parametrize("num_items", [8, 1000, 4000])
def test_eager_wide_list(benchmark, num_items):
    items = [b"x" * 32] * num_items
    encoded = rlp.encode(items)
    assert benchmark(rlp.decode, encoded) == items
