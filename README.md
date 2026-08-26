# Focus

**Focus** is a Windows desktop productivity application that turns a normal PC into a controlled, low-distraction work environment. It combines task management, time planning, calendar-aware scheduling, focus/Pomodoro sessions, a fullscreen Focus Mode, distraction control, universal media controls, and productivity analytics into one tool.

Focus is not another generic task manager or Pomodoro timer. It is a **control layer** that sits on top of the tools you already use (Google Calendar, Spotify/VLC/browser media, Windows) and helps you get from "what should I do" to "I'm actually doing it" with as little friction as possible.

> **Plan → Prepare → Focus → Track → Review**

---

## Table of Contents

- [Core Philosophy](#core-philosophy)
- [Features](#features)
- [How It Works](#how-it-works)
  - [Application Modes](#application-modes)
  - [Focus Session Lifecycle](#focus-session-lifecycle)
  - [Scheduling](#scheduling)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Getting Started](#getting-started)
- [Development Principles](#development-principles)
- [Roadmap](#roadmap)
- [Privacy Model](#privacy-model)

---

## Core Philosophy

1. **What should I do?** — Task management and priorities.
2. **When should I do it?** — Time planning, calendar-aware scheduling.
3. **How effectively did I use my time?** — Session tracking and analytics.

During a Focus session, the computer should feel like a **workspace**, not a general-purpose PC — the timer, current task, progress, and media controls are all available without leaving the app.

---

## Features

- ✅ **Task management** — title, description, estimated duration, priority, deadline, category, and status (`TODO`, `IN_PROGRESS`, `COMPLETED`, `POSTPONED`, `CANCELLED`)
- ⏱️ **Focus sessions** — countdown timer, pause/resume, early-exit with reason capture, session history
- 🖥️ **Fullscreen Focus Mode** — minimal UI showing the timer, current task, progress bar, and controls
- 📅 **Manual & calendar-aware scheduling** — turns available time + tasks + recurring commitments into a suggested block-by-block schedule
- 🔁 **Recurring weekly commitments** — define fixed unavailable periods (school, work, tuition) that the scheduler treats as busy
- 🧭 **First-run onboarding wizard** — collects wake/sleep time, weekly commitments, and focus/break preferences
- 📊 **Productivity statistics** — focused time, sessions completed, longest session, and full session history for the day
- 🎨 **Dark, minimal theme** — centralized styling with a single accent color, no gamification, no clutter
- 🧩 **Modular, testable core** — scheduling and timer logic are pure Python, fully decoupled from the UI

### Planned (not yet implemented in this codebase)

- Google Calendar sync (OAuth, busy/free calculation, optional event creation)
- Focus Profiles (allowed/restricted applications per session)
- Application/process monitoring and distraction control
- Universal media control panel (Spotify, browser, VLC, Windows media session APIs)
- Reminders (one-time, recurring, task-linked)
- Exit protection (PIN, delayed exit)
- Weekly/monthly analytics, focus efficiency, planned-vs-actual reporting

See [Roadmap](#roadmap) for the full phased build-out.

---

## How It Works

### Application Modes

**Normal Mode** is the main interface: a sidebar with **Dashboard**, **Schedule**, and **Statistics** screens inside a `QStackedWidget`.

**Focus Mode** is a separate fullscreen window (`FocusScreen`) launched on top of Normal Mode. It shows:

- A live countdown timer
- The current task
- A progress bar
- Pause / End Focus controls
- A confirmation dialog (with a required reason) before ending a session early — including intercepting window-close attempts (e.g. Alt+F4) so exits are deliberate, not impulsive

When the timer completes or the session is ended early, the session is saved and Normal Mode is restored.

### Focus Session Lifecycle

```
IDLE → PREPARING → ACTIVE ⇄ PAUSED → COMPLETED / ENDED_EARLY
```

1. `FocusManager.start_focus(task, duration)` starts the `TimerEngine` and creates a session via `SessionManager`.
2. `TimerEngine` ticks once per second (via `QTimer`) and emits `tick`, `paused`, `resumed`, and `finished` signals — it has no knowledge of the UI.
3. `SessionManager` owns session state, records `TimeRecord` entries for focused time, and persists everything through `SessionRepository`.
4. On completion or early exit, `FocusManager` emits `session_finished` / `session_ended_early`, the task's actual time is updated, and the Dashboard/Statistics screens refresh.

### Scheduling

The `Scheduler` (`core/scheduler.py`) is pure logic with no UI or database dependencies:

1. Takes a time window (e.g. `18:00`–`23:00`), active tasks, focus/break durations, and a list of `BusyInterval`s (currently sourced from recurring weekly commitments).
2. Builds a chronological timeline of `BUSY` and `FREE` segments.
3. Fills `FREE` segments with task blocks (chunked to the configured focus length), inserting breaks between them.
4. Never schedules over a busy interval, and reports any tasks that didn't fit as `unscheduled_tasks`.
5. Returns a deterministic, testable `SchedulerResult` — the scheduler only **suggests**; the user always approves and starts the actual session.

---

## Architecture

```
                    ┌──────────────────────┐
                    │      Dashboard        │
                    └──────────┬────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                   │
            ▼                  ▼                   ▼
       Task Manager       Time Planner        Calendar Sync
            │                  │                   │
            └──────────────────┼──────────────────┘
                               ▼
                       ┌───────────────┐
                       │ Focus Manager │
                       └───────┬───────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                 │
              ▼                ▼                 ▼
       Focus Mode       Process Manager    Media Controller
              │                │                 │
              └────────────────┼────────────────┘
                               ▼
                       Session / Time Tracker
                               │
                               ▼
                          Analytics
```

**Dependency direction** (enforced throughout the codebase):

```
UI
 ↓
Application Services (core/*)
 ↓
Domain/Core Logic
 ↓
Repositories / Integration Interfaces
 ↓
OS / Database / External APIs
```

The UI layer never touches SQLite, Windows processes, or external APIs directly — it only calls manager classes in `core/`.

---

## Tech Stack

| Layer                | Choice                          |
|-----------------------|----------------------------------|
| Language              | Python                          |
| Desktop UI            | [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python) |
| Database              | SQLite (via Python's built-in `sqlite3`) |
| Process monitoring *(planned)* | `psutil` |
| OS integration *(planned)* | Windows APIs (media session, window management) |
| External integration *(planned)* | Google Calendar API (OAuth) |
| Testing               | `pytest` (scheduler/timer logic is pure Python and fully unit-testable) |

**Why PySide6:** native desktop performance, strong signal/slot event system (used throughout for timer ticks and session events), good support for fullscreen custom interfaces.

**Why SQLite:** zero-config, local-first storage that matches the app's privacy model — no server, no account required.

---

## Project Structure

```
focus_app/
│
├── main.py                        # Entry point — wires dependencies, starts Qt event loop
│
├── app/
│   ├── application.py
│   └── config.py                  # App name, window size constants
│
├── ui/
│   ├── main_window.py             # Normal Mode shell (sidebar + stacked screens)
│   ├── theme.py                   # Centralized dark theme / global stylesheet
│   ├── dashboard/
│   │   └── dashboard.py           # Task list, Start Focus, today's time summary
│   ├── focus/
│   │   └── focus_screen.py        # Fullscreen Focus Mode window
│   ├── schedule/
│   │   └── schedule_screen.py     # Manual availability + suggested schedule
│   ├── statistics/
│   │   └── statistics_screen.py   # Today's summary + session list
│   ├── tasks/
│   │   └── task_dialog.py         # Create/edit task modal
│   └── onboarding/
│       └── onboarding_wizard.py   # First-run setup (routine, commitments, preferences)
│
├── core/
│   ├── task_manager.py            # Task CRUD + status rules
│   ├── session_manager.py         # Session lifecycle + time records
│   ├── focus_manager.py           # Orchestrates TimerEngine + SessionManager
│   ├── timer_engine.py            # UI-agnostic countdown timer (Qt signals)
│   ├── scheduler.py               # Pure scheduling logic (no UI/DB deps)
│   └── onboarding_manager.py      # Preferences + weekly commitments
│
├── database/
│   ├── database.py                # SQLite connection + schema creation
│   ├── models.py                  # Typed dataclasses (Task, Session, etc.)
│   └── repositories/
│       ├── task_repository.py
│       ├── session_repository.py
│       ├── settings_repository.py
│       └── commitment_repository.py
│
├── integrations/                  # (planned) Google Calendar, Windows APIs
│
├── services/                      # (planned) analytics, recovery
│
├── tests/
│
└── assets/
```

---

## Database Schema

SQLite tables created on startup (`database/database.py`):

```sql
tasks                 -- id, title, description, estimated_minutes, priority,
                       -- deadline, status, category, actual_minutes,
                       -- created_at, completed_at

sessions               -- id, task_id, planned_minutes, actual_minutes,
                       -- started_at, ended_at, paused_seconds,
                       -- status, exit_reason

time_records            -- id, session_id, task_id, record_type,
                       -- start_at, end_at, duration_seconds

settings                -- key, value (generic app + onboarding preferences)

weekly_commitments      -- id, day_of_week, start_time, end_time, label, created_at
```

The schema is expected to evolve as calendar sync, focus profiles, and reminders are added.

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/jeremiah-exe/focus_app/
cd focus_app
pip install PySide6
```

### Run

```bash
python main.py
```

On first launch, the **Onboarding Wizard** will walk you through your daily routine, recurring weekly commitments, and focus/break preferences before the main app opens. The local SQLite database is created automatically at `data/focus.db`.

### Run tests

```bash
pytest
```

---

## Development Principles

This project follows a strict layering discipline (see `database/models.py`, `core/*`, and every `ui/*` module's docstring for concrete examples):

1. One subsystem at a time.
2. Business logic stays independent of the UI (`core/` has no PySide6 widget code beyond Qt's signal system).
3. Typed dataclasses/models over dicts.
4. OS/external integrations sit behind interfaces (`integrations/`), isolated from `core/`.
5. Focus Profiles and similar behavior are data-driven, not hardcoded.
6. Scheduling and timer logic are unit-tested in isolation from Qt.
7. No user-specific tasks, applications, or credentials hardcoded anywhere.
8. System-level features (app restriction, process monitoring) must be optional and fail-safe, with automatic restoration if the app crashes.

---

## Roadmap

| Phase | Focus |
|-------|-------|
| 1 | Core application shell, dashboard, SQLite, task CRUD ✅ |
| 2 | Focus engine — timer, session manager, fullscreen mode ✅ |
| 3 | Planning — manual availability, scheduler, reminders (partial ✅ — scheduler + commitments done, reminders pending) |
| 4 | Media — Windows media session detection, playback controls |
| 5 | Focus Profiles — allowed/restricted apps, safe process monitoring, exit PIN |
| 6 | Google Calendar — OAuth, event sync, calendar-aware scheduling |
| 7 | Analytics — weekly/monthly stats, focus efficiency, trends |
| 8 | Polish — animations, shortcuts, accessibility, installer, docs |

The MVP intentionally does **not** start with Windows application blocking or Google Calendar — the core focus loop (task → schedule → focus → track) is proven first.

---
