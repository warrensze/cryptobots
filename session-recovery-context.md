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

The user wants a LEGO SPIKE Prime datalogging workflow using stock LEGO SPIKE Prime MicroPython and Visual Studio Code, without Pybricks. The latest target is to mimic the original Pybricks `DataLog` spreadsheet format with exactly these saved CSV columns:

```csv
time,distance,gyro_angle
```

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
3. Press a hub button to start datalogging.
4. Move the robot manually while the drive wheels turn the motor encoders.
5. Press a hub button to stop logging.
6. Store one run on the hub in memory.
7. Connect computer only at the end if needed.
8. Press left button to print plain CSV in the VS Code console.
9. Copy/paste the CSV directly.

Important caveat:

The first design should assume RAM-based storage on the hub, not persistent file storage. If the hub powers off or resets before download, logs may be lost.

## Proposed Components

Hub-side:

- custom `DataLog` class
- one saved run at a time
- plain CSV headers and rows
- button-triggered console print

Computer-side:

- VS Code/SPIKE console output
- copy/paste from `time,distance,gyro_angle` through the last row
- `code/tools/collect_spike_logs.py` remains in the repo as an older optional helper, but it is no longer required for the normal one-run workflow

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

`hub/main.py` defines `DataLog` inside the same file so only one program must be uploaded to the hub. `hub/logger.py` is only a reference copy.

`hub/main.py` is now the recommended manual gyro logger:

- right button: start recording
- right button again: stop recording
- left button: print plain CSV to the VS Code console
- both buttons: clear saved run

Important: the SPIKE upload flow can only upload one hub program. Upload only `code/hub/main.py` for the recommended workflow.

It records:

- `time`
- `distance`
- `gyro_angle`

The normal workflow no longer needs `tools/collect_spike_logs.py` because the hub prints plain CSV for one run at a time.

## Proposed Logger API

```python
log = DataLog(
    "time",
    "distance",
    "gyro_angle",
    name="log_robot",
    max_rows=8000
)

log.log(time_ms, distance_mm, gyro_angle)
log.dump()
```

## Proposed Output Format

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

## Current Documentation Added

This folder now contains:

- `spike-prime-datalogging-plan.md`
- `session-recovery-context.md`
- `prompt-history.md`

The implementation documentation is in:

- `code/README.md`
- `manual-gyro-datalogging-steps.md`

Sampling rate:

- `SAMPLE_MS = 1`
- `MAX_ROWS_PER_LOG = 8000`
- This is tuned for short 2-3 second routes and aims to be as dense as practical on stock SPIKE MicroPython.

## User Preferences From This Session

- Use stock LEGO SPIKE Prime MicroPython.
- Do not use Pybricks.
- Use Visual Studio Code.
- Keep the original EV3/Pybricks code untouched.
- Keep `cryptobots` disconnected from the original SuperPowered repo.
- Put implementation code under `code/`.
