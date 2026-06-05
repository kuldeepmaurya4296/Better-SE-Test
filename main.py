import sys
from alarm_store import AlarmStore, VALID_DAYS
from sound_manager import SoundManager
from alarm_engine import AlarmEngine
from ui import ConsoleUI

def resolve_alarm_id(store: AlarmStore, num_str: str) -> str:
    """Helper to resolve a 1-indexed console list number to its UUID in the store."""
    try:
        idx = int(num_str) - 1
        alarms = store.get_alarms()
        if 0 <= idx < len(alarms):
            return alarms[idx].id
    except ValueError:
        pass
    return None

def main():
    store = AlarmStore()
    sound_mgr = SoundManager()
    engine = AlarmEngine(store, sound_mgr)
    ui = ConsoleUI()

    # Start background scheduler
    engine.start()

    success_msg = "Chronos Alarm Engine started successfully!"
    error_msg = None

    try:
        while True:
            # Check if background engine flagged a ringing alarm
            ringing_alarm = engine.get_ringing_alarm()
            if ringing_alarm:
                ui.render_ringing_screen(ringing_alarm)
                while True:
                    choice = ui.get_input("Respond (S/D): ").strip().upper()
                    if choice in ('S', 'SNOOZE'):
                        engine.snooze_active_alarm(snooze_minutes=5)
                        success_msg = f"Alarm '{ringing_alarm.label}' snoozed for 5 minutes."
                        error_msg = None
                        break
                    elif choice in ('D', 'DISMISS'):
                        engine.dismiss_active_alarm()
                        success_msg = f"Alarm '{ringing_alarm.label}' dismissed."
                        error_msg = None
                        break
                    else:
                        ui.console.print("[bold red]Invalid response.[/] Enter [bold yellow]S[/] to Snooze or [bold yellow]D[/] to Dismiss.")
                # Ringing handled, redraw dashboard
                ui.render_dashboard(store, error_msg, success_msg)
                success_msg = None
                continue

            # Standard interactive UI
            ui.render_dashboard(store, error_msg, success_msg)
            # Reset notifications
            success_msg = None
            error_msg = None

            cmd_input = ui.get_input("Enter command or press Enter: ").strip().lower()
            if not cmd_input:
                continue

            parts = cmd_input.split(maxsplit=1)
            cmd = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if cmd in ('exit', 'quit', 'q'):
                break

            elif cmd == 'add':
                # Sub-prompt workflow for adding alarm
                try:
                    time_str = ui.get_input("Enter time (HH:MM or +Xm, e.g., 08:30 or +5m): ").strip()
                    if not time_str:
                        error_msg = "Alarm time cannot be empty."
                        continue
                    
                    label = ui.get_input("Enter label/message (optional): ").strip()
                    
                    # We only prompt for days if time is NOT a relative timer
                    repeat_days = []
                    if not time_str.startswith('+'):
                        days_input = ui.get_input("Enter repeat days separated by space (Mon Tue Wed Thu Fri Sat Sun, optional): ").strip()
                        if days_input:
                            # Split and title case to match Mon, Tue, etc.
                            raw_days = [d.strip().capitalize() for d in days_input.split()]
                            
                            # Validate days
                            invalid_days = [d for d in raw_days if d not in VALID_DAYS]
                            if invalid_days:
                                error_msg = f"Invalid day abbreviation(s): {', '.join(invalid_days)}. Use Mon, Tue, etc."
                                continue
                            repeat_days = raw_days

                    alarm = store.add_alarm(time_str, label, repeat_days)
                    success_msg = f"Added alarm '{alarm.label}' scheduled for {alarm.get_remaining_time_desc(alarm.target_datetime if alarm.target_datetime else alarm.alarm_time)}."
                except Exception as e:
                    error_msg = str(e)

            elif cmd == 'toggle':
                num_str = args
                if not num_str:
                    num_str = ui.get_input("Enter alarm number to toggle: ").strip()
                
                alarm_id = resolve_alarm_id(store, num_str)
                if alarm_id:
                    store.toggle_alarm(alarm_id)
                    success_msg = f"Toggled alarm #{num_str}."
                else:
                    error_msg = f"Invalid alarm number: '{num_str}'"

            elif cmd in ('delete', 'remove'):
                num_str = args
                if not num_str:
                    num_str = ui.get_input("Enter alarm number to delete: ").strip()

                alarm_id = resolve_alarm_id(store, num_str)
                if alarm_id:
                    store.delete_alarm(alarm_id)
                    success_msg = f"Deleted alarm #{num_str}."
                else:
                    error_msg = f"Invalid alarm number: '{num_str}'"

            else:
                error_msg = f"Unknown command: '{cmd}'. Try 'add', 'toggle [num]', 'delete [num]', or 'exit'."

    except Exception as e:
        ui.console.print(f"[bold red]An unexpected system error occurred:[/] {e}")
    finally:
        # Clean shutdown of engine and threads
        ui.clear_screen()
        ui.console.print("[bold yellow]Stopping Chronos Alarm Engine...[/]")
        engine.stop()
        ui.console.print("[bold green]Goodbye![/]")
        sys.exit(0)

if __name__ == '__main__':
    main()
