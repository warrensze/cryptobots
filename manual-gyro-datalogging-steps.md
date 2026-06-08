# Manual Gyro Datalogging Steps

Use this first. It is the simplest workflow: press a button, move the robot by hand, press a button to stop, then download the data later.

## Files Used

Hub file to upload:

```text
cryptobots/code/hub/main.py
```

Only upload `main.py` to the hub. It contains the logger code inside the same file.

Computer collector:

```text
cryptobots/code/tools/collect_spike_logs.py
```

Generated CSV files:

```text
cryptobots/code/logs/
```

## Upload To The Hub

1. Open the SPIKE Prime project in Visual Studio Code.
2. Upload `cryptobots/code/hub/main.py` to the hub as the program to run.
3. Start the program.

The hub should show:

```text
S
```

That means standby.

## Collect Data Without The Computer

1. Disconnect the computer if desired.
2. Press the right button on the SPIKE hub.
3. The hub shows `R`, meaning recording.
4. Move the robot by hand.
5. Press the right button again to stop recording.
6. The hub shows the number of saved recordings, such as `1`.
7. Repeat if needed. The default program stores up to 5 recordings.

Do not turn off or reset the hub before downloading. The logs are stored in memory.

## Download The Data

1. Plug the hub into the computer.
2. Start the collector.

macOS/Linux example:

```bash
python3 cryptobots/code/tools/collect_spike_logs.py --port /dev/cu.usbmodemXXXX
```

Windows example:

```bash
python cryptobots/code/tools/collect_spike_logs.py --port COM5
```

3. Press the left button on the SPIKE hub.
4. The hub shows `U`, meaning upload/dump.
5. The collector saves CSV files in:

```text
cryptobots/code/logs/
```

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
time_ms
yaw_ddeg
pitch_ddeg
roll_ddeg
x_rate_ddeg_s
y_rate_ddeg_s
z_rate_ddeg_s
event
```

SPIKE reports angles in decidegrees.

```text
450 decidegrees = 45.0 degrees
```

## Button Summary

```text
Right button = start recording
Right button = stop recording
Left button = dump/download saved logs
Both buttons = clear saved logs
```
