# Chronos CLI Alarm Clock ⏰

Chronos is a robust, responsive, and highly interactive Python CLI Alarm Clock application designed with rich terminal aesthetics. It utilizes custom background scheduling, thread-safe memory storage, local serialization, and platform-independent sound triggers.

---

## 🚀 Key Features

- **Dynamic Terminal UI**: Implemented via the `rich` library, showcasing a layout panel with live system clock updates, status dashboards, and structured data tables.
- **Flex-Time Scheduling**: Supports absolute 24-hour schedules (e.g., `14:30`), relative timer offsets (e.g., `+15m`, `+1h30m`, `+45s`), and custom weekday recurring patterns (e.g., `Mon Wed Fri`).
- **Interactive Ringing Screen**: Flashing visual alert screen featuring quick action keys (`S` to Snooze for 5 minutes, `D` to Dismiss).
- **Audio Feedback**: Cross-platform alert manager that triggers local audio bleeps (using `winsound` on Windows and standard terminal ANSI bells on other systems).
- **Persistent Storage**: Save/load logic targeting local `alarms.json` ensuring configurations persist across application life cycles.
- **Index-Based Commands**: Interact with alarms using friendly sequential indices (e.g., `toggle 1`, `delete 2`) rather than copy-pasting raw UUID strings.

---

## 🛠️ How It Works (Working Design & Architecture)

```
+-------------------------------------------------------+
|                 Main Application Thread               |
|  - Controls REPL loop                                 |
|  - Receives and parses user commands (add, toggle...)  |
|  - Triggers UI clears and rendering widgets           |
+---------------------------+---------------------------+
                            |
                     (Reads/Writes)
                            v
+-------------------------------------------------------+
|                    AlarmStore                         |
|  - Houses in-memory collection of Alarm models        |
|  - Controls thread-safe lock for state updates        |
|  - Serializes state to local alarms.json              |
+---------------------------+---------------------------+
                            ^
                     (Reads/Checks)
                            |
+---------------------------+---------------------------+
|               AlarmEngine Background Thread           |
|  - Runs on daemon loop (ticks every 500ms)            |
|  - Compares system time against active alarms         |
|  - Launches SoundManager sound loops                  |
|  - Preempts REPL display into Ringing Mode            |
+-------------------------------------------------------+
```

### 1. Concurrency & Thread Safety
A responsive alarm clock requires background monitoring. To achieve this, the application separates concerns into two main threads:
- **Main Thread**: Runs the interactive user loop (REPL), capturing user inputs for adding, deleting, and editing alarms.
- **Background Daemon Thread (`AlarmEngine`)**: Polls active alarms every 500ms to compare scheduled times with the real system clock.

Because both threads access the in-memory array of alarms simultaneously, the `AlarmStore` uses a mutual exclusion lock (`threading.Lock()`). Any modification (addition, deletion, status toggling) or evaluation read is wrapped inside a safe context manager:
```python
with self.lock:
    # Safe multi-threaded state operations
```

### 2. Relative vs. Recurring Alarm Logic
At creation time, user inputs are dynamically converted into matching temporal models:
- **Relative timers** (e.g. `+10m`): Calculated immediately to an absolute future `target_datetime` (`now + 10m`). Once triggered and dismissed, they automatically disable themselves.
- **One-off absolute alarms** (e.g., `14:30`): If the time has already passed today, it automatically rolls forward to tomorrow. Like relative timers, they turn off after one run.
- **Recurring schedules** (e.g., weekdays): Stored as an abstract `alarm_time` (hour/minute) and a list of valid days (`["Mon", "Wed"]`). The engine matches the weekday and time, triggering the alert while persisting the `last_triggered_date` to prevent the alarm from triggering repeatedly within the same 60-second window.

### 3. CLI Command Loop vs. Live Text Entry
In pure CLI environments, capturing continuous keyboard strokes while updating a clock live can lead to broken input lines. To ensure a bulletproof user experience across all terminal emulators (Cmd, PowerShell, Bash, VS Code Terminal):
- The screen redraws on command executions or explicit refreshes (pressing `Enter` on empty input).
- When an alarm is triggered, the background engine starts the alarm sound and flags the trigger state. The user can press `Enter` to access the responsive `Ringing` dialog modal where they select to Snooze or Dismiss.

### 4. Zero-Dependency Audio Pipeline
To avoid heavy dependencies like `pygame` or `simpleaudio` (which require C compilers and binary linkers on some operating systems), we utilize:
- **Windows**: Built-in `winsound.Beep` for clean pitch-frequency alert notes.
- **macOS/Linux**: Standard ANSI terminal bell (`\a`) output.

---

## 📂 Project Directory Structure

```
.
├── alarms.json           # Local storage for persisted alarms (auto-created)
├── alarm_engine.py       # Background scheduler thread loop
├── alarm_store.py        # Alarm models, parsing logic, and thread-safe store
├── main.py               # Main application runner
├── README.md             # Project documentation
├── sound_manager.py      # Cross-platform sound generator
├── ui.py                 # Rich UI layout panels and inputs
└── tests/
    └── test_alarm.py     # Comprehensive unit tests
```

---

## 🚀 Setup & Installation

### Prerequisites
- **Python 3.10+** (verified up to Python 3.14)
- Command terminal access

### Installation Steps

1. **Clone or navigate to the workspace directory**:
   ```bash
   cd "e:/maurya/Software Er test Better"
   ```

2. **Create a Python Virtual Environment**:
   ```bash
   py -m venv .venv
   ```

3. **Activate the Virtual Environment**:
   - **Windows PowerShell**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Windows Command Prompt**:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **Bash/macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. **Install Dependencies**:
   ```bash
   pip install rich
   ```

---

## 🏃 How to Run the Application

With the virtual environment active, execute the main entry point:
```bash
python main.py
```

---

## 🧪 Running Unit Tests

A comprehensive suite of 10 unit tests is included, verifying parsing functions, relative time offsets, recurring weekly checks, snooze logic, and thread-safe file serialization.

Run the tests using Python's built-in discovery tool:
```bash
python -m unittest discover -s tests
```

---

## 📖 How to Use (Interactive CLI Guide)

### Commands

| Command | Sub-prompts / Args | Description |
| :--- | :--- | :--- |
| **`add`** | Time, Label, Repeat days | Adds a new alarm. Supports timers (`+5m`) and clock times (`08:30`). |
| **`toggle [num]`** | Alarm list index | Toggles the active state (`ON`/`OFF`) of the specified alarm index. |
| **`delete [num]`** | Alarm list index | Deletes the specified alarm from the schedule. |
| **`exit`** | None | Safely stops the scheduler engine, kills audio threads, and exits. |

### Adding Alarms Examples:
- **Absolute Time (Daily)**: 
  - Type `add`
  - Enter time: `07:30`
  - Enter label: `Morning Gym`
  - Enter repeat days: `Mon Tue Wed Thu Fri` (leave empty for a one-off alarm)
- **Timer / Relative Alarm**:
  - Type `add`
  - Enter time: `+10m` (10 minutes from now) or `+45s` (45 seconds from now)
  - Enter label: `Boil Eggs`
  - *(Repeat days are automatically bypassed for relative alarms)*

### Snoozing and Dismissing:
When an alarm rings:
1. The sound starts repeating and a warning notice is indicated.
2. Press **Enter** to focus the response shell.
3. Type **`S`** to snooze (delay alarm by 5 minutes) or **`D`** to dismiss (turn off alarm).
