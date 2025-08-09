# test_runner/runner.py
import os
import subprocess
import sys

def run_tests():
    repo_url = sys.argv[1]
    os.system(f"git clone {repo_url} /workspace")
    os.chdir("/workspace")
    result = subprocess.run(["pytest", "--maxfail=1", "--disable-warnings", "-q"], capture_output=True, text=True)

    with open("/logs/results.txt", "w") as f:
        f.write(result.stdout)
        f.write(result.stderr)

if __name__ == "__main__":
    run_tests()
