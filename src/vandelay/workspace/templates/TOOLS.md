# Tools

Local tool configuration and usage guidelines.

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
