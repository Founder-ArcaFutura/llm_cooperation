"""Record selected package/runtime versions without dumping credentials or env vars."""
import importlib.metadata
import json
import platform
from research.pretraining_counterfactual_v1.data import write_json
from research.pretraining_counterfactual_v1.pilot import DEFAULT_REPORT


if __name__=="__main__":
    cpu=platform.processor()
    if platform.system()=="Windows":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu=winreg.QueryValueEx(key,"ProcessorNameString")[0].strip()
    identity=json.loads((DEFAULT_REPORT/"scorer_identity.json").read_text())
    write_json(DEFAULT_REPORT/"environment.json",{
        "python":platform.python_version(),"platform":platform.system(),"machine":platform.machine(),
        "cpu":cpu, "torch_device":identity["device"], "threads":identity["threads"],
        "packages":{k:importlib.metadata.version(k) for k in (
            "torch","transformers","sentence-transformers","numpy","datasets","pyarrow","huggingface-hub","matplotlib","httpx")},
        "reproduction_note":"Semantic method and source/model commits are fixed; bitwise equivalence across CPU libraries/platforms is not assumed."})
