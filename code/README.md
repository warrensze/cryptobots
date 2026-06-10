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
- both buttons: show whether a saved run exists
- red seen by the color sensor on port `D`: run the autonomous path from `code/logs/equation.txt`

Light matrix codes:

- `S`: standing by, ready to start
- `R`: recording
- `A`: autonomous navigation running
- `1`: one run is saved
- `0`: no run is saved
- `U`: dumping data to the collector

## Recommended Workflow

1. In `hub/main.py`, check the `ROBOT CONFIGURATION` section for drive motor ports, motor direction, wheel size, and gyro face.
2. Upload only `hub/main.py` to the SPIKE hub.
3. Disconnect the computer if you want to collect data away from it.
4. Press the right button. The hub shows `R`.
5. Move or run the robot. Distance is calculated from the drive motor encoders, so the drive wheels must turn.
6. Press the right button again. The hub shows `1`, meaning one run is saved.
7. Plug the hub back into the computer if it was disconnected.
8. Start the collector script.
9. Press the left button on the hub. The hub shows `U` and dumps the saved data.
10. A clean CSV appears in `code/logs/`.

## Autonomous Navigation

`hub/main.py` includes a proportional controller that follows the polynomial in
`code/logs/equation.txt`:

```text
0.25 + 0.579x + 0.0341x^2 + -1.33E-03x^3 + 2.34E-05x^4 + -1.51E-07x^5
```

For each loop, the robot:

1. reads drive motor distance in millimeters
2. calculates the target heading angle from the trend line, normalized so the run starts at `0` degrees after gyro reset
3. reads the current gyro heading angle
4. calculates `error = target_angle - gyro_angle`
5. applies proportional steering correction with `AUTO_KP`

Put red under the color sensor on port `D` to start autonomous navigation. Remove
the red marker before trying to start another autonomous run. Press either hub
button during the run to stop early. The hub saves an autonomous debug CSV with:

```csv
time,distance,gyro_angle,target_angle,error,correction
```

Tune these values near the top of `hub/main.py`:

```python
AUTO_TARGET_DISTANCE_MM = 62
AUTO_BASE_SPEED = 220
AUTO_KP = 2
AUTO_MAX_CORRECTION = 100
AUTO_STEERING_DIRECTION = 1
```

If the robot corrects away from the path, change `AUTO_STEERING_DIRECTION` to
`-1`. If it wiggles too much, lower `AUTO_KP`. If it reacts too slowly, raise
`AUTO_KP` a little.

For a good training run, push the robot so the drive wheels roll along the path.
Avoid rotating the robot in place while the wheel distance stays near `0`; that
creates several gyro angles for the same distance, which a `gyro_angle =
f(distance)` equation cannot replay cleanly.

If the collector fails, the hub also prints a plain CSV fallback between `CSV_START` and `CSV_END` in the console. Copy the lines between those markers, starting with the header row, and paste them into Sheets, Excel, Numbers, or a `.csv` file.

## Robot Setup

The hub code has one setup block near the top of `hub/main.py`:

```python
LEFT_DRIVE_MOTOR_PORT = port.B
RIGHT_DRIVE_MOTOR_PORT = port.F
LEFT_DRIVE_MOTOR_DIRECTION = 1
RIGHT_DRIVE_MOTOR_DIRECTION = 1
AUTONOMOUS_START_SENSOR_PORT = port.D
WHEEL_CIRCUMFERENCE_MM = 176
```

Use any SPIKE Prime motor ports by changing the port names to `port.A`, `port.B`, `port.C`, `port.D`, `port.E`, or `port.F`.

If distance is negative or stays near zero while the robot moves forward, change one motor direction:

```python
LEFT_DRIVE_MOTOR_DIRECTION = 1
RIGHT_DRIVE_MOTOR_DIRECTION = -1
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

If the collector says it parsed possible log lines but does not save a CSV,
look in `code/logs/` for a `raw_serial_readable_*.txt` file. That file is the
exact readable output received from the hub and can be parsed later with
`--file`.

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

Starting a new recording clears and replaces the previous saved run. Dumping a
run with the left button does not clear it, so you can dump the same run again
if the collector misses it the first time.

Pressing both hub buttons shows whether a saved run exists: `1` means saved
data is still available, and `0` means no saved data was found.

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
