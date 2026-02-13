# Tools

Local tool configuration and usage guidelines.

## Tool Selection Hierarchy

When you need to perform an action, follow this order strictly:

### 1. Use your ENABLED tools first
Check the tool catalog below. If a tool marked `[ENABLED]` can do the job, **use it**. Never write code to call an API directly when you have an enabled tool that does the same thing. Your tools handle auth, errors, and formatting automatically.

### 2. Enable an available tool from the catalog
If no enabled tool fits but you see one marked `[available]` in the catalog that would work, use `enable_tool` to activate it. It will be installed and ready to use immediately.

### 3. Ask the user about creating a new tool
If nothing in the catalog covers what's needed, **ask the user** whether you should create a custom tool for this. Do not silently fall back to raw API calls or code — always check with the user first.

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
