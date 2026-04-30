# ftp_sync — Future Enhancements

Tracked items for future development. All current functionality is production-ready.
Items below are improvements, not defects.

---

## Reliability

- **Connection retry with exponential backoff**
  A single network hiccup currently fails the entire connection for that run.
  Implement retry with backoff in `ftp_client.py` wrapping the session open.
  Max attempts and base delay should be config keys under `ftp:`.

- **Per-file download timeout**
  A stalled transfer currently hangs indefinitely.
  Add a configurable timeout (seconds) applied to each file download.
  Config key: `ftp.download_timeout_seconds`.

- **Disk space check before downloading**
  If the local destination drive fills up, downloads fail silently mid-run.
  Check available disk space against estimated download size before starting.
  Config key: `sync.min_free_space_mb`.

---

## Observability

- **Email alert on failure**
  No one knows a run failed unless they check the log.
  Send an email when a connection fails entirely or files are abandoned.
  Config keys: `alerts.smtp_host`, `alerts.recipients`, `alerts.from_address`.
  SMTP credentials via `.env`.

- **Daily run summary report**
  A digest email or log entry summarising all connections:
  files downloaded, files failed, files abandoned, across the full run.
  Sent at the end of each scheduled execution.

- **Health check file**
  Write a `health.json` to a config-specified path after every successful run.
  Contains: last run timestamp, connection statuses, file counts.
  Allows external monitoring tools (Nagios, Datadog, etc.) to detect missed runs.
  Config key: `sync.health_file`.

---

## Security

- **SSH host key verification for SFTP**
  Currently `paramiko.AutoAddPolicy()` accepts all host keys automatically.
  This is a security risk — a MITM attack would be silently accepted.
  Add support for a `known_hosts` file per connection.
  Config key: `ftp.known_hosts_file`.

- **SSH key authentication for SFTP**
  Currently only password auth is supported.
  Add support for private key files as an alternative to passwords.
  Config keys: `ftp.key_file_env` (path from `.env`), `ftp.key_passphrase_env`.

---

## Operations

- **CLI: inspect state**
  Allow operators to view the current state, retry queue, and failed files
  for a connection without reading raw JSON.
  Command: `python main.py --inspect client01`

- **CLI: clear failed files**
  Allow operators to clear the `.failed.json` for a connection, or remove
  individual entries, so files are re-queued for download.
  Command: `python main.py --clear-failed client01`
  Command: `python main.py --retry-failed client01 filename.csv`

- **CLI: force full re-sync**
  Reset the stamp and state for a connection so all files are re-evaluated.
  Useful after a local destination is wiped or corrupted.
  Command: `python main.py --reset client01`

- **Post-download hook**
  Run a configurable script or command after each successful download.
  Allows downstream processing (move, transform, import) to be triggered automatically.
  Config key: `sync.post_download_hook` (command string).
  Passes filename, remote path, and local path as arguments.

---

## Notes

- All new config keys follow existing conventions: values in YAML, secrets in `.env`
- All new CLI commands follow existing `--env` pattern and use `argparse`
- All new functionality belongs in `rey_lib` unless it is ftp_sync-specific
