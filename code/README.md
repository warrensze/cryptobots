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

`hub/main.py` is the only file you need to upload to the SPIKE hub for the recommended workflow. It records the hub gyro/motion sensor while a user moves the robot by hand.

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
2. Disconnect the computer if you want to collect data away from it.
3. Press the right button. The hub shows `R`.
4. Move the robot by hand. Turn it, push it, rotate it, or test the path you care about.
5. Press the right button again. The hub shows the number of saved logs.
6. Repeat steps 3-5 if you want more recordings. Up to 5 are stored.
7. Plug the hub back into the computer.
8. Start the collector script.
9. Press the left button on the hub. The hub shows `U` and dumps the saved data.
10. CSV files appear in `code/logs/`.

The CSV columns are:

```text
time_ms,yaw_ddeg,pitch_ddeg,roll_ddeg,x_rate_ddeg_s,y_rate_ddeg_s,z_rate_ddeg_s,event
```

SPIKE reports angles in decidegrees. Divide by 10 to get degrees.

Example:

```text
yaw_ddeg = 450 means yaw = 45.0 degrees
```

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

The collector looks for blocks like this:

```csv
LOG_START,manual_gyro_1
time_ms,yaw_ddeg,pitch_ddeg,roll_ddeg,x_rate_ddeg_s,y_rate_ddeg_s,z_rate_ddeg_s,event
0,0,0,0,0,0,0,start
50,12,0,1,240,0,10,record
100,25,0,1,260,0,10,record
LOG_END,manual_gyro_1
```

It saves only the CSV headers and rows, without the `LOG_START` and `LOG_END` marker lines.

## Important Limit

The hub stores logs in memory. Download the data before powering off or resetting the hub.

Start with short tests and `SAMPLE_MS = 50`. The default `MAX_ROWS_PER_LOG = 1200` is about one minute of data per recording.

## Notes

This code targets the SPIKE 3 style MicroPython API, which uses modules such as:

- `hub.button`
- `hub.light_matrix`
- `hub.motion_sensor`
- `runloop`
