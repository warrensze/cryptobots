# Cryptobots SPIKE Datalogging Code

This folder contains a starter datalogging kit for LEGO SPIKE Prime using stock LEGO SPIKE MicroPython. It does not use Pybricks and does not modify the original EV3/Pybricks SuperPowered code.

## Repository

This project is a standalone git repo at:

```text
/Users/warren/LegoLeagueAutoDrive/cryptobots
```

It was moved out of the original SuperPowered repo so commits and pushes happen only from this project.

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
    optional generated CSV files
```

## Hub File

`hub/main.py` is the only file you need to upload to the SPIKE hub for the recommended workflow. It dumps tagged log rows that the collector turns into a spreadsheet-friendly CSV:

```csv
time,distance,gyro_angle
```

Button controls:

- right button: start recording
- right button again: stop recording
- left button: dump the saved run so the collector can save a CSV
- both buttons: clear the saved run

Light matrix codes:

- `S`: standing by, ready to start
- `R`: recording
- `1`: one run is saved
- `0`: no run is saved
- `U`: dumping data to the collector

## Recommended Workflow

1. In `hub/main.py`, check the drive motor ports and wheel size.
2. Upload only `hub/main.py` to the SPIKE hub.
3. Disconnect the computer if you want to collect data away from it.
4. Press the right button. The hub shows `R`.
5. Move or run the robot. Distance is calculated from the drive motor encoders, so the drive wheels must turn.
6. Press the right button again. The hub shows `1`, meaning one run is saved.
7. Plug the hub back into the computer if it was disconnected.
8. Start the collector script.
9. Press the left button on the hub. The hub shows `U` and dumps the saved data.
10. A clean CSV appears in `code/logs/`.

If the collector fails, the hub also prints a plain CSV fallback between `CSV_START` and `CSV_END` in the console. Copy the lines between those markers, starting with `time,distance,gyro_angle`, and paste them into Sheets, Excel, Numbers, or a `.csv` file.

## Robot Setup

The default hub code assumes the current team robot setup:

```python
LEFT_MOTOR = port.B
RIGHT_MOTOR = port.F
WHEEL_CIRCUMFERENCE_MM = 176
```

If distance is negative or stays near zero while the robot moves forward, change one motor direction:

```python
LEFT_MOTOR_DIRECTION = 1
RIGHT_MOTOR_DIRECTION = -1
```

If `gyro_angle` stays at `0` while turning, update `YAW_FACE` near the top of `hub/main.py`.

## Collector Usage

If your setup exposes hub output as a serial port:

```bash
python3 code/tools/collect_spike_logs.py --port /dev/cu.usbmodemXXXX
```

On Windows, the port may look like:

```bash
python code/tools/collect_spike_logs.py --port COM5
```

If you saved hub output to a text file, parse it afterward:

```bash
python3 code/tools/collect_spike_logs.py --file hub-output.txt
```

## Saved CSV Format

The collector saves a CSV with exactly:

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

`time` is milliseconds from the start of the recording.
`distance` is millimeters calculated from the drive motor encoders.
`gyro_angle` is hub yaw in degrees.

The hub transfer may show `LOG_START`, `CBLOG_HEADER`, and `CBLOG_ROW` lines in the console. Those are only for reliable transfer; the collector strips them out of the saved CSV.

The console also includes a human fallback:

```text
CSV_START
time,distance,gyro_angle
4,0,0
11,0,0
CSV_END
```

Use that fallback only if the collector does not save a CSV.

## Important Limits

The hub stores one run in memory. It also writes a backup file named `robot_log.csv` on the hub after recording. This helps if reconnecting to the computer restarts the program before you press the left button.

Starting a new recording replaces the previous saved run.

Pressing both hub buttons clears the saved run and the backup file.

The logger uses `SAMPLE_MS = 1` to collect dense data for short 2-3 second FLL paths. Actual row spacing is limited by SPIKE sensor reads and MicroPython overhead, but this is intentionally tuned to be as close as practical to the original Pybricks `DataLog` density.

The default `MAX_ROWS_PER_LOG = 8000` is sized for short route recordings.

## Notes

This code targets the SPIKE 3 style MicroPython API, which uses modules such as:

- `hub.button`
- `hub.light_matrix`
- `hub.motion_sensor`
- `hub.port`
- `motor`
- `runloop`
