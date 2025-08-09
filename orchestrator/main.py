from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import subprocess
import tempfile
import os
import shutil

app = FastAPI()

class TestRunRequest(BaseModel):
    repo_url: str
    test_command: str

@app.post("/run-tests")
def run_tests(request: TestRunRequest):
    temp_dir = tempfile.mkdtemp()
    try:
        # Step 1: Clone repo
        clone_cmd = ["git", "clone", request.repo_url, temp_dir]
        subprocess.run(clone_cmd, check=True)

        # Step 2: Build test runner image (if not built already)
        subprocess.run(["docker", "build", "-f", "Dockerfile.test-runner", "-t", "test-runner", "."], check=True)

        # Step 3: Run tests in container
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{temp_dir}:/app",  # mount repo into /app
            "test-runner",
            "sh", "-c", request.test_command
        ]
        result = subprocess.run(docker_cmd, capture_output=True, text=True)

        return {
            "repo_url": request.repo_url,
            "command": request.test_command,
            "status": "success" if result.returncode == 0 else "failure",
            "output": result.stdout + "\n" + result.stderr,
            "timestamp": datetime.now().isoformat()
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        # Clean up temp dir
        shutil.rmtree(temp_dir, ignore_errors=True)
