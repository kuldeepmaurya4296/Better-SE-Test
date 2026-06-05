import time
import threading
from datetime import datetime
from alarm_store import AlarmStore
from sound_manager import SoundManager

class AlarmEngine:
    """Background engine that polls alarms every second, triggers alerts, and manages the audio state."""
    def __init__(self, store: AlarmStore, sound_mgr: SoundManager):
        self.store = store
        self.sound_mgr = sound_mgr
        self.running = False
        self.thread = None
        self.ringing_alarm = None  # Holds the Alarm currently ringing
        self._lock = threading.Lock()

    def start(self):
        """Starts the background engine thread."""
        with self._lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stops the background engine thread."""
        with self._lock:
            self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        self.sound_mgr.stop_alarm_sound()

    def get_ringing_alarm(self):
        """Returns the currently ringing alarm, thread-safe."""
        with self._lock:
            return self.ringing_alarm

    def snooze_active_alarm(self, snooze_minutes: int = 5):
        """Snoozes the currently ringing alarm, updating store state and stopping sound."""
        with self._lock:
            if not self.ringing_alarm:
                return
            alarm_id = self.ringing_alarm.id
            self.ringing_alarm = None
        
        # Stop sound and tell store to snooze
        self.sound_mgr.stop_alarm_sound()
        self.store.snooze_alarm(alarm_id, snooze_minutes)

    def dismiss_active_alarm(self):
        """Dismisses the currently ringing alarm, updating store state and stopping sound."""
        with self._lock:
            if not self.ringing_alarm:
                return
            alarm_id = self.ringing_alarm.id
            self.ringing_alarm = None

        # Stop sound and tell store to dismiss
        self.sound_mgr.stop_alarm_sound()
        self.store.dismiss_alarm(alarm_id)

    def _run_loop(self):
        """Loop run by the daemon background thread checking alarm status."""
        while True:
            with self._lock:
                if not self.running:
                    break
            
            now = datetime.now()
            
            # Only check for new triggers if we aren't already ringing an alarm
            with self._lock:
                is_currently_ringing = self.ringing_alarm is not None

            if not is_currently_ringing:
                triggered_alarm = None
                # Fetch a snapshot of alarms to evaluate
                alarms = self.store.get_alarms()
                for alarm in alarms:
                    if alarm.is_triggered(now):
                        triggered_alarm = alarm
                        break
                
                if triggered_alarm:
                    with self._lock:
                        self.ringing_alarm = triggered_alarm
                    # Trigger audio playback
                    self.sound_mgr.start_alarm_sound()

            time.sleep(0.5)
