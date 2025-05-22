import re
import time
import shutil
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent
WATCH_FOLDER = BASE_DIR / "reports"
DEST_FOLDER = BASE_DIR / "reports_md"
FILE_EXTENSION = ".md"
LOG_FILE = BASE_DIR / "slugifier.log"
# ==============

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("[%(levelname)s] %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text).strip("-")


def get_heading(file_path: Path) -> str | None:
    """Extracts the first level-1 Markdown heading from the file."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                if re.match(r"^\s*#\s+", line):
                    return slugify(line.strip("# ").strip())
    except Exception as e:
        logging.error(f"Failed to read {file_path.name}: {e}")
    return None


def wait_until_ready(file_path: Path, timeout=10) -> bool:
    """Wait until the file stops growing in size."""
    start = time.time()
    last_size = -1
    while time.time() - start < timeout:
        try:
            current_size = file_path.stat().st_size
            if current_size == last_size:
                return True
            last_size = current_size
            time.sleep(0.5)
        except FileNotFoundError:
            pass  # Still being created
    return False


class MarkdownHandler(FileSystemEventHandler):
    def on_created(self, event):
        path = Path(event.src_path)
        if path.is_dir() or path.suffix != FILE_EXTENSION:
            return

        logging.info(f"Detected new file: {path.name}")

        if not wait_until_ready(path):
            logging.warning(f"File never stabilized: {path.name}")
            return

        heading_slug = get_heading(path)
        if not heading_slug:
            logging.warning(f"No heading found in {path.name}, skipping")
            return

        new_filename = f"{heading_slug}{FILE_EXTENSION}"
        dest_path = DEST_FOLDER / new_filename

        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            dest_path = DEST_FOLDER / f"{heading_slug}-{counter}{FILE_EXTENSION}"
            counter += 1

        try:
            shutil.move(str(path), str(dest_path))
            logging.info(f"Moved '{path.name}' → '{dest_path.name}'")
        except Exception as e:
            logging.error(f"Error processing file {path.name}: {e}")


def main():
    WATCH_FOLDER.mkdir(exist_ok=True)
    DEST_FOLDER.mkdir(exist_ok=True)

    logging.info(f"Watching folder: {WATCH_FOLDER}")

    event_handler = MarkdownHandler()
    observer = Observer()
    observer.schedule(event_handler, path=str(WATCH_FOLDER), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Stopped watching.")
    observer.join()


if __name__ == "__main__":
    main()