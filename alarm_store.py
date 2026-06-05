import json
import os
import re
import uuid
import threading
from datetime import datetime, timedelta, time

DAYS_MAP = {
    "Mon": "Monday",
    "Tue": "Tuesday",
    "Wed": "Wednesday",
    "Thu": "Thursday",
    "Fri": "Friday",
    "Sat": "Saturday",
    "Sun": "Sunday"
}

VALID_DAYS = list(DAYS_MAP.keys())

def parse_relative_time(time_str: str, now: datetime) -> datetime:
    """Parses relative time strings like +5m, +1h30m, +10s and returns a target datetime."""
    match = re.match(r'^\+(\d+h)?(\d+m)?(\d+s)?$', time_str)
    if not match:
        raise ValueError("Invalid relative format. Use '+[Xh][Ym][Zs]' e.g., +5m, +1h30m, +30s")
    
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    
    if hours == 0 and minutes == 0 and seconds == 0:
        raise ValueError("Relative offset cannot be zero.")
        
    return now + timedelta(hours=hours, minutes=minutes, seconds=seconds)

def parse_absolute_time(time_str: str) -> time:
    """Parses HH:MM (24-hour format) and returns a time object."""
    match = re.match(r'^([0-1]?\d|2[0-3]):([0-5]\d)$', time_str)
    if not match:
        raise ValueError("Invalid time format. Use 24-hour format HH:MM (e.g., 14:30, 08:05)")
    hour = int(match.group(1))
    minute = int(match.group(2))
    return time(hour=hour, minute=minute)

class Alarm:
    def __init__(self, time_str, label="", repeat_days=None, enabled=True, id=None, 
                 target_datetime=None, alarm_time=None, snoozed_until=None, last_triggered_date=None):
        self.id = id or str(uuid.uuid4())
        self.time_str = time_str
        self.label = label or "Alarm"
        self.enabled = enabled
        self.repeat_days = repeat_days or []  # e.g., ["Mon", "Tue"]
        
        # Internal resolved times
        self.target_datetime = target_datetime  # datetime object for relative / explicit one-off alarms
        self.alarm_time = alarm_time  # time object for recurring daily alarms
        self.snoozed_until = snoozed_until  # datetime object when snoozed
        self.last_triggered_date = last_triggered_date  # ISO format date "YYYY-MM-DD"

    @classmethod
    def create(cls, time_str: str, label: str = "", repeat_days: list = None, now: datetime = None):
        """Factory method to create and resolve an Alarm from user input."""
        now = now or datetime.now()
        repeat_days = repeat_days or []
        
        if time_str.startswith('+'):
            # Relative time
            target_dt = parse_relative_time(time_str, now)
            # Normalize to exclude microseconds for cleaner logs/UI
            target_dt = target_dt.replace(microsecond=0)
            return cls(
                time_str=time_str,
                label=label,
                repeat_days=[],  # Timers cannot be recurring
                enabled=True,
                target_datetime=target_dt
            )
        else:
            # Absolute time
            t = parse_absolute_time(time_str)
            if repeat_days:
                # Recurring alarm
                return cls(
                    time_str=time_str,
                    label=label,
                    repeat_days=repeat_days,
                    enabled=True,
                    alarm_time=t
                )
            else:
                # One-off alarm at specific time
                target_dt = datetime.combine(now.date(), t)
                if target_dt <= now:
                    # Time already passed today, schedule for tomorrow
                    target_dt += timedelta(days=1)
                target_dt = target_dt.replace(second=0, microsecond=0)
                return cls(
                    time_str=time_str,
                    label=label,
                    repeat_days=[],
                    enabled=True,
                    target_datetime=target_dt
                )

    def is_triggered(self, now: datetime) -> bool:
        """Determines if the alarm should trigger right now."""
        if not self.enabled:
            return False
            
        # 1. Check if snoozed
        if self.snoozed_until:
            return now >= self.snoozed_until

        # 2. Check target_datetime (relative / one-offs)
        if self.target_datetime:
            return now >= self.target_datetime and self.last_triggered_date != now.date().isoformat()

        # 3. Check recurring daily time
        if self.alarm_time:
            # Compare hours and minutes
            if now.hour == self.alarm_time.hour and now.minute == self.alarm_time.minute:
                # If there are repeat days, check if today is matching
                if self.repeat_days:
                    day_name = now.strftime("%a")
                    if day_name not in self.repeat_days:
                        return False
                
                # Check if already triggered today
                return self.last_triggered_date != now.date().isoformat()
                
        return False

    def get_remaining_time_desc(self, now: datetime) -> str:
        """Returns a string describing the remaining time until next trigger."""
        if not self.enabled:
            return "Disabled"
            
        if self.snoozed_until:
            diff = self.snoozed_until - now
            seconds = int(diff.total_seconds())
            if seconds <= 0:
                return "Ringing (Snoozed)"
            return f"Snoozed ({seconds // 60}m {seconds % 60}s)"
            
        if self.target_datetime:
            diff = self.target_datetime - now
            seconds = int(diff.total_seconds())
            if seconds <= 0:
                return "Ringing"
            
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m {secs}s"
            else:
                return f"{secs}s"
                
        if self.alarm_time:
            # Calculate next occurrence
            target_dt = datetime.combine(now.date(), self.alarm_time)
            
            if self.repeat_days:
                # Find the next scheduled day
                current_weekday = now.weekday()  # Mon=0, Sun=6
                weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                
                # Find distance to closest active day
                min_days = 8
                for r_day in self.repeat_days:
                    r_idx = weekdays.index(r_day)
                    days_diff = (r_idx - current_weekday) % 7
                    # If it's today, check if the time has already passed
                    if days_diff == 0 and target_dt <= now:
                        days_diff = 7
                    if days_diff < min_days:
                        min_days = days_diff
                
                target_dt += timedelta(days=min_days)
            else:
                # One-off daily time
                if target_dt <= now:
                    target_dt += timedelta(days=1)
                    
            diff = target_dt - now
            hours = int(diff.total_seconds()) // 3600
            minutes = (int(diff.total_seconds()) % 3600) // 60
            return f"In {hours}h {minutes}m"

        return "Unknown"

    def to_dict(self):
        return {
            "id": self.id,
            "time_str": self.time_str,
            "label": self.label,
            "enabled": self.enabled,
            "repeat_days": self.repeat_days,
            "target_datetime": self.target_datetime.isoformat() if self.target_datetime else None,
            "alarm_time": self.alarm_time.strftime("%H:%M") if self.alarm_time else None,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "last_triggered_date": self.last_triggered_date
        }

    @classmethod
    def from_dict(cls, d):
        target_datetime = datetime.fromisoformat(d["target_datetime"]) if d.get("target_datetime") else None
        
        alarm_time = None
        if d.get("alarm_time"):
            h, m = map(int, d["alarm_time"].split(':'))
            alarm_time = time(hour=h, minute=m)
            
        snoozed_until = datetime.fromisoformat(d["snoozed_until"]) if d.get("snoozed_until") else None
        
        return cls(
            id=d["id"],
            time_str=d["time_str"],
            label=d["label"],
            enabled=d["enabled"],
            repeat_days=d["repeat_days"],
            target_datetime=target_datetime,
            alarm_time=alarm_time,
            snoozed_until=snoozed_until,
            last_triggered_date=d.get("last_triggered_date")
        )


class AlarmStore:
    def __init__(self, filepath="alarms.json"):
        self.filepath = filepath
        self.alarms = []
        self.lock = threading.Lock()
        self.load_alarms()

    def load_alarms(self):
        with self.lock:
            if not os.path.exists(self.filepath):
                self.alarms = []
                return
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    self.alarms = [Alarm.from_dict(d) for d in data]
            except Exception:
                # If corrupt, initialize empty
                self.alarms = []

    def save_alarms(self):
        with self.lock:
            try:
                with open(self.filepath, 'w') as f:
                    json.dump([a.to_dict() for a in self.alarms], f, indent=4)
            except Exception as e:
                print(f"Error saving alarms: {e}")

    def add_alarm(self, time_str: str, label: str = "", repeat_days: list = None) -> Alarm:
        alarm = Alarm.create(time_str, label, repeat_days)
        with self.lock:
            self.alarms.append(alarm)
        self.save_alarms()
        return alarm

    def delete_alarm(self, alarm_id: str) -> bool:
        found = False
        with self.lock:
            initial_len = len(self.alarms)
            self.alarms = [a for a in self.alarms if a.id != alarm_id]
            found = len(self.alarms) < initial_len
        if found:
            self.save_alarms()
        return found

    def toggle_alarm(self, alarm_id: str) -> bool:
        # Toggles enabled state of alarm, resets snooze / triggered state if re-enabling
        found_alarm = None
        with self.lock:
            for a in self.alarms:
                if a.id == alarm_id:
                    a.enabled = not a.enabled
                    if a.enabled:
                        a.snoozed_until = None
                        a.last_triggered_date = None
                        # Recalculate target_datetime if it was a one-off and time has already passed
                        if a.target_datetime and not a.time_str.startswith('+'):
                            t = parse_absolute_time(a.time_str)
                            now = datetime.now()
                            target_dt = datetime.combine(now.date(), t)
                            if target_dt <= now:
                                target_dt += timedelta(days=1)
                            a.target_datetime = target_dt.replace(second=0, microsecond=0)
                    found_alarm = a
                    break
        if found_alarm:
            self.save_alarms()
            return True
        return False

    def snooze_alarm(self, alarm_id: str, snooze_minutes: int = 5):
        with self.lock:
            for a in self.alarms:
                if a.id == alarm_id:
                    a.snoozed_until = datetime.now() + timedelta(minutes=snooze_minutes)
                    # Clear target_datetime from flagging again immediately
                    a.last_triggered_date = None 
                    break
        self.save_alarms()

    def dismiss_alarm(self, alarm_id: str, now: datetime = None):
        now = now or datetime.now()
        with self.lock:
            for a in self.alarms:
                if a.id == alarm_id:
                    a.snoozed_until = None
                    a.last_triggered_date = now.date().isoformat()
                    
                    # If it's a one-off (non-recurring) or relative timer, we disable it after dismiss
                    if not a.repeat_days:
                        a.enabled = False
                    break
        self.save_alarms()

    def get_alarms(self) -> list:
        with self.lock:
            return list(self.alarms)
