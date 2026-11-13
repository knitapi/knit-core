"""Flow names on top of the runner's existing sync-named SDK, without changing the live code.

The runner's weavex_core already has working, live implementations that use `sync_id`, `get_sync_state`, `log_sync_event` and
so on. Agents now write against the flow names (`flow_id`, `get_state_store`, `log_flow_event`, ...). This file puts the
flow names in front of the live code: every call is passed straight through, so storage, keys and behaviour do not change.

What the wrapper does, for each object a factory returns (the state store, the object store, the logger):
  * a method called by its flow name is run as the live method (`get_flow_hash` -> `get_sync_hash`)
  * a keyword argument `flow_id=` is passed as `sync_id=` when the live method has that parameter
  * anything else, including the old names, passes through unchanged, so flows already deployed keep working
  * the method signatures it shows (inspect.signature) use the flow names, so tests/test_public_surface.py can run
    against weavex_core (SURFACE_MODULE=weavex_core) and still check the names agents see

Positional calls need no translation at all, which is why the guide tells agents to pass the ids positionally.

Use it in the runner's weavex_core/__init__.py, after the live names are imported:

    from flow_compat import flow_view, STATE_METHODS, LOGGER_METHODS
    get_state_store = flow_view(get_sync_state, STATE_METHODS)        # a new name over the live function
    get_object_store = flow_view(get_object_store)                    # same name, flow arguments accepted
    get_logger = flow_view(get_logger, LOGGER_METHODS)
    FlowError, TerminalFlowError, TransientFlowError = SyncError, TerminalSyncError, TransientSyncError

(The runner's error classes are the live ones, so the Flow names are simply the same classes. Because the classes are the same
objects, an error raised through either name is caught through either name.)
"""
import functools
import inspect
from typing import Callable, Dict, Optional

# flow name -> the live method it runs
STATE_METHODS: Dict[str, str] = {
    "get_flow_hash": "get_sync_hash",
    "set_flow_hash": "set_sync_hash",
    "delete_flow_hash": "delete_sync_hash",
    "create_flow_hash": "create_sync_hash",
}
LOGGER_METHODS: Dict[str, str] = {
    "log_flow_event": "log_sync_event",
}

_FLOW = "flow_id"
_LIVE = "sync_id"


def _flow_signature(live_fn: Callable) -> Optional[inspect.Signature]:
    """The live method's signature with sync_id shown as flow_id, or None when it cannot be read."""
    try:
        sig = inspect.signature(live_fn)
    except (TypeError, ValueError):
        return None
    params = [p.replace(name=_FLOW) if p.name == _LIVE else p for p in sig.parameters.values()]
    return sig.replace(parameters=params)


def _accepts_live_name(live_fn: Callable) -> bool:
    try:
        params = inspect.signature(live_fn).parameters
    except (TypeError, ValueError):
        return True            # cannot tell; translating is the safer default (the live code is sync-named)
    return _LIVE in params or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


# What is learned about a live method (does it take sync_id, what does its signature look like) depends only on the live class
# and the method name, so it is worked out once. Reading a signature is the slow part of a call; without this each call costs
# about 40 microseconds, with it a few.
_METHOD_INFO: Dict[tuple, tuple] = {}


def _method_info(target, live_name: str, attr: Callable) -> tuple:
    key = (type(target), live_name)
    info = _METHOD_INFO.get(key)
    if info is None:
        info = (_accepts_live_name(attr), _flow_signature(attr))
        _METHOD_INFO[key] = info
    return info


class _FlowView:
    """Wraps one live object. Not a copy: every call reaches the live object."""

    def __init__(self, target, method_names: Dict[str, str]):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_method_names", method_names)

    def __getattr__(self, name: str):
        target = object.__getattribute__(self, "_target")
        live_name = object.__getattribute__(self, "_method_names").get(name, name)
        attr = getattr(target, live_name)
        if not callable(attr):
            return attr
        translate, sig = _method_info(target, live_name, attr)

        if translate:
            def call(*args, **kwargs):
                if _FLOW in kwargs and _LIVE not in kwargs:
                    kwargs[_LIVE] = kwargs.pop(_FLOW)
                return attr(*args, **kwargs)
        else:
            call = attr                      # nothing to translate: hand back the live method itself
            return call

        call.__name__ = getattr(attr, "__name__", name)
        call.__doc__ = getattr(attr, "__doc__", None)
        if sig is not None:
            call.__signature__ = sig
        return call

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_target"), name, value)

    def __dir__(self):
        target = object.__getattribute__(self, "_target")
        names = set(dir(target))
        for flow_name, live_name in object.__getattribute__(self, "_method_names").items():
            if live_name in names:
                names.add(flow_name)
        return sorted(names)

    def __repr__(self):
        return f"<flow view of {object.__getattribute__(self, '_target')!r}>"


def flow_view(factory: Callable, method_names: Optional[Dict[str, str]] = None) -> Callable:
    """A function with the same arguments as `factory` that returns the live object seen through the flow names."""
    names = dict(method_names or {})

    @functools.wraps(factory)
    def make(*args, **kwargs):
        return _FlowView(factory(*args, **kwargs), names)

    return make