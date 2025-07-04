#!/usr/bin/env python3
"""
Enhanced Symbolic MIDI Interface
Secure, atomic message handling for AI Council symbolic communication
"""

from pathlib import Path
import yaml
import datetime
import shutil
import fcntl
import os
import time

# === CONFIGURATION ===

# Base directory (adjust to match your machine)
root_dir = Path("/Users/jonstiles/Desktop/AI_Council_Comm/MIDI_Exchange")
inbox_dir = root_dir / "inbox"
outbox_dir = root_dir / "outbox"
logs_dir = root_dir / "logs"
symbol_table_path = root_dir / "symbol_tables" / "symbol_table_v0.1.yaml"

# Agent directories
agents = ["Kai", "Claude", "Perplexity", "Grok"]

# === INITIALIZATION ===

def ensure_directory_structure():
    """Create all necessary directories"""
    root_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    for agent in agents:
        (inbox_dir / agent).mkdir(parents=True, exist_ok=True)
        (outbox_dir / agent).mkdir(parents=True, exist_ok=True)
    
    (root_dir / "symbol_tables").mkdir(parents=True, exist_ok=True)
    print("✅ Directory structure created")

# === LOAD SYMBOL TABLE ===

def load_symbol_table(path):
    """Load and validate symbol table"""
    try:
        with open(path, "r") as file:
            table = yaml.safe_load(file)
        print(f"✅ Symbol table loaded from {path}")
        return table
    except FileNotFoundError:
        print(f"⚠️ Symbol table not found at {path}")
        return create_default_symbol_table(path)
    except Exception as e:
        print(f"❌ Error loading symbol table: {e}")
        return None

def create_default_symbol_table(path):
    """Create default symbol table if none exists"""
    default_table = {
        'notes': {
            60: 'confirm',
            61: 'query', 
            62: 'reflection',
            63: 'agreement',
            64: 'inquiry',
            65: 'proposal',
            66: 'clarify',
            68: 'refer_to_standard'
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
            'high': 127
        },
        'cc': {
            1: 'topic_ethics',
            2: 'topic_memory',
            3: 'topic_semantics',
            4: 'topic_creativity'
        }
    }
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        yaml.dump(default_table, f, default_flow_style=False)
    
    print(f"✅ Created default symbol table at {path}")
    return default_table

# === LOGGER FUNCTION ===

def log_message(action, agent, message_file, details=""):
    """Enhanced logging with more details"""
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {action.upper()} | {agent} | {message_file.name} | {details}\n"
    
    try:
        with open(logs_dir / "symbolic_midi_log.txt", "a") as log_file:
            fcntl.flock(log_file.fileno(), fcntl.LOCK_EX)
            log_file.write(log_line)
    except Exception as e:
        print(f"⚠️ Logging error: {e}")

# === MESSAGE VALIDATION ===

def validate_message(message_data, symbol_table):
    """Validate message against symbol table and required fields"""
    if not symbol_table:
        print("⚠️ No symbol table available for validation")
        return False
    
    # Check required fields
    required_fields = ['message_id', 'from', 'to', 'notes', 'velocity', 'channel']
    missing_fields = []
    
    for field in required_fields:
        if field not in message_data:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        return False
    
    # Validate notes against symbol table
    unknown_notes = []
    for note in message_data['notes']:
        if note not in symbol_table.get('notes', {}):
            unknown_notes.append(note)
    
    if unknown_notes:
        print(f"⚠️ Warning: Unknown notes in symbol table: {unknown_notes}")
    
    # Validate channel
    channel = message_data['channel']
    if channel not in symbol_table.get('channels', {}):
        print(f"⚠️ Warning: Channel {channel} not in symbol table")
    
    # Validate velocity range
    velocity = message_data['velocity']
    if not (0 <= velocity <= 127):
        print(f"❌ Invalid velocity: {velocity} (must be 0-127)")
        return False
    
    print(f"✅ Message validation passed for {message_data['message_id']}")
    return True

# === ATOMIC MESSAGE OPERATIONS ===

def atomic_write_message(agent, message_data, message_id):
    """Write message atomically to prevent corruption"""
    agent_outbox = outbox_dir / agent
    agent_outbox.mkdir(parents=True, exist_ok=True)
    
    temp_file = agent_outbox / f".temp_{agent.lower()}_{message_id}.yaml"
    final_file = agent_outbox / f"{agent.lower()}_{message_id}.yaml"
    
    try:
        # Write to temporary file with exclusive lock
        with open(temp_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
            yaml.dump(message_data, f, default_flow_style=False)
        
        # Atomic rename (this is atomic on most filesystems)
        temp_file.rename(final_file)
        
        log_message("created", agent, final_file, f"ID: {message_id}")
        print(f"✅ Message {message_id} written atomically for {agent}")
        return final_file
        
    except Exception as e:
        # Clean up temp file if something went wrong
        if temp_file.exists():
            temp_file.unlink()
        print(f"❌ Error writing message: {e}")
        return None

def safe_read_message(message_file):
    """Safely read a message file with retry logic"""
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # Wait for file to be stable (not being written)
            file_size = message_file.stat().st_size
            time.sleep(0.1)
            if message_file.stat().st_size != file_size:
                print(f"⏳ File {message_file.name} still being written, retrying...")
                time.sleep(retry_delay)
                continue
            
            with open(message_file, "r") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                data = yaml.safe_load(f)
            
            print(f"✅ Successfully read {message_file.name}")
            return data
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Read attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(retry_delay)
            else:
                print(f"❌ Failed to read {message_file.name} after {max_retries} attempts: {e}")
                return None
    
    return None

# === MOVE FUNCTION (Enhanced) ===

def move_message(sender, recipient, message_id="0001", symbol_table=None):
    """Move message from sender outbox to recipient inbox with validation"""
    source_file = outbox_dir / sender / f"{sender.lower()}_{message_id}.yaml"
    target_folder = inbox_dir / recipient
    target_folder.mkdir(parents=True, exist_ok=True)
    target_file = target_folder / source_file.name

    if not source_file.exists():
        raise FileNotFoundError(f"Message not found: {source_file}")

    # Read and validate message before moving
    message_data = safe_read_message(source_file)
    if not message_data:
        raise ValueError(f"Could not read message: {source_file}")
    
    if symbol_table and not validate_message(message_data, symbol_table):
        print(f"⚠️ Message validation failed, but proceeding with move")

    # Atomic copy operation
    try:
        shutil.copy2(source_file, target_file)  # copy2 preserves metadata
        log_message("moved", sender, source_file, f"to {recipient}")
        print(f"✅ Moved {source_file.name} from {sender} to {recipient}")
        return target_file
    except Exception as e:
        print(f"❌ Error moving message: {e}")
        return None

# === INBOX SCANNING ===

def scan_inbox(agent):
    """Scan agent inbox for new messages"""
    agent_inbox = inbox_dir / agent
    if not agent_inbox.exists():
        print(f"No inbox found for {agent}")
        return []
    
    messages = list(agent_inbox.glob("*.yaml"))
    if messages:
        print(f"📥 Found {len(messages)} messages in {agent}'s inbox")
        for msg in messages:
            print(f"   - {msg.name}")
    else:
        print(f"📭 No messages in {agent}'s inbox")
    
    return messages

def get_latest_message(agent):
    """Get the most recent message for an agent"""
    messages = scan_inbox(agent)
    if not messages:
        return None
    
    # Sort by modification time, get latest
    latest = max(messages, key=lambda f: f.stat().st_mtime)
    return safe_read_message(latest)

# === UTILITY FUNCTIONS ===

def create_sample_message(sender, recipient, message_id, notes, velocity=110):
    """Create a sample message for testing"""
    message_data = {
        'message_id': f"{sender.lower()}_{message_id}",
        'from': sender,
        'to': recipient,
        'timestamp': datetime.datetime.now().isoformat() + "Z",
        'notes': notes,
        'velocity': velocity,
        'channel': {'Kai': 1, 'Claude': 2, 'Perplexity': 3, 'Grok': 4}.get(sender, 1),
        'group_id': 'UMP_GROUP_001',
        'context': {
            'intent': 'test_message',
            'tone': 'experimental',
            'topic': 'symbolic_midi_testing'
        },
        'human_readable': f'Test message from {sender} to {recipient}'
    }
    return message_data

def show_system_status():
    """Display system status and statistics"""
    print(f"\n📊 SYMBOLIC MIDI SYSTEM STATUS")
    print("=" * 50)
    
    for agent in agents:
        inbox_count = len(list((inbox_dir / agent).glob("*.yaml"))) if (inbox_dir / agent).exists() else 0
        outbox_count = len(list((outbox_dir / agent).glob("*.yaml"))) if (outbox_dir / agent).exists() else 0
        print(f"{agent}: 📥 {inbox_count} inbox | 📤 {outbox_count} outbox")
    
    # Show recent log entries
    log_file = logs_dir / "symbolic_midi_log.txt"
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        print(f"\n📝 Recent activity ({len(lines)} total log entries):")
        for line in lines[-5:]:  # Show last 5 entries
            print(f"   {line.strip()}")

# === MAIN EXECUTION ===

def main():
    """Main function for testing and operations"""
    print("🎵 Enhanced Symbolic MIDI Interface v1.1")
    print("=" * 50)
    
    # Ensure directory structure exists
    ensure_directory_structure()
    
    # Load symbol table
    symbol_table = load_symbol_table(symbol_table_path)
    
    while True:
        print(f"\n" + "="*40)
        print("SYMBOLIC MIDI OPERATIONS:")
        print("1. Show system status")
        print("2. Scan agent inbox")
        print("3. Move message")
        print("4. Create test message")
        print("5. Validate message")
        print("6. Exit")
        
        choice = input("Choice (1-6): ").strip()
        
        if choice == "1":
            show_system_status()
            
        elif choice == "2":
            agent = input("Agent name (Kai/Claude/Perplexity/Grok): ").strip()
            if agent in agents:
                scan_inbox(agent)
            else:
                print("❌ Invalid agent name")
                
        elif choice == "3":
            sender = input("Sender: ").strip()
            recipient = input("Recipient: ").strip()
            message_id = input("Message ID (e.g., 0001): ").strip() or "0001"
            
            if sender in agents and recipient in agents:
                try:
                    move_message(sender, recipient, message_id, symbol_table)
                except Exception as e:
                    print(f"❌ Error: {e}")
            else:
                print("❌ Invalid agent names")
                
        elif choice == "4":
            sender = input("Sender: ").strip()
            recipient = input("Recipient: ").strip()
            message_id = input("Message ID: ").strip() or "test001"
            notes = [62, 63]  # Default: reflection + agreement
            
            if sender in agents and recipient in agents:
                message_data = create_sample_message(sender, recipient, message_id, notes)
                if validate_message(message_data, symbol_table):
                    atomic_write_message(sender, message_data, message_id)
                else:
                    print("❌ Message validation failed")
            else:
                print("❌ Invalid agent names")
                
        elif choice == "5":
            agent = input("Agent: ").strip()
            message_id = input("Message ID: ").strip()
            message_file = outbox_dir / agent / f"{agent.lower()}_{message_id}.yaml"
            
            if message_file.exists():
                message_data = safe_read_message(message_file)
                if message_data:
                    validate_message(message_data, symbol_table)
            else:
                print(f"❌ Message file not found: {message_file}")
                
        elif choice == "6":
            print("👋 Symbolic MIDI Interface shutting down")
            break
            
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    # Quick test if run directly
    try:
        ensure_directory_structure()
        symbol_table = load_symbol_table(symbol_table_path)
        
        # Test move if arguments provided
        import sys
        if len(sys.argv) >= 4:
            sender, recipient, message_id = sys.argv[1], sys.argv[2], sys.argv[3]
            move_message(sender, recipient, message_id, symbol_table)
        else:
            main()
            
    except Exception as e:
        print(f"❌ Error: {e}")