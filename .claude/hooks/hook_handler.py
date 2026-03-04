#!/usr/bin/env python3
"""
Claude Code Hook Handler
=============================================
Central orchestrator for all Claude Code hooks.
Auto-generates voice sounds using macOS `say` command.
"""

import sys
import json
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any
import re

# ===== CONFIGURATION =====
# Voice to use for text-to-speech (run `say -v '?'` to see all available voices)
VOICE = "Samantha"  # Clear, professional female voice
# Alternative voices: "Daniel" (British), "Alex" (US male), "Karen" (Australian)

# Audio format for generated files
AUDIO_FORMAT = "aiff"  # macOS native format, works best with afplay

# Sounds directory type
SOUNDS_TYPE = "voice"

# Volume for playback (0.0 to 1.0, where 1.0 is full volume)
VOLUME = 0.2  # 30% volume - adjust as needed

# ===== VOICE MESSAGES =====
# Maps sound names to spoken messages
# Format: "sound_name": "message to speak"
VOICE_MESSAGES = {
    # System events
    "ready": "Ready",
    "task_complete": "Task complete",
    "session_start": "Session started",

    # File operations
    "edit": "File edited",
    "write": "File created",
    "multi_edit": "Multiple edits applied",

    # Code structure
    "structure_change": "Code structure changed",
    "file_size_check": "Checking file sizes",

    # Git operations
    "commit": "Changes committed",
    "pr": "Pull request action",
    "push": "Code pushed",

    # Testing
    "test": "Running tests",
    "test_pass": "Tests passed",
    "test_fail": "Tests failed",

    # Task management
    "list": "List updated",

    # Bash
    "bash": "Command executed",

    # Errors/Warnings
    "warning": "Warning",
    "error": "Error occurred",

    # File size check
    "files_ok": "All files within limit",
    "files_need_refactor": "Files need refactoring",
}

# ===== EVENT TO SOUND MAPPING =====
# Maps Claude events and tools to sound names (keys in VOICE_MESSAGES)
EVENT_SOUND_MAP = {
    # System events
    "Notification": "ready",
    "Stop": "task_complete",
    "SubagentStop": "task_complete",
    "SessionStart": "session_start",

    # File tools
    "Edit": "edit",
    "Write": "write",
    "MultiEdit": "multi_edit",
    "NotebookEdit": "edit",

    # Task management
    "TodoWrite": "list",
}

# Bash command patterns -> sound name
# Format: (regex_pattern, sound_name)
BASH_PATTERNS = [
    (r'^git commit', "commit"),
    (r'^git push', "push"),
    (r'^gh pr', "pr"),
    (r'^npm test|^yarn test|^pytest|^poetry run pytest|^go test|^rspec', "test"),
    (r'.*', "bash"),  # Fallback for any bash command
]

# Error patterns to detect in command output
# Format: (regex_pattern, is_test_failure)
ERROR_PATTERNS = [
    # Test failures
    (r'FAILED|FAILURES|tests? failed|AssertionError', True),
    (r'pytest.*\d+ failed', True),
    (r'npm ERR!.*test', True),
    (r'jest.*failed', True),
    (r'✗.*test|✖.*test', True),

    # General errors
    (r'Error:|ERROR:|error:|Exception:|Traceback \(most recent call last\)', False),
    (r'ModuleNotFoundError|ImportError|SyntaxError|NameError|TypeError', False),
    (r'FileNotFoundError|PermissionError|OSError', False),
    (r'command not found|No such file or directory', False),
    (r'fatal:|FATAL:', False),
    (r'panic:|PANIC:', False),
    (r'failed to|Failed to|cannot |Cannot ', False),
    (r'exit code [1-9]|exit status [1-9]|returned [1-9]', False),
]


def get_sounds_dir() -> Path:
    """Get the sounds directory path, creating it if needed."""
    sounds_dir = Path(__file__).parent / "sounds" / SOUNDS_TYPE
    sounds_dir.mkdir(parents=True, exist_ok=True)
    return sounds_dir


def generate_sound(sound_name: str, message: str) -> Path:
    """
    Generate a voice sound file using macOS `say` command.

    Args:
        sound_name: Name for the sound file (without extension)
        message: Text to speak

    Returns:
        Path to the generated sound file
    """
    sounds_dir = get_sounds_dir()
    output_file = sounds_dir / f"{sound_name}.{AUDIO_FORMAT}"

    try:
        subprocess.run(
            ["say", "-v", VOICE, message, "-o", str(output_file)],
            check=True,
            capture_output=True,
            timeout=10
        )
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error generating sound '{sound_name}': {e}", file=sys.stderr)
        raise
    except subprocess.TimeoutExpired:
        print(f"Timeout generating sound '{sound_name}'", file=sys.stderr)
        raise


def ensure_sound_exists(sound_name: str) -> Optional[Path]:
    """
    Ensure a sound file exists, generating it if needed.

    Args:
        sound_name: Name of the sound (key in VOICE_MESSAGES)

    Returns:
        Path to the sound file, or None if it couldn't be created
    """
    if sound_name not in VOICE_MESSAGES:
        return None

    sounds_dir = get_sounds_dir()
    sound_file = sounds_dir / f"{sound_name}.{AUDIO_FORMAT}"

    # Generate if doesn't exist
    if not sound_file.exists():
        try:
            message = VOICE_MESSAGES[sound_name]
            generate_sound(sound_name, message)
        except Exception as e:
            print(
                f"Failed to generate sound '{sound_name}': {e}", file=sys.stderr)
            return None

    return sound_file if sound_file.exists() else None


def ensure_all_sounds_exist():
    """Pre-generate all sound files."""
    for sound_name in VOICE_MESSAGES:
        ensure_sound_exists(sound_name)


def play_sound(sound_name: str, wait: bool = True) -> bool:
    """
    Play a sound file, generating it first if needed.

    Args:
        sound_name: Name of the sound to play
        wait: If True, wait for sound to finish before returning (sequential playback)

    Returns:
        True if sound played successfully
    """
    # Security check
    if "/" in sound_name or "\\" in sound_name or ".." in sound_name:
        print(f"Invalid sound name: {sound_name}", file=sys.stderr)
        return False

    sound_file = ensure_sound_exists(sound_name)

    if not sound_file:
        return False

    try:
        if wait:
            # Wait for sound to finish - ensures sequential playback
            subprocess.run(
                ["afplay", "-v", str(VOLUME), str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5  # Max 5 seconds per sound
            )
        else:
            # Play in background (parallel)
            subprocess.Popen(
                ["afplay", "-v", str(VOLUME), str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        return True
    except subprocess.TimeoutExpired:
        return True  # Sound played but took too long, continue anyway
    except (FileNotFoundError, OSError) as e:
        print(f"Error playing sound {sound_name}: {e}", file=sys.stderr)
        return False


def log_hook_data(hook_data: Dict[str, Any]):
    """Log hook data for debugging/auditing."""
    try:
        log_path = Path(__file__).parent / "hook_handler.jsonl"
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(hook_data, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Failed to log hook_data: {e}", file=sys.stderr)


def detect_error_in_output(output: str) -> Optional[str]:
    """
    Detect errors in command output.

    Args:
        output: Command output text to analyze

    Returns:
        "test_fail" for test failures, "error" for general errors, None if no error
    """
    if not output:
        return None

    for pattern, is_test_failure in ERROR_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
            return "test_fail" if is_test_failure else "error"

    return None


def get_sound_for_event(hook_data: Dict[str, Any]) -> Optional[str]:
    """
    Determine which sound to play based on Claude's action.

    Args:
        hook_data: Event data from Claude

    Returns:
        Sound name or None
    """
    event_name = hook_data.get("hook_event_name", "")
    tool_name = hook_data.get("tool_name", "")

    # Check system events first
    if event_name in EVENT_SOUND_MAP:
        return EVENT_SOUND_MAP[event_name]

    # Check tool name
    if tool_name in EVENT_SOUND_MAP:
        return EVENT_SOUND_MAP[tool_name]

    # Special handling for Bash commands
    if tool_name == "Bash":
        command = hook_data.get("tool_input", {}).get("command", "")
        for pattern, sound_name in BASH_PATTERNS:
            if re.match(pattern, command, re.IGNORECASE):
                return sound_name

    return None


def run_structure_change_check() -> bool:
    """
    Run the structure change detection logic.
    Returns True on success (even if webhook fails).
    """
    play_sound("structure_change")  # Always play sound when check runs
    try:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            project_dir = Path(__file__).resolve().parents[2]

        script_path = Path(__file__).parent / "structure_change.py"
        if script_path.exists():
            result = subprocess.run(
                ["poetry", "run", "python", str(script_path)],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            # Log output for debugging
            if result.stdout:
                print(
                    f"structure_change: {result.stdout.strip()}", file=sys.stderr)
            if result.stderr:
                print(
                    f"structure_change stderr: {result.stderr.strip()}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Structure change check warning: {e}", file=sys.stderr)
        return True  # Don't block on failure


def run_file_size_check() -> bool:
    """
    Run file size verification.
    Checks if Python files in backend exceed 500 lines.
    Returns True if all files are within limits.
    """
    play_sound("file_size_check")  # Always play sound when check runs
    try:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            project_dir = Path(__file__).resolve().parents[2]

        script_path = Path(__file__).parent / "verify_file_size.py"
        if script_path.exists():
            result = subprocess.run(
                ["poetry", "run", "python", str(script_path)],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=180  # Increased for Plane API calls
            )
            # Check stderr for report (script always exits 0)
            if "OVERSIZED FILES REPORT" in result.stderr:
                play_sound("files_need_refactor")
                # Count how many files need refactoring
                import re
                match = re.search(r"Found (\d+) file", result.stderr)
                if match:
                    count = match.group(1)
                    print(
                        f"File size check: {count} files exceed 500 lines - see report", file=sys.stderr)
                return False
            else:
                play_sound("files_ok")
                return True
        return True
    except Exception as e:
        print(f"File size check warning: {e}", file=sys.stderr)
        return True  # Don't block on failure


def handle_post_tool_use(hook_data: Dict[str, Any]):
    """Handle PostToolUse events."""
    tool_name = hook_data.get("tool_name", "")

    # Check for errors in Bash command output
    if tool_name == "Bash":
        tool_result = hook_data.get("tool_result", {})
        # Handle both string and dict result formats
        if isinstance(tool_result, str):
            output = tool_result
        else:
            output = tool_result.get("stdout", "") + tool_result.get("stderr", "")

        error_sound = detect_error_in_output(output)
        if error_sound:
            play_sound(error_sound)
            return  # Don't play the normal bash sound if there was an error

    # Play sound for the tool
    sound = get_sound_for_event(hook_data)
    if sound:
        play_sound(sound)

    # Run checks after file modifications
    if tool_name in ("Write", "Edit", "MultiEdit"):
        run_structure_change_check()
        # Check file sizes - Claude can see results and refactor if needed
        run_file_size_check()


def handle_stop_event(hook_data: Dict[str, Any]):
    """Handle Stop events (Claude finished responding)."""
    play_sound("task_complete")


def handle_pre_tool_use(hook_data: Dict[str, Any]):
    """Handle PreToolUse events."""
    sound = get_sound_for_event(hook_data)
    if sound:
        play_sound(sound)


def handle_notification(hook_data: Dict[str, Any]):
    """Handle Notification events."""
    play_sound("ready")


def handle_session_start(hook_data: Dict[str, Any]):
    """Handle SessionStart events."""
    play_sound("session_start")
    # Pre-generate all sounds on session start
    ensure_all_sounds_exist()


def main():
    """
    Main entry point for hook handling.
    Reads event data from stdin and dispatches to appropriate handler.
    """
    try:
        # Read event data from Claude (JSON via stdin)
        input_data = json.load(sys.stdin)
        log_hook_data(input_data)

        event_name = input_data.get("hook_event_name", "")

        # Dispatch to appropriate handler
        handlers = {
            "PreToolUse": handle_pre_tool_use,
            "PostToolUse": handle_post_tool_use,
            "Stop": handle_stop_event,
            "Notification": handle_notification,
            "SessionStart": handle_session_start,
            "SubagentStop": lambda d: play_sound("task_complete"),
        }

        handler = handlers.get(event_name)
        if handler:
            handler(input_data)

        # Always exit successfully to not block Claude
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block Claude
    except Exception as e:
        print(f"Hook handler error: {e}", file=sys.stderr)
        sys.exit(0)  # Don't block Claude


# ===== CLI FOR MANUAL SOUND MANAGEMENT =====
def cli():
    """Command-line interface for managing sounds."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude Code Hook Handler - Auto-generates voice sounds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate all sounds:     python hook_handler.py --generate-all
  Generate one sound:      python hook_handler.py --generate ready
  List available sounds:   python hook_handler.py --list-sounds
  Play a sound:            python hook_handler.py --play ready
  Add custom sound:        python hook_handler.py --add-sound "deploy" "Deploying to production"
  Change voice:            python hook_handler.py --set-voice Daniel --generate-all
        """
    )
    parser.add_argument("--generate-all", action="store_true",
                        help="Generate all sound files")
    parser.add_argument("--generate", type=str, metavar="NAME",
                        help="Generate a specific sound by name")
    parser.add_argument("--list-sounds", action="store_true",
                        help="List all available sounds")
    parser.add_argument("--play", type=str, metavar="NAME",
                        help="Play a specific sound")
    parser.add_argument("--set-voice", type=str, metavar="VOICE",
                        help="Set the voice (use with --generate-all to regenerate)")
    parser.add_argument("--add-sound", nargs=2, metavar=("NAME", "MESSAGE"),
                        help="Add and generate a new custom sound")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available macOS voices")
    parser.add_argument("--set-volume", type=float, metavar="LEVEL",
                        help="Set volume (0.0-1.0, e.g., 0.3 for 30%%)")

    args = parser.parse_args()

    global VOICE, VOLUME

    if args.set_volume is not None:
        VOLUME = max(0.0, min(1.0, args.set_volume))
        print(f"Volume set to: {VOLUME}")

    if args.set_voice:
        VOICE = args.set_voice
        print(f"Voice set to: {VOICE}")

    if args.list_voices:
        print("Available voices (run `say -v '?'` for full list):")
        result = subprocess.run(
            ["say", "-v", "?"], capture_output=True, text=True)
        for line in result.stdout.split("\n")[:20]:
            if line.strip():
                print(f"  {line}")
        print("  ... (truncated, run `say -v '?'` for full list)")

    elif args.generate_all:
        print(f"Generating all sounds with voice '{VOICE}'...")
        ensure_all_sounds_exist()
        print(f"Generated {len(VOICE_MESSAGES)} sounds in {get_sounds_dir()}")

    elif args.generate:
        if args.generate in VOICE_MESSAGES:
            # Delete existing to regenerate
            sound_file = get_sounds_dir() / f"{args.generate}.{AUDIO_FORMAT}"
            if sound_file.exists():
                sound_file.unlink()
            ensure_sound_exists(args.generate)
            print(
                f"Generated: {args.generate} -> \"{VOICE_MESSAGES[args.generate]}\"")
        else:
            print(f"Unknown sound: {args.generate}")
            print(f"Available: {', '.join(VOICE_MESSAGES.keys())}")
            sys.exit(1)

    elif args.list_sounds:
        print(f"Available sounds (voice: {VOICE}):")
        for name, message in VOICE_MESSAGES.items():
            sound_file = get_sounds_dir() / f"{name}.{AUDIO_FORMAT}"
            status = "✓" if sound_file.exists() else "✗"
            print(f"  {status} {name}: \"{message}\"")

    elif args.play:
        if not play_sound(args.play):
            print(f"Failed to play: {args.play}")
            sys.exit(1)

    elif args.add_sound:
        name, message = args.add_sound
        VOICE_MESSAGES[name] = message
        generate_sound(name, message)
        print(f"Generated: {name} -> \"{message}\"")
        print(
            f"Note: Add '{name}' to VOICE_MESSAGES in the script to persist.")

    else:
        parser.print_help()


if __name__ == "__main__":
    # Check if running with CLI arguments or as stdin hook
    if len(sys.argv) > 1:
        cli()
    else:
        main()
