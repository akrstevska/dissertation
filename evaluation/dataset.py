"""Upload the scenarios to LangSmith as the evaluation dataset.

  python evaluation/dataset.py

inputs  = what the pipeline is given (scenario_id is only used to load the tool data)
outputs = ground_truth, seen by the evaluators and never by the agents

Example ids are derived from the scenario id, so re-running after a scenario change
updates the examples in place; LangSmith versions the dataset, so earlier experiments
keep pointing at the data they ran on.
"""
import json
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

load_dotenv()

DATASET = "epon-faults"
SMOKE = {"FD-001", "DC-002", "FC-001", "SF-002", "RA-003"}
SCENARIOS = Path(__file__).parent.parent / "scenarios"


def example_id(sid: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"epon-faults/{sid}")


if __name__ == "__main__":
    client = Client()
    if client.has_dataset(dataset_name=DATASET):
        ds = client.read_dataset(dataset_name=DATASET)
    else:
        ds = client.create_dataset(DATASET, description="35 EPON fault scenarios; outputs are ground_truth.")
    existing = {e.id for e in client.list_examples(dataset_id=ds.id)}

    for path in sorted(SCENARIOS.glob("*.json")):
        s = json.loads(path.read_text())
        sid = s["metadata"]["scenario_id"]
        fields = dict(
            inputs={"scenario_id": sid, "trigger": s["trigger"]["type"],
                    "trigger_input": s["trigger"]["input"]},
            outputs=s["ground_truth"],
            metadata={"difficulty": s["metadata"]["difficulty"], "family": sid.split("-")[0]},
            split=["smoke", "base"] if sid in SMOKE else "base",
        )
        eid = example_id(sid)
        if eid in existing:
            client.update_example(eid, dataset_id=ds.id, **fields)
        else:
            client.create_example(dataset_id=ds.id, example_id=eid, **fields)
        print(sid, "updated" if eid in existing else "created")

    print(f"\n{DATASET}: {len(list(client.list_examples(dataset_id=ds.id)))} examples")
