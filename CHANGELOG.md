# Changelog

All notable changes to Vandelay are documented here.

---

## [Unreleased]

---

## 2026-02-21 — Tool Integration Fixes

### Fixed

- **CamoufoxTools: sync API so functions are visible to agents** (`d040025`)

  CamoufoxTools methods were defined as `async def`, which placed them in Agno's
  `async_functions` registry. In some delegation paths the agent framework only
  consulted `functions` (the sync registry), so the browser functions were never
  forwarded to the model — even though the toolkit appeared in the config.

  All methods are now regular `def` using `camoufox.sync_api.Camoufox`. Agno's
  `get_async_functions()` merges both registries (sync wins, async overrides), so
  sync-only tools are now visible in every execution context.

  **Verified:** CTO agent called `open_tab("https://example.com")` and returned
  "Example Domain" — confirmed via AgentOS trace `caa94195b72b15be6478d9fa4cc71a76`.

- **Gmail missing `gmail.compose` scope** (`e22ca64`)

  Agno's `GmailTools` checks for the literal string `"gmail.compose"` in the
  granted scopes. Our OAuth flow included `gmail.modify` (a superset), but not
  the literal `gmail.compose` string — so Agno skipped the tool at startup.

  Fixed by adding `gmail.compose` and `gmail.send` to `_google_all_scopes()` and
  the CLI `auth-google` scope list.

- **GoogleDriveTools: `auth_port=0` treated as "not set"** (`e22ca64`)

  Agno's `GoogleDriveTools.__init__` calls `if not self.auth_port: raise ValueError(...)`.
  Passing `auth_port=0` is falsy, so it always raised. Changed default to `8765`.

- **Auto-install missing tool deps on startup** (`59b4037`)

  Tools listed in `enabled_tools` that had missing Python packages were silently
  skipped at server start. Now, if a tool's dependencies are not installed, the
  server installs them automatically before loading the tool — the same behaviour
  as running `vandelay tools enable <name>` manually.

- **CamoufoxTools GeoIP database** (manual step)

  Camoufox requires a GeoIP database. Download with:
  ```bash
  uv run python -m camoufox fetch
  ```

### Changed

- **Logging: timestamps on daemon and server output** (`7102d22`)

  All log lines now include an ISO timestamp (`2026-02-21 06:00:00`), making it
  easier to correlate daemon logs with AgentOS traces.

- **Tool instantiation failures now logged at WARNING** (`05c62db`)

  Previously logged at DEBUG and invisible in default log levels. Now surfaced
  at WARNING so config/dependency problems are immediately visible.

---

## 2026-02-15 — Camoufox + Google OAuth Unification

### Added

- **Google OAuth unified auth flow** — single `vandelay auth-google` command
  covers Gmail, Calendar, Drive, and Sheets
- **Headless OAuth** — console-based flow for servers without a browser
- **Camoufox browser toolkit** — anti-detect Firefox via `camoufox[geoip]`
  (replaces old Node.js/HTTP approach)
- **Daemon restart from `/config`** — detects running daemon, offers restart

---

## 2026-01-28 — Stage 7b: Daemon + Self-Restart

### Added

- `vandelay daemon install/uninstall/start/stop/restart/status/logs`
- Linux (systemd), macOS (launchd), Windows (PID file + detached subprocess)
- `restart_daemon()` / `is_daemon_running()` public API
- 14 starter agent templates (CTO, Sales, Marketer, PA, Chef, Trainer, …)
- OpenRouter provider support
- Knowledge/RAG with LanceDB + auto-resolved embedder

---

## 2026-01-10 — Stage 6: Scheduler + Heartbeat

### Added

- Cron job store (`~/.vandelay/cron_jobs.json`)
- `vandelay scheduler add/list/remove` CLI
- Heartbeat: configurable interval, active hours, timezone
- Task queue (`~/.vandelay/task_queue.json`) with priority levels
- Deep Work: autonomous background sessions with progress reporting

---

## 2026-01-01 — Stage 4-5: Channels + Browser

### Added

- Telegram channel (webhook + polling)
- WhatsApp channel (Meta Cloud API)
- Browser toolkit (initial Camoufox integration)
- Safety system: trust / confirm / tiered modes

---

## 2025-12-15 — Stage 1-3: Foundation

### Added

- CLI (`vandelay chat`, `vandelay config`, `vandelay onboard`)
- FastAPI server + WebSocket terminal (`/ws/terminal`)
- Shell, File, Python toolkits
- SQLite-backed memory and session storage
- Agent team supervisor (Agno teams)
- `vandelay tools enable/disable/list` hot-reload
