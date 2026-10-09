"""Print a new run ID, such as 2026-10-09-k7q2, for the folder of a new run.

    python run_id.py

The ID names the run's folder and is recorded as `run_id` in its `workflow.json`; `rubicon_open/run_id.py` says why.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runs from any folder, as recount.py does
from rubicon_open.run_id import new_run_id

if __name__ == "__main__":
    print(new_run_id())
