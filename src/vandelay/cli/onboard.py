"""Interactive onboarding wizard — sets up config on first run."""

from __future__ import annotations

import os
from datetime import UTC
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel

from vandelay.config.constants import MODEL_PROVIDERS
from vandelay.config.models import (
    ChannelConfig,
    DeepWorkConfig,
    HeartbeatConfig,
    KnowledgeConfig,
    MemberConfig,
    ModelConfig,
    SafetyConfig,
    ServerConfig,
)
from vandelay.config.settings import Settings
from vandelay.workspace.manager import init_workspace

console = Console()


def _select_provider() -> tuple[str, str]:
    """Prompt user to pick a model provider and model ID."""
    choices = [
        questionary.Choice(title=info["name"], value=key)
        for key, info in MODEL_PROVIDERS.items()
    ]
    provider = questionary.select(
        "Which AI model provider?",
        choices=choices,
    ).ask()

    if provider is None:
        raise KeyboardInterrupt

    info = MODEL_PROVIDERS[provider]
    default_model = info["default_model"]

    model_id = questionary.text(
        f"Model ID (default: {default_model}):",
        default=default_model,
    ).ask()

    if model_id is None:
        raise KeyboardInterrupt

    return provider, model_id


def _write_env_key(env_key: str, value: str) -> None:
    """Write or update a key in the project .env file."""
    from vandelay.config.constants import VANDELAY_HOME

    env_path = VANDELAY_HOME / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing lines
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    # Update existing key or append
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{env_key}="):
            lines[i] = f"{env_key}={value}"
            found = True
            break

    if not found:
        lines.append(f"{env_key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _configure_auth(provider: str) -> str:
    """Configure authentication. Returns auth method chosen: 'api_key' or 'token'."""
    info = MODEL_PROVIDERS[provider]
    env_key = info.get("env_key")
    token_env_key = info.get("token_env_key")

    if not env_key and not token_env_key:
        return "api_key"  # Ollama — no auth needed

    # Check if already configured
    has_token = token_env_key and os.environ.get(token_env_key)
    has_key = env_key and os.environ.get(env_key)

    if has_token or has_key:
        which = token_env_key if has_token else env_key
        console.print(f"  [green]✓[/green] {which} already set")
        update = questionary.confirm("  Update credentials?", default=False).ask()
        if not update:
            return "token" if has_token else "api_key"

    # Build auth method choices
    choices = []

    if token_env_key:
        choices.append(questionary.Choice(
            title=f"{info['token_label']} [dim]({info['token_help']})[/dim]",
            value="token",
        ))

    if env_key:
        choices.append(questionary.Choice(
            title=info["api_key_label"],
            value="api_key",
        ))

    choices.append(questionary.Choice(title="Back", value="back"))

    auth_method = questionary.select(
        f"{info['name']} auth method",
        choices=choices,
    ).ask()

    if auth_method is None or auth_method == "back":
        raise KeyboardInterrupt

    if auth_method == "token":
        console.print(f"  [dim]{info['token_help']}[/dim]")
        value = questionary.password("  Paste token:").ask()
        if not value:
            console.print(
                f"  [yellow]⚠[/yellow] No token provided — set {token_env_key} in .env later"
            )
            return "token"
        os.environ[token_env_key] = value
        _write_env_key(token_env_key, value)
        console.print(f"  [green]✓[/green] {token_env_key} saved to ~/.vandelay/.env")
        return "token"

    else:  # api_key
        console.print(f"  [dim]{info['api_key_help']}[/dim]")
        value = questionary.password("  Paste API key:").ask()
        if not value:
            console.print(f"  [yellow]⚠[/yellow] No key provided — set {env_key} in .env later")
            return "api_key"
        os.environ[env_key] = value
        _write_env_key(env_key, value)
        console.print(f"  [green]✓[/green] {env_key} saved to ~/.vandelay/.env")
        return "api_key"


def _select_safety_mode() -> str:
    """Choose shell command safety level."""
    mode = questionary.select(
        "Shell command safety mode?",
        choices=[
            questionary.Choice(
                title="Confirm — every command needs your approval (recommended)",
                value="confirm",
            ),
            questionary.Choice(
                title="Tiered — safe commands run freely, risky ones need approval",
                value="tiered",
            ),
            questionary.Choice(
                title="Trust — all commands execute immediately (advanced users)",
                value="trust",
            ),
        ],
    ).ask()

    if mode is None:
        raise KeyboardInterrupt

    return mode


def _select_timezone(default: str = "UTC") -> str:
    """Prompt user to pick their timezone."""
    # Try to detect system timezone
    detected = _detect_system_timezone()

    common_timezones = [
        "US/Eastern",
        "US/Central",
        "US/Mountain",
        "US/Pacific",
        "Europe/London",
        "Europe/Berlin",
        "Europe/Paris",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Asia/Kolkata",
        "Australia/Sydney",
        "Pacific/Auckland",
        "UTC",
    ]

    # Build choices — put detected timezone first if found
    choices = []
    if detected and detected != "UTC":
        choices.append(questionary.Choice(
            title=f"{detected} (detected)",
            value=detected,
        ))

    for tz in common_timezones:
        if tz != detected:  # Don't duplicate detected
            choices.append(questionary.Choice(title=tz, value=tz))

    choices.append(questionary.Choice(title="Other (type manually)", value="_other"))

    tz = questionary.select(
        "What's your timezone?",
        choices=choices,
        default=detected if detected and detected != "UTC" else default,
    ).ask()

    if tz is None:
        raise KeyboardInterrupt

    if tz == "_other":
        tz = questionary.text(
            "Enter timezone (e.g. America/New_York):",
            default=default,
        ).ask()
        if tz is None:
            raise KeyboardInterrupt

    return tz


def _detect_system_timezone() -> str | None:
    """Try to detect the system timezone. Returns None if unavailable."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo  # noqa: F401

        # On Python 3.9+ we can try tzlocal or fall back to UTC offset
        try:
            import tzlocal
            return str(tzlocal.get_localzone())
        except ImportError:
            pass

        # Fallback: check TZ env var
        import os
        tz_env = os.environ.get("TZ")
        if tz_env:
            return tz_env

        # Fallback: compute UTC offset and map to common name
        local_offset = datetime.now(UTC).astimezone().utcoffset()
        if local_offset is not None:
            hours = int(local_offset.total_seconds() // 3600)
            offset_map = {
                -5: "US/Eastern", -6: "US/Central", -7: "US/Mountain",
                -8: "US/Pacific", 0: "Europe/London", 1: "Europe/Berlin",
                9: "Asia/Tokyo", 8: "Asia/Shanghai", 10: "Australia/Sydney",
            }
            return offset_map.get(hours)
    except Exception:
        pass
    return None


def _configure_agent_name(default: str = "Art") -> str:
    """Let user name their agent."""
    name = questionary.text(
        "What should your agent be called?",
        default=default,
    ).ask()

    if name is None:
        raise KeyboardInterrupt

    return name


def _configure_user_id(default: str = "") -> str:
    """Ask for user's email/identifier for consistent memory across channels."""
    user_id = questionary.text(
        "Your email (for syncing memory across AgentOS, terminal, etc.):",
        default=default,
    ).ask()

    if user_id is None:
        raise KeyboardInterrupt

    return user_id.strip()


def _populate_user_md(workspace_dir: Path, timezone: str = "UTC") -> None:
    """Write timezone into USER.md if it has the placeholder."""
    user_md = workspace_dir / "USER.md"
    if user_md.exists():
        content = user_md.read_text(encoding="utf-8")
        # Fill in the timezone placeholder
        has_placeholder = "**Timezone:**" in content
        already_set = "**Timezone:** " in content.replace("**Timezone:**\n", "")
        if has_placeholder and not already_set:
            content = content.replace("**Timezone:**", f"**Timezone:** {timezone}")
            user_md.write_text(content, encoding="utf-8")


def _channel_summary(settings: Settings) -> str:
    """One-line summary of active channels for the config menu."""
    active = []
    if settings.channels.telegram_enabled:
        active.append("Telegram")
    if settings.channels.whatsapp_enabled:
        active.append("WhatsApp")
    return ", ".join(active) if active else "none"


def _configure_channels(channel_cfg: ChannelConfig) -> ChannelConfig:
    """Interactive channel setup for Telegram and/or WhatsApp."""

    # --- Telegram ---
    setup_telegram = questionary.confirm(
        "Set up Telegram?",
        default=False,
    ).ask()

    if setup_telegram is None:
        raise KeyboardInterrupt

    if setup_telegram:
        console.print()
        console.print("  [bold]Telegram Setup[/bold]")
        console.print("  [dim]Get your bot token from @BotFather on Telegram[/dim]")

        bot_token = questionary.password("  Bot token:").ask()
        if bot_token:
            channel_cfg.telegram_enabled = True
            channel_cfg.telegram_bot_token = bot_token
            _write_env_key("TELEGRAM_TOKEN", bot_token)

            chat_id = questionary.text(
                "  Default chat ID (optional — press Enter to skip):",
                default="",
            ).ask()
            if chat_id:
                channel_cfg.telegram_chat_id = chat_id

            console.print("  [green]✓[/green] Telegram configured")
        else:
            console.print("  [yellow]⚠[/yellow] No token — Telegram skipped")

    # --- WhatsApp ---
    setup_whatsapp = questionary.confirm(
        "Set up WhatsApp?",
        default=False,
    ).ask()

    if setup_whatsapp is None:
        raise KeyboardInterrupt

    if setup_whatsapp:
        console.print()
        console.print("  [bold]WhatsApp Setup[/bold]")
        console.print("  [dim]You need a Meta Business app with WhatsApp API access[/dim]")

        access_token = questionary.password("  Access token:").ask()
        phone_id = questionary.text("  Phone number ID:").ask()
        verify_token = questionary.text(
            "  Verify token (for webhook validation):",
            default="vandelay-verify",
        ).ask()
        app_secret = questionary.password("  App secret (optional):").ask()

        if access_token and phone_id:
            channel_cfg.whatsapp_enabled = True
            channel_cfg.whatsapp_access_token = access_token
            channel_cfg.whatsapp_phone_number_id = phone_id
            channel_cfg.whatsapp_verify_token = verify_token or "vandelay-verify"
            if app_secret:
                channel_cfg.whatsapp_app_secret = app_secret

            _write_env_key("WHATSAPP_ACCESS_TOKEN", access_token)
            _write_env_key("WHATSAPP_PHONE_NUMBER_ID", phone_id)
            _write_env_key("WHATSAPP_VERIFY_TOKEN", channel_cfg.whatsapp_verify_token)
            if app_secret:
                _write_env_key("WHATSAPP_APP_SECRET", app_secret)

            console.print("  [green]✓[/green] WhatsApp configured")
        else:
            console.print("  [yellow]⚠[/yellow] Missing fields — WhatsApp skipped")

    return channel_cfg


def _configure_knowledge(provider: str) -> bool:
    """Ask if user wants to enable knowledge/RAG."""
    # Anthropic has no embeddings — let user know we'll use local embedder
    no_embedder_providers = {"anthropic"}
    if provider in no_embedder_providers:
        console.print(
            f"  [dim]{provider} doesn't have a native embeddings API.[/dim]"
        )
        console.print(
            "  [dim]A local embedder (fastembed) will be used"
            " automatically — no extra API key needed.[/dim]"
        )

    enabled = questionary.confirm(
        "Enable knowledge/RAG? (lets the agent search your documents)",
        default=False,
    ).ask()

    if enabled is None:
        raise KeyboardInterrupt

    if enabled:
        console.print(
            "  [green]\u2713[/green] Knowledge enabled"
            " — add docs with: vandelay knowledge add <path>"
        )
    else:
        console.print(
            "  [dim]Knowledge skipped — enable later with /config or config.json[/dim]"
        )

    return enabled


def _offer_daemon_install() -> None:
    """Offer to install as a system service (Linux/macOS only)."""
    from vandelay.cli.daemon import install_daemon_service, is_daemon_supported

    if not is_daemon_supported():
        return

    console.print()
    install = questionary.confirm(
        "Install Vandelay as a system service? (starts on boot, auto-restarts)",
        default=False,
    ).ask()

    if install is None:
        return  # Ctrl+C — skip gracefully, don't abort onboarding

    if install:
        success = install_daemon_service()
        if success:
            console.print(
                "  [dim]Start the service anytime with:"
                " vandelay daemon start[/dim]"
            )
    else:
        console.print(
            "  [dim]You can install later with:"
            " vandelay daemon install[/dim]"
        )
    console.print()


def _tools_summary(enabled_tools: list[str]) -> str:
    """One-line summary of enabled tool count."""
    count = len(enabled_tools)
    return f"{count} enabled" if count else "none"


def run_config_menu(settings: Settings, exit_label: str = "Back to chat") -> Settings:
    """Interactive config editor — pick a section to change."""
    while True:
        console.print()
        section = questionary.select(
            "What would you like to change?",
            choices=[
                questionary.Choice(
                    title=f"Agent name      [{settings.agent_name}]",
                    value="name",
                ),
                questionary.Choice(
                    title=f"Model           [{settings.model.provider} / "
                          f"{settings.model.model_id}]",
                    value="model",
                ),
                questionary.Choice(
                    title=f"Auth            [{settings.model.auth_method}]",
                    value="auth",
                ),
                questionary.Choice(
                    title=f"Safety mode     [{settings.safety.mode}]",
                    value="safety",
                ),
                questionary.Choice(
                    title=f"User ID         [{settings.user_id or 'not set'}]",
                    value="user_id",
                ),
                questionary.Choice(
                    title=f"Timezone        [{settings.timezone}]",
                    value="timezone",
                ),
                questionary.Choice(
                    title=f"Tools           [{_tools_summary(settings.enabled_tools)}]",
                    value="tools",
                ),
                questionary.Choice(
                    title=f"Browser tools   [{_browser_tools_summary(settings.enabled_tools)}]",
                    value="browser",
                ),
                questionary.Choice(
                    title=f"Channels        [{_channel_summary(settings)}]",
                    value="channels",
                ),
                questionary.Choice(
                    title=f"Knowledge       "
                          f"[{'enabled' if settings.knowledge.enabled else 'disabled'}]",
                    value="knowledge",
                ),
                questionary.Choice(
                    title=f"Team mode       [{_team_summary(settings)}]",
                    value="team",
                ),
                questionary.Choice(
                    title=f"Deep work       [{_deep_work_summary(settings)}]",
                    value="deep_work",
                ),
                questionary.Choice(
                    title=f"Heartbeat       [{_heartbeat_summary(settings)}]",
                    value="heartbeat",
                ),
                *_daemon_restart_choice(),
                questionary.Choice(
                    title=exit_label,
                    value="done",
                ),
            ],
        ).ask()

        if section is None or section == "done":
            break

        if section == "name":
            settings.agent_name = _configure_agent_name(default=settings.agent_name)
            name = settings.agent_name
            console.print(f"  [green]✓[/green] Agent name set to [bold]{name}[/bold]")

        elif section == "model":
            provider, model_id = _select_provider()
            auth_method = _configure_auth(provider)
            settings.model = ModelConfig(
                provider=provider, model_id=model_id, auth_method=auth_method,
            )
            console.print(f"  [green]✓[/green] Model set to {provider} / {model_id}")

        elif section == "auth":
            auth_method = _configure_auth(settings.model.provider)
            settings.model.auth_method = auth_method

        elif section == "safety":
            mode = _select_safety_mode()
            settings.safety.mode = mode
            console.print(f"  [green]✓[/green] Safety mode set to {mode}")

        elif section == "user_id":
            uid = _configure_user_id(default=settings.user_id)
            settings.user_id = uid
            console.print(f"  [green]✓[/green] User ID set to {uid or '(empty)'}")

        elif section == "timezone":
            tz = _select_timezone(default=settings.timezone)
            settings.timezone = tz
            settings.heartbeat.timezone = tz
            console.print(f"  [green]✓[/green] Timezone set to {tz}")

        elif section == "tools":
            from vandelay.cli.tools_commands import interactive_tools_browser
            interactive_tools_browser(settings)
            continue  # skip save — browser handles its own saves

        elif section == "browser":
            settings.enabled_tools = _configure_browser_tools(list(settings.enabled_tools))
            browser = _browser_tools_summary(settings.enabled_tools)
            console.print(f"  [green]✓[/green] Browser: {browser}")

        elif section == "channels":
            settings.channels = _configure_channels(settings.channels)
            console.print(f"  [green]✓[/green] Channels: {_channel_summary(settings)}")

        elif section == "knowledge":
            enabled = _configure_knowledge(settings.model.provider)
            settings.knowledge.enabled = enabled

        elif section == "team":
            settings = _configure_team(settings)

        elif section == "deep_work":
            settings.deep_work = _configure_deep_work(settings.deep_work)

        elif section == "heartbeat":
            settings.heartbeat = _configure_heartbeat(settings.heartbeat, settings.timezone)

        elif section == "restart_daemon":
            _do_daemon_restart()
            continue  # skip save — no settings changed

        settings.save()
        console.print("  [dim]Config saved.[/dim]")

    return settings


def _team_summary(settings: Settings) -> str:
    """One-line summary of team config for the config menu."""
    if not settings.team.enabled:
        return "disabled"
    member_names = []
    for m in settings.team.members:
        if isinstance(m, (str, MemberConfig)):
            name = m if isinstance(m, str) else m.name
            member_names.append(name)
    return f"{settings.team.mode}, {len(member_names)} members"


def _configure_team(settings: Settings) -> Settings:
    """Interactive team configuration — toggle, mode, and member management."""
    toggle = questionary.confirm(
        "Enable team mode? (routes queries to specialist agents)",
        default=settings.team.enabled,
    ).ask()
    if toggle is None:
        return settings

    settings.team.enabled = toggle
    if not toggle:
        console.print("  [green]\u2713[/green] Team mode disabled")
        return settings

    # Mode selection
    mode = questionary.select(
        "Team execution mode?",
        choices=[
            questionary.Choice(
                title="Coordinate — supervisor delegates and synthesizes responses (recommended)",
                value="coordinate",
            ),
            questionary.Choice(
                title="Route — supervisor picks one member, returns their response directly",
                value="route",
            ),
            questionary.Choice(
                title="Broadcast — all members respond, supervisor picks the best",
                value="broadcast",
            ),
        ],
        default=settings.team.mode,
    ).ask()
    if mode is None:
        return settings

    settings.team.mode = mode

    # Member management loop
    while True:
        member_names = []
        for m in settings.team.members:
            name = m if isinstance(m, str) else m.name
            member_names.append(name)
        console.print(f"\n  Members: {', '.join(member_names) or 'none'}")

        action = questionary.select(
            "Manage members?",
            choices=[
                questionary.Choice(title="Add a member", value="add"),
                questionary.Choice(title="Edit a member's instructions", value="edit"),
                questionary.Choice(title="Remove a member", value="remove"),
                questionary.Choice(title="Done", value="done"),
            ],
        ).ask()

        if action is None or action == "done":
            break

        if action == "add":
            settings = _add_team_member(settings)
        elif action == "edit":
            settings = _edit_member_instructions(settings)
        elif action == "remove":
            settings = _remove_team_member(settings)

    member_count = len(settings.team.members)
    console.print(f"  [green]\u2713[/green] Team: {mode} mode, {member_count} members")
    return settings


def _add_team_member(settings: Settings) -> Settings:
    """Add a new member to the team with guided flow."""
    from vandelay.agents.templates import (
        STARTER_TEMPLATES,
        get_template_content,
        list_templates,
    )
    from vandelay.config.constants import MEMBERS_DIR

    # Step 0 — Offer starter templates
    use_template = questionary.confirm(
        "Start from a template?", default=True
    ).ask()
    if use_template is None:
        return settings

    template = None
    if use_template:
        templates = list_templates()
        choices = [
            questionary.Choice(
                title=f"{t.name} — {t.role}",
                value=t.slug,
            )
            for t in templates
        ]
        choices.append(questionary.Choice(title="Blank (start from scratch)", value=""))

        slug = questionary.select("Choose a template:", choices=choices).ask()
        if slug is None:
            return settings
        if slug:
            template = STARTER_TEMPLATES[slug]

    if template:
        # Pre-fill from template
        name = template.slug
        role = template.role

        # Check for duplicates — offer rename
        existing_names = [
            m if isinstance(m, str) else m.name for m in settings.team.members
        ]
        if name in existing_names:
            console.print(
                f"  [yellow]\u26a0[/yellow] Member '{name}' already exists."
            )
            name = questionary.text(
                "Enter a different name:",
                default=f"{name}-2",
            ).ask()
            if not name:
                return settings
            name = name.strip().lower().replace(" ", "-")
            if name in existing_names:
                console.print(f"  [yellow]\u26a0[/yellow] '{name}' also exists. Aborting.")
                return settings

        # Copy template .md to ~/.vandelay/members/
        MEMBERS_DIR.mkdir(parents=True, exist_ok=True)
        instructions_path = MEMBERS_DIR / f"{name}.md"
        content = get_template_content(template.slug)
        instructions_path.write_text(content, encoding="utf-8")
        console.print(f"  [green]\u2713[/green] Template saved to {instructions_path}")

        # Prompt to enable any suggested tools that aren't globally enabled
        suggested = set(template.suggested_tools)
        enabled = set(settings.enabled_tools or [])
        missing = sorted(suggested - enabled)
        if missing:
            console.print(
                f"  [yellow]\u26a0[/yellow] This template suggests tools not yet enabled: "
                f"[bold]{', '.join(missing)}[/bold]"
            )
            to_enable = questionary.checkbox(
                "Enable these tools globally?",
                choices=[
                    questionary.Choice(title=t, value=t, checked=True)
                    for t in missing
                ],
            ).ask()
            if to_enable:
                settings.enabled_tools = list(settings.enabled_tools or []) + to_enable
                enabled = set(settings.enabled_tools)

        # Select which enabled tools this member should have access to
        tools: list[str] = []
        if settings.enabled_tools:
            selected = questionary.checkbox(
                "Which tools should this member have access to?",
                choices=[
                    questionary.Choice(
                        title=t, value=t, checked=t in suggested
                    )
                    for t in settings.enabled_tools
                ],
            ).ask()
            if selected:
                tools = selected

        # Model override
        model_provider = ""
        model_id = ""
        use_custom_model = questionary.confirm(
            "Use a different model for this member? (default: inherits main model)",
            default=False,
        ).ask()
        if use_custom_model:
            model_provider, model_id = _select_provider()

        mc = MemberConfig(
            name=name,
            role=role,
            tools=tools,
            model_provider=model_provider,
            model_id=model_id,
            instructions_file=f"{name}.md",
        )

        # Offer to customize before adding
        customize = questionary.confirm(
            "Customize before adding?", default=False
        ).ask()
        if customize:
            new_role = questionary.text("Role description:", default=role).ask()
            if new_role is not None:
                mc.role = new_role
            mc = _offer_instructions_paste(mc)

    else:
        # Blank flow — original behavior
        name = questionary.text("Member name (e.g. cto, research, writer):").ask()
        if not name:
            return settings
        name = name.strip().lower().replace(" ", "-")

        existing_names = [
            m if isinstance(m, str) else m.name for m in settings.team.members
        ]
        if name in existing_names:
            console.print(f"  [yellow]\u26a0[/yellow] Member '{name}' already exists.")
            return settings

        console.print(
            "  [dim]The team leader uses this description to decide when to route"
            " tasks to this member. Be specific about what they specialize in.[/dim]"
        )
        role = questionary.text("Role description:", default="").ask()
        if role is None:
            return settings

        tools = []
        if settings.enabled_tools:
            selected = questionary.checkbox(
                "Which tools should this member have access to?",
                choices=[
                    questionary.Choice(title=t, value=t, checked=False)
                    for t in settings.enabled_tools
                ],
            ).ask()
            if selected:
                tools = selected

        model_provider = ""
        model_id = ""
        use_custom_model = questionary.confirm(
            "Use a different model for this member? (default: inherits main model)",
            default=False,
        ).ask()
        if use_custom_model:
            model_provider, model_id = _select_provider()

        mc = MemberConfig(
            name=name,
            role=role,
            tools=tools,
            model_provider=model_provider,
            model_id=model_id,
        )
        mc = _offer_instructions_paste(mc)

    # Preview and confirm
    _preview_member_config(mc, settings)

    confirm = questionary.confirm("Add this member?", default=True).ask()
    if not confirm:
        console.print("  [dim]Member not added.[/dim]")
        return settings

    settings.team.members.append(mc)
    console.print(f"  [green]\u2713[/green] Added member: {mc.name}")
    return settings


def _preview_member_config(mc: MemberConfig, settings: Settings) -> None:
    """Show a rich preview panel of a member config before confirming."""
    if mc.model_provider and mc.model_id:
        model_str = f"{mc.model_provider} / {mc.model_id}"
    else:
        model_str = f"inherited ({settings.model.provider} / {settings.model.model_id})"

    tools_str = ", ".join(mc.tools) if mc.tools else "none"
    instructions_str = mc.instructions_file if mc.instructions_file else "none"

    content = (
        f"[bold]{mc.name}[/bold]\n\n"
        f"Role: {mc.role or '(none)'}\n"
        f"Tools: {tools_str}\n"
        f"Model: {model_str}\n"
        f"Instructions: {instructions_str}"
    )

    console.print()
    console.print(Panel(content, title="Member Preview", border_style="cyan"))
    console.print()


def _edit_member_instructions(settings: Settings) -> Settings:
    """Edit instructions for an existing member."""
    if not settings.team.members:
        console.print("  [dim]No members to edit.[/dim]")
        return settings

    choices = []
    for i, m in enumerate(settings.team.members):
        name = m if isinstance(m, str) else m.name
        choices.append(questionary.Choice(title=name, value=i))
    choices.append(questionary.Choice(title="Back", value=-1))

    idx = questionary.select("Which member?", choices=choices).ask()
    if idx is None or idx == -1:
        return settings

    member = settings.team.members[idx]

    # Convert string member to MemberConfig for editing
    if isinstance(member, str):
        from vandelay.agents.factory import _resolve_member
        member = _resolve_member(member)
        settings.team.members[idx] = member

    member = _offer_instructions_paste(member)
    settings.team.members[idx] = member
    return settings


def _remove_team_member(settings: Settings) -> Settings:
    """Remove a member from the team."""
    if not settings.team.members:
        console.print("  [dim]No members to remove.[/dim]")
        return settings

    choices = []
    for i, m in enumerate(settings.team.members):
        name = m if isinstance(m, str) else m.name
        choices.append(questionary.Choice(title=name, value=i))
    choices.append(questionary.Choice(title="Back", value=-1))

    idx = questionary.select("Which member to remove?", choices=choices).ask()
    if idx is None or idx == -1:
        return settings

    removed = settings.team.members.pop(idx)
    name = removed if isinstance(removed, str) else removed.name
    console.print(f"  [green]\u2713[/green] Removed member: {name}")
    return settings


def _offer_instructions_paste(mc: MemberConfig) -> MemberConfig:
    """Offer to paste instructions for a member, saved to ~/.vandelay/members/<name>.md."""
    from vandelay.config.constants import MEMBERS_DIR

    # Show existing instructions if any
    existing_file = MEMBERS_DIR / f"{mc.name}.md"
    if existing_file.exists():
        preview = existing_file.read_text(encoding="utf-8")[:200]
        console.print(f"  [dim]Current instructions ({existing_file}):[/dim]")
        console.print(f"  [dim]{preview}{'...' if len(preview) >= 200 else ''}[/dim]")

    add_instructions = questionary.confirm(
        f"Add/update instructions for {mc.name}? (paste markdown context)",
        default=not existing_file.exists(),
    ).ask()

    if not add_instructions:
        # Still set the instructions_file if it exists
        if existing_file.exists() and not mc.instructions_file:
            mc.instructions_file = f"{mc.name}.md"
        return mc

    console.print("  [bold]Paste your instructions below.[/bold]")
    console.print("  [dim]When done, type END on its own line and press Enter.[/dim]")
    console.print()

    lines: list[str] = []
    try:
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        pass

    if not lines:
        console.print("  [yellow]\u26a0[/yellow] No instructions provided — skipped")
        return mc

    content = "\n".join(lines).strip()

    # Save to ~/.vandelay/members/<name>.md
    MEMBERS_DIR.mkdir(parents=True, exist_ok=True)
    instructions_path = MEMBERS_DIR / f"{mc.name}.md"
    instructions_path.write_text(content + "\n", encoding="utf-8")
    mc.instructions_file = f"{mc.name}.md"

    console.print(f"  [green]\u2713[/green] Instructions saved to {instructions_path}")
    return mc


def _daemon_restart_choice() -> list:
    """Return a restart choice if the daemon is running, else empty list."""
    from vandelay.cli.daemon import is_daemon_running, is_daemon_supported

    if is_daemon_supported() and is_daemon_running():
        return [questionary.Choice(
            title="Restart daemon  [apply config changes]",
            value="restart_daemon",
        )]
    return []


def _do_daemon_restart() -> None:
    """Restart the daemon and report result."""
    from vandelay.cli.daemon import restart_daemon

    console.print("  Restarting daemon...")
    if restart_daemon():
        console.print("  [green]\u2713[/green] Daemon restarted with new config.")
    else:
        console.print("  [red]\u2717[/red] Daemon restart failed. Try: vandelay daemon restart")


def _deep_work_summary(settings) -> str:
    """One-line summary for config menu display."""
    dw = settings.deep_work
    if not dw.enabled:
        return "disabled"
    return f"{dw.activation}, {dw.max_iterations} iter, {dw.max_time_minutes}m"


def _configure_deep_work(dw: DeepWorkConfig) -> DeepWorkConfig:
    """Interactive deep work configuration. Returns updated DeepWorkConfig."""
    toggle = questionary.confirm(
        "Enable deep work? (autonomous background execution for complex tasks)",
        default=dw.enabled,
    ).ask()
    if toggle is None:
        return dw

    if not toggle:
        console.print("  [green]\u2713[/green] Deep work disabled")
        return DeepWorkConfig(enabled=False)

    # Activation mode
    activation = questionary.select(
        "How should deep work be activated?",
        choices=[
            questionary.Choice(
                title="Suggest — agent suggests deep work for complex tasks (recommended)",
                value="suggest",
            ),
            questionary.Choice(
                title="Explicit — only when you explicitly request it",
                value="explicit",
            ),
            questionary.Choice(
                title="Auto — agent starts deep work automatically for complex tasks",
                value="auto",
            ),
        ],
        default=dw.activation,
    ).ask()
    if activation is None:
        return dw

    # Max iterations
    max_iter = questionary.text(
        "Max iterations:",
        default=str(dw.max_iterations),
        validate=lambda v: v.isdigit() and int(v) > 0,
    ).ask()
    if max_iter is None:
        return dw

    # Max time
    max_time = questionary.text(
        "Max time (minutes):",
        default=str(dw.max_time_minutes),
        validate=lambda v: v.isdigit() and int(v) > 0,
    ).ask()
    if max_time is None:
        return dw

    # Progress interval
    progress_interval = questionary.text(
        "Progress update interval (minutes):",
        default=str(dw.progress_interval_minutes),
        validate=lambda v: v.isdigit() and int(v) > 0,
    ).ask()
    if progress_interval is None:
        return dw

    # Background mode
    background = questionary.confirm(
        "Run in background? (recommended — lets you keep chatting)",
        default=dw.background,
    ).ask()
    if background is None:
        return dw

    result = DeepWorkConfig(
        enabled=True,
        background=background,
        activation=activation,
        max_iterations=int(max_iter),
        max_time_minutes=int(max_time),
        progress_interval_minutes=int(progress_interval),
        save_results_to_workspace=dw.save_results_to_workspace,
    )
    console.print(
        f"  [green]\u2713[/green] Deep work enabled: {activation} mode, "
        f"max {max_iter} iterations / {max_time} min"
    )
    return result


def _heartbeat_summary(settings) -> str:
    """One-line summary for config menu display."""
    hb = settings.heartbeat
    if not hb.enabled:
        return "disabled"
    return f"every {hb.interval_minutes}m, {hb.active_hours_start}-{hb.active_hours_end}h"


def _configure_heartbeat(hb, default_tz: str):
    """Interactive heartbeat configuration. Returns updated HeartbeatConfig."""
    from vandelay.config.models import HeartbeatConfig

    toggle = questionary.confirm(
        "Enable heartbeat? (periodic health checks)",
        default=hb.enabled,
    ).ask()
    if toggle is None:
        return hb

    if not toggle:
        console.print("  [green]\u2713[/green] Heartbeat disabled")
        return HeartbeatConfig(enabled=False, timezone=hb.timezone)

    interval = questionary.text(
        "Check interval in minutes:",
        default=str(hb.interval_minutes),
        validate=lambda v: v.isdigit() and int(v) > 0,
    ).ask()
    if interval is None:
        return hb

    start = questionary.text(
        "Active hours start (0-23):",
        default=str(hb.active_hours_start),
        validate=lambda v: v.isdigit() and 0 <= int(v) <= 23,
    ).ask()
    if start is None:
        return hb

    end = questionary.text(
        "Active hours end (0-23):",
        default=str(hb.active_hours_end),
        validate=lambda v: v.isdigit() and 0 <= int(v) <= 23,
    ).ask()
    if end is None:
        return hb

    result = HeartbeatConfig(
        enabled=True,
        interval_minutes=int(interval),
        active_hours_start=int(start),
        active_hours_end=int(end),
        timezone=hb.timezone or default_tz,
    )
    console.print(
        f"  [green]\u2713[/green] Heartbeat enabled: every {interval}m, "
        f"{start}:00-{end}:00 ({result.timezone})"
    )
    return result


def _browser_tools_summary(enabled_tools: list[str]) -> str:
    """One-line summary of active browser tools."""
    active = []
    if "crawl4ai" in enabled_tools:
        active.append("Crawl4ai")
    if "camofox" in enabled_tools:
        active.append("Camofox")
    return ", ".join(active) if active else "none"


def _configure_browser_tools(enabled_tools: list[str]) -> list[str]:
    """Interactive browser tool selection. Modifies and returns enabled_tools."""
    choices = questionary.checkbox(
        "Which browser tools would you like to enable?",
        choices=[
            questionary.Choice(
                title="Crawl4ai (Recommended) — Free web crawling with JS rendering",
                value="crawl4ai",
                checked=True,
            ),
            questionary.Choice(
                title="Camofox (Experimental) — Anti-detection browser with a11y snapshots",
                value="camofox",
            ),
            questionary.Choice(
                title="None (skip)",
                value="none",
            ),
        ],
    ).ask()

    if choices is None:
        raise KeyboardInterrupt

    if "none" in choices or not choices:
        console.print(
            "  [dim]Browser tools skipped"
            " — enable later with: vandelay tools add[/dim]"
        )
        return enabled_tools

    if "crawl4ai" in choices:
        enabled_tools.append("crawl4ai")
        console.print("  [green]✓[/green] Crawl4ai enabled")
        console.print("  [dim]Install its deps with: uv add crawl4ai[/dim]")

    if "camofox" in choices:
        console.print("  Setting up Camofox browser environment...")
        try:
            from vandelay.tools.camofox_server import CamofoxServer
            server = CamofoxServer()
            server.install()
            enabled_tools.append("camofox")
            console.print("  [green]✓[/green] Camofox installed and enabled")
        except Exception as e:
            console.print(f"  [red]✗[/red] Camofox setup failed: {e}")
            console.print("  [dim]You can retry later with: vandelay tools add camofox[/dim]")

    return enabled_tools


def run_onboarding() -> Settings:
    """Run the full interactive onboarding wizard. Returns configured Settings."""
    from vandelay.cli.banner import print_banner

    print_banner(console)
    console.print("  [dim]Let's set up your always-on AI assistant.[/dim]")
    console.print()

    # Step 1: Identity
    console.print("[bold]1/8[/bold] — Identity")
    agent_name = _configure_agent_name()
    user_id = _configure_user_id()
    console.print()

    # Step 2: Model provider
    console.print("[bold]2/8[/bold] — AI Model")
    provider, model_id = _select_provider()
    auth_method = _configure_auth(provider)
    console.print()

    # Step 3: Safety mode
    console.print("[bold]3/8[/bold] — Safety")
    safety_mode = _select_safety_mode()
    console.print()

    # Step 4: Timezone
    console.print("[bold]4/8[/bold] — Timezone")
    timezone = _select_timezone()
    console.print(f"  [green]✓[/green] Timezone set to {timezone}")
    console.print()

    # Step 5: Browser Tools
    console.print("[bold]5/8[/bold] — Browser Tools")
    enabled_tools: list[str] = []
    enabled_tools = _configure_browser_tools(enabled_tools)
    console.print()

    # Step 6: Workspace
    console.print("[bold]6/8[/bold] — Workspace")
    ws = init_workspace()
    console.print(f"  [green]✓[/green] Workspace initialized at {ws}")
    console.print()

    # Pre-populate USER.md timezone
    _populate_user_md(ws, timezone=timezone)

    # Step 7: Messaging channels
    console.print("[bold]7/8[/bold] — Messaging Channels")
    channel_cfg = _configure_channels(ChannelConfig())
    console.print()

    # Step 8: Knowledge base
    console.print("[bold]8/8[/bold] — Knowledge Base")
    knowledge_enabled = _configure_knowledge(provider)
    console.print()

    # Build settings
    settings = Settings(
        agent_name=agent_name,
        user_id=user_id,
        timezone=timezone,
        model=ModelConfig(provider=provider, model_id=model_id, auth_method=auth_method),
        safety=SafetyConfig(mode=safety_mode),
        channels=channel_cfg,
        heartbeat=HeartbeatConfig(timezone=timezone),
        server=ServerConfig(),
        knowledge=KnowledgeConfig(enabled=knowledge_enabled),
        workspace_dir=str(ws),
        enabled_tools=enabled_tools,
    )

    # Persist
    settings.save()
    config_path = settings.model_config.get("env_prefix", "~/.vandelay/config.json")
    console.print(f"  [green]✓[/green] Config saved to {config_path}")
    console.print()
    channels_str = _channel_summary(settings) or "Terminal only"
    browser_str = _browser_tools_summary(enabled_tools) or "none"
    knowledge_str = "enabled" if knowledge_enabled else "disabled"
    # Optional: daemon service (Linux/macOS only)
    _offer_daemon_install()

    console.print(
        Panel.fit(
            f"[bold green]Setup complete![/bold green]\n\n"
            f"Agent: [bold]{agent_name}[/bold]\n"
            f"Model: {provider} / {model_id}\n"
            f"Safety: {safety_mode}\n"
            f"Timezone: {timezone}\n"
            f"Browser: {browser_str}\n"
            f"Channels: {channels_str}\n"
            f"Knowledge: {knowledge_str}\n\n"
            f"Launching chat...",
            border_style="green",
        )
    )

    return settings


def _headless_channels() -> ChannelConfig:
    """Auto-detect channel configuration from environment variables."""
    cfg = ChannelConfig()

    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if telegram_token:
        cfg.telegram_enabled = True
        cfg.telegram_bot_token = telegram_token
        cfg.telegram_chat_id = telegram_chat_id

    wa_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    wa_phone = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    if wa_token and wa_phone:
        cfg.whatsapp_enabled = True
        cfg.whatsapp_access_token = wa_token
        cfg.whatsapp_phone_number_id = wa_phone
        cfg.whatsapp_verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "vandelay-verify")
        cfg.whatsapp_app_secret = os.environ.get("WHATSAPP_APP_SECRET", "")

    return cfg


def run_headless_onboarding() -> Settings:
    """Non-interactive setup from environment variables.

    Designed for PaaS/CI deployments (Railway, Render, etc.) where interactive
    prompts aren't available. All configuration comes from env vars:

    Required:
      - ``VANDELAY_MODEL_PROVIDER`` (default: "anthropic")
      - The provider's API key env var (e.g. ``ANTHROPIC_API_KEY``)

    Optional:
      - ``VANDELAY_MODEL_ID`` — override default model
      - ``VANDELAY_AGENT_NAME`` — agent display name (default: "Claw")
      - ``VANDELAY_TIMEZONE`` — timezone (default: "UTC")
      - ``VANDELAY_SAFETY_MODE`` — trust | confirm | tiered (default: "confirm")
      - ``VANDELAY_USER_ID`` — user identifier
      - ``VANDELAY_KNOWLEDGE_ENABLED`` — "1" or "true" to enable knowledge/RAG
      - ``TELEGRAM_TOKEN`` + ``TELEGRAM_CHAT_ID`` — enable Telegram
      - ``WHATSAPP_ACCESS_TOKEN`` + ``WHATSAPP_PHONE_NUMBER_ID`` — enable WhatsApp
    """
    provider = os.environ.get("VANDELAY_MODEL_PROVIDER", "anthropic")
    model_id = os.environ.get(
        "VANDELAY_MODEL_ID",
        MODEL_PROVIDERS.get(provider, {}).get("default_model", "claude-sonnet-4-5-20250929"),
    )
    agent_name = os.environ.get("VANDELAY_AGENT_NAME", "Art")
    timezone = os.environ.get("VANDELAY_TIMEZONE", "UTC")
    safety_mode = os.environ.get("VANDELAY_SAFETY_MODE", "confirm")
    user_id = os.environ.get("VANDELAY_USER_ID", "")

    # Validate provider
    if provider not in MODEL_PROVIDERS:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Choose from: {list(MODEL_PROVIDERS.keys())}"
        )

    # Validate API key is available
    env_key = MODEL_PROVIDERS[provider].get("env_key")
    if env_key and not os.environ.get(env_key):
        raise ValueError(f"{env_key} must be set for provider '{provider}'")

    # Knowledge
    knowledge_raw = os.environ.get("VANDELAY_KNOWLEDGE_ENABLED", "").lower()
    knowledge_enabled = knowledge_raw in ("1", "true", "yes")

    # Build settings
    ws = init_workspace()

    settings = Settings(
        agent_name=agent_name,
        user_id=user_id,
        timezone=timezone,
        model=ModelConfig(provider=provider, model_id=model_id, auth_method="api_key"),
        safety=SafetyConfig(mode=safety_mode),
        channels=_headless_channels(),
        heartbeat=HeartbeatConfig(timezone=timezone),
        server=ServerConfig(),
        knowledge=KnowledgeConfig(enabled=knowledge_enabled),
        workspace_dir=str(ws),
    )

    settings.save()
    return settings
