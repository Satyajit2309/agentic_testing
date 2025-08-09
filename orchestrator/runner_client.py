# orchestrator/runner_client.py
import subprocess
import uuid
import os

def trigger_test_run(repo_url: str):
    run_id = str(uuid.uuid4())
    logs_dir = f"./logs/{run_id}"
    os.makedirs(logs_dir, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{os.path.abspath(logs_dir)}:/logs",
        "agentic-test-runner",
        repo_url
    ]

    subprocess.run(cmd, check=True)
    return {"run_id": run_id, "logs_dir": logs_dir}
