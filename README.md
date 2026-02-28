# AI_Employee_Vault

An automated task processing system powered by Claude Code that monitors an Obsidian vault for incoming files and processes them using configurable agent skills.

## Tier

**Bronze** - Basic automation tier with file watching and task processing capabilities.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Inbox     │────▶│ Needs_Action │────▶│    Done     │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Plans     │
                    └──────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │     Claude Code         │
              │   + Agent Skills        │
              └─────────────────────────┘
```

**Components:**
- **Watcher** - Python script that monitors `/Inbox` for new files
- **Claude Code** - AI agent that processes tasks
- **Obsidian** - Vault interface for file management and visualization
- **Agent Skills** - Configurable skills in `/Skills/` for specialized tasks

## Setup Instructions

### Prerequisites
- Python 3.8+
- Claude Code CLI installed
- Obsidian (optional, for UI)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd AI_Employee_Vault
   ```

2. Verify Python is available:
   ```bash
   python --version
   ```

3. Ensure folder structure exists:
   ```
   AI_Employee_Vault/
   ├── Inbox/
   ├── Needs_Action/
   ├── Plans/
   ├── Done/
   ├── Skills/
   ├── Logs/
   ├── Claude.md.md
   ├── Company_Handbook.md.md
   └── Dashboard.md.md
   ```

## How to Run

Open **two terminals** in the vault directory:

**Terminal 1 - File Watcher:**
```bash
python file_watcher.py
```
This monitors `/Inbox` and moves new files to `/Needs_Action` with metadata.

**Terminal 2 - Claude Code:**
```bash
claude
```
Then run the processing command:
```
Process all tasks in /Needs_Action following CLAUDE.md. Use skills from /Skills/. Update Dashboard.md when done.
```

## File Flow

```
Inbox/ → Needs_Action/ → Plans/ → Done/
            │               │
            │               └── Plan files (PLAN_*.md)
            │
            └── Task files with metadata (.md)
                and original files
```

1. **Inbox** - Drop new files here
2. **Needs_Action** - Files are timestamped and metadata is added
3. **Plans** - Claude creates execution plans for each task
4. **Done** - Completed tasks and plans are archived here

## Security

### Credentials Handling

All sensitive files are excluded from version control via `.gitignore`:

```gitignore
# Environment and secrets
.env
*.secret
*.token

# Credentials
credentials.json

# Python
__pycache__/

# Obsidian
.obsidian/
```

### Best Practices
- Never commit `.env` files or credential files
- Store API keys and secrets in `.env` (local only)
- Review `.gitignore` before adding new file types
- The `/Pending_Approval` folder is used for sensitive operations requiring human approval

## Agent Skills

Skills are located in `/Skills/` as `SKILL.md.md` files:

| Skill | Purpose |
|-------|---------|
| Summarize File | Extract key points and action items from documents |
| Process Task | Handle new task files with prioritization and planning |

## Key Files

| File | Purpose |
|------|---------|
| `Claude.md.md` | Master instructions for the AI Employee |
| `Company_Handbook.md.md` | Rules and priority levels |
| `Dashboard.md.md` | Status board with recent activity |
| `file_watcher.py` | Python script for inbox monitoring |

## License

Personal use - Muhammad Hassaan