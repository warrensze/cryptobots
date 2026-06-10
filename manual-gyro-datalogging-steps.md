# Manual Gyro Datalogging Steps

Use this first. It is the simplest workflow: press a button, move the robot by hand, press a button to stop, then download the data later.

The saved CSV matches the original SuperPowered Pybricks `DataLog` spreadsheet format:

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

## Files Used

Hub file to upload:

```text
cryptobots/code/hub/main.py
```

Only upload `main.py` to the hub. It contains the logger code inside the same file.

If you opened the standalone `cryptobots` folder directly in VS Code, the same paths are:

```text
code/hub/main.py
```

For the normal one-run workflow, you do not need the collector script. You can copy the CSV directly from the VS Code console.

## Upload To The Hub

1. Open the SPIKE Prime project in Visual Studio Code.
2. Open `code/hub/main.py`.
3. Check these constants near the top of the file:

```python
LEFT_MOTOR = port.A
RIGHT_MOTOR = port.B
WHEEL_DIAMETER_MM = 56
```

4. Upload `code/hub/main.py` to the hub as the program to run.
5. Start the program.

The hub should show:

```text
S
```

That means standby.

## Collect Data Without The Computer

1. Disconnect the computer if desired.
2. Press the right button on the SPIKE hub.
3. The hub shows `R`, meaning recording.
4. Move the robot by hand. Distance is calculated from the drive motor encoders, so the drive wheels must turn.
5. Press the right button again to stop recording.
6. The hub shows `1`, meaning one run is saved.

Do not turn off or reset the hub before copying the data. The log is stored in memory.

Starting a new recording replaces the previous saved run.

## Copy The Data

1. Plug the hub into the computer.
2. Open the SPIKE/VS Code console output.
3. Press the left button on the SPIKE hub.
4. The hub shows `U`, meaning it is printing the CSV.
5. In the console, copy from the header row through the last data row:

```csv
time,distance,gyro_angle
4,0,0
11,0,0
20,0,0
```

6. Paste into Google Sheets, Excel, Numbers, or a `.csv` file.

## Clear Old Logs

Press both hub buttons at the same time.

The hub shows:

```text
0
```

That means the saved recordings were cleared.

## CSV Columns

The generated CSV files contain:

```text
time
distance
gyro_angle
```

`time` is milliseconds from the start of the recording.

`distance` is millimeters calculated from the drive motor encoders.

`gyro_angle` is hub yaw in degrees.

If distance is negative or stays near zero while the robot moves forward, change `LEFT_MOTOR_DIRECTION` or `RIGHT_MOTOR_DIRECTION` in `code/hub/main.py`.

## Sampling Rate

The logger uses a 1 ms loop delay to collect dense data for short 2-3 second routes.

The actual row spacing will be limited by SPIKE sensor reads and MicroPython overhead, but this should be much closer to the original Pybricks datalog output than the earlier 50 ms or 10 ms settings.

The default `MAX_ROWS_PER_LOG = 8000` is sized for short route recordings.

## Button Summary

```text
Right button = start recording
Right button = stop recording
Left button = print saved CSV
Both buttons = clear saved run
```
