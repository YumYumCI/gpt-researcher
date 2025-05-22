import json
import subprocess
import sys
from pathlib import Path
import argparse
import traceback

from colorama import Fore, Style, init
init(autoreset=True)


def load_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)


def validate_task(task, required_keys):
    missing_keys = [key for key in required_keys if key not in task]
    return missing_keys


def run_task(config, defaults, task_updates, task_file, task_index, total_tasks):
    print(f"\n--- Processing task {task_index}/{total_tasks} ---")

    # Merge defaults with task updates (ignoring None values)
    merged_config = {
        **defaults,
        **{k: v for k, v in task_updates.items() if v is not None}
    }

    # # Special logic for a local source
    # if merged_config.get('source') == 'local':
    #     merged_config.setdefault('DOC_PATH', config.get('defaults', {}).get('local_research', {}).get('DOC_PATH'))
    #
    # # Optional validation (expand required keys as needed)
    # required_keys = ["source"]
    # missing_keys = validate_task(merged_config, required_keys)
    # if missing_keys:
    #     print(Fore.YELLOW + f"✗ Skipping task {task_index}: Missing keys: {missing_keys}")
    #     return

    # Write the task config
    with open(task_file, 'w') as f:
        json.dump(merged_config, f, indent=2)

    print("Task configuration ready")

    try:
        subprocess.run([sys.executable, "-m", "custom_agents.main"], check=True)
        print(Fore.GREEN + f"✓ Task {task_index} completed")
    except subprocess.CalledProcessError as e:
        print(Fore.RED + f"✗ Task {task_index} failed with return code {e.returncode}")
        print(f"Command: {e.cmd}")
        traceback.print_exc()


def process_tasks(config_path, task_path):
    config = load_config(config_path)

    defaults = config.get("defaults", {}).copy()
    queue = config.get("updates_queue", [])

    total_tasks = len(queue)
    for task_index, task_updates in enumerate(queue, 1):
        run_task(config, defaults, task_updates, task_path, task_index, total_tasks)

    print(Fore.CYAN + "\nAll tasks processed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tasks from a config file using main.py module")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--task", default="task.json", help="Path to task file")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    config_path = base_dir / args.config
    task_path = base_dir / args.task

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")

    task_path.parent.mkdir(parents=True, exist_ok=True)

    process_tasks(config_path, task_path)