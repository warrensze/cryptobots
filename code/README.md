# Cryptobots SPIKE Datalogging Code

This folder contains a starter datalogging kit for LEGO SPIKE Prime using stock LEGO SPIKE MicroPython. It does not use Pybricks and does not modify the original EV3/Pybricks SuperPowered code.

## Repository

This project is a standalone git repo at:

```text
/Users/warren/LegoLeagueAutoDrive/cryptobots
```

It was moved out of the original SuperPowered repo so commits and pushes happen only from this project.

Initial local commit:

```text
eb21777 Initial SPIKE datalogging kit
```

A GitHub remote has not been added yet.

## Folder Layout

```text
code/
  hub/
    main.py
    logger.py
    manual_gyro_logger.py
    drive_log_example.py
  tools/
    collect_spike_logs.py
  logs/
    generated CSV files
```

## Hub Files

`hub/main.py` is the only file you need to upload to the SPIKE hub for the recommended workflow. It records the same basic CSV columns shown in the original SuperPowered Pybricks `DataLog` spreadsheet:

```csv
time,distance,gyro_angle
```

It includes its own copy of:

- `DataLog`: stores CSV rows in memory and dumps them later

Button controls:

- right button: start recording
- right button again: stop recording
- left button: print the saved CSV to the VS Code console
- both buttons: clear the saved run

Light matrix codes:

- `S`: standing by, ready to start
- `R`: recording
- `1`: one run is saved
- `0`: no run is saved
- `U`: printing CSV to the console

`hub/logger.py` is now only a readable reference copy of the logger design. Do not upload it separately for this workflow.

`hub/manual_gyro_logger.py` is an even smaller one-shot version. It is also self-contained, starts with the right button, stops with the right button, and immediately dumps one log. Use this if you do not need to store several logs before download.

`hub/drive_log_example.py` is an older motor-driven example for testing the logger with drive motors.

## Recommended Workflow

1. In `hub/main.py`, check the drive motor ports and wheel size.
2. Upload only `hub/main.py` to the SPIKE hub.
3. Disconnect the computer if you want to collect data away from it.
4. Press the right button. The hub shows `R`.
5. Move the robot by hand. Distance is calculated from the drive motor encoders, so the drive wheels must turn.
6. Press the right button again. The hub shows `1`, meaning one run is saved.
7. Plug the hub back into the computer if it was disconnected.
8. Open the SPIKE/VS Code console output.
9. Press the left button on the hub. The hub shows `U` and prints the CSV.
10. Copy from the `time,distance,gyro_angle` header through the last data row.
11. Paste directly into Google Sheets, Excel, Numbers, or a `.csv` file.

## Robot Setup

The default hub code assumes:

```python
LEFT_MOTOR = port.A
RIGHT_MOTOR = port.B
WHEEL_DIAMETER_MM = 56
```

If distance is negative or stays near zero while the robot moves forward, change one motor direction:

```python
LEFT_MOTOR_DIRECTION = 1
RIGHT_MOTOR_DIRECTION = -1
```

## CSV Format

The saved CSV columns are exactly:

```text
time,distance,gyro_angle
```

Example saved CSV:

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

`time` is milliseconds from the start of the recording.
`distance` is millimeters calculated from the drive motor encoders.
`gyro_angle` is hub yaw in degrees.

## Copy/Paste Output

Because the team is doing one run at a time, the hub prints plain CSV with no wrapper lines:

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

The old collector script is still in `code/tools/collect_spike_logs.py`, but the normal workflow no longer needs it.

## Important Limit

The hub stores one run in memory. Copy the data before powering off or resetting the hub. Starting a new recording replaces the previous saved run.

The logger uses `SAMPLE_MS = 1` to collect dense data for short 2-3 second FLL paths. The real row spacing will be limited by SPIKE sensor reads and MicroPython loop overhead, but this is intentionally tuned to be as close as practical to the original Pybricks `DataLog` density.

The default `MAX_ROWS_PER_LOG = 8000` is sized for short route recordings.

## Notes

This code targets the SPIKE 3 style MicroPython API, which uses modules such as:

- `hub.button`
- `hub.light_matrix`
- `hub.motion_sensor`
- `hub.port`
- `motor`
- `runloop`
