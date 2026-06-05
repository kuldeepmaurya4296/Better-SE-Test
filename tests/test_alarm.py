import unittest
import os
import tempfile
from datetime import datetime, timedelta, time
from alarm_store import (
    Alarm, AlarmStore, parse_relative_time, parse_absolute_time
)

class TestAlarmClock(unittest.TestCase):

    def test_parse_relative_time(self):
        now = datetime(2026, 6, 5, 12, 0, 0)
        
        # Test 5 minutes
        t1 = parse_relative_time("+5m", now)
        self.assertEqual(t1, now + timedelta(minutes=5))
        
        # Test 1h 30m
        t2 = parse_relative_time("+1h30m", now)
        self.assertEqual(t2, now + timedelta(hours=1, minutes=30))
        
        # Test 10s
        t3 = parse_relative_time("+10s", now)
        self.assertEqual(t3, now + timedelta(seconds=10))

        # Test invalid formats
        with self.assertRaises(ValueError):
            parse_relative_time("5m", now)
        with self.assertRaises(ValueError):
            parse_relative_time("+", now)
        with self.assertRaises(ValueError):
            parse_relative_time("+0h0m0s", now)

    def test_parse_absolute_time(self):
        t1 = parse_absolute_time("14:30")
        self.assertEqual(t1, time(14, 30))

        t2 = parse_absolute_time("08:05")
        self.assertEqual(t2, time(8, 5))

        # Test invalid formats
        with self.assertRaises(ValueError):
            parse_absolute_time("25:00")
        with self.assertRaises(ValueError):
            parse_absolute_time("14:60")
        with self.assertRaises(ValueError):
            parse_absolute_time("8:5")  # Needs padding

    def test_alarm_create_relative(self):
        now = datetime(2026, 6, 5, 12, 0, 0)
        alarm = Alarm.create("+15m", label="Coffee Break", now=now)
        
        self.assertEqual(alarm.label, "Coffee Break")
        self.assertEqual(alarm.target_datetime, now + timedelta(minutes=15))
        self.assertIsNone(alarm.alarm_time)
        self.assertEqual(alarm.repeat_days, [])

    def test_alarm_create_one_off_future(self):
        now = datetime(2026, 6, 5, 12, 0, 0)
        # 14:30 is in the future relative to 12:00
        alarm = Alarm.create("14:30", label="Afternoon meeting", now=now)
        
        self.assertEqual(alarm.target_datetime, datetime(2026, 6, 5, 14, 30))
        self.assertIsNone(alarm.alarm_time)

    def test_alarm_create_one_off_past(self):
        now = datetime(2026, 6, 5, 12, 0, 0)
        # 10:30 is in the past relative to 12:00
        alarm = Alarm.create("10:30", label="Morning standup", now=now)
        
        # Should be scheduled for tomorrow (June 6th)
        self.assertEqual(alarm.target_datetime, datetime(2026, 6, 6, 10, 30))
        self.assertIsNone(alarm.alarm_time)

    def test_alarm_create_recurring(self):
        now = datetime(2026, 6, 5, 12, 0, 0)
        alarm = Alarm.create("07:00", label="Wakeup", repeat_days=["Mon", "Wed", "Fri"], now=now)
        
        self.assertIsNone(alarm.target_datetime)
        self.assertEqual(alarm.alarm_time, time(7, 0))
        self.assertEqual(alarm.repeat_days, ["Mon", "Wed", "Fri"])

    def test_alarm_trigger_relative(self):
        now = datetime(2026, 6, 5, 12, 0, 0)
        alarm = Alarm.create("+5m", now=now)
        
        # At 12:02, not triggered yet
        self.assertFalse(alarm.is_triggered(datetime(2026, 6, 5, 12, 2, 0)))
        
        # At 12:05, should trigger
        self.assertTrue(alarm.is_triggered(datetime(2026, 6, 5, 12, 5, 0)))

        # Disable it, shouldn't trigger
        alarm.enabled = False
        self.assertFalse(alarm.is_triggered(datetime(2026, 6, 5, 12, 5, 0)))

    def test_alarm_trigger_recurring(self):
        # 2026-06-05 is a Friday
        now = datetime(2026, 6, 5, 8, 0, 0)
        
        # Alarm scheduled for Mon, Fri at 8:00
        alarm = Alarm.create("08:00", repeat_days=["Mon", "Fri"], now=now)
        
        # Friday 8:00:00 -> triggers
        self.assertTrue(alarm.is_triggered(now))
        
        # Saturday 8:00:00 -> doesn't trigger
        sat_now = datetime(2026, 6, 6, 8, 0, 0)
        self.assertFalse(alarm.is_triggered(sat_now))

    def test_alarm_trigger_snooze(self):
        now = datetime(2026, 6, 5, 12, 0, 0)
        alarm = Alarm.create("+5m", now=now)
        
        # Trigger at 12:05
        trigger_time = datetime(2026, 6, 5, 12, 5, 0)
        self.assertTrue(alarm.is_triggered(trigger_time))
        
        # Snooze for 5 minutes (snoozed_until = 12:10)
        alarm.snoozed_until = trigger_time + timedelta(minutes=5)
        
        # Check trigger at 12:07 -> false
        self.assertFalse(alarm.is_triggered(datetime(2026, 6, 5, 12, 7, 0)))
        
        # Check trigger at 12:10 -> true
        self.assertTrue(alarm.is_triggered(datetime(2026, 6, 5, 12, 10, 0)))

    def test_store_lifecycle(self):
        # Create temp file path
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        
        try:
            store = AlarmStore(filepath=temp_path)
            self.assertEqual(len(store.get_alarms()), 0)
            
            # Add alarm
            a = store.add_alarm("12:00", label="Test Alarm")
            self.assertEqual(len(store.get_alarms()), 1)
            self.assertEqual(store.get_alarms()[0].label, "Test Alarm")
            
            # Check serialization worked
            store2 = AlarmStore(filepath=temp_path)
            self.assertEqual(len(store2.get_alarms()), 1)
            self.assertEqual(store2.get_alarms()[0].id, a.id)
            
            # Toggle alarm
            store.toggle_alarm(a.id)
            self.assertFalse(store.get_alarms()[0].enabled)
            
            # Delete alarm
            store.delete_alarm(a.id)
            self.assertEqual(len(store.get_alarms()), 0)
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == '__main__':
    unittest.main()
