"""Compatibility exports; implementation lives in llm_cooperation.items.dose_response_bank."""
from llm_cooperation.items.dose_response_bank import *  # noqa: F401,F403

if __name__ == "__main__":
    path = write_dose_response_bank_file()
    print(f"Generated {path}")
