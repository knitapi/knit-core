"""Make one package importable under a second name, with the SAME module objects.

Use it in the runner so that `import knit_core` and `import weavex_core` (and their submodules, e.g.
`weavex_core.durable` / `knit_core.durable`) resolve to one set of modules. Two separate copies would be two different
exception classes (an error raised through one name would not be caught through the other) and two different state stores.

Call it once, before anything imports either name, for example at the top of the runner's main.py:

    from module_alias import install_alias
    install_alias("knit_core", "weavex_core")      # today: the runner's real package is weavex_core
    # later, after the rename: install_alias("weavex_core", "knit_core")
"""
import importlib
import importlib.abc
import importlib.util
import sys


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target_name: str):
        self._target_name = target_name

    def create_module(self, spec):
        return importlib.import_module(self._target_name)   # the existing module object, not a copy

    def exec_module(self, module):
        pass


class _AliasFinder(importlib.abc.MetaPathFinder):
    def __init__(self, alias: str, target: str):
        self._alias, self._target = alias, target

    def find_spec(self, fullname, path=None, target=None):
        if fullname != self._alias and not fullname.startswith(self._alias + "."):
            return None
        real_name = self._target + fullname[len(self._alias):]
        try:
            real = importlib.util.find_spec(real_name)
        except (ImportError, ValueError):
            return None
        if real is None:
            return None
        spec = importlib.util.spec_from_loader(fullname, _AliasLoader(real_name),
                                               is_package=real.submodule_search_locations is not None)
        return spec


def install_alias(alias: str, target: str) -> None:
    """Import `alias` (and `alias.sub.module`) as `target` (and `target.sub.module`). Safe to call twice."""
    for finder in sys.meta_path:
        if isinstance(finder, _AliasFinder) and finder._alias == alias:
            return
    if alias in sys.modules or any(name.startswith(alias + ".") for name in sys.modules):
        raise RuntimeError(f"{alias!r} is already imported; install the alias before anything imports it")
    sys.meta_path.insert(0, _AliasFinder(alias, target))
