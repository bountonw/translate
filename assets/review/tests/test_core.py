"""Runs tests/core_test.js, the checks of the page's plain functions, with node; skipped without node."""
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class PageCore(unittest.TestCase):
    def test_core_functions(self):
        r = subprocess.run(["node", str(HERE / "core_test.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "ok"), r.stderr)


if __name__ == "__main__":
    unittest.main()
