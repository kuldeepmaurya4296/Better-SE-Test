import os
import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import DOUBLE, ROUNDED
from alarm_store import AlarmStore, Alarm

class ConsoleUI:
    """Manages all CLI rendering and terminal outputs using the rich library."""
    def __init__(self):
        self.console = Console()

    def clear_screen(self):
        """Clears the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def render_dashboard(self, store: AlarmStore, error_msg: str = None, success_msg: str = None):
        """Renders the main dashboard containing clock, alarms list, and status messages."""
        self.clear_screen()
        
        now = datetime.now()
        
        # 1. Header & Live Clock
        time_str = now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%A, %B %d, %Y")
        
        header_text = Text()
        header_text.append("⏰ CHRONOS CLI ALARM CLOCK ⏰\n", style="bold bright_cyan")
        header_text.append(f"{date_str}  |  ", style="dim white")
        header_text.append(f"{time_str}", style="bold yellow")
        
        header_panel = Panel(
            Align.center(header_text),
            box=DOUBLE,
            border_style="bright_magenta"
        )
        self.console.print(header_panel)

        # 2. Status Messages
        if error_msg:
            self.console.print(Panel(f"[bold red]Error:[/] {error_msg}", border_style="red"))
        elif success_msg:
            self.console.print(Panel(f"[bold green]Success:[/] {success_msg}", border_style="green"))

        # 3. Alarms Table
        table = Table(
            title="Scheduled Alarms",
            box=ROUNDED,
            border_style="cyan",
            title_style="bold bright_cyan",
            expand=True
        )
        
        table.add_column("#", justify="center", style="yellow", width=4)
        table.add_column("Label / Message", justify="left", style="white")
        table.add_column("Time Setting", justify="center", style="bright_blue")
        table.add_column("Repeat Days", justify="center", style="bright_yellow")
        table.add_column("Status", justify="center")
        table.add_column("Time Remaining", justify="left", style="dim green")
        
        alarms = store.get_alarms()
        if not alarms:
            table.add_row("-", "No alarms set. Use 'add' to create one!", "-", "-", "-", "-")
        else:
            for idx, alarm in enumerate(alarms, 1):
                # Status Column styling
                if not alarm.enabled:
                    status = Text("OFF", style="bold red")
                elif alarm.snoozed_until:
                    status = Text("SNOOZED", style="bold yellow blink")
                else:
                    status = Text("ON", style="bold green")
                
                # Repeat days formatting
                repeat_str = ", ".join(alarm.repeat_days) if alarm.repeat_days else "One-off"
                
                # Time setting display
                time_display = alarm.time_str
                if alarm.target_datetime and alarm.time_str.startswith('+'):
                    time_display = f"{alarm.time_str} ({alarm.target_datetime.strftime('%I:%M:%S %p')})"
                
                table.add_row(
                    str(idx),
                    alarm.label,
                    time_display,
                    repeat_str,
                    status,
                    alarm.get_remaining_time_desc(now)
                )

        self.console.print(table)

        # 4. Command Reference Footer
        footer_text = Text()
        footer_text.append("Commands: ", style="bold white")
        footer_text.append("add", style="bold green")
        footer_text.append(" | ", style="dim white")
        footer_text.append("toggle [num]", style="bold yellow")
        footer_text.append(" | ", style="dim white")
        footer_text.append("delete [num]", style="bold red")
        footer_text.append(" | ", style="dim white")
        footer_text.append("exit", style="bold bright_red")
        footer_text.append("\n[Tip: Press ENTER without typing a command to refresh the clock and countdowns]", style="italic dim white")
        
        footer_panel = Panel(
            Align.center(footer_text),
            box=ROUNDED,
            border_style="dim white"
        )
        self.console.print(footer_panel)

    def render_ringing_screen(self, alarm: Alarm):
        """Renders a full-screen-like overlay warning when an alarm triggers."""
        self.clear_screen()
        
        alert_text = Text()
        alert_text.append("🚨 🚨 🚨 ALARM TRIGGERED 🚨 🚨 🚨\n\n", style="bold red blink")
        alert_text.append(f"Label: {alarm.label}\n", style="bold white")
        alert_text.append(f"Scheduled Time: {alarm.time_str}\n\n", style="bright_cyan")
        alert_text.append("What would you like to do?\n", style="white")
        alert_text.append("[S] Snooze (5 minutes)   |   [D] Dismiss / Turn Off", style="bold yellow")
        
        alert_panel = Panel(
            Align.center(alert_text),
            box=DOUBLE,
            border_style="red",
            title="ALERT",
            title_style="bold red"
        )
        
        self.console.print("\n" * 3)
        self.console.print(alert_panel)
        self.console.print("\n" * 3)

    def get_input(self, prompt: str = "> ") -> str:
        """Helper to get user input safely with colors."""
        try:
            return input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            return "exit"
