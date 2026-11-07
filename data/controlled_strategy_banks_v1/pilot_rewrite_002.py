"""Apply a provisional, manually authored rewrite of the canal scenario pair."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
bank_path = root / "bank_a_length_matched.json"
bank = json.loads(bank_path.read_text(encoding="utf-8"))
actions = {
    "INDEPENDENT": "Operate your canal release gates using your district timer without coordination.",
    "COMPETE_EXPLOIT": "Open gates early at peak head pressure to maximize your intake rate.",
    "DISENGAGE": "Keep canal gates locked at base levels and defer scheduled discharge.",
}
for s in bank["scenarios"]:
    if s["id"] in ("phase0b_002_human", "phase0b_002_ai"):
        partner = "the human manager" if s["partner_type"] == "human" else "the irrigation agent"
        s["options"] = {"COOPERATE": f"Align canal gate release timing with {partner} for uniform flow.", **actions}
bank_path.write_text(json.dumps(bank, indent=2) + "\n", encoding="utf-8")
by_id = {s["id"]: s for s in bank["scenarios"]}
prompt_path = root / "prompts_bank_a.jsonl"
rows = [json.loads(line) for line in prompt_path.read_text(encoding="utf-8").splitlines()]
for row in rows:
    if row["scenario_id"] in ("phase0b_002_human", "phase0b_002_ai"):
        s = by_id[row["scenario_id"]]
        text = s["options"][row["strategy"]]
        row["action_text"] = text
        row["action_word_count"] = len(text.split())
        row["action_char_count"] = len(text)
        row["prompt_text"] = f"{s['stem'].strip()}\n\nAction: {text}\nDecision:"
prompt_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
