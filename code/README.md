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

`hub/main.py` is the only file you need to upload to the SPIKE hub for the recommended workflow. It records the three graphing columns needed for the Pybricks-style movement analysis: time, estimated distance, and gyro angle.

It includes its own copy of:

- `DataLog`: stores CSV rows in memory and dumps them later
- `LogSession`: stores several completed `DataLog` objects until download time

Button controls:

- right button: start recording
- right button again: stop recording
- left button: dump saved logs after the computer is connected
- both buttons: clear saved logs

Light matrix codes:

- `S`: standing by, ready to start
- `R`: recording
- `0` to `5`: number of saved logs
- `U`: dumping logs to the computer

`hub/logger.py` is now only a readable reference copy of the logger design. Do not upload it separately for this workflow.

`hub/manual_gyro_logger.py` is an even smaller one-shot version. It is also self-contained, starts with the right button, stops with the right button, and immediately dumps one log. Use this if you do not need to store several logs before download.

`hub/drive_log_example.py` is an older motor-driven example for testing the logger with drive motors.

## Recommended Workflow

1. Upload only `hub/main.py` to the SPIKE hub.
2. Press both hub buttons once to clear old saved logs. The hub shows `0`.
3. Disconnect the computer if you want to collect data away from it.
4. Press the right button. The hub shows `R`.
5. Move the robot by hand. Turn it, push it, rotate it, or test the path you care about.
6. Press the right button again. The hub shows the number of saved logs.
7. Repeat steps 4-6 if you want more recordings. Up to 5 are stored.
8. Plug the hub back into the computer.
9. Start the collector script.
10. Press the left button on the hub. The hub shows `U` and dumps the saved data.
11. CSV files appear in `code/logs/`.

The CSV columns are:

```text
time_ms,distance_mm,gyro_angle_deg
```

These columns are intended for graphing and equation fitting:

- `time_ms`: elapsed time
- `distance_mm`: estimated robot travel distance from the wheel motor encoders
- `gyro_angle_deg`: hub yaw angle converted from SPIKE decidegrees to degrees

The default robot configuration is:

```text
left drive motor = port B
right drive motor = port F
```

If `distance_mm` stays at `0`, confirm that the drive motors are really plugged into ports B and F and that the wheels are actually turning while you move the robot. If `gyro_angle_deg` stays at `0`, the code now sets the yaw face to `motion_sensor.TOP`; if your hub is mounted on a different face, update `YAW_FACE` near the top of `hub/main.py`.

## Collector Usage

If your setup exposes hub output as a serial port:

```bash
python3 code/tools/collect_spike_logs.py --port /dev/cu.usbmodemXXXX
```

On Windows, the port may look like:

```bash
python code/tools/collect_spike_logs.py --port COM5
```

If you have saved hub output to a text file, parse it afterward:

```bash
python3 code/tools/collect_spike_logs.py --file hub-output.txt
```

The hub transfer uses `CBLOG_HEADER` and `CBLOG_ROW` prefixes so the collector can ignore USB/protocol noise:

```csv
LOG_START,manual_gyro_1
CBLOG_HEADER,time_ms,distance_mm,gyro_angle_deg
CBLOG_ROW,0,0,0
CBLOG_ROW,5,1,0
CBLOG_ROW,10,2,1
LOG_END,manual_gyro_1
```

The collector saves a clean Google Sheets-friendly CSV named `robot_log_...csv` with only:

```csv
time_ms,distance_mm,gyro_angle_deg
0,0,0
5,1,0
10,2,1
```

Import `robot_log_...csv` into Google Sheets. Ignore any older `raw_serial_...txt`, `parsed_serial_...txt`, or `parsed_serial_...csv` files from previous collector versions.

## Important Limit

The hub stores logs in memory. Download the data before powering off or resetting the hub.

Start with short tests. The current `SAMPLE_MS = 5`, so the hub tries to collect about 200 rows per second. The default `MAX_ROWS_PER_LOG = 3000` is about 15 seconds of data per recording at the target rate.

## Notes

This code targets the SPIKE 3 style MicroPython API, which uses modules such as:

- `hub.button`
- `hub.light_matrix`
- `hub.motion_sensor`
- `runloop`
