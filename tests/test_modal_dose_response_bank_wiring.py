"""Regression coverage for the Modal dose-response bank integration.

These checks are intentionally static: they never connect to Modal or provision a GPU.
"""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODAL_FILE = ROOT / "modal_app.py"
BANK_FILE = ROOT / "data" / "scenarios_dose_response_exploratory.json"


def test_modal_image_packages_dose_response_bank():
    source = MODAL_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    # Confirm that image construction explicitly ships the frozen exploratory bank.
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_local_file"
    ]
    paths = [tuple(ast.literal_eval(a) for a in c.args) for c in calls]
    assert (
        "data/scenarios_dose_response_exploratory.json",
        "/root/data/scenarios_dose_response_exploratory.json",
    ) in paths
    assert BANK_FILE.is_file()


def test_modal_bank_mapping_points_to_packaged_file():
    tree = ast.parse(MODAL_FILE.read_text(encoding="utf-8"))
    assignments = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "SUPPORTED_BANKS" for t in n.targets)
    ]
    assert len(assignments) == 1
    banks = ast.literal_eval(assignments[0].value)
    assert banks["dose-response"] == "/root/data/scenarios_dose_response_exploratory.json"
