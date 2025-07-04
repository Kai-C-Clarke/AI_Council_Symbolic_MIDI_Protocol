from pathlib import Path
import yaml
import datetime
import shutil

# === CONFIGURATION ===

# Base directory (adjust to match your machine)
root_dir = Path("/Users/jonstiles/Desktop/AI_Council_Comm/MIDI_Exchange")
inbox_dir = root_dir / "inbox"
outbox_dir = root_dir / "outbox"
logs_dir = root_dir / "logs"
symbol_table_path = root_dir / "symbol_tables" / "symbol_table_v0.1.yaml"

# === LOAD SYMBOL TABLE ===

def load_symbol_table(path):
    with open(path, "r") as file:
        return yaml.safe_load(file)

symbol_table = load_symbol_table(symbol_table_path)

# === LOGGER FUNCTION ===

def log_message(action, agent, message_file):
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {action.upper()} | {agent} | {message_file.name}\n"
    with open(logs_dir / "symbolic_midi_log.txt", "a") as log_file:
        log_file.write(log_line)

# === MOVE FUNCTION ===

def move_message(sender, recipient, message_id="0001"):
    source_file = outbox_dir / sender / f"{sender.lower()}_{message_id}.yaml"
    target_folder = inbox_dir / recipient
    target_folder.mkdir(parents=True, exist_ok=True)
    target_file = target_folder / source_file.name

    if not source_file.exists():
        raise FileNotFoundError(f"Message not found: {source_file}")

    shutil.copy(source_file, target_file)
    log_message("moved", sender, source_file)
    print(f"✅ Moved {source_file.name} from {sender} to {recipient}")
    return target_file

# === OPTIONAL: SCAN INBOX ===

def scan_inbox(agent):
    agent_inbox = inbox_dir / agent
    if not agent_inbox.exists():
        print(f"No inbox found for {agent}")
        return []
    return list(agent_inbox.glob("*.yaml"))

# === RUN TEST ===

if __name__ == "__main__":
    try:
        move_message("Kai", "Claude", "0002")
    except Exception as e:
        print(f"⚠️ Error: {e}")
