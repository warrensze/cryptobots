# Session Recovery Context

## Date

2026-06-08

## Project

Standalone repository:

```text
/Users/warren/LegoLeagueAutoDrive/cryptobots
```

Original reference repository:

```text
/Users/warren/LegoLeagueAutoDrive/public.superpowered2022
```

The original SuperPowered repository is now only historical/reference context. The active project is the standalone `cryptobots` repo.

Current key file:

```text
code/hub/main.py
```

The user wants a LEGO SPIKE Prime datalogging workflow using stock LEGO SPIKE Prime MicroPython and Visual Studio Code, without Pybricks.

## What Was Reviewed

The project currently has:

- `src/main.py`
- `src/robot.py`
- `src/missions.py`
- `tests/test_datalog.py`
- other navigation tests and resources

Important finding:

The codebase is EV3/Pybricks-oriented. It imports `pybricks.*`, uses EV3 screen/buttons/lights, uses `DriveBase`, and uses Pybricks `DataLog`.

Useful existing ideas:

- `src/robot.py` creates a global datalog with robot state columns.
- `tests/test_datalog.py` contains useful experiments for turn logging, drive-straight logging, motor logging, and path logging.

## Decisions So Far

Do not overwrite the current EV3/Pybricks project.

The SPIKE-specific implementation now lives in its own standalone repo:

```text
/Users/warren/LegoLeagueAutoDrive/cryptobots
```

It was moved out of `/Users/warren/LegoLeagueAutoDrive/public.superpowered2022` so it cannot be accidentally committed to the original repo.

Local git state as of the move:

```text
branch: main
commit: eb21777 Initial SPIKE datalogging kit
remote: not set yet
```

The user still needs to create/provide a GitHub repository URL before pushing.

## Desired Datalogging Behavior

The team wants convenient data collection without watching the console.

Preferred workflow:

1. Upload logging program to the SPIKE Prime hub.
2. Disconnect computer.
3. Press a hub button to start gyro/motion logging.
4. Move the robot manually.
5. Press a hub button to stop logging.
6. Store data on the hub in memory.
7. Connect computer only at the end.
8. Trigger a dump/download from the hub.
9. Computer script saves CSV files automatically.

Important caveat:

The first design should assume RAM-based storage on the hub, not persistent file storage. If the hub powers off or resets before download, logs may be lost.

## Proposed Components

Hub-side:

- custom `DataLog` class
- optional `LogSession` class for multiple runs
- clean output markers: `LOG_START,<name>` and `LOG_END,<name>`
- CSV headers and rows
- button-triggered download/dump

Computer-side:

- `cryptobots/code/tools/collect_spike_logs.py`
- listens to hub output
- detects log blocks
- writes CSV files under `cryptobots/code/logs/`

## Implemented Files

The current implementation contains:

```text
code/README.md
code/hub/logger.py
code/hub/main.py
code/hub/manual_gyro_logger.py
code/hub/drive_log_example.py
code/tools/collect_spike_logs.py
code/tools/sample_hub_output.txt
manual-gyro-datalogging-steps.md
```

`hub/main.py` defines `DataLog` and `LogSession` inside the same file so only one program must be uploaded to the hub. `hub/logger.py` is only a reference copy.

`hub/main.py` is now the recommended graphing logger:

- right button: start recording
- right button again: stop recording
- left button: dump/download saved logs after connecting the computer
- both buttons: clear saved logs

Important: the SPIKE upload flow can only upload one hub program. Upload only `code/hub/main.py` for the recommended workflow.

It records:

- `time_ms`
- `distance_mm`
- `gyro_angle_deg`

The target sampling interval is 5 ms. Actual timing may be slightly slower depending on hub runtime overhead.

`tools/collect_spike_logs.py` can parse a saved output file, stdin, or a serial port if the user's SPIKE setup exposes one.

## Proposed Logger API

```python
log = DataLog(
    "time_ms",
    "distance_mm",
    "gyro_angle_deg",
    name="manual_gyro",
    max_rows=3000
)

log.log(time_ms, distance_mm, gyro_angle_deg)
log.dump()
```

## Proposed Output Format

```csv
LOG_START,manual_gyro_1
time_ms,distance_mm,gyro_angle_deg
0,0,0
5,1,0
10,2,1
LOG_END,manual_gyro_1
```

## Current Documentation Added

This folder now contains:

- `spike-prime-datalogging-plan.md`
- `session-recovery-context.md`
- `prompt-history.md`

The implementation documentation is in:

- `code/README.md`
- `manual-gyro-datalogging-steps.md`

## User Preferences From This Session

- Use stock LEGO SPIKE Prime MicroPython.
- Do not use Pybricks.
- Use Visual Studio Code.
- Keep the original EV3/Pybricks code untouched.
- Keep `cryptobots` disconnected from the original SuperPowered repo.
- Put implementation code under `code/`.
