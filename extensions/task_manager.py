import json
import subprocess


def process_tasks(config_file, task_file, main_script_path):
    """Process tasks using defaults as reference without modification"""
    # Load config once (including protected defaults)
    with open(config_file, 'r') as f:
        config = json.load(f)

    defaults = config.get('defaults', {}).copy()  # Create safe copy
    queue = config.get('updates_queue', [])

    for task_index, task_updates in enumerate(queue, 1):
        print(f"\n--- Processing task {task_index}/{len(queue)} ---")

        # Fresh merge for each task (defaults remain unchanged)
        merged_config = {
            **defaults,  # Default values
            **{k: v for k, v in task_updates.items() if v is not None}  # Task overrides
        }

        # Special handling for local research
        if merged_config.get('source') == 'local':
            merged_config.setdefault('DOC_PATH', config.get('defaults', {}).get('local_research', {}).get('DOC_PATH'))

        # Write to task.json
        with open(task_file, 'w') as f:
            json.dump(merged_config, f, indent=2)

        print(f"Task configuration ready (defaults preserved)")

        try:
            subprocess.run(['python', str(main_script_path)], check=True)
            print(f"✓ Task {task_index} completed")
        except subprocess.CalledProcessError as e:
            print(f"✗ Task failed: {e}")
