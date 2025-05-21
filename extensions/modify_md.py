import os
import time
import shutil
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === CONFIG ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WATCH_FOLDER = os.path.join(BASE_DIR, "outputs")
DEST_FOLDER = os.path.join(BASE_DIR, "processed")
FILE_EXTENSION = ".md"
# ==============

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[\s_]+', '-', text).strip('-')

def get_heading(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('# '):
                return slugify(line[2:].strip())
    return None

def wait_until_ready(file_path, timeout=10):
    """Wait until the file stops changing in size (likely fully written)."""
    start = time.time()
    last_size = -1
    while time.time() - start < timeout:
        try:
            current_size = os.path.getsize(file_path)
            if current_size == last_size:
                return True
            last_size = current_size
            time.sleep(0.5)
        except FileNotFoundError:
            pass  # File may not exist yet
    return False

class MarkdownHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(FILE_EXTENSION):
            return

        print(f"Detected new file: {event.src_path}")

        if not wait_until_ready(event.src_path):
            print(f"File never stabilized: {event.src_path}")
            return

        filename = os.path.basename(event.src_path)
        folder_path = os.path.dirname(event.src_path)

        heading_slug = get_heading(event.src_path)
        if not heading_slug:
            print(f"No heading found in {filename}")
            return

        new_filename = f"{heading_slug}{FILE_EXTENSION}"
        dest_path = os.path.join(DEST_FOLDER, new_filename)

        try:
            shutil.move(event.src_path, dest_path)
            print(f"Moved '{filename}' → '{new_filename}'")

            time.sleep(0.5)  # Ensure move completes before checking folder
            if not os.listdir(folder_path):
                os.rmdir(folder_path)
                print(f"Deleted empty folder: {folder_path}")
        except Exception as e:
            print(f"Error processing file: {e}")

if __name__ == "__main__":
    os.makedirs(WATCH_FOLDER, exist_ok=True)
    os.makedirs(DEST_FOLDER, exist_ok=True)

    event_handler = MarkdownHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_FOLDER, recursive=True)
    observer.start()

    print(f"Watching folder: {WATCH_FOLDER}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()