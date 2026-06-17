# SPIKE Prime Datalogging Plan

> **Note (2026-06-17):** A parallel Pybricks track has been planned. See `session-recovery-context.md` → "Session 2026-06-17 — Pybricks Datalogging Planning Direction" for the full analysis. The Pybricks version ports the datalogging infrastructure from `code/hub/main.py` into `code/hub/pybricks_datalog.py`, adapted to the Pybricks API while preserving the exact same output format. This file documents the original stock-SPIKE plan; the Pybricks plan is tracked in the session context.

## Goal

Create a datalogging workflow for a LEGO SPIKE Prime robot using regular LEGO SPIKE Prime MicroPython and Visual Studio Code, without Pybricks.

The team wants behavior similar to the Pybricks `DataLog` examples in the existing SuperPowered 2022 project, but adapted for stock SPIKE Prime.

## Current Project Context

The current project is EV3 and Pybricks based.

Important files:

- `src/main.py`: EV3/Pybricks mission menu using EV3 screen, buttons, and Pybricks imports.
- `src/robot.py`: EV3/Pybricks robot abstraction. It creates a Pybricks `DataLog` for time, distance, gyro angle, color reflection, and motor speed.
- `tests/test_datalog.py`: Useful reference examples for drive, turn, motor, and smooth-drive logging experiments.

Do not try to run the existing EV3/Pybricks code directly on stock SPIKE Prime firmware. Instead, create a SPIKE-specific implementation alongside it.

## Recommended Folder Structure

Keep the original EV3 code untouched and add SPIKE-specific files separately:

```text
src_spike/
  logger.py
  main.py
  drive_log_example.py
  turn_log_example.py

tools/
  collect_spike_log.py

logs/
  generated CSV files
```

## Main Design

Use two layers:

1. Hub-side logger
2. Computer-side collector

The hub records rows during robot movement and stores them in memory. The computer is only needed at the end, when the team wants to download the data.

## Hub-Side Logger

Create a small `DataLog`-style class for stock SPIKE MicroPython.

Responsibilities:

- define CSV headers
- collect rows while the robot runs
- avoid printing during movement
- dump clean machine-readable log blocks at the end
- support a maximum row count so memory does not grow forever

Example hub-side API:

```python
log = DataLog(
    "time_ms",
    "distance_mm",
    "gyro_angle_deg",
    name="drive_test",
    max_rows=3000
)

log.log(time_ms, distance_mm, gyro_angle_deg)
log.dump()
```

Example output:

```csv
LOG_START,drive_test
time_ms,distance_mm,gyro_angle_deg
0,0,0
5,1,0
10,2,1
LOG_END,drive_test
```

## Session Logger

For the "computer only at the end" workflow, add a session object that can store multiple logs in memory:

```python
session = LogSession(max_logs=5)
session.add(log)
session.dump_all()
session.clear()
```

Hub controls could be:

- left button: choose test
- right button: run selected test
- both buttons: dump all saved logs for download

The hub can show the number of saved logs on the light matrix after each run.

## Computer-Side Collector

Create a Python script on the laptop that listens to the hub output and saves logs automatically.

Responsibilities:

- connect to the SPIKE hub over USB serial or Bluetooth, depending on the final VS Code setup
- listen for text output
- detect `LOG_START` and `LOG_END`
- write each completed block to a CSV file
- save files under `logs/`

Example generated filename:

```text
logs/drive_test_2026-06-08_153012.csv
```

## Recommended Team Workflow

1. Upload the single-file SPIKE logging program to the hub.
2. Disconnect the computer.
3. Run one or more tests from the hub.
4. The hub stores completed logs in memory.
5. Reconnect the computer at the end.
6. Start the collector script.
7. Press the hub download button combination.
8. CSV files are saved automatically.
9. Open the CSV files in Excel, Google Sheets, Numbers, or Python.

## Important Limitation

This first design stores logs in hub RAM, not permanent hub storage.

That means:

- The computer does not need to be connected while testing.
- The hub must remain powered until the logs are downloaded.
- If the hub turns off, resets, or the program crashes, unsaved logs can be lost.

This is still a good fit for FLL testing because the normal workflow is run, return to base/table, connect, download, and graph.

## Sampling Recommendation

For equation fitting and graphs similar to the original datalogging example, use a faster sampling interval of 5-9 ms.

Current default:

```text
5 ms = target of about 200 rows per second
10 second run = about 2000 rows
```

Actual timing may be a little slower because the hub has to read sensors and store rows. Keep test runs short at this speed because rows are stored in hub RAM.

## Suggested Columns

Start with:

- `time_ms`
- `distance_mm`
- `gyro_angle_deg`

Later add calculated values:

- `left_deg`
- `right_deg`
- `left_speed`
- `right_speed`
- `target_yaw`
- `error`
- `correction`

## First Programs To Build

Build small experiments before integrating into full mission code:

1. `drive_log_example.py`: drive straight and log yaw, motor position, and color reflection.
2. `turn_log_example.py`: turn to a target yaw and log error over time.
3. `line_square_log_example.py`: drive until each color sensor sees a line and log sensor values.

These correspond to the useful ideas already present in `tests/test_datalog.py`.

## API Mapping From Pybricks To Stock SPIKE

Approximate mapping:

- Pybricks `DataLog` -> custom `DataLog`
- Pybricks `StopWatch` -> `time.ticks_ms()` and `time.ticks_diff()`
- Pybricks `DriveBase` -> `motor_pair`
- EV3 gyro sensor -> SPIKE hub motion sensor yaw/tilt reading
- EV3 color sensor -> SPIKE color sensor reflection
- EV3 screen menu -> SPIKE light matrix and buttons
- Pybricks `run_parallel` -> `runloop` async functions where needed

## Open Questions

- Which SPIKE firmware/API version is installed on the hub?
- Which VS Code extension or upload tool will the team use?
- Do we want USB serial collection first, Bluetooth collection first, or both?
- What are the actual SPIKE Prime port assignments for the robot?
- How many test runs should the hub store before requiring download?

## Next Implementation Step

When ready to code, create:

- `src_spike/logger.py`
- `src_spike/drive_log_example.py`
- `tools/collect_spike_log.py`

Start with a RAM-based logger and a manual dump button. Add automatic collector behavior after the hub output format is stable.
