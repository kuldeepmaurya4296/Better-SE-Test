import os
import sys
import time
import threading

class SoundManager:
    """Manages audio feedback for alarms. Plays a synthesized beep sequence in a background thread."""
    def __init__(self):
        self._playing = False
        self._thread = None
        self._lock = threading.Lock()

    def start_alarm_sound(self):
        """Starts playing the alarm sound in a background thread if not already playing."""
        with self._lock:
            if self._playing:
                return
            self._playing = True
            self._thread = threading.Thread(target=self._play_loop, daemon=True)
            self._thread.start()

    def stop_alarm_sound(self):
        """Stops the alarm sound loop."""
        with self._lock:
            self._playing = False
        if self._thread:
            # We don't join aggressively because winsound block might hold briefly,
            # but setting playing to False will break the loop on next tick.
            self._thread = None

    def _play_loop(self):
        """Internal audio feedback playback loop."""
        is_windows = os.name == 'nt'
        
        while True:
            with self._lock:
                if not self._playing:
                    break
            
            try:
                if is_windows:
                    import winsound
                    # Play alternating frequencies for a real alarm clock vibe
                    winsound.Beep(2000, 300)
                    time.sleep(0.1)
                    winsound.Beep(2000, 300)
                    time.sleep(0.6)
                else:
                    # Non-Windows fallback using standard terminal bell
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                    time.sleep(1.0)
            except Exception:
                # Silently catch errors (e.g. no audio output device, permission errors)
                # and fall back to terminal bell or sleep to prevent CPU hogging
                try:
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                except Exception:
                    pass
                time.sleep(1.5)
