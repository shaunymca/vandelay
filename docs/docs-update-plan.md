# Docs Update Plan

Branch: `docs-update`
Audit date: 2026-02-25
Based on: commit 85a8114

---

## Priority 1 — Critical (Wrong or Broken)

| File | Issue | Fix |
|---|---|---|
| `docs/cli/tools.md` | Commands documented as `enable/disable/search` — none exist. Actual: `add/remove/list/browse/info/refresh/create/auth-google` | Full rewrite |
| `docs/cli/daemon.md` | Says Windows "not supported (use WSL)" — Windows IS supported via PID file + detached subprocess (PR #80) | Update Windows section |
| `docs/cli/start.md` | `--no-terminal` flag doesn't exist; actual flag is `--server`. Missing `--watch` flag | Fix flag names, add `--watch` |
| `docs/concepts/memory.md` | Says MEMORY.md is loaded into the system prompt — removed in PR #78 (DB-only memory now) | Remove that section |
| `docs/guides/workspace-files.md` | Lists 7 workspace files including MEMORY.md — now 6 files (MEMORY.md no longer in system prompt) | Update count, remove MEMORY.md entry |
| `docs/concepts/architecture.md` | Same 7-file count issue | Update to 6 files |

---

## Priority 2 — Missing (Feature Exists, No Docs)

### New files to create

| File | Content |
|---|---|
| `docs/cli/update.md` | `vandelay update` — git pull + uv sync + optional daemon restart. Flags: `--no-restart`. When to use it. |
| `docs/cli/status.md` | `vandelay status` — shows agent name, model, provider, safety mode, timezone, DB path, workspace dir, enabled channels, team members, server URL |
| `docs/guides/tui-guide.md` | Full TUI dashboard guide: tab-by-tab walkthrough covering Chat, Agents, Knowledge, Memory, Config, Scheduler, Status, Workspace tabs. Includes onboarding wizard steps. |

---

## Priority 3 — Gaps (Documented but Incomplete)

| File | Gap | Fix |
|---|---|---|
| `docs/getting-started/quickstart.md` | TUI is now the primary entry point. Onboarding runs inside the TUI (5-step wizard), not as a post-exit CLI flow. Flow description is outdated. | Rewrite to reflect TUI-first flow |
| `docs/concepts/teams.md` | Doesn't mention how to change team mode (coordinate/route/broadcast/tasks) via TUI Agents tab. Leader now has direct tool access (PR #92). | Add TUI workflow section, add note on leader tools |
| `docs/guides/scheduling.md` | TUI Scheduler tab exists with full CRUD for cron jobs and task history — not mentioned at all | Add "Managing Schedules in the TUI" section |
| `docs/cli/tools.md` (after rewrite) | `auth-google`, `browse`, `refresh`, `info`, `create` subcommands undocumented | Include all 8 subcommands |
| `docs/cli/onboard.md` | `--non-interactive` flag not documented | Add flag + use case (headless/CI) |

---

## Priority 4 — Polish

- `docs/guides/agent-templates.md` — template count says 14, actual is 16. Update count and list.
- `docs/concepts/channels.md` — WhatsApp labeled "Untested"; it's implemented (PR #53), file sending is a known stub. Update label to reflect actual status.
- `docs/concepts/teams.md` — Add note that the team leader now receives all user-enabled tools directly (PR #92), so it can execute tasks without delegating when appropriate.

---

## Out of Scope (Accurate, No Changes Needed)

- `docs/configuration/index.md` — config reference is accurate
- `docs/guides/scheduling.md` cron CLI section — accurate
- `docs/guides/custom-tools.md` — accurate
- `docs/deployment/` — accurate
- `docs/changelog.md` — leave history as-is

---

## File Change Summary

**Modified (12):**
- `docs/cli/tools.md` — full rewrite
- `docs/cli/daemon.md` — Windows support fix
- `docs/cli/start.md` — flag name fixes
- `docs/cli/onboard.md` — add `--non-interactive`
- `docs/concepts/memory.md` — remove MEMORY.md system prompt claim
- `docs/concepts/architecture.md` — 7 → 6 workspace files
- `docs/concepts/teams.md` — TUI workflow + leader tools note
- `docs/concepts/channels.md` — WhatsApp label
- `docs/guides/workspace-files.md` — 7 → 6 files, remove MEMORY.md entry
- `docs/guides/agent-templates.md` — template count 14 → 16
- `docs/guides/scheduling.md` — add TUI Scheduler section
- `docs/getting-started/quickstart.md` — TUI-first onboarding flow

**Created (3):**
- `docs/cli/update.md`
- `docs/cli/status.md`
- `docs/guides/tui-guide.md`
