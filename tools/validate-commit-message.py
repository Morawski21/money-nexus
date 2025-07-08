"""
Validate commit message format following Angular-style conventions.
Format: 'type: Commit message starting with a capital letter'
"""

import re
import sys
from pathlib import Path


def validate_commit_message(message: str) -> bool:
    """
    Validate commit message format.

    Args:
        message: The commit message to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Remove leading/trailing whitespace
    message = message.strip()

    # Valid Angular commit types
    valid_types = {
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "test",
        "chore",
        "perf",
        "ci",
        "build",
        "revert",
    }

    # Pattern: 'type: Message starting with capital letter'
    pattern = r"^([a-z]+):\s+([A-Z].*)$"
    match = re.match(pattern, message)

    if not match:
        return False

    commit_type = match.group(1)
    commit_message = match.group(2)

    # Check if type is valid
    if commit_type not in valid_types:
        print(f"Error: Invalid commit type '{commit_type}'")
        print(f"Valid types: {', '.join(sorted(valid_types))}")
        return False

    # Check if message starts with capital letter
    if not commit_message[0].isupper():
        print("Error: Commit message must start with a capital letter")
        return False

    return True


def main():
    """Main function with error handling."""
    if len(sys.argv) != 2:
        print("Usage: validate-commit-message.py <commit-message-file>")
        sys.exit(1)

    commit_msg_file = Path(sys.argv[1])

    if not commit_msg_file.exists():
        print(f"Error: Commit message file '{commit_msg_file}' not found")
        sys.exit(1)

    try:
        with open(commit_msg_file, "r", encoding="utf-8") as f:
            commit_message = f.read().strip()
    except Exception as e:
        print(f"Error reading commit message file: {e}")
        sys.exit(1)

    if not commit_message:
        print("Error: Commit message is empty")
        sys.exit(1)

    print(f"Validating commit message: '{commit_message}'")

    if validate_commit_message(commit_message):
        print("Commit message format is valid")
        sys.exit(0)
    else:
        print("Commit message format is invalid")
        print("Expected format: 'type: Message starting with capital letter'")
        print("Example: 'feat: Add new user authentication feature'")
        sys.exit(1)


if __name__ == "__main__":
    main()
