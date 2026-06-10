# Session Recovery Context

## Date

2026-06-10

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

The current `code/hub/main.py` is a one-file hub upload.

It records:

- `time`
- `distance`
- `gyro_angle`

It uses:

- `time.ticks_ms()` / `time.ticks_diff()` for milliseconds
- drive motor encoders for estimated distance
- hub yaw for gyro angle
- `SAMPLE_MS = 1` for dense short-route logging
- `MAX_ROWS_PER_LOG = 8000`
- stable button-release detection before arming the next button action

The active program has a `ROBOT CONFIGURATION` section near the top. Default robot constants:

```python
LEFT_DRIVE_MOTOR_PORT = port.B
RIGHT_DRIVE_MOTOR_PORT = port.F
LEFT_DRIVE_MOTOR_DIRECTION = 1
RIGHT_DRIVE_MOTOR_DIRECTION = 1
AUTONOMOUS_START_SENSOR_PORT = port.D
WHEEL_CIRCUMFERENCE_MM = 176
```

Valid SPIKE Prime motor ports are `port.A` through `port.F`.

There is no intentional recording time limit. The right button starts and stops
recording. The code waits for a stable release after the start press so the
same press is not reused as the stop press, but it does not ignore a later stop
press based on elapsed time.

The autonomous equation is treated as a relative heading curve. The polynomial
value at distance `0` is subtracted so the autonomous run starts from target
angle `0` after the gyro is reset.

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
