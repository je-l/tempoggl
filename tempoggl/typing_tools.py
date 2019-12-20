from typing import NoReturn


def unreachable(a: NoReturn) -> NoReturn:
    """Use for narrowing down Union types."""
    raise RuntimeError('illegal state, reached unreachable point')
