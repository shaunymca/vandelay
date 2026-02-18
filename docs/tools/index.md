# Tool Catalog

Vandelay supports 100+ tools from Agno's ecosystem, grouped by category. Enable any tool with `vandelay tools enable <slug>`.

## Categories

### Search & Web

| Tool | Slug | Pricing | Description |
|------|------|---------|-------------|
| Tavily | `tavily` | API key | AI-powered web search |
| DuckDuckGo | `duckduckgo` | Free | Web search |
| Exa | `exa` | API key | Neural search engine |
| SerpAPI | `serpapi` | API key | Google search results |
| Crawl4AI | `crawl4ai` | Free | Web page crawling and extraction |
| Newspaper4k | `newspaper4k` | Free | Article extraction |
| ArXiv | `arxiv` | Free | Academic paper search |
| Wikipedia | `wikipedia` | Free | Wikipedia search |
| HackerNews | `hackernews` | Free | Hacker News stories |

### Communication

| Tool | Slug | Pricing | Description |
|------|------|---------|-------------|
| Gmail | `gmail` | Google OAuth | Email read/send/search |
| Slack | `slack` | API token | Slack messaging |
| Discord | `discord` | Bot token | Discord messaging |
| Twilio | `twilio` | API key | SMS and voice |

### Productivity

| Tool | Slug | Pricing | Description |
|------|------|---------|-------------|
| Google Calendar | `googlecalendar` | Google OAuth | Calendar management |
| Google Drive | `googledrive` | Google OAuth | File storage |
| Google Sheets | `googlesheets` | Google OAuth | Spreadsheets |
| Notion | `notion` | API key | Workspace and docs |
| Linear | `linear` | API key | Issue tracking |
| Todoist | `todoist` | API key | Task management |

### Development

| Tool | Slug | Pricing | Description |
|------|------|---------|-------------|
| GitHub | `github` | Token | Repos, issues, PRs |
| GitLab | `gitlab` | Token | Repos, issues, MRs |

### Data & Analytics

| Tool | Slug | Pricing | Description |
|------|------|---------|-------------|
| SQL | `sql` | Free | Database queries |
| Pandas | `pandas` | Free | Data analysis |
| Matplotlib | `matplotlib` | Free | Chart generation |

### AI & Models

| Tool | Slug | Pricing | Description |
|------|------|---------|-------------|
| OpenBB | `openbb` | Free/API | Financial data |
| Replicate | `replicate` | API key | ML model inference |

<!-- TODO: Complete the full catalog with all 25 categories and 117 tools -->

## Enabling Tools

```bash
# Enable one or more tools
vandelay tools enable shell file python tavily

# Disable a tool
vandelay tools disable tavily

# List enabled tools
vandelay tools list

# Search available tools
vandelay tools search "search"
```

## Pricing Notes

- **Free** — No API key needed, runs locally
- **API key** — Requires a third-party API key (stored in `~/.vandelay/.env`)
- **Google OAuth** — Uses unified Google OAuth flow (`vandelay auth-google`)

See [Built-in Tools](built-in.md) for Vandelay's custom toolkits.
