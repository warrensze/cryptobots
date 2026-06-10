# Manual Datalogging Steps

Use this first. It is the simplest workflow: press a button, move or run the robot, press a button to stop, then let the collector save a CSV in `code/logs/`.

The CSV matches the original SuperPowered Pybricks `DataLog` spreadsheet format:

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

## File To Upload

Upload only this file to the SPIKE hub:

```text
code/hub/main.py
```

It contains the logger code inside the same file.

## Upload To The Hub

1. Open the standalone `cryptobots` folder in VS Code.
2. Open `code/hub/main.py`.
3. Check the `ROBOT CONFIGURATION` section near the top of the file:

```python
LEFT_DRIVE_MOTOR_PORT = port.B
RIGHT_DRIVE_MOTOR_PORT = port.F
LEFT_DRIVE_MOTOR_DIRECTION = 1
RIGHT_DRIVE_MOTOR_DIRECTION = 1
WHEEL_CIRCUMFERENCE_MM = 176
```

Use the real drive motor ports on your robot. Valid SPIKE Prime ports are `port.A`, `port.B`, `port.C`, `port.D`, `port.E`, and `port.F`.

4. Upload `code/hub/main.py` to the hub as the program to run.
5. Start the program.

The hub should show:

```text
S
```

That means standby.

## Record Away From The Computer

1. Disconnect the computer if desired.
2. Press the right button on the SPIKE hub.
3. The hub shows `R`, meaning recording.
4. Move or run the robot. Distance is calculated from the drive motor encoders, so the drive wheels must turn.
5. Press the right button again to stop recording.
6. The hub shows `1`, meaning one run is saved.

Do not turn off or reset the hub before copying the data if you can avoid it. The program stores the run in memory and also writes a backup file named `robot_log.csv` on the hub.

Starting a new recording clears and replaces the previous saved run.

## Save The Data

1. Plug the hub into the computer.
2. Start the collector.

macOS/Linux example:

```bash
python3 code/tools/collect_spike_logs.py --port /dev/cu.usbmodemXXXX
```

Windows example:

```bash
python code/tools/collect_spike_logs.py --port COM5
```

3. Press the left button on the SPIKE hub.
4. The hub shows `U`, meaning it is dumping the saved run.
5. The collector saves a CSV in:

```text
code/logs/
```

If the collector fails, use the console fallback. Copy the lines between `CSV_START` and `CSV_END`, starting with the header row:

```text
CSV_START
time,distance,gyro_angle
4,0,0
11,0,0
CSV_END
```

Paste only the CSV lines into Google Sheets, Excel, Numbers, or a `.csv` file.

If the collector says it parsed possible log lines but does not save a CSV,
look in `code/logs/` for a `raw_serial_readable_*.txt` file. That file is the
readable hub output that reached the computer. You can parse it afterward with
`python3 code/tools/collect_spike_logs.py --file code/logs/raw_serial_readable_YYYYMMDD_HHMMSS.txt`.

The saved file contains:

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

## Keep Or Replace Data

The saved run stays on the hub after you dump it. Pressing the left button again
prints the same saved run again.

To replace old data, start a new recording with the right button. The old saved
run is cleared when the new recording starts.

Press both hub buttons at the same time to check whether data is currently
saved.

The hub shows:

```text
1
```

That means saved data is still available. If the hub shows `0`, no saved data
was found.

## CSV Columns

The generated CSV contains:

```text
time
distance
gyro_angle
```

`time` is milliseconds from the start of the recording.

`distance` is millimeters calculated from the drive motor encoders.

`gyro_angle` is hub yaw in degrees.

If distance is negative or stays near zero while the robot moves forward, change `LEFT_DRIVE_MOTOR_DIRECTION` or `RIGHT_DRIVE_MOTOR_DIRECTION` in `code/hub/main.py`.

If `gyro_angle` stays at zero while turning, update `YAW_FACE` in `code/hub/main.py`.

## Sampling Rate

The logger uses a 1 ms loop delay to collect dense data for short 2-3 second routes.

Actual row spacing is limited by SPIKE sensor reads and MicroPython overhead, but this should be much closer to the original Pybricks datalog output than the earlier 50 ms or 10 ms settings.

The default `MAX_ROWS_PER_LOG = 8000` is sized for short route recordings.

## Button Summary

```text
Right button = start recording
Right button = stop recording
Left button = print saved CSV
Both buttons = show whether a saved run exists
```
