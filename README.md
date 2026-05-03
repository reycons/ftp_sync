# ftp_sync

Downloads new and updated files from a configured FTP server on a daily schedule.

State is persisted in a JSON file so re-running is always safe — files that have
already been downloaded are skipped unless the server reports a newer modification
time.

---

## Prerequisites

- Python 3.11 or later
- Windows (for Task Scheduler setup) — the Python code itself is cross-platform

---

## Setup

### 1 — Clone / copy the project

Place the project folder anywhere on the target machine, e.g. `C:\ftp_sync`.

### 2 — Create the virtual environment

```powershell
cd C:\ftp_sync
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3 — Create the secrets file

Copy `.env.example` to `.env` and fill in the FTP password:

```
FTP_PASSWORD=your_actual_password
```

`.env` is listed in `.gitignore` and must never be committed.

### 4 — Edit the config files

Update `config/config.prod.yaml` (and `config/config.dev.yaml` for local testing),
plus your connection file under `config/data_feeds/`:

| Key | Description |
|---|---|
| `ftp.host` | FTP server hostname or IP |
| `ftp.port` | FTP port (usually 21) |
| `ftp.user` | FTP username |
| `sync.remote_paths` | List of remote directories to watch |
| `sync.local_destination` | Local root folder for downloaded files |
| `sync.state_file` | Path to the JSON tracking file |
| `sync.chunk_size` | Files per processing chunk (set per connection in `config/data_feeds/ftp.<name>.yaml`) |
| `filters.extensions` | File extensions to download; empty = all |
| `filters.name_pattern` | Glob filter on filename, e.g. `report_*`; null = disabled |
| `filters.max_age_days` | Skip files older than N days; null = disabled |

### 5 — Run manually to verify

```powershell
.venv\Scripts\activate
python main.py --env prod
```

Logs are written to the directory specified in `logging.log_dir`.

---

## Scheduling (Windows Task Scheduler)

Run the setup script **once** from an elevated PowerShell session:

```powershell
.\setup_task.ps1 -ProjectDir "C:\ftp_sync" -RunAt "06:00" -Env "prod"
```

| Parameter | Default | Description |
|---|---|---|
| `-ProjectDir` | _(required)_ | Full path to the project folder |
| `-RunAt` | `06:00` | Daily start time (24-hour HH:MM) |
| `-Env` | `prod` | Environment — `dev` or `prod` |

To run immediately after registering:

```powershell
Start-ScheduledTask -TaskName "ftp_sync_daily"
```

To remove the task:

```powershell
Unregister-ScheduledTask -TaskName "ftp_sync_daily" -Confirm:$false
```

---

## Project structure

```
main.py                  # Orchestration only
config/
    config.dev.yaml      # Dev singleton config
    config.prod.yaml     # Prod singleton config
    data_feeds/
        ftp.client01.yaml
.env                     # Secrets — never committed
.env.example             # Template for .env
.gitignore
requirements.txt
setup_task.ps1           # Registers Windows Task Scheduler job
README.md
.venv/
ftp_sync/
    __init__.py
    error_utils.py       # App-specific exceptions
sql/
    duckdb/
tests/
    conftest.py
    ftp_sync/
        test_state_manager.py
        test_sync_engine.py
```

---

## Porting to a new client

1. Copy the entire project folder.
2. Update `config/config.prod.yaml` and `config/data_feeds/ftp.<client>.yaml` with the
    new client's settings.
3. Create a new `.env` with the new FTP password.
4. Run `setup_task.ps1` on the new machine.

No code changes are required.

---

## Running tests

```powershell
.venv\Scripts\activate
pytest tests/
```

---

## Linting and formatting

```powershell
ruff check .
black --check .
```
