import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_alias_gives_the_same_module_objects(tmp_path):
    code = textwrap.dedent("""
        from module_alias import install_alias
        install_alias("weavex_core", "knit_core")
        install_alias("weavex_core", "knit_core")               # twice is fine
        import knit_core, weavex_core
        import weavex_core.durable, knit_core.durable
        from weavex_core.state import get_sync_state
        from knit_core.state import get_sync_state as g2
        assert weavex_core is knit_core
        assert weavex_core.durable is knit_core.durable
        assert get_sync_state is g2
        assert weavex_core.TerminalSyncError is knit_core.TerminalSyncError
        try:
            raise weavex_core.TerminalSyncError("x")
        except knit_core.SyncError:
            pass
        print("ok")
    """)
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                         env={"PYTHONPATH": f"{ROOT}:{ROOT / 'src'}", "PATH": ""})
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr


def test_alias_refuses_when_already_imported():
    code = "import knit_core, weavex_core_x\n" if False else textwrap.dedent("""
        import sys, types
        sys.modules['aliased_name'] = types.ModuleType('aliased_name')
        from module_alias import install_alias
        try:
            install_alias('aliased_name', 'knit_core')
        except RuntimeError as e:
            print('refused')
    """)
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                         env={"PYTHONPATH": f"{ROOT}:{ROOT / 'src'}", "PATH": ""})
    assert out.stdout.strip() == "refused", out.stderr
