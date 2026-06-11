# Session Recovery Context

## Date

2026-06-11 (Updated from 2026-06-10)

## Project

Standalone repository:

```text
/Users/warren/LegoLeagueAutoDrive/cryptobots
```

Original reference repository:

```text
/Users/warren/LegoLeagueAutoDrive/public.superpowered2022
```

The original SuperPowered repository is historical/reference context only. The active project is the standalone `cryptobots` repo.

Current key file:

```text
code/hub/main.py
```

## Goal

Build a stock LEGO SPIKE Prime MicroPython datalogger, without Pybricks, that mimics the original SuperPowered Pybricks `DataLog` spreadsheet output as closely as practical.

The desired console/CSV output is exactly:

```csv
time,distance,gyro_angle
```

For autonomous navigation, the robot follows a polynomial equation to trace a curved path based on drive distance.

## Original SuperPowered Findings

The EV3/Pybricks code logs with `pybricks.tools.DataLog`.

Relevant files:

- `src/robot.py`
- `tests/test_datalog.py`

Important details:

- `StopWatch.time()` values are milliseconds.
- `DriveBase.distance()` values are millimeters.
- `gyro.angle()` values are degrees.
- The original logger often logs as fast as the loop allows, so row spacing is dense.

## Current SPIKE Design

The current `code/hub/main.py` is a one-file hub upload (updated 2026-06-11).

It records:

- `time` (milliseconds)
- `distance` (millimeters)
- `gyro_angle` (degrees)

Motor control (fixed in session 2026-06-11):
- Previously used `motor_pair.pair()` + `motor_pair.move_tank()` which broke individual encoder reads
- Now uses `motor.run(port, speed)` for each motor individually
- This allows distance feedback to work correctly during autonomous navigation

It uses:

- `time.ticks_ms()` / `time.ticks_diff()` for milliseconds
- drive motor encoders for estimated distance (individual motor reads)
- hub yaw for gyro angle
- `SAMPLE_MS = 5` for dense short-route logging
- `MAX_ROWS_PER_LOG = 8000`
- stable button-release detection before arming the next button action

The active program has a `ROBOT CONFIGURATION` section near the top. Default robot constants (updated 2026-06-11):

```python
LEFT_DRIVE_MOTOR_PORT = port.B
RIGHT_DRIVE_MOTOR_PORT = port.F
LEFT_DRIVE_MOTOR_DIRECTION = 1
RIGHT_DRIVE_MOTOR_DIRECTION = -1  # Fixed: motors wired in opposite polarity
AUTONOMOUS_START_SENSOR_PORT = port.D
WHEEL_CIRCUMFERENCE_MM = 176
```

Valid SPIKE Prime motor ports are `port.A` through `port.F`.

Motor direction fix: RIGHT motor is physically wired backward, so `RIGHT_DRIVE_MOTOR_DIRECTION = -1` 
compensates during distance calculation to ensure both encoders read positive when moving forward.

There is no intentional recording time limit. The right button starts and stops recording. The code waits for a stable release after the start press so the same press is not reused as the stop press, but it does not ignore a later stop press based on elapsed time.

The autonomous navigation (updated 2026-06-11):
- Now uses individual motor.run() control instead of motor_pair for accurate distance feedback
- Follows polynomial curve: `-5.39 + 1.15x + -0.0102x² + -2.83E-04x³ + 1.12E-05x⁴ + -8.16E-08x⁵`
- Uses proportional steering control: `AUTO_KP = 3`, `AUTO_MAX_CORRECTION = 120`
- Gyro readings are consistent (uses tilt_angles, not angular velocity)
- Robot should now move forward and follow the equation curve correctly

## Workflow

1. Upload only `code/hub/main.py` to the SPIKE hub.
2. Disconnect the computer if desired.
3. Press right button to start recording.
4. Move or run the robot.
5. Press right button to stop recording.
6. Hub shows `1`.
7. Reconnect to VS Code/SPIKE console.
8. Start the collector script.
9. Press left button.
10. Hub dumps tagged log rows.
11. Collector saves a clean CSV into `code/logs/`.
12. If the collector fails, copy the plain CSV fallback printed between `CSV_START` and `CSV_END`.
13. If serial data arrives but no CSV is saved, check `code/logs/` for a `raw_serial_readable_*.txt` troubleshooting file and parse it later with `code/tools/collect_spike_logs.py --file`.

Button behavior:

- right button: start/stop recording
- left button: dump saved run to collector
- both buttons: show whether a saved run exists
- red seen by the color sensor on port `D`: start autonomous navigation

Autonomous navigation is latched so it starts once when red is first seen. The
red marker must be removed before another red trigger can start another
autonomous run.

## Persistence

The hub stores one run in memory and also writes a backup file named:

```text
robot_log.csv
```

This backup helps if the hub program restarts when reconnecting to the computer.

Starting a new recording clears and replaces the previous saved run. Dumping the
run with the left button does not clear it, so the same run can be dumped again
if the collector misses it.

The backup file includes both tagged collector rows and the plain CSV fallback
so reconnect/restart recovery still has a copy/paste path.

## Recent Debugging Context

**Session 2026-06-10:**
- The collector previously printed `info: parsed N possible log line(s) from serial data` without explaining why no CSV was saved.
- `code/tools/collect_spike_logs.py` now saves readable raw serial output to `code/logs/raw_serial_readable_*.txt` whenever serial data is received.
- If no CSV rows are saved from serial data, the collector now prints a warning and points to the raw file.
- A temporary `MIN_RECORDING_MS` stop-button lockout was rejected and removed. The current code uses stable button-release detection instead.
- `code/logs/debug.txt` from the hub was XOR-3 encoded. Decoding it showed a hub `MemoryError` in `DataLog.csv_lines()` while dumping data.
- The hub logger now streams tagged rows and plain CSV rows directly to `print()` / file writes instead of building a second large list of all output lines.
- The collector now detects and decodes XOR-3 hub output when saving/reading raw serial text.
- `robot_log_20260610_134858.csv` showed `gyro_angle` changing while `distance` stayed near `0`, and a `20 -> 1` degree gyro jump. This is poor training data for `gyro_angle = f(distance)`.
- `GyroTracker` now uses `motion_sensor.tilt_angles()` consistently instead of switching between tilt-angle yaw and integrated angular velocity mid-run.
- Autonomous steering was softened from `AUTO_KP = 6` / `AUTO_MAX_CORRECTION = 160` to `AUTO_KP = 2` / `AUTO_MAX_CORRECTION = 100`.

**Session 2026-06-11 Analysis & Fixes:**
- Analyzed robot logs: distance was always ≈0 even during clear motion. Gyro changed but distance feedback was broken.
- **Root Cause 1 - Motor Pair Encoder Bug:** Code called `motor_pair.pair()` then `motor_pair.move_tank()`, but then tried to read `motor.relative_position()` on individual motors. Motor pair APIs interfere with individual motor position reads, returning stale/zero data.
  - **Fix:** Replaced with `motor.run(port, speed)` for individual motor control. Removed `pair_drive_motors()` call.
  - **Result:** Individual encoder reads now work. Distance feedback restored to proportional steering control.
- **Root Cause 2 - Motor Direction Mismatch:** Manual arc-to-left push showed distance oscillating -1/0 instead of increasing smoothly. Both motors moved, gyro changed, but distance stayed wrong.
  - **Analysis:** RIGHT motor physically wired in opposite polarity to LEFT. Both had direction=1, so readings cancelled: `(+left + -right)/2 ≈ 0`.
  - **Fix:** Changed `RIGHT_DRIVE_MOTOR_DIRECTION` from `1` to `-1`.
  - **Result:** Distance calculation now works: `(+left + +right)/2 = true forward distance`.

## Merge Context

The local branch had the simple one-run workflow. The remote branch had better hub persistence, collector support, and improved encoder/gyro handling. The intended merged result keeps:

- one run at a time
- collector-generated CSV files in `code/logs/`
- tagged hub transfer lines for reliability
- plain console CSV fallback for manual copy/paste if the collector fails
- dense 1 ms loop delay
- hub-file backup
- robust motor and gyro helpers from the remote branch

## Git State Note

The user prefers to commit changes manually. Do not commit unless explicitly asked.

## Code Changes Session 2026-06-11

**File Modified:** `code/hub/main.py`

**Changes:**
1. Replaced `pair_drive_motors()` function with new `drive_motors(left_speed, right_speed)` function
   - Old: Used `motor_pair.pair()` and `motor_pair.move_tank()`
   - New: Uses `motor.run(port, speed)` for each motor individually
   - Motor direction multipliers now applied inside `drive_motors()` function

2. Updated `stop_drive_motors()` function
   - Old: Used `motor_pair.stop(DRIVE_PAIR)`
   - New: Uses `motor.stop(port)` for each motor individually

3. Updated `apply_proportional_drive()` function
   - Old: Applied direction multipliers, then called `motor_pair.move_tank()`
   - New: Calls `drive_motors(left_speed, right_speed)` which handles direction multipliers

4. Removed `pair_drive_motors()` call from `run_autonomous_navigation()`
   - No longer needed since individual motors are controlled directly

5. Changed motor direction configuration
   - `RIGHT_DRIVE_MOTOR_DIRECTION` changed from `1` to `-1`
   - Compensates for opposite physical wiring of the drive motors

## Expected Behavior After Upload

1. **Manual Datalogging:** Push robot forward → distance increases smoothly (not 0/-1 bouncing)
2. **Arc Movement:** Push in arc → distance increases + gyro changes show curved path
3. **Autonomous:** Show red → robot moves forward following equation curve (not erratic)
