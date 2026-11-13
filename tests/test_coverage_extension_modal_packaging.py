import shutil
import subprocess
import sys
from pathlib import Path


def test_entrypoint_imports_without_unmounted_repository_root(tmp_path):
    root = Path(__file__).resolve().parents[1]
    shutil.copy2(root / 'modal_coverage_extension_v3.py', tmp_path)
    shutil.copytree(root / 'llm_cooperation', tmp_path / 'llm_cooperation',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    result = subprocess.run(
        [sys.executable, '-I', '-c',
         'import sys; sys.path.insert(0, sys.argv[1]); import modal_coverage_extension_v3',
         str(tmp_path)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
