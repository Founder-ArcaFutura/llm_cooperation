import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

base = Path("reports/manuscript_readiness/construct_luna_qa/pilot_20261112")
source = base / "development.jsonl"
output = base / "development_sync_output.jsonl"
errors = base / "development_sync_errors.jsonl"

requests = [
    json.loads(line)
    for line in source.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

completed = set()
if output.exists():
    for line in output.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if record.get("response"):
                completed.add(record["custom_id"])

pending = [r for r in requests if r["custom_id"] not in completed]
print(f"Already completed: {len(completed)}")
print(f"Remaining: {len(pending)}")

client = OpenAI(timeout=120.0, max_retries=2)

def process(request):
    try:
        response = client.responses.create(**request["body"])
        if response.status != "completed":
            raise RuntimeError(f"Response status: {response.status}")
        return request["custom_id"], response, None
    except Exception as exc:
        return request["custom_id"], None, str(exc)

with ThreadPoolExecutor(max_workers=4) as pool:
    futures = [pool.submit(process, r) for r in pending]

    with output.open("a", encoding="utf-8") as out, \
         errors.open("a", encoding="utf-8") as err:

        for i, future in enumerate(as_completed(futures), 1):
            custom_id, response, error = future.result()

            if error:
                err.write(json.dumps({
                    "custom_id": custom_id,
                    "error": error
                }) + "\n")
                err.flush()
                print(f"FAILED {custom_id}: {error}")
            else:
                record = {
                    "id": "sync_" + custom_id,
                    "custom_id": custom_id,
                    "response": {
                        "status_code": 200,
                        "request_id": getattr(response, "_request_id", None),
                        "body": response.model_dump(mode="json", by_alias=True)
                    },
                    "error": None
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()

            if i % 10 == 0 or i == len(pending):
                print(f"Processed this run: {i}/{len(pending)}")

print("Synchronous execution finished.")
