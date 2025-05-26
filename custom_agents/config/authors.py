import json
import random
from pathlib import Path

AUTHORS_FILE = Path(__file__).parent.parent / 'config' / 'authors.json'

def get_random_author():
    with open(AUTHORS_FILE) as f:
        authors = json.load(f)
    return random.choice(authors)