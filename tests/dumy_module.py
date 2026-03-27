MY_VAR = "original"

STRING = "a string"
FLOAT = 3.14
INT = 42
BOOL = True
NONE = None


def original_func() -> str:
    return "original"


def func_two_params(x: int, y: str) -> bool:
    return bool(x) and bool(y)


def func_one_int_param(x: int) -> None:
    pass


def func_int_to_str(x: int) -> str:
    return str(x)


class DummyClass:
    def method(self) -> str:
        return "original"
