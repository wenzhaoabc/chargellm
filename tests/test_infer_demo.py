import json
import subprocess
import sys


def test_infer_demo_outputs_json() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "chargellm.inference.infer_demo", "--data-path", "dataset/sft.json", "--index", "0"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert "label" in payload
    assert "confidence" in payload
    assert "key_processes" in payload
    assert "explanation" in payload