# Agent Templates

Vandelay ships with 14 starter templates for common agent roles. Use them as-is or as a starting point for custom members.

## Available Templates

| Template | Role | Default Tools |
|----------|------|---------------|
| CTO | Technical leadership, architecture decisions | shell, file, python |
| AI Engineer | Prompt engineering, model selection | file, python |
| Sales Executive | Pipeline management, outreach | gmail, googlesheets |
| Marketer | Content strategy, campaigns | crawl4ai, googlesheets |
| Personal Assistant | Calendar, email, reminders | gmail, googlecalendar |
| Chef | Meal planning, recipes | - |
| Personal Trainer | Workouts, fitness tracking | googlesheets |
| Research Analyst | Deep research, reports | tavily, crawl4ai |
| Vandelay Expert | Agent builder: creates and improves team members | file, python, shell |
| Writer | Content creation, editing | file |
| Data Analyst | Data analysis, visualization | python, googlesheets |
| DevOps | Infrastructure, CI/CD, monitoring | shell, file |
| Content Creator | Social media, blog posts | file, crawl4ai |
| Project Manager | Roadmap, task tracking, sprints | file, googlesheets |

## Using a Template

### Via CLI

```bash
vandelay config  # → Team → Add member → "Start from template?"
```

Select a template from the picker. The template `.md` file is copied to `~/.vandelay/members/<slug>.md` and the member is added to your team config.

### What's in a Template

Each template includes:

- **Role:** What the agent does
- **Expertise:** Domain knowledge areas
- **How You Work:** Behavioral patterns and workflows
- **Boundaries:** What the agent should and shouldn't do
- **Memory First:** What to check before acting
- **Tools You Prefer:** Recommended tools for the role

## Customizing Templates

After adding a template, edit the member file directly:

```bash
nano ~/.vandelay/members/cto.md
```

Changes take effect on the next agent reload.

## Authoring Your Own

Create a new `.md` file in `~/.vandelay/members/`:

```markdown
# My Custom Agent

## Role
What this agent does.

## Expertise
- Domain 1
- Domain 2

## How You Work
Behavioral instructions...

## Boundaries
What NOT to do...
```

Then add it to your team config:

```json
{
  "name": "my-agent",
  "role": "Description for the supervisor",
  "tools": ["shell", "file"],
  "instructions_file": "my-agent.md"
}
```
