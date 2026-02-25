"""Scheduler tab — CRUD for cron jobs + task history view."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

# Common IANA timezones shown in the dropdown (ordered by region)
_TIMEZONES: list[tuple[str, str]] = [
    # UTC / Universal
    ("UTC", "UTC"),
    # Americas
    ("America/New_York (ET)", "America/New_York"),
    ("America/Chicago (CT)", "America/Chicago"),
    ("America/Denver (MT)", "America/Denver"),
    ("America/Los_Angeles (PT)", "America/Los_Angeles"),
    ("America/Anchorage (AK)", "America/Anchorage"),
    ("Pacific/Honolulu (HI)", "Pacific/Honolulu"),
    ("America/Toronto", "America/Toronto"),
    ("America/Vancouver", "America/Vancouver"),
    ("America/Sao_Paulo", "America/Sao_Paulo"),
    ("America/Argentina/Buenos_Aires", "America/Argentina/Buenos_Aires"),
    ("America/Mexico_City", "America/Mexico_City"),
    # Europe
    ("Europe/London (GMT/BST)", "Europe/London"),
    ("Europe/Dublin", "Europe/Dublin"),
    ("Europe/Lisbon", "Europe/Lisbon"),
    ("Europe/Paris (CET)", "Europe/Paris"),
    ("Europe/Berlin", "Europe/Berlin"),
    ("Europe/Amsterdam", "Europe/Amsterdam"),
    ("Europe/Madrid", "Europe/Madrid"),
    ("Europe/Rome", "Europe/Rome"),
    ("Europe/Stockholm", "Europe/Stockholm"),
    ("Europe/Warsaw", "Europe/Warsaw"),
    ("Europe/Helsinki", "Europe/Helsinki"),
    ("Europe/Athens", "Europe/Athens"),
    ("Europe/Moscow", "Europe/Moscow"),
    # Africa / Middle East
    ("Africa/Cairo", "Africa/Cairo"),
    ("Africa/Johannesburg", "Africa/Johannesburg"),
    ("Africa/Lagos", "Africa/Lagos"),
    ("Asia/Dubai", "Asia/Dubai"),
    ("Asia/Riyadh", "Asia/Riyadh"),
    # Asia
    ("Asia/Kolkata (IST)", "Asia/Kolkata"),
    ("Asia/Karachi", "Asia/Karachi"),
    ("Asia/Dhaka", "Asia/Dhaka"),
    ("Asia/Bangkok", "Asia/Bangkok"),
    ("Asia/Singapore", "Asia/Singapore"),
    ("Asia/Shanghai (CST)", "Asia/Shanghai"),
    ("Asia/Hong_Kong", "Asia/Hong_Kong"),
    ("Asia/Taipei", "Asia/Taipei"),
    ("Asia/Seoul", "Asia/Seoul"),
    ("Asia/Tokyo (JST)", "Asia/Tokyo"),
    # Oceania
    ("Australia/Perth", "Australia/Perth"),
    ("Australia/Adelaide", "Australia/Adelaide"),
    ("Australia/Sydney (AEST)", "Australia/Sydney"),
    ("Australia/Brisbane", "Australia/Brisbane"),
    ("Pacific/Auckland", "Pacific/Auckland"),
]

logger = logging.getLogger("vandelay.tui.scheduler")


# ---------------------------------------------------------------------------
# Shared horizontal row (same pattern as chat.py)
# ---------------------------------------------------------------------------


class _HRow(Widget):
    """Horizontal row — avoids Horizontal's height:auto problem in grid cells."""

    DEFAULT_CSS = "_HRow { layout: horizontal; overflow: hidden hidden; }"


# ---------------------------------------------------------------------------
# Modal — Add / Edit cron job
# ---------------------------------------------------------------------------


class CronJobModal(ModalScreen):
    """Add or edit a cron job.

    Dismisses with the new/updated CronJob on save, or None on cancel.
    """

    def __init__(self, job=None) -> None:  # job: CronJob | None
        super().__init__()
        self._job = job  # None → Add mode
        self._default_tz = _config_timezone()

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical

        job = self._job
        title = "Edit Cron Job" if job else "Add Cron Job"

        with Vertical(id="cron-modal-container"):
            yield Label(title, id="cron-modal-title")
            yield Label("Name:", classes="cron-field-label")
            yield Input(
                value=job.name if job else "",
                placeholder="e.g. Daily summary",
                id="cron-name",
            )
            yield Label("Expression:", classes="cron-field-label")
            yield Input(
                value=job.cron_expression if job else "",
                placeholder="*/30 * * * *",
                id="cron-expr",
            )
            yield Label('  (e.g. "*/30 * * * *" = every 30 min)', classes="cron-hint")
            yield Label("Command:", classes="cron-field-label")
            yield Input(
                value=job.command if job else "",
                placeholder="Summarise the last hour of activity",
                id="cron-cmd",
            )
            yield Label("Timezone:", classes="cron-field-label")
            yield Select(
                options=_TIMEZONES,
                value=job.timezone if job else self._default_tz,
                id="cron-tz",
            )
            yield Static("", id="cron-error")
            with Horizontal(id="cron-modal-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
            return
        if event.button.id == "btn-save":
            self._save()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _save(self) -> None:
        from vandelay.scheduler.models import CronJob, JobType

        error_widget = self.query_one("#cron-error", Static)

        name = self.query_one("#cron-name", Input).value.strip()
        expr = self.query_one("#cron-expr", Input).value.strip()
        cmd = self.query_one("#cron-cmd", Input).value.strip()
        tz_select = self.query_one("#cron-tz", Select)
        tz = str(tz_select.value) if tz_select.value is not Select.BLANK else "UTC"

        if not name:
            error_widget.update("[red]Name is required.[/red]")
            return
        if len(expr.split()) != 5:
            error_widget.update(
                "[red]Expression must have exactly 5 space-separated fields.[/red]"
            )
            return
        if not cmd:
            error_widget.update("[red]Command is required.[/red]")
            return

        error_widget.update("")

        if self._job:
            # Edit mode — preserve id/type/metadata
            updated = self._job.model_copy(
                update={"name": name, "cron_expression": expr, "command": cmd, "timezone": tz}
            )
            self.dismiss(updated)
        else:
            # Add mode
            new_job = CronJob(
                name=name,
                cron_expression=expr,
                command=cmd,
                timezone=tz,
                job_type=JobType.USER,
            )
            self.dismiss(new_job)


# ---------------------------------------------------------------------------
# Task edit modal
# ---------------------------------------------------------------------------


class TaskEditModal(ModalScreen):
    """Show a task's full JSON in an editable TextArea.

    Dismisses with the updated dict on save, or None on cancel.
    """

    def __init__(self, task: dict) -> None:
        super().__init__()
        self._task_data = task
        self._original_json = json.dumps(task, indent=2, default=str)

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical

        tid = str(self._task_data.get("id", ""))[:8]
        with Vertical(id="task-modal-container"):
            yield Label(f"Edit Task  #{tid}", id="task-modal-title")
            yield TextArea(
                self._original_json,
                language="json",
                id="task-json",
            )
            yield Static("", id="task-error")
            with Horizontal(id="task-modal-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#task-json", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            self._save()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _save(self) -> None:
        raw = self.query_one("#task-json", TextArea).text
        error = self.query_one("#task-error", Static)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            error.update(f"[red]Invalid JSON: {exc}[/red]")
            return
        if not isinstance(parsed, dict):
            error.update("[red]Task must be a JSON object ({{ … }}).[/red]")
            return
        self.dismiss(parsed)


# ---------------------------------------------------------------------------
# Scheduler tab
# ---------------------------------------------------------------------------


class SchedulerTab(Widget):
    """Cron + task manager — sub-tabs for Cron jobs and Task queue."""

    DEFAULT_CSS = "SchedulerTab { height: 1fr; }"

    def __init__(self) -> None:
        super().__init__()
        self._store = None  # CronJobStore — lazy loaded
        self._selected_job_id: str | None = None
        self._selected_task_id: str | None = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with TabbedContent(id="sched-tabs"):
            with TabPane("Cron", id="pane-cron"):
                with _HRow(id="sched-toolbar"):
                    yield Button("+ Add", id="btn-add", variant="primary")
                    yield Button("Edit", id="btn-edit", variant="default")
                    yield Button("Enable / Disable", id="btn-toggle", variant="default")
                    yield Button("Delete", id="btn-delete", variant="error")
                yield DataTable(id="cron-table", cursor_type="row")
            with TabPane("Tasks", id="pane-tasks"):
                with _HRow(id="task-toolbar"):
                    yield Button("Refresh", id="btn-refresh", variant="default")
                    yield Button("Edit", id="btn-edit-task", variant="default")
                    yield Button("Clear Completed", id="btn-clear", variant="warning")
                yield DataTable(id="task-table", cursor_type="row")
            with TabPane("Heartbeat", id="pane-heartbeat"):
                with Vertical(id="hb-form"):
                    yield Checkbox("Enable heartbeat", id="hb-enabled", value=False)
                    with Horizontal(classes="hb-field-row"):
                        yield Label("Interval (minutes):", classes="hb-label")
                        yield Input("30", id="hb-interval", type="integer")
                    with Horizontal(classes="hb-field-row"):
                        yield Label("Active from (24h):", classes="hb-label")
                        yield Input("8", id="hb-start", type="integer")
                        yield Label("to", classes="hb-to")
                        yield Input("22", id="hb-end", type="integer")
                    with Horizontal(classes="hb-field-row"):
                        yield Label("Timezone:", classes="hb-label")
                        yield Select(_TIMEZONES, id="hb-tz", allow_blank=False)
                    yield Static("", id="hb-error", classes="hb-error")
                    yield Button("Save", id="btn-hb-save", variant="primary")

    def on_mount(self) -> None:
        self._init_store()
        self._build_cron_table()
        self._build_task_table()
        self._update_button_state()
        self._update_task_button_state()
        self._load_heartbeat()

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def _init_store(self) -> None:
        try:
            from vandelay.scheduler.store import CronJobStore

            self._store = CronJobStore()
        except Exception as exc:
            logger.warning("Could not load CronJobStore: %s", exc)

    # ------------------------------------------------------------------
    # Cron table
    # ------------------------------------------------------------------

    def _build_cron_table(self) -> None:
        table = self.query_one("#cron-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Name", "Expression", "Next Run", "Last Run", "Status", "Type")

        if not self._store:
            return

        for job in self._store.all():
            style = "dim" if job.job_type == "heartbeat" else ""
            next_run = _fmt_dt(job.next_run) if job.next_run else "—"
            last_run = _fmt_dt(job.last_run) if job.last_run else "—"
            status = "[green]enabled[/green]" if job.enabled else "[red]disabled[/red]"
            row = (job.name, job.cron_expression, next_run, last_run, status, job.job_type)
            table.add_row(*row, key=job.id)

    def _reload_cron(self) -> None:
        prev_id = self._selected_job_id
        if self._store:
            self._store.load()
        self._build_cron_table()
        # Restore cursor to the previously selected row
        if prev_id and self._store:
            jobs = self._store.all()
            for idx, job in enumerate(jobs):
                if job.id == prev_id:
                    self.query_one("#cron-table", DataTable).move_cursor(row=idx, animate=False)
                    break
            else:
                self._selected_job_id = None  # row was deleted
        self._update_button_state()

    # ------------------------------------------------------------------
    # Task table
    # ------------------------------------------------------------------

    def _build_task_table(self) -> None:
        from vandelay.config.constants import TASK_QUEUE_FILE

        table = self.query_one("#task-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Created", "Status", "Command")

        tasks = _load_tasks(TASK_QUEUE_FILE)
        for t in tasks:
            tid = str(t.get("id", ""))[:8]
            created = str(t.get("created_at", "—"))[:19]
            status = t.get("status", "—")
            title = str(t.get("title", t.get("command", "")))[:40]
            table.add_row(tid, created, status, title, key=str(t.get("id", "")))

    # ------------------------------------------------------------------
    # Button state
    # ------------------------------------------------------------------

    def _update_button_state(self) -> None:
        job = self._selected_job()
        is_heartbeat = job is not None and getattr(job, "job_type", "") == "heartbeat"
        editable = job is not None and not is_heartbeat

        self.query_one("#btn-edit", Button).disabled = not editable
        self.query_one("#btn-delete", Button).disabled = not editable

        toggle = self.query_one("#btn-toggle", Button)
        toggle.disabled = job is None
        if job is not None:
            toggle.label = "Disable" if job.enabled else "Enable"
        else:
            toggle.label = "Enable / Disable"

    def _selected_job(self):
        if not self._store or not self._selected_job_id:
            return None
        return self._store.get(self._selected_job_id)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "cron-table":
            self._selected_job_id = str(event.row_key.value) if event.row_key else None
            self._update_button_state()
        elif event.data_table.id == "task-table":
            self._selected_task_id = str(event.row_key.value) if event.row_key else None
            self._update_task_button_state()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Double-click / Enter on a task row opens the edit modal."""
        if event.data_table.id == "task-table":
            self._edit_task()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "hb-enabled":
            event.checkbox.label = "Disable heartbeat" if event.value else "Enable heartbeat"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-add":
            self._add_job()
        elif btn_id == "btn-edit":
            self._edit_job()
        elif btn_id == "btn-toggle":
            self._toggle_job()
        elif btn_id == "btn-delete":
            self._delete_job()
        elif btn_id == "btn-refresh":
            self._build_task_table()
        elif btn_id == "btn-edit-task":
            self._edit_task()
        elif btn_id == "btn-clear":
            self._clear_completed()
        elif btn_id == "btn-hb-save":
            self._save_heartbeat()

    # ------------------------------------------------------------------
    # Cron CRUD actions
    # ------------------------------------------------------------------

    def _add_job(self) -> None:
        def _on_result(job) -> None:
            if job is not None and self._store:
                self._store.add(job)
                self._reload_cron()

        self.app.push_screen(CronJobModal(), callback=_on_result)

    def _edit_job(self) -> None:
        job = self._selected_job()
        if not job:
            return

        def _on_result(updated) -> None:
            if updated is not None and self._store:
                self._store.update(updated)
                self._reload_cron()

        self.app.push_screen(CronJobModal(job=job), callback=_on_result)

    def _toggle_job(self) -> None:
        job = self._selected_job()
        if not job or not self._store:
            return
        updated = job.model_copy(update={"enabled": not job.enabled})
        self._store.update(updated)
        self._reload_cron()

    def _delete_job(self) -> None:
        if not self._selected_job_id or not self._store:
            return
        job = self._selected_job()
        if not job or job.job_type == "heartbeat":
            return
        self._store.remove(self._selected_job_id)
        self._reload_cron()

    # ------------------------------------------------------------------
    # Task actions
    # ------------------------------------------------------------------

    def _update_task_button_state(self) -> None:
        self.query_one("#btn-edit-task", Button).disabled = self._selected_task_id is None

    def _edit_task(self) -> None:
        if not self._selected_task_id:
            return

        from vandelay.config.constants import TASK_QUEUE_FILE

        tasks = _load_tasks(TASK_QUEUE_FILE)
        task = next((t for t in tasks if str(t.get("id", "")) == self._selected_task_id), None)
        if task is None:
            return

        prev_task_id = self._selected_task_id

        def _on_result(updated: dict | None) -> None:
            if updated is None:
                return
            all_tasks = _load_tasks(TASK_QUEUE_FILE)
            for i, t in enumerate(all_tasks):
                if str(t.get("id", "")) == prev_task_id:
                    all_tasks[i] = updated
                    break
            _save_tasks(TASK_QUEUE_FILE, all_tasks)
            self._selected_task_id = prev_task_id
            self._build_task_table()
            # Restore cursor
            table = self.query_one("#task-table", DataTable)
            reloaded = _load_tasks(TASK_QUEUE_FILE)
            for idx, t in enumerate(reloaded):
                if str(t.get("id", "")) == prev_task_id:
                    table.move_cursor(row=idx, animate=False)
                    break
            self._update_task_button_state()

        self.app.push_screen(TaskEditModal(task), callback=_on_result)

    # ------------------------------------------------------------------
    # Heartbeat settings
    # ------------------------------------------------------------------

    def _load_heartbeat(self) -> None:
        try:
            from vandelay.config.settings import Settings, get_settings

            if not Settings.config_exists():
                return
            hb = get_settings().heartbeat
            cb = self.query_one("#hb-enabled", Checkbox)
            cb.value = hb.enabled
            cb.label = "Disable heartbeat" if hb.enabled else "Enable heartbeat"
            self.query_one("#hb-interval", Input).value = str(hb.interval_minutes)
            self.query_one("#hb-start", Input).value = str(hb.active_hours_start)
            self.query_one("#hb-end", Input).value = str(hb.active_hours_end)
            tz = hb.timezone or "UTC"
            tz_values = [t[1] for t in _TIMEZONES]
            sel = self.query_one("#hb-tz", Select)
            if tz in tz_values:
                sel.value = tz
        except Exception as exc:
            logger.warning("Could not load heartbeat config: %s", exc)

    def _save_heartbeat(self) -> None:
        error = self.query_one("#hb-error", Static)
        error.update("")
        try:
            enabled = self.query_one("#hb-enabled", Checkbox).value
            interval = int(self.query_one("#hb-interval", Input).value.strip() or "30")
            start = int(self.query_one("#hb-start", Input).value.strip() or "8")
            end = int(self.query_one("#hb-end", Input).value.strip() or "22")
            tz_val = self.query_one("#hb-tz", Select).value
            tz = str(tz_val) if tz_val and tz_val is not Select.BLANK else "UTC"
        except ValueError as exc:
            error.update(f"[red]Invalid value: {exc}[/red]")
            return

        if not (0 <= start <= 23 and 0 <= end <= 23):
            error.update("[red]Hours must be 0–23.[/red]")
            return
        if start >= end:
            error.update("[red]Start must be before end.[/red]")
            return
        if interval < 1:
            error.update("[red]Interval must be at least 1 minute.[/red]")
            return

        try:
            from vandelay.config.settings import get_settings

            s = get_settings()
            s.heartbeat.enabled = enabled
            s.heartbeat.interval_minutes = interval
            s.heartbeat.active_hours_start = start
            s.heartbeat.active_hours_end = end
            s.heartbeat.timezone = tz
            s.save()
            self.app.notify("Heartbeat settings saved.", severity="information", timeout=3)
        except Exception as exc:
            error.update(f"[red]Save failed: {exc}[/red]")

    def _clear_completed(self) -> None:
        from vandelay.config.constants import TASK_QUEUE_FILE

        tasks = _load_tasks(TASK_QUEUE_FILE)
        remaining = [t for t in tasks if t.get("status") not in {"completed", "failed", "cancelled"}]
        _save_tasks(TASK_QUEUE_FILE, remaining)
        self._selected_task_id = None
        self._build_task_table()
        self._update_task_button_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)


def _load_tasks(path: Path) -> list[dict]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load task queue: %s", exc)
    return []


def _save_tasks(path: Path, tasks: list[dict]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(tasks, indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to save task queue: %s", exc)


def _config_timezone() -> str:
    """Return the user's configured timezone, falling back to UTC."""
    try:
        from vandelay.config.settings import Settings, get_settings

        if Settings.config_exists():
            return get_settings().timezone or "UTC"
    except Exception:
        pass
    return "UTC"
