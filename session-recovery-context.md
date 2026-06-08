# Session Recovery Context

## Date

2026-06-08

## Project

Repository:

```text
/Users/warren/LegoLeagueAutoDrive/public.superpowered2022
```

Active IDE file:

```text
src/main.py
```

The user wants to adapt the SuperPowered 2022 robot project toward a LEGO SPIKE Prime datalogging workflow using stock LEGO SPIKE Prime MicroPython and Visual Studio Code, without Pybricks.

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

The SPIKE-specific implementation now lives under:

```text
cryptobots/code/
```

The user first clarified that the work was planning/documentation only, then later asked to proceed with the plan while keeping all new code in a code subfolder under `cryptobots`.

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
cryptobots/code/README.md
cryptobots/code/hub/logger.py
cryptobots/code/hub/main.py
cryptobots/code/hub/manual_gyro_logger.py
cryptobots/code/hub/drive_log_example.py
cryptobots/code/tools/collect_spike_logs.py
cryptobots/code/tools/sample_hub_output.txt
cryptobots/manual-gyro-datalogging-steps.md
```

`hub/main.py` defines `DataLog` and `LogSession` inside the same file so only one program must be uploaded to the hub. `hub/logger.py` is only a reference copy.

`hub/main.py` is now the recommended manual gyro logger:

- right button: start recording
- right button again: stop recording
- left button: dump/download saved logs after connecting the computer
- both buttons: clear saved logs

Important: the SPIKE upload flow can only upload one hub program. Upload only `cryptobots/code/hub/main.py` for the recommended workflow.

It records:

- `time_ms`
- `yaw_ddeg`
- `pitch_ddeg`
- `roll_ddeg`
- `x_rate_ddeg_s`
- `y_rate_ddeg_s`
- `z_rate_ddeg_s`
- `event`

`tools/collect_spike_logs.py` can parse a saved output file, stdin, or a serial port if the user's SPIKE setup exposes one.

## Proposed Logger API

```python
log = DataLog(
    "time_ms",
    "yaw_ddeg",
    "pitch_ddeg",
    "roll_ddeg",
    name="manual_gyro",
    max_rows=1200
)

log.log(time_ms, yaw_ddeg, pitch_ddeg, roll_ddeg)
log.dump()
```

## Proposed Output Format

```csv
LOG_START,manual_gyro_1
time_ms,yaw_ddeg,pitch_ddeg,roll_ddeg,x_rate_ddeg_s,y_rate_ddeg_s,z_rate_ddeg_s,event
0,0,0,0,0,0,0,start
50,12,0,1,240,0,10,record
100,25,0,1,260,0,10,record
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
- Put new implementation code under `cryptobots/code`.
