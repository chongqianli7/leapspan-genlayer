import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace


class UserError(Exception):
    pass


def eq(fn):
    first = fn()
    if fn() != first:
        raise UserError("NO_CONSENSUS")
    return first


def load(name):
    host = ModuleType("genlayer")
    host.TreeMap = dict
    host.u32 = host.u64 = int
    identity = lambda fn: fn
    host.gl = SimpleNamespace(
        Contract=object, UserError=UserError,
        public=SimpleNamespace(view=identity, write=identity),
        message=SimpleNamespace(sender_address="0x" + "1"*40),
        eq_principle=SimpleNamespace(strict_eq=eq),
        nondet=SimpleNamespace(web=SimpleNamespace()),
    )
    sys.modules["genlayer"] = host
    path = Path(__file__).parents[1] / "contracts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return host.gl, module
