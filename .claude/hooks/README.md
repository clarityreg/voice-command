# Claude Code Hooks Package

A comprehensive hooks system for Claude Code that provides audio feedback, file size monitoring, and code structure change detection.

## Features

- **Audio Feedback**: Voice notifications for tool usage, task completion, errors, and more
- **File Size Monitoring**: Automatically checks Python files against a 500-line limit
- **Structure Change Detection**: Detects significant changes and optionally sends webhooks
- **Auto-generated Voice Files**: Uses macOS `say` command to generate voice notifications

## Requirements

- **macOS** (for voice synthesis via `say` and playback via `afplay`)
- **Python 3.8+**
- **Poetry** (for running Python scripts in the correct environment)

### Python Dependencies

```bash
uv pip install python-decouple   # preferred
# or: pip install python-decouple
```

## Quick Install

```bash
# From project root
./.claude/hooks/install.sh
```

Or manually copy the hooks configuration to your `.claude/settings.json`.

## File Structure

```
.claude/hooks/
├── README.md                    # This file
├── install.sh                   # Installation script
├── hook_handler.py              # Main hook orchestrator
├── structure_change.py          # Code structure change detector
├── verify_file_size.py          # File size limit checker
├── oversized_files_report.txt   # Generated report (auto)
├── tracked_oversized_issues.json # Issue tracking (auto)
├── hook_handler.jsonl           # Hook event log (auto)
└── sounds/
    └── voice/                   # Auto-generated voice files
        ├── ready.aiff
        ├── task_complete.aiff
        ├── edit.aiff
        └── ... (more sound files)
```

## Hook Events

| Event | Sound | Description |
|-------|-------|-------------|
| SessionStart | "Session started" | When Claude Code session begins |
| Notification | "Ready" | When Claude is ready for input |
| Stop | "Task complete" | When Claude finishes responding |
| Edit/Write/MultiEdit | "File edited/created" | After file modifications |
| Bash (git commit) | "Changes committed" | After git commits |
| Bash (git push) | "Code pushed" | After pushing code |
| Bash (pytest) | "Running tests" | When running tests |

## Configuration

### settings.json

The hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/hook_handler.py",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [...],
    "Stop": [...],
    "Notification": [...],
    "SessionStart": [...],
    "SubagentStop": [...]
  }
}
```

### Environment Variables

For structure change webhooks, add to `.claude/prp-secrets.env`:

```bash
VISUALIZER_WEBHOOK=http://your-webhook-url/api/hooks/claude-code
```

For Plane issue creation (file size violations), add to `.claude/prp-secrets.env`:

```bash
PLANE_API_KEY=your-api-key
PLANE_API_URL=https://api.plane.so/api/v1
PLANE_WORKSPACE_SLUG=your-workspace
```

## Customization

### Changing the Voice

Edit `hook_handler.py`:

```python
VOICE = "Samantha"  # Default
# Try: "Daniel" (British), "Alex" (US male), "Karen" (Australian)
```

List available voices:

```bash
say -v '?'
```

### Adjusting Volume

```python
VOLUME = 0.2  # 20% volume (0.0 to 1.0)
```

### Adding Custom Sounds

```python
VOICE_MESSAGES = {
    # Add your custom sounds
    "deploy": "Deploying to production",
    "review": "Code review needed",
}
```

Then map to events in `EVENT_SOUND_MAP`:

```python
EVENT_SOUND_MAP = {
    "YourCustomTool": "deploy",
}
```

### CLI Commands

```bash
# Generate all sounds
python .claude/hooks/hook_handler.py --generate-all

# Generate specific sound
python .claude/hooks/hook_handler.py --generate ready

# List available sounds
python .claude/hooks/hook_handler.py --list-sounds

# Play a sound
python .claude/hooks/hook_handler.py --play task_complete

# Change voice and regenerate
python .claude/hooks/hook_handler.py --set-voice Daniel --generate-all

# Add custom sound
python .claude/hooks/hook_handler.py --add-sound "deploy" "Deploying now"
```

## File Size Monitoring

The `verify_file_size.py` hook monitors Python files in the `backend/` directory:

- **Limit**: 500 lines per file
- **Exclusions**: `__init__.py`, migrations, tests directories
- **Report**: Saves to `.claude/hooks/oversized_files_report.txt`
- **Integration**: Can create Plane issues for oversized files

### Adjusting the Limit

Edit `verify_file_size.py`:

```python
MAX_LINES = 500  # Change this value
BACKEND_DIR = "backend"  # Or your source directory
```

## Troubleshooting

### Sounds not playing

1. Check volume: `python .claude/hooks/hook_handler.py --set-volume 0.5`
2. Regenerate sounds: `python .claude/hooks/hook_handler.py --generate-all`
3. Test manually: `afplay .claude/hooks/sounds/voice/ready.aiff`

### Hooks not triggering

1. Verify `.claude/settings.json` exists and is valid JSON
2. Check Claude Code recognized the hooks: `/hooks` in Claude Code
3. Check the log file: `tail .claude/hooks/hook_handler.jsonl`

### File size check not working

1. Verify Poetry is installed: `poetry --version`
2. Run manually: `poetry run python .claude/hooks/verify_file_size.py`

## Uninstall

Remove the hooks configuration from `.claude/settings.json`:

```json
{
  "hooks": {}
}
```

Or delete the hooks directory entirely:

```bash
rm -rf .claude/hooks
```

## License

MIT License - Feel free to use and modify for your projects.
