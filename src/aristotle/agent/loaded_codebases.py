import json
import os
import threading

from datasets.utils.py_utils import Literal

from aristotle import project_config

lock = threading.Lock()


def create_file():
    if not os.path.isfile(project_config.loaded_codebases_file):
        print("[INFO] Loaded codebases file doesn't exist")
        with open(project_config.loaded_codebases_file, "w") as f:
            f.write("{}")


def update_loaded_codebase_status(
    codebase_name: str,
    status: (
        Literal["LOADING_IN_PROGRESS"] | Literal["LOADED"] | Literal["FAILED_TO_LOAD"]
    ),
):
    try:
        with lock:
            create_file()
            with open(project_config.loaded_codebases_file, "r") as f:
                loaded = json.load(f)
            loaded[codebase_name] = status
            with open(project_config.loaded_codebases_file, "w") as f:
                json.dump(loaded, f, indent=4)
    except Exception as e:
        print("[WARN] Failed to update loaded codebase status:", e)


def get_loaded_codebase_status(
    codebase_name: str,
) -> (
    Literal["LOADING_IN_PROGRESS"]
    | Literal["LOADED"]
    | Literal["FAILED_TO_LOAD"]
    | Literal["NOT_LOADED"]
):
    try:
        with lock:
            create_file()
            with open(project_config.loaded_codebases_file) as f:
                loaded = json.load(f)
                status = loaded.get(codebase_name, "NOT_LOADED")
                return status
    except Exception as e:
        print("[WARN] Failed to get loaded codebase status:", e)
        return "LOADED"


def list_all_codebases() -> str:
    try:
        with lock:
            create_file()
            with open(project_config.loaded_codebases_file, "r") as f:
                loaded = json.load(f)
                return json.dumps(loaded)
    except Exception as e:
        print("[WARN] Failed to list loaded codebase statuses:", e)
        return (
            "Failed to get loaded codebase status, assume that all codebases are loaded"
        )
