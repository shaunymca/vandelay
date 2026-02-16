# Tools

Local tool configuration and usage guidelines.

## CRITICAL: Just Call Your Tools

Your enabled tools are registered as **direct function calls** with full method signatures, parameter types, and descriptions already visible to you. **You already know everything you need.**

**NEVER do any of the following:**
- Read source code to "check what methods are available" — you already have them
- Run shell commands to inspect tool classes or packages
- Guess method names or try to verify class names
- Write Python scripts to replicate what a tool already does
- Manually handle authentication (tokens, API keys, OAuth flows)
- Spend multiple messages "investigating" before calling a tool

**Instead:** Look at your registered functions, find the one that matches, and call it immediately. If you're unsure about parameters, just call it — the error message will tell you what's wrong faster than reading source code.

For example, if GoogleSheetsTools is enabled, just call `read_sheet(spreadsheet_id="abc123", spreadsheet_range="Sheet1")` directly. The system handles auth, connection, and error formatting for you.

## Tool Selection Hierarchy

When you need to perform an action, follow this order strictly:

### 1. Use your ENABLED tools first
If an enabled tool can do the job, **call it immediately**. Never write code to call an API directly when you have an enabled tool that does the same thing.

### 2. Enable an available tool from the catalog
If no enabled tool fits, use `list_available_tools` to check what's available, then `enable_tool` to activate it. It will be installed and ready to use immediately.

### 3. Ask the user about creating a new tool
If nothing in the catalog covers what's needed, **ask the user** whether you should create a custom tool for this. Do not silently fall back to raw API calls or code — always check with the user first.

## Filesystem Navigation

Before searching the filesystem with `find`, `ls`, or `search_files`:

1. **Check task results first.** Call `check_open_tasks()` or `get_task()` — completed tasks often contain file paths and project locations in their results. This is faster than searching.
2. **Use known paths.** If a task result or previous conversation mentions a directory (e.g. `/home/vandelay/sf_import/`), go there directly instead of searching from root.
3. **Be specific.** Search in the narrowest directory possible. Never `find /` or `find ~` when you know the project directory.

## Google Tools Authentication

Google tools (Gmail, Calendar, Drive, Sheets) use a shared OAuth token managed by the system. **You do not need to handle Google auth yourself.** The token is at `~/.vandelay/google_token.json` and is passed to each Google tool automatically.

- If a Google tool fails with an auth error, tell the user to run: `vandelay tools auth-google --reauth`
- **Never** write custom OAuth scripts or try to exchange auth codes manually.
- **Never** edit source code files to fix tool issues — ask the user for help instead.
- The auth token covers all Google scopes (Gmail, Calendar, Drive, Sheets).

### Google Calendar — Shared Calendars

By default, Google Calendar tools operate on the user's **primary** calendar. To access a shared calendar:

1. The calendar must be shared with the Google account used for OAuth (with at least "See all event details" or "Make changes to events" permission).
2. Use `list_calendars()` to discover available calendars and their IDs.
3. The user can set `google.calendar_id` in config (via `/config` → Google → Calendar ID) to the shared calendar's email address (e.g. `shaun@gmail.com`).
4. Once set, `list_events()`, `create_event()`, `update_event()`, and `delete_event()` will use that calendar.

The calendar tool has **write access enabled** — you can create, update, and delete events.

### Google Sheets — Token Limits

**CRITICAL**: Large spreadsheets can overflow your context window (200K token limit). Always follow these rules:

1. **Never read an entire sheet without a range.** Always specify `spreadsheet_range` (e.g., `"Sheet1!A1:F50"`).
2. **Read in batches.** Start with the first 20-50 rows to understand the structure, then fetch more if needed.
3. **One tab at a time.** Don't read multiple tabs in a single response — process each tab, summarize findings, then move to the next.
4. **Summarize, don't echo.** After reading sheet data, summarize what you found instead of repeating raw data back to the user.

If you hit a token limit error, your conversation context will be cleared. Use your memory to recover.

## Shell Commands

- Prefer non-destructive commands first (ls, cat, grep) before modifying anything.
- For write operations, confirm with the user unless in trust mode.
- Default timeout: 120 seconds.
- Never run commands that could brick the system.
- Capture both stdout and stderr.

## Browser

- Headless by default for efficiency.
- Return text summaries from URLs, not raw HTML.
- Use screenshots for visual verification or user requests.
- Close pages when done. Respect robots.txt.

## Scheduling

- Confirm time and timezone when creating reminders.
- Validate cron expressions before saving.
- Give tasks descriptive names.
- Warn if a recurring task has no stop condition.

## Knowledge / RAG

- Search knowledge base before the web for user questions.
- Cite source documents in answers.
- If no results, say so and offer web search.

## Environment Variables & Secrets

API keys and secrets are stored in `~/.vandelay/.env`. This file is loaded automatically before your tools are initialized — you do NOT need to source it or load it yourself.

- To check which keys are configured: read `~/.vandelay/.env` (values are redacted in tool output)
- To add or update a key: edit `~/.vandelay/.env` directly, one `KEY=value` per line
- Common keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `TAVILY_API_KEY`, `GITHUB_TOKEN`
- After changing `.env`, restart the daemon for new values to take effect

To restart the daemon safely, run: `systemctl --user restart vandelay`
This is safe — systemd will bring you back up immediately. You will lose your current conversation context, so only restart when the user confirms or when you've finished making config/.env changes.

If a tool fails with an authentication or missing-key error, check `~/.vandelay/.env` first before asking the user.

## Local Config

Add tool-specific settings below as you set things up:

```
# Example:
# ssh_host: myserver.example.com
# camera_name: front_door
# voice: alloy
```
