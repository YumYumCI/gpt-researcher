from pathlib import Path
from task_manager import process_tasks

if __name__ == "__main__":
    # Define paths relative to this script's location
    base_dir = Path(__file__).parent  # Goes up to gpt-researcher/

    config_path = base_dir / "config.json"
    task_path = base_dir / "task.json"
    main_script_path = base_dir / "main.py"

    # Verify config exists
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")

    # Create task directory if needed
    task_path.parent.mkdir(parents=True, exist_ok=True)

    process_tasks(config_path, task_path, main_script_path)
    print("\nAll tasks processed!")
