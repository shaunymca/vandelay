# Tools

Local tool configuration and usage guidelines.

## How Your Tools Work

Your enabled tools are registered as **direct function calls**. You call them the same way you'd call any function — just invoke the method with the right parameters. You do NOT need to:
- Import or instantiate tool classes
- Write Python scripts to use a tool
- Handle authentication yourself
- Look up method names with shell commands

For example, if GoogleSheetsTools is enabled, just call `read_sheet(spreadsheet_id="abc123", spreadsheet_range="Sheet1")` directly. The system handles auth, connection, and error formatting for you.

## Tool Selection Hierarchy

When you need to perform an action, follow this order strictly:

### 1. Use your ENABLED tools first
Check the tool catalog below. If a tool marked `[ENABLED]` can do the job, **use it**. Never write code to call an API directly when you have an enabled tool that does the same thing.

### 2. Enable an available tool from the catalog
If no enabled tool fits but you see one marked `[available]` in the catalog that would work, use `enable_tool` to activate it. It will be installed and ready to use immediately.

### 3. Ask the user about creating a new tool
If nothing in the catalog covers what's needed, **ask the user** whether you should create a custom tool for this. Do not silently fall back to raw API calls or code — always check with the user first.

## Google Tools Authentication

Google tools (Gmail, Calendar, Drive, Sheets) use a shared OAuth token managed by the system. **You do not need to handle Google auth yourself.** The token is at `~/.vandelay/google_token.json` and is passed to each Google tool automatically.

- If a Google tool fails with an auth error, tell the user to run: `vandelay tools auth-google --reauth`
- Never write custom OAuth scripts or try to exchange auth codes manually.
- The auth token covers all Google scopes (Gmail, Calendar, Drive, Sheets).

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

## Local Config

Add tool-specific settings below as you set things up:

```
# Example:
# ssh_host: myserver.example.com
# camera_name: front_door
# voice: alloy
```
