import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "data" / "state"
TODOS_FILE = STATE_DIR / "todos.json"
NOTE_FILE = STATE_DIR / "note.txt"


def _ensure_state():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not TODOS_FILE.exists():
        TODOS_FILE.write_text("[]\n", encoding="utf-8")
    if not NOTE_FILE.exists():
        NOTE_FILE.write_text("", encoding="utf-8")


def load_todos(limit=7):
    _ensure_state()
    data = json.loads(TODOS_FILE.read_text(encoding="utf-8") or "[]")
    return data[:limit]


def save_todos(items):
    _ensure_state()
    TODOS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_todo(text, due=""):
    items = load_todos(limit=1000)
    items.append({"text": text, "due": due, "done": False})
    save_todos(items)
    return items


def set_todo_done(index, done=True):
    items = load_todos(limit=1000)
    idx = index - 1
    if idx < 0 or idx >= len(items):
        raise IndexError("todo index out of range")
    items[idx]["done"] = bool(done)
    save_todos(items)
    return items


def delete_todo(index):
    items = load_todos(limit=1000)
    idx = index - 1
    if idx < 0 or idx >= len(items):
        raise IndexError("todo index out of range")
    del items[idx]
    save_todos(items)
    return items


def load_note():
    _ensure_state()
    return NOTE_FILE.read_text(encoding="utf-8").strip()


def save_note(note):
    _ensure_state()
    NOTE_FILE.write_text(str(note).strip() + "\n", encoding="utf-8")

