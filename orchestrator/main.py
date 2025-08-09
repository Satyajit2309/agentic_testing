# # main.py
# import logging
# import sys
# import subprocess
# import tempfile
# import shutil
# import os
# import shlex
# import re
# from typing import Optional, List
# from fastapi import FastAPI
# from pydantic import BaseModel

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("orchestrator")

# app = FastAPI(title="Agentic Testing Orchestrator (MVP)")

# MAX_RETRIES = 8  # max automatic installs/retries for missing packages

# class RunRequest(BaseModel):
#     repo_url: str
#     test_command: Optional[str] = "pytest"

# def run_cmd(cmd: List[str], cwd: Optional[str] = None) -> Optional[subprocess.CompletedProcess]:
#     """Run a command and return CompletedProcess. Return None if executable missing."""
#     try:
#         logger.info("Running command: %s (cwd=%s)", " ".join(cmd), cwd)
#         cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
#         logger.info("Returncode: %s", cp.returncode)
#         return cp
#     except FileNotFoundError:
#         logger.error("Command not found: %s", cmd[0])
#         return None

# def find_requirements_files(root_dir: str) -> List[str]:
#     reqs = []
#     for r, _, files in os.walk(root_dir):
#         for f in files:
#             if f.startswith("requirements") and f.endswith(".txt"):
#                 reqs.append(os.path.join(r, f))
#     return reqs

# def install_requirements_files(req_files: List[str], step_logs: List[dict], cwd: str):
#     for rf in req_files:
#         cp = run_cmd([sys.executable, "-m", "pip", "install", "-r", rf], cwd=cwd)
#         if cp is None:
#             step_logs.append({"step": "pip install -r", "file": rf, "error": "pip (python) not found"})
#         else:
#             step_logs.append({"step": "pip install -r", "file": rf, "returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})

# def best_effort_install_package(pkg_name: str, step_logs: List[dict], cwd: Optional[str] = None):
#     """Attempt to pip install a package (name guessed from missing module)."""
#     # Try installing the module name directly
#     cp = run_cmd([sys.executable, "-m", "pip", "install", pkg_name], cwd=cwd)
#     if cp is None:
#         step_logs.append({"step": "pip install pkg", "pkg": pkg_name, "error": "pip not found"})
#         return False, cp
#     else:
#         step_logs.append({"step": "pip install pkg", "pkg": pkg_name, "returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})
#         return cp.returncode == 0, cp

# @app.get("/")
# async def health():
#     return {"status": "ok", "message": "Orchestrator running. POST /run-tests to run tests."}

# @app.post("/run-tests")
# async def run_tests(req: RunRequest):
#     logger.info("Received run-tests request: repo=%s, command=%s", req.repo_url, req.test_command)
#     temp_dir = tempfile.mkdtemp(prefix="repo_")
#     step_logs = []
#     installed_auto = []

#     try:
#         # 1) Clone
#         cp = run_cmd(["git", "clone", req.repo_url, temp_dir])
#         if cp is None:
#             return {"status": "error", "output": "git not found. Please install git and add to PATH.", "logs": step_logs}
#         step_logs.append({"step": "git clone", "returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})
#         if cp.returncode != 0:
#             return {"status": "error", "output": "git clone failed:\n" + cp.stderr, "logs": step_logs}

#         # 2) Ensure setuptools installed (fixes many test suites)
#         cp = run_cmd([sys.executable, "-m", "pip", "install", "setuptools"])
#         if cp is None:
#             step_logs.append({"step": "install setuptools", "error": "python/pip not found"})
#         else:
#             step_logs.append({"step": "install setuptools", "returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})

#         # 3) Install any requirements*.txt found (root + subfolders)
#         req_files = find_requirements_files(temp_dir)
#         if req_files:
#             install_requirements_files(req_files, step_logs, cwd=temp_dir)
#         else:
#             step_logs.append({"step": "requirements", "info": "no requirements*.txt found"})

#         # 4) If pyproject.toml or setup.py exists, attempt a pip install . (best-effort)
#         if os.path.exists(os.path.join(temp_dir, "pyproject.toml")) or os.path.exists(os.path.join(temp_dir, "setup.py")):
#             cp = run_cmd([sys.executable, "-m", "pip", "install", "."], cwd=temp_dir)
#             if cp:
#                 step_logs.append({"step": "pip install .", "returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})

#         # 5) Prepare test command (run pytest with current interpreter to match env)
#         if req.test_command and "pytest" in req.test_command:
#             parts = shlex.split(req.test_command)
#             extra = parts[1:] if parts and ("pytest" in parts[0]) else []
#             test_cmd = [sys.executable, "-m", "pytest"] + extra
#         else:
#             test_cmd = shlex.split(req.test_command)

#         # 6) Run tests with auto package-install on ModuleNotFoundError
#         retries = 0
#         last_output = ""
#         while retries <= MAX_RETRIES:
#             cp = run_cmd(test_cmd, cwd=temp_dir)
#             if cp is None:
#                 return {"status": "error", "output": f"Failed to run test command; '{test_cmd[0]}' not found", "logs": step_logs}
#             last_output = (cp.stdout or "") + "\n" + (cp.stderr or "")
#             step_logs.append({"step": "run tests", "attempt": retries + 1, "returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})

#             # find missing module patterns: ModuleNotFoundError: No module named 'xyz'
#             missing = re.findall(r"No module named '([^']+)'", last_output)
#             # also try ImportError pattern (older style)
#             missing += re.findall(r"ImportError: No module named ([\w\.]+)", last_output)

#             # normalize, dedupe
#             missing = list({m.strip() for m in missing if m and m.strip()})

#             # filter out modules we've already auto-installed this run
#             missing = [m for m in missing if m.lower() not in {p.lower() for p in installed_auto}]

#             if not missing:
#                 # no missing packages; break and return result (success or failure)
#                 status = "success" if cp.returncode == 0 else "failed"
#                 return {"status": status, "output": last_output, "logs": step_logs, "installed_auto": installed_auto}

#             # If we do have missing modules, attempt to install them (best-effort)
#             if retries >= MAX_RETRIES:
#                 break

#             for pkg in missing:
#                 success, install_cp = best_effort_install_package(pkg, step_logs, cwd=temp_dir)
#                 installed_auto.append(pkg)
#                 # If pip returns non-zero, that's okay — we continue and may retry, but log it
#                 if install_cp is None:
#                     # pip/py launcher missing; abort
#                     return {"status": "error", "output": "python/pip not found on the server", "logs": step_logs, "installed_auto": installed_auto}
#             retries += 1
#             # loop continues to retry tests

#         # If we exit loop without a clean run:
#         return {"status": "failed", "output": last_output, "logs": step_logs, "installed_auto": installed_auto}

#     except Exception as e:
#         logger.exception("Unexpected error while running tests")
#         return {"status": "error", "output": str(e), "logs": step_logs, "installed_auto": installed_auto}
#     finally:
#         try:
#             shutil.rmtree(temp_dir)
#             logger.info("Cleaned up %s", temp_dir)
#         except Exception:
#             logger.exception("Failed to remove temp dir")
import os
import shutil
import subprocess
import tempfile
import sys
import stat
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from git import Repo

app = FastAPI()

class RepoRequest(BaseModel):
    repo_url: str

# --- FIX 1: Twisted install check ---
def ensure_twisted_installed():
    try:
        import twisted  # noqa: F401
    except ImportError:
        print("📦 Installing twisted...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "twisted"])

# --- FIX 2: Safe folder deletion ---
def remove_readonly(func, path, _):
    """Clear readonly bit and retry removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_rmtree(path):
    """Safely remove directory tree on all OS."""
    try:
        shutil.rmtree(path, onerror=remove_readonly)
    except Exception as e:
        print(f"⚠ Warning: could not fully delete {path} - {e}")

# Install Twisted automatically before starting
ensure_twisted_installed()

@app.post("/run-tests")
def run_tests(request: RepoRequest):
    repo_url = request.repo_url
    temp_dir = tempfile.mkdtemp()

    try:
        # Clone repo
        print(f"⬇ Cloning {repo_url} into {temp_dir}")
        Repo.clone_from(repo_url, temp_dir)

        # Install requirements if found
        requirements_path = os.path.join(temp_dir, "requirements.txt")
        if os.path.exists(requirements_path):
            print("📦 Installing repo requirements...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])

        # Run pytest
        print("🧪 Running tests...")
        result = subprocess.run(
            [sys.executable, "-m", "pytest"],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )

        return {
            "status": "success" if result.returncode == 0 else "failed",
            "output": result.stdout,
            "errors": result.stderr
        }

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    finally:
        # Cleanup safely
        safe_rmtree(temp_dir)
