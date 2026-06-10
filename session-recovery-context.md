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
WHEEL_CIRCUMFERENCE_MM = 176
```

Valid SPIKE Prime motor ports are `port.A` through `port.F`.

There is no intentional recording time limit. The right button starts and stops
recording. The code waits for a stable release after the start press so the
same press is not reused as the stop press, but it does not ignore a later stop
press based on elapsed time.

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
- both buttons: clear saved run and hub backup file

## Persistence

The hub stores one run in memory and also writes a backup file named:

```text
robot_log.csv
```

This backup helps if the hub program restarts when reconnecting to the computer.

Starting a new recording replaces the previous saved run.

The backup file includes both tagged collector rows and the plain CSV fallback
so reconnect/restart recovery still has a copy/paste path.

## Recent Debugging Context

- The collector previously printed `info: parsed N possible log line(s) from serial data` without explaining why no CSV was saved.
- `code/tools/collect_spike_logs.py` now saves readable raw serial output to `code/logs/raw_serial_readable_*.txt` whenever serial data is received.
- If no CSV rows are saved from serial data, the collector now prints a warning and points to the raw file.
- A temporary `MIN_RECORDING_MS` stop-button lockout was rejected and removed. The current code uses stable button-release detection instead.

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
