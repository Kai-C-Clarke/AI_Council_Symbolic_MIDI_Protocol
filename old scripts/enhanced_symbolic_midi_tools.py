#!/usr/bin/env python3
"""
Enhanced Symbolic MIDI Tools
Utility suite to support symbolic MIDI AI communication
Enhanced with error handling, validation, and robust operations
"""

import time
import yaml
import os
from pathlib import Path
from shutil import copyfile, copy2
import datetime
import json

# === CONFIGURATION ===
BASE = Path("/Users/jonstiles/Desktop/AI_Council_Comm/MIDI_Exchange")
INBOX = BASE / "inbox"
OUTBOX = BASE / "outbox"
ARCHIVE = BASE / "archive"
LOGS = BASE / "logs"
SYMBOL_TABLE = BASE / "symbol_tables" / "symbol_table_v0.1.yaml"

# Agent list for validation
AGENTS = ["Kai", "Claude", "Perplexity", "Grok"]

# === ENHANCED LOGGING ===
def log(msg, level="INFO"):
    """Enhanced logging with levels and better formatting"""
    try:
        LOGS.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {level.upper()} | {msg}\n"
        
        with open(LOGS / "symbolic_midi_log.txt", "a") as f:
            f.write(log_entry)
        
        # Also print to console for immediate feedback
        print(f"[{level}] {msg}")
        
    except Exception as e:
        print(f"LOGGING ERROR: {e}")

def log_error(msg):
    """Convenience function for error logging"""
    log(msg, "ERROR")

def log_warning(msg):
    """Convenience function for warning logging"""
    log(msg, "WARNING")

def log_success(msg):
    """Convenience function for success logging"""
    log(msg, "SUCCESS")

# === DIRECTORY MANAGEMENT ===
def ensure_directories():
    """Create all required directories"""
    directories = [BASE, INBOX, OUTBOX, ARCHIVE, LOGS, SYMBOL_TABLE.parent]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_error(f"Failed to create directory {directory}: {e}")
            return False
    
    # Create agent-specific directories
    for agent in AGENTS:
        try:
            (INBOX / agent).mkdir(parents=True, exist_ok=True)
            (OUTBOX / agent).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_error(f"Failed to create agent directories for {agent}: {e}")
    
    log_success("Directory structure verified and created")
    return True

# === SYMBOL TABLE MANAGEMENT ===
def create_default_symbol_table():
    """Create a default symbol table if none exists"""
    default_table = {
        'notes': {
            60: 'confirm',           # C4
            61: 'query',             # C#4
            62: 'reflection',        # D4
            63: 'agreement',         # D#4
            64: 'inquiry',           # E4
            65: 'proposal',          # F4
            66: 'clarify',           # F#4
            67: 'challenge',         # G4
            68: 'refer_to_standard', # G#4
            69: 'synthesize',        # A4
            70: 'acknowledge',       # A#4
            71: 'disagree'           # B4
        },
        'channels': {
            1: 'Kai',
            2: 'Claude',
            3: 'Perplexity',
            4: 'Grok'
        },
        'velocity': {
            'low': 32,
            'medium': 64,
            'high': 95,
            'maximum': 127
        },
        'cc': {
            1: 'topic_ethics',
            2: 'topic_memory',
            3: 'topic_semantics',
            4: 'topic_creativity',
            5: 'topic_philosophy',
            6: 'topic_technical'
        }
    }
    
    try:
        SYMBOL_TABLE.parent.mkdir(parents=True, exist_ok=True)
        with open(SYMBOL_TABLE, 'w') as f:
            yaml.dump(default_table, f, default_flow_style=False)
        log_success(f"Created default symbol table at {SYMBOL_TABLE}")
        return default_table
    except Exception as e:
        log_error(f"Failed to create default symbol table: {e}")
        return None

def load_symbol_table():
    """Load symbol table with error handling and fallback"""
    try:
        if not SYMBOL_TABLE.exists():
            log_warning("Symbol table not found, creating default")
            return create_default_symbol_table()
        
        with open(SYMBOL_TABLE) as f:
            table = yaml.safe_load(f)
        
        log_success(f"Loaded symbol table with {len(table.get('notes', {}))} notes")
        return table
        
    except Exception as e:
        log_error(f"Failed to load symbol table: {e}")
        log_warning("Attempting to create default symbol table")
        return create_default_symbol_table()

def validate_symbol_table(table):
    """Validate symbol table structure"""
    if not table:
        return False
    
    required_sections = ['notes', 'channels', 'velocity', 'cc']
    missing_sections = [section for section in required_sections if section not in table]
    
    if missing_sections:
        log_warning(f"Symbol table missing sections: {missing_sections}")
        return False
    
    return True

# === MESSAGE VALIDATION ===
def validate_message(message_data, symbol_table=None):
    """Validate message structure and content"""
    if not message_data:
        log_error("Message data is empty")
        return False
    
    # Check required fields
    required_fields = ['message_id', 'from', 'to', 'notes', 'velocity', 'channel']
    missing_fields = [field for field in required_fields if field not in message_data]
    
    if missing_fields:
        log_error(f"Message missing required fields: {missing_fields}")
        return False
    
    # Validate agents
    sender = message_data['from']
    recipient = message_data['to']
    
    if sender not in AGENTS:
        log_warning(f"Unknown sender: {sender}")
    
    if recipient not in AGENTS:
        log_warning(f"Unknown recipient: {recipient}")
    
    # Validate velocity range
    velocity = message_data['velocity']
    if not (0 <= velocity <= 127):
        log_error(f"Invalid velocity: {velocity} (must be 0-127)")
        return False
    
    # Validate against symbol table if provided
    if symbol_table and validate_symbol_table(symbol_table):
        notes = message_data['notes']
        unknown_notes = [note for note in notes if note not in symbol_table['notes']]
        
        if unknown_notes:
            log_warning(f"Unknown notes in message: {unknown_notes}")
    
    log_success(f"Message validation passed for {message_data['message_id']}")
    return True

# === ENHANCED MESSAGE TRANSPORT ===
def move_message(sender, recipient, msg_id):
    """Move message from sender outbox to recipient inbox with validation"""
    try:
        src = OUTBOX / sender / f"{sender.lower()}_{msg_id}.yaml"
        dst = INBOX / recipient / src.name
        
        if not src.exists():
            raise FileNotFoundError(f"Message not found: {src}")
        
        # Validate sender and recipient
        if sender not in AGENTS or recipient not in AGENTS:
            raise ValueError(f"Invalid agents: {sender} -> {recipient}")
        
        # Ensure destination directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and validate message before moving
        try:
            with open(src, 'r') as f:
                message_data = yaml.safe_load(f)
            
            if not validate_message(message_data):
                log_warning("Message validation failed, but proceeding with move")
        
        except Exception as e:
            log_warning(f"Could not validate message content: {e}")
        
        # Atomic copy operation (copy2 preserves metadata)
        copy2(src, dst)
        log_success(f"Moved {src.name} from {sender} to {recipient}")
        
        return dst
        
    except Exception as e:
        log_error(f"Failed to move message: {e}")
        raise

def archive_message(agent, msg_id):
    """Archive a message from inbox to archive"""
    try:
        src = INBOX / agent / f"{agent.lower()}_{msg_id}.yaml"
        if not src.exists():
            # Try outbox
            src = OUTBOX / agent / f"{agent.lower()}_{msg_id}.yaml"
        
        if not src.exists():
            raise FileNotFoundError(f"Message not found for archiving: {msg_id}")
        
        # Create archive directory with date
        archive_date = datetime.datetime.now().strftime("%Y-%m-%d")
        archive_dir = ARCHIVE / archive_date
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        dst = archive_dir / src.name
        copy2(src, dst)
        
        log_success(f"Archived {src.name} to {archive_date}")
        return dst
        
    except Exception as e:
        log_error(f"Failed to archive message: {e}")
        raise

# === ENHANCED CONVERSION FUNCTIONS ===
def midi_to_json(yaml_path):
    """Convert MIDI YAML message to JSON with symbol lookups"""
    try:
        if isinstance(yaml_path, str):
            yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        
        with open(yaml_path) as f:
            msg = yaml.safe_load(f)
        
        # Load symbol table for note meaning lookup
        symbols = load_symbol_table()
        note_meanings = []
        
        if symbols and 'notes' in symbols:
            note_meanings = [symbols['notes'].get(note, f"unknown_{note}") 
                           for note in msg.get("notes", [])]
        
        # Build comprehensive JSON representation
        json_data = {
            "message_id": msg.get("message_id"),
            "timestamp": msg.get("timestamp"),
            "agent": msg.get("from"),
            "recipient": msg.get("to"),
            "notes": msg.get("notes", []),
            "note_meanings": note_meanings,
            "velocity": msg.get("velocity"),
            "channel": msg.get("channel"),
            "group_id": msg.get("group_id"),
            "context": msg.get("context", {}),
            "intent": msg.get("context", {}).get("intent", "unknown"),
            "tone": msg.get("context", {}).get("tone", "neutral"),
            "human_readable": msg.get("human_readable", ""),
            "reply_to": msg.get("reply_to")
        }
        
        log_success(f"Converted MIDI YAML to JSON: {yaml_path.name}")
        return json_data
        
    except Exception as e:
        log_error(f"MIDI to JSON conversion failed: {e}")
        return None

def json_to_midi(data, output_path, message_id=None):
    """Convert JSON data to MIDI YAML format"""
    try:
        if not message_id:
            message_id = data.get("message_id", f"msg_{int(time.time())}")
        
        # Build MIDI YAML structure
        midi_msg = {
            "message_id": message_id,
            "from": data.get("agent", data.get("from", "Unknown")),
            "to": data.get("recipient", data.get("to", "Unknown")),
            "timestamp": data.get("timestamp", datetime.datetime.now().isoformat() + "Z"),
            "notes": data.get("notes", []),
            "velocity": data.get("velocity", 100),
            "channel": data.get("channel", 1),
            "group_id": data.get("group_id", "UMP_GROUP_001"),
            "context": {
                "intent": data.get("intent", "unknown"),
                "tone": data.get("tone", "neutral"),
                "topic": data.get("context", {}).get("topic", "general")
            },
            "human_readable": data.get("human_readable", ""),
            "reply_to": data.get("reply_to")
        }
        
        # Remove None values
        midi_msg = {k: v for k, v in midi_msg.items() if v is not None}
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            yaml.dump(midi_msg, f, default_flow_style=False)
        
        log_success(f"Generated MIDI YAML message at {output_path}")
        return output_path
        
    except Exception as e:
        log_error(f"JSON to MIDI conversion failed: {e}")
        return None

# === SYSTEM STATUS AND UTILITIES ===
def get_system_status():
    """Get comprehensive system status"""
    status = {
        "timestamp": datetime.datetime.now().isoformat(),
        "directories_exist": BASE.exists(),
        "symbol_table_exists": SYMBOL_TABLE.exists(),
        "agents": {}
    }
    
    for agent in AGENTS:
        inbox_path = INBOX / agent
        outbox_path = OUTBOX / agent
        
        inbox_count = len(list(inbox_path.glob("*.yaml"))) if inbox_path.exists() else 0
        outbox_count = len(list(outbox_path.glob("*.yaml"))) if outbox_path.exists() else 0
        
        status["agents"][agent] = {
            "inbox_messages": inbox_count,
            "outbox_messages": outbox_count,
            "inbox_exists": inbox_path.exists(),
            "outbox_exists": outbox_path.exists()
        }
    
    return status

def print_system_status():
    """Print formatted system status"""
    status = get_system_status()
    
    print(f"\n🎵 SYMBOLIC MIDI SYSTEM STATUS")
    print("=" * 50)
    print(f"Timestamp: {status['timestamp']}")
    print(f"Base Directory: {BASE}")
    print(f"Symbol Table: {'✅' if status['symbol_table_exists'] else '❌'}")
    print()
    
    for agent, info in status["agents"].items():
        inbox_icon = "📥" if info["inbox_exists"] else "❌"
        outbox_icon = "📤" if info["outbox_exists"] else "❌"
        print(f"{agent}: {inbox_icon} {info['inbox_messages']} inbox | {outbox_icon} {info['outbox_messages']} outbox")
    
    # Show recent log entries
    log_file = LOGS / "symbolic_midi_log.txt"
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            print(f"\n📝 Recent Activity ({len(lines)} total entries):")
            for line in lines[-5:]:  # Show last 5 entries
                print(f"   {line.strip()}")
        except Exception as e:
            print(f"Could not read log file: {e}")

def cleanup_old_messages(days_old=7):
    """Archive messages older than specified days"""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
    archived_count = 0
    
    for agent in AGENTS:
        for directory in [INBOX / agent, OUTBOX / agent]:
            if not directory.exists():
                continue
                
            for message_file in directory.glob("*.yaml"):
                try:
                    file_time = datetime.datetime.fromtimestamp(message_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        # Archive the message
                        archive_message(agent, message_file.stem.split('_')[-1])
                        message_file.unlink()  # Remove original
                        archived_count += 1
                except Exception as e:
                    log_warning(f"Could not archive old message {message_file}: {e}")
    
    log_success(f"Archived {archived_count} old messages")
    return archived_count

# === MAIN EXECUTION AND TESTING ===
def main():
    """Main function for testing and utility operations"""
    print("🎵 Enhanced Symbolic MIDI Tools v1.1")
    print("=" * 50)
    
    # Initialize system
    if not ensure_directories():
        print("❌ Failed to initialize directory structure")
        return
    
    # Load and validate symbol table
    symbols = load_symbol_table()
    if not symbols:
        print("❌ Failed to load symbol table")
        return
    
    print(f"✅ Loaded symbol table with {len(symbols.get('notes', {}))} symbolic notes")
    
    while True:
        print(f"\n" + "="*40)
        print("SYMBOLIC MIDI TOOLS:")
        print("1. Show system status")
        print("2. Move message")
        print("3. Convert MIDI to JSON")
        print("4. Convert JSON to MIDI")
        print("5. Archive old messages")
        print("6. Test message validation")
        print("7. Exit")
        
        choice = input("Choice (1-7): ").strip()
        
        if choice == "1":
            print_system_status()
            
        elif choice == "2":
            sender = input("Sender: ").strip()
            recipient = input("Recipient: ").strip()
            msg_id = input("Message ID: ").strip()
            
            try:
                result = move_message(sender, recipient, msg_id)
                print(f"✅ Message moved to: {result}")
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == "3":
            yaml_path = input("YAML file path: ").strip()
            result = midi_to_json(yaml_path)
            if result:
                print("✅ Conversion successful:")
                print(json.dumps(result, indent=2))
            else:
                print("❌ Conversion failed")
                
        elif choice == "4":
            print("Enter JSON data (or press Enter for sample):")
            json_input = input().strip()
            
            if not json_input:
                # Sample data
                sample_data = {
                    "agent": "Claude",
                    "recipient": "Kai",
                    "notes": [62, 63],
                    "velocity": 110,
                    "intent": "test_conversion",
                    "human_readable": "Test conversion from JSON to MIDI"
                }
                json_input = json.dumps(sample_data)
            
            try:
                data = json.loads(json_input)
                output_path = input("Output path: ").strip() or "test_output.yaml"
                result = json_to_midi(data, output_path)
                if result:
                    print(f"✅ MIDI YAML created: {result}")
                else:
                    print("❌ Conversion failed")
            except json.JSONDecodeError:
                print("❌ Invalid JSON input")
                
        elif choice == "5":
            days = input("Archive messages older than days (default 7): ").strip()
            days = int(days) if days.isdigit() else 7
            count = cleanup_old_messages(days)
            print(f"✅ Archived {count} messages")
            
        elif choice == "6":
            yaml_path = input("YAML file to validate: ").strip()
            try:
                with open(yaml_path, 'r') as f:
                    message_data = yaml.safe_load(f)
                
                if validate_message(message_data, symbols):
                    print("✅ Message is valid")
                else:
                    print("❌ Message validation failed")
            except Exception as e:
                print(f"❌ Error validating message: {e}")
                
        elif choice == "7":
            print("👋 Symbolic MIDI Tools shutting down")
            break
            
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        # Quick initialization and status check
        ensure_directories()
        symbols = load_symbol_table()
        
        if len(os.sys.argv) > 1:
            # Command line mode
            if os.sys.argv[1] == "status":
                print_system_status()
            elif os.sys.argv[1] == "move" and len(os.sys.argv) >= 5:
                sender, recipient, msg_id = os.sys.argv[2], os.sys.argv[3], os.sys.argv[4]
                move_message(sender, recipient, msg_id)
            else:
                print("Usage: python symbolic_midi_tools.py [status|move sender recipient msg_id]")
        else:
            # Interactive mode
            main()
            
    except Exception as e:
        log_error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")