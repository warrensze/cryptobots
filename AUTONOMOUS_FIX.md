# Autonomous Navigation Fix (2026-06-11)

## Problem Identified

The autonomous navigation code was not working correctly. Analysis of recent test logs showed:
- **Distance was always ≈0** (occasional -1, but never increasing)
- **Gyro angle changed slightly** (showing sensors worked)
- **Robot did not follow the polynomial equation**

## Root Cause

The code used `motor_pair.pair()` to control motors:

```python
# OLD CODE (BROKEN)
pair_drive_motors()  # Calls motor_pair.pair(PAIR_1, port.B, port.F)
...
motor_pair.move_tank(DRIVE_PAIR, left_speed, right_speed)  # Drive the pair
...
# But then tried to read individual motor positions:
motor.relative_position(LEFT_DRIVE_MOTOR_PORT)  # ← Doesn't work when motors are in a pair!
```

**When motors are controlled as a motor pair, individual motor position APIs return stale or incorrect data.** This broke the encoder-based distance tracking, causing:
- Distance always read as 0
- Proportional control couldn't see the robot moving
- Robot couldn't follow the trendline equation

## Solution Implemented

Changed from motor pair control to individual motor control:

```python
# NEW CODE (FIXED)
def drive_motors(left_speed, right_speed):
    """Drive each motor individually so encoder reads work correctly."""
    motor.run(LEFT_DRIVE_MOTOR_PORT, left_speed * LEFT_DRIVE_MOTOR_DIRECTION)
    motor.run(RIGHT_DRIVE_MOTOR_PORT, right_speed * RIGHT_DRIVE_MOTOR_DIRECTION)

def apply_proportional_drive(error):
    # ... calculate speeds ...
    drive_motors(left_speed, right_speed)  # ← Use individual motor control
```

**Benefits:**
- Individual motor position reads now work correctly
- Distance tracking will be accurate
- Proportional control can now see robot movement
- Robot should follow the trendline equation

## Changes Made

1. Replaced `motor_pair.pair()` + `motor_pair.move_tank()` with `motor.run()` for each motor
2. Updated `drive_motors()` function to apply direction multipliers
3. Updated `stop_drive_motors()` to use `motor.stop()` for each motor
4. Removed `pair_drive_motors()` call from `run_autonomous_navigation()`

## Testing Checklist

Before committing, verify:

- [ ] Upload fixed `code/hub/main.py` to SPIKE hub
- [ ] Show red to port D color sensor to trigger autonomous run
- [ ] Observe robot movement (should now actually move forward)
- [ ] Check that distance values increase in the log
- [ ] Verify robot follows curved path according to trendline
- [ ] Compare new autonomous CSV with expected values
- [ ] Test both manual (right button) and autonomous (color sensor) modes

## Next Steps If Issues Persist

If the robot still doesn't follow the equation correctly after this fix:

1. **Check proportional control tuning:**
   - Adjust `AUTO_KP` (try 2-5)
   - Adjust `AUTO_BASE_SPEED` (try 140-180)
   - Adjust `AUTO_MAX_CORRECTION`

2. **Verify training data:**
   - The equation was derived from manually-pushed data
   - Motor-driven movement may have different characteristics
   - Consider recording new training data with motors running

3. **Check robot configuration:**
   - Verify `LEFT_DRIVE_MOTOR_PORT` and `RIGHT_DRIVE_MOTOR_PORT` are correct
   - Verify motor directions (`LEFT_DRIVE_MOTOR_DIRECTION`, `RIGHT_DRIVE_MOTOR_DIRECTION`)
   - Verify wheel circumference (`WHEEL_CIRCUMFERENCE_MM`)
