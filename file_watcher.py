#!/usr/bin/env python3
"""
File Watcher for AI Employee Vault
Watches /Inbox folder and moves new files to /Needs_Action with metadata.
"""

import os
import time
import shutil
from datetime import datetime
from pathlib import Path

# Get the vault root directory (where this script is located)
VAULT_ROOT = Path(__file__).parent.resolve()
INBOX_DIR = VAULT_ROOT / "Inbox"
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"

# Supported file extensions and their suggested actions
FILE_ACTIONS = {
    ".txt": ["Summarize content", "Extract key points", "File for reference"],
    ".md": ["Review and process", "Summarize content", "Extract action items"],
    ".pdf": ["Review document", "Extract key information", "Archive"],
    ".doc": ["Review document", "Extract key information", "Archive"],
    ".docx": ["Review document", "Extract key information", "Archive"],
    ".csv": ["Analyze data", "Generate report", "Import to database"],
    ".xlsx": ["Analyze data", "Generate report", "Import to database"],
    ".json": ["Process data", "Validate structure", "Import to system"],
    ".xml": ["Process data", "Validate structure", "Transform format"],
    ".email": ["Reply to sender", "Extract action items", "Archive"],
    ".eml": ["Reply to sender", "Extract action items", "Archive"],
}

DEFAULT_ACTIONS = ["Review and process", "Determine next steps", "Archive"]


def get_file_type(extension: str) -> str:
    """Categorize file by extension."""
    ext = extension.lower()
    if ext in [".txt", ".md"]:
        return "text"
    elif ext in [".pdf", ".doc", ".docx"]:
        return "document"
    elif ext in [".csv", ".xlsx", ".json", ".xml"]:
        return "data"
    elif ext in [".email", ".eml"]:
        return "email"
    else:
        return "file"


def get_suggested_actions(extension: str) -> list:
    """Get suggested actions based on file extension."""
    return FILE_ACTIONS.get(extension.lower(), DEFAULT_ACTIONS)


def create_metadata_file(original_name: str, new_name: str, file_path: Path) -> None:
    """Create a markdown metadata file for the processed file."""
    extension = Path(original_name).suffix
    file_type = get_file_type(extension)
    suggested_actions = get_suggested_actions(extension)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metadata_content = f"""---
type: {file_type}
priority: normal
status: pending
original_name: {original_name}
processed_name: {new_name}
created_at: {timestamp}
source: inbox
---

# File: {original_name}

## Metadata
- **Original Name:** {original_name}
- **Processed Name:** {new_name}
- **Type:** {file_type}
- **Received:** {timestamp}

## Suggested Actions
"""

    for action in suggested_actions:
        metadata_content += f"- [ ] {action}\n"

    metadata_content += f"""
## Notes
_Add any notes or context about this file here._

## Status History
- {timestamp}: File received and moved from Inbox
"""

    # Create metadata file with same name but .md extension
    metadata_path = file_path.with_suffix(".md")
    metadata_path.write_text(metadata_content, encoding="utf-8")
    print(f"  Created metadata: {metadata_path.name}")


def process_file(file_path: Path) -> bool:
    """Process a single file: move to Needs_Action and create metadata."""
    try:
        # Generate timestamp prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get original filename
        original_name = file_path.name
        extension = file_path.suffix
        stem = file_path.stem

        # Create new filename with timestamp prefix
        new_name = f"{timestamp}_{original_name}"
        new_path = NEEDS_ACTION_DIR / new_name

        # Ensure Needs_Action directory exists
        NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)

        # Move the file
        shutil.move(str(file_path), str(new_path))
        print(f"  Moved: {original_name} -> {new_name}")

        # Create metadata file
        create_metadata_file(original_name, new_name, new_path)

        return True

    except Exception as e:
        print(f"  ERROR processing {file_path.name}: {e}")
        return False


def get_existing_files() -> set:
    """Get set of files currently in Inbox."""
    if not INBOX_DIR.exists():
        return set()
    return set(f.name for f in INBOX_DIR.iterdir() if f.is_file())


def main():
    """Main watcher loop."""
    print("=" * 50)
    print("AI Employee File Watcher")
    print("=" * 50)
    print(f"Watching: {INBOX_DIR}")
    print(f"Output to: {NEEDS_ACTION_DIR}")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    # Ensure directories exist
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)

    # Track existing files
    known_files = get_existing_files()

    if known_files:
        print(f"\nFound {len(known_files)} existing file(s) in Inbox (will process new files only)")
    else:
        print("\nInbox is empty. Waiting for new files...")

    try:
        while True:
            try:
                # Get current files
                current_files = get_existing_files()

                # Find new files
                new_files = current_files - known_files

                if new_files:
                    for filename in new_files:
                        file_path = INBOX_DIR / filename
                        print(f"\n[NEW FILE DETECTED] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  File: {filename}")
                        process_file(file_path)

                    # Update known files after processing
                    known_files = get_existing_files()
                    print(f"\nWaiting for new files...")

                # Check for deleted files (cleanup known_files)
                deleted_files = known_files - current_files
                if deleted_files:
                    known_files = current_files

                # Wait before next check
                time.sleep(1)

            except Exception as e:
                print(f"\nERROR: {e}")
                print("Continuing to watch...")
                time.sleep(5)  # Wait a bit longer after an error

    except KeyboardInterrupt:
        print("\n\n" + "=" * 50)
        print("File watcher stopped by user.")
        print("=" * 50)


if __name__ == "__main__":
    main()