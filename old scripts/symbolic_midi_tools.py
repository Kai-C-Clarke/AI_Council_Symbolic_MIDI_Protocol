# === symbolic_midi_tools.py ===
# Utility suite to support symbolic MIDI AI communication

import time
import yaml
import os
from pathlib import Path
from shutil import copyfile
import datetime

# CONFIGURATION
BASE = Path("/Users/jonstiles/Desktop/AI_Council_Comm/MIDI_Exchange")
INBOX = BASE / "inbox"
OUTBOX = BASE / "outbox"
ARCHIVE = BASE / "archive"
LOGS = BASE / "logs"
SYMBOL_TABLE = BASE / "symbol_tables" / "symbol_table_v0.1.yaml"

# === LOGGING ===
def log(msg):
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "symbolic_midi_log.txt", "a") as f:
        f.write(f"{datetime.datetime.now()} | {msg}\n")

# === MESSAGE TRANSPORT ===
def move_message(sender, recipient, msg_id):
    src = OUTBOX / sender / f"{sender.lower()}_{msg_id}.yaml"
    dst = INBOX / recipient / src.name
    if not src.exists():
        raise FileNotFoundError(f"{src} does not exist")
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / recipient).mkdir(parents=True, exist_ok=True)
    copyfile(src, dst)
    log(f"Moved message {src.name} from {sender} to {recipient}")
    return dst

# === SYMBOL TABLE ===
def load_symbol_table():
    with open(SYMBOL_TABLE) as f:
        return yaml.safe_load(f)

# === CONVERSION PLACEHOLDERS ===
def midi_to_json(yaml_path):
    with open(yaml_path) as f:
        msg = yaml.safe_load(f)
    return {
        "agent": msg["Agent"],
        "notes": msg["Notes"],
        "velocity": msg["Velocity"],
        "intent": "(symbol lookup)"
    }

def json_to_midi(data, output_path):
    msg = {
        "Agent": data["agent"],
        "Channel": data.get("channel", 1),
        "Notes": data["notes"],
        "Velocity": data.get("velocity", 100),
        "Timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "Group ID": data.get("group", "001")
    }
    with open(output_path, "w") as f:
        yaml.dump(msg, f)
    log(f"Generated MIDI YAML message at {output_path}")

# === TEST ===
if __name__ == "__main__":
    print("Symbolic MIDI Toolset Ready.")
    symbols = load_symbol_table()
    print(f"Loaded {len(symbols['notes'])} symbolic notes.")
