---
name: cryptobots-spike-prime-datalogging
description: Use when working on the cryptobots LEGO SPIKE Prime MicroPython project, including datalogging, hub serial collection, autonomous path replay from logged distance/gyro data, equation tuning, and Git sync for the standalone cryptobots repo.
---

# Cryptobots SPIKE Prime Datalogging Skill

## First Rules

- Work in `/Users/warren/LegoLeagueAutoDrive/cryptobots`.
- Do not edit `/Users/warren/LegoLeagueAutoDrive/public.superpowered2022` unless the user explicitly asks; it is historical/reference context only.
- The active hub program is `code/hub/main.py`.
- The hub can upload one program, so keep required hub behavior in `code/hub/main.py`.
- Use stock LEGO SPIKE Prime MicroPython, not Pybricks.
- Do not commit unless the user explicitly asks. The user often wants to commit manually.

## Read First

Before changing behavior, inspect these files:

- `session-recovery-context.md` for current project state and prior debugging.
- `code/README.md` for user-facing workflow.
- `code/hub/main.py` for actual hub behavior.
- `code/logs/equation*.txt` for autonomous path equations.
- Recent logs in `code/logs/`, especially `robot_log_*.csv` and `raw_serial_readable_*.txt`.

Treat docs as helpful but not authoritative. If docs and `main.py` disagree, verify with code and update the docs.

## Current Hub Behavior

`code/hub/main.py` provides both datalogging and autonomous navigation.

Controls:

- Right button: start manual datalogging.
- Right button again: stop manual datalogging.
- Left button: dump the saved run to the console/collector.
- Both buttons: show whether a saved run exists.
- Color sensor on `port.D` sees red: start autonomous navigation.

Light matrix:

- `S`: standby.
- `R`: recording.
- `A`: autonomous navigation running.
- `1`: saved data exists / run saved.
- `0`: no saved data found.
- `U`: dumping data.

Saved data stays available after dumping. A new recording clears/replaces the previous saved run.

## CSV Contract

Manual datalog CSV must stay exactly:

```csv
time,distance,gyro_angle
```

Units:

- `time`: milliseconds from start.
- `distance`: millimeters from drive motor encoders.
- `gyro_angle`: degrees from hub yaw.

Autonomous debug CSV should include:

```csv
time,distance,gyro_angle,target_angle,error,correction
```

Do not casually rename columns. Google Sheets compatibility matters.

## Hub Memory Constraints

The SPIKE hub has limited memory. Avoid building large duplicate lists of log lines.

Required pattern:

- Store only the rows needed for the active saved run.
- When dumping or persisting, stream rows line by line to `print()` or file writes.
- Keep both tagged collector rows and plain CSV fallback output.

Avoid returning a huge `dump_lines()` list. A previous version crashed with `MemoryError` while building `csv_lines()`.

## Collector Behavior

Computer-side collector: `code/tools/collect_spike_logs.py`.

It should:

- Save clean CSVs into `code/logs/`.
- Parse tagged rows like `CBLOG_ROW,...`.
- Preserve both 3-column manual logs and 6-column autonomous debug logs.
- Save raw readable serial text as `raw_serial_readable_*.txt` when serial data arrives.
- Decode XOR-3 hub output when needed.
- Give useful warnings if serial data arrives but no CSV rows are found.

Test with:

```bash
python3 code/tools/collect_spike_logs.py --file code/tools/sample_hub_output.txt --log-dir /private/tmp/cryptobots-check
```

## Autonomous Equation Rules

Autonomous path replay uses `gyro_angle = f(distance)`.

Current code points to `code/logs/equation2.txt`; verify the active equation in `main.py` before editing. There may also be `equation.txt` from older runs.

Important:

- `main.py` hardcodes the polynomial; it does not dynamically read `equation*.txt` on the hub.
- If the equation file changes, update `raw_target_angle_for_distance()` and the comment/settings near the top of `main.py`.
- The target heading is relative: subtract the polynomial value at distance `0` so the run starts at target angle `0` after gyro reset.
- Clamp the polynomial input to the training distance range when configured.
- If the robot corrects the wrong direction, try `AUTO_STEERING_DIRECTION = -1`.
- If it wiggles, lower `AUTO_KP` or `AUTO_MAX_CORRECTION`.

A path equation is only good if training data is good. Bad signs:

- `gyro_angle` changes a lot while `distance` stays near `0`.
- Distance jumps backward/forward due to wheel slip or manual twisting.
- Multiple very different gyro angles exist for the same distance.

For a clean training run, the robot should start still, then roll on its drive wheels along the path. Avoid pivoting in place before distance increases.

## Sensor/Port Configuration

Current defaults live near the top of `code/hub/main.py`:

```python
LEFT_DRIVE_MOTOR_PORT = port.B
RIGHT_DRIVE_MOTOR_PORT = port.F
AUTONOMOUS_START_SENSOR_PORT = port.D
WHEEL_CIRCUMFERENCE_MM = 176
```

If distance is negative or near zero while wheels roll forward, adjust:

```python
LEFT_DRIVE_MOTOR_DIRECTION
RIGHT_DRIVE_MOTOR_DIRECTION
```

If `gyro_angle` stays zero while turning, inspect `YAW_FACE`.

`GyroTracker` should use one source consistently. Avoid switching between `motion_sensor.tilt_angles()` and integrated angular velocity mid-run unless carefully designed; that caused impossible jumps in past logs.

## Analysis Workflow

When the robot behaves badly:

1. Inspect the latest `robot_log_*.csv`.
2. Confirm whether it is a manual 3-column log or autonomous 6-column debug log.
3. Compute min/max and key samples for `distance` and `gyro_angle`.
4. Check whether distance increases smoothly.
5. Compare the active equation curve to the data.
6. Compute controller corrections from `AUTO_KP`, `AUTO_MAX_CORRECTION`, and `AUTO_STEERING_DIRECTION`.
7. Recommend one small robot test at a time.

Prefer boring, repeatable robot strategies over clever curves when reliability is poor:

- Segment drive: straight, turn-to-angle, straight.
- Gyro-hold straight sections.
- Turn-to-angle for major direction changes.
- Slower speed with lower correction cap.
- Physical alignment aids at launch.

## Validation

After code changes, run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/cryptobots-pycache python3 -m py_compile code/hub/main.py code/tools/collect_spike_logs.py
python3 code/tools/collect_spike_logs.py --file code/tools/sample_hub_output.txt --log-dir /private/tmp/cryptobots-check
git diff --check
```

If testing writes under `.git` or needs network/push/pull, elevated permission may be required.

## Git

This is a standalone Git repo with remote:

```text
https://github.com/warrensze/cryptobots.git
```

For sync issues:

- Check `git status --short --branch`.
- If `ahead` and `behind`, merge remote changes with `git pull --no-rebase --no-edit`.
- Resolve conflicts only in `cryptobots`.
- Push only when the user asks or when fixing an explicit sync problem.

Do not reset or discard user changes unless explicitly asked.
