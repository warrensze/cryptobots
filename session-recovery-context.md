# Session Recovery Context

## Date

2026-06-11 (Updated from 2026-06-10)

## Project

Standalone repository:

```text
/Users/warren/LegoLeagueAutoDrive/cryptobots
```

Original reference repository:

```text
/Users/warren/LegoLeagueAutoDrive/public.superpowered2022
```

The original SuperPowered repository is historical/reference context only. The active project is the standalone `cryptobots` repo.

Current key file:

```text
code/hub/main.py
```

## Goal

Build a stock LEGO SPIKE Prime MicroPython datalogger, without Pybricks, that mimics the original SuperPowered Pybricks `DataLog` spreadsheet output as closely as practical.

The desired console/CSV output is exactly:

```csv
time,distance,gyro_angle
```

For autonomous navigation, the robot follows a polynomial equation to trace a curved path based on drive distance.

## Original SuperPowered Findings

The EV3/Pybricks code logs with `pybricks.tools.DataLog`.

Relevant files:

- `src/robot.py`
- `tests/test_datalog.py`

Important details:

- `StopWatch.time()` values are milliseconds.
- `DriveBase.distance()` values are millimeters.
- `gyro.angle()` values are degrees.
- The original logger often logs as fast as the loop allows, so row spacing is dense.

## Current SPIKE Design

The current `code/hub/main.py` is a one-file hub upload (updated 2026-06-11).

It records:

- `time` (milliseconds)
- `distance` (millimeters)
- `gyro_angle` (degrees)

Motor control (fixed in session 2026-06-11):
- Previously used `motor_pair.pair()` + `motor_pair.move_tank()` which broke individual encoder reads
- Now uses `motor.run(port, speed)` for each motor individually
- This allows distance feedback to work correctly during autonomous navigation

It uses:

- `time.ticks_ms()` / `time.ticks_diff()` for milliseconds
- drive motor encoders for estimated distance (individual motor reads)
- hub yaw for gyro angle
- `SAMPLE_MS = 5` for dense short-route logging
- `MAX_ROWS_PER_LOG = 8000`
- stable button-release detection before arming the next button action

The active program has a `ROBOT CONFIGURATION` section near the top. Default robot constants (updated 2026-06-11):

```python
LEFT_DRIVE_MOTOR_PORT = port.B
RIGHT_DRIVE_MOTOR_PORT = port.F
LEFT_DRIVE_MOTOR_DIRECTION = 1
RIGHT_DRIVE_MOTOR_DIRECTION = -1  # Fixed: motors wired in opposite polarity
AUTONOMOUS_START_SENSOR_PORT = port.D
WHEEL_CIRCUMFERENCE_MM = 176
```

Valid SPIKE Prime motor ports are `port.A` through `port.F`.

Motor direction fix: RIGHT motor is physically wired backward, so `RIGHT_DRIVE_MOTOR_DIRECTION = -1` 
compensates during distance calculation to ensure both encoders read positive when moving forward.

There is no intentional recording time limit. The right button starts and stops recording. The code waits for a stable release after the start press so the same press is not reused as the stop press, but it does not ignore a later stop press based on elapsed time.

The autonomous navigation (updated 2026-06-12):
- Now uses individual motor.run() control instead of motor_pair for accurate distance feedback
- Uses equation5.txt: `7.57 + 0.755x + 4.26E-03x² + 5.82E-06x³ + 2.25E-09x⁴` where x = distance_mm
- Uses proportional steering control: `AUTO_KP = 3`, `AUTO_MAX_CORRECTION = 120`
- Gyro readings are consistent (uses tilt_angles, not angular velocity)
- Angle error wraps through `angle_error()` to handle ±180° gyro crossing

## Workflow

1. Upload only `code/hub/main.py` to the SPIKE hub.
2. Disconnect the computer if desired.
3. Press right button to start recording.
4. Move or run the robot.
5. Press right button to stop recording.
6. Hub shows `1`.
7. Reconnect to VS Code/SPIKE console.
8. Start the collector script.
9. Press left button.
10. Hub dumps tagged log rows.
11. Collector saves a clean CSV into `code/logs/`.
12. If the collector fails, copy the plain CSV fallback printed between `CSV_START` and `CSV_END`.
13. If serial data arrives but no CSV is saved, check `code/logs/` for a `raw_serial_readable_*.txt` troubleshooting file and parse it later with `code/tools/collect_spike_logs.py --file`.

Button behavior:

- right button: start/stop recording
- left button: dump saved run to collector
- both buttons: show whether a saved run exists
- red seen by the color sensor on port `D`: start autonomous navigation

Autonomous navigation is latched so it starts once when red is first seen. The
red marker must be removed before another red trigger can start another
autonomous run.

## Persistence

The hub stores one run in memory and also writes a backup file named:

```text
robot_log.csv
```

This backup helps if the hub program restarts when reconnecting to the computer.

Starting a new recording clears and replaces the previous saved run. Dumping the
run with the left button does not clear it, so the same run can be dumped again
if the collector misses it.

The backup file includes both tagged collector rows and the plain CSV fallback
so reconnect/restart recovery still has a copy/paste path.

## Recent Debugging Context

**Session 2026-06-10:**
- The collector previously printed `info: parsed N possible log line(s) from serial data` without explaining why no CSV was saved.
- `code/tools/collect_spike_logs.py` now saves readable raw serial output to `code/logs/raw_serial_readable_*.txt` whenever serial data is received.
- If no CSV rows are saved from serial data, the collector now prints a warning and points to the raw file.
- A temporary `MIN_RECORDING_MS` stop-button lockout was rejected and removed. The current code uses stable button-release detection instead.
- `code/logs/debug.txt` from the hub was XOR-3 encoded. Decoding it showed a hub `MemoryError` in `DataLog.csv_lines()` while dumping data.
- The hub logger now streams tagged rows and plain CSV rows directly to `print()` / file writes instead of building a second large list of all output lines.
- The collector now detects and decodes XOR-3 hub output when saving/reading raw serial text.
- `robot_log_20260610_134858.csv` showed `gyro_angle` changing while `distance` stayed near `0`, and a `20 -> 1` degree gyro jump. This is poor training data for `gyro_angle = f(distance)`.
- `GyroTracker` now uses `motion_sensor.tilt_angles()` consistently instead of switching between tilt-angle yaw and integrated angular velocity mid-run.
- Autonomous steering was softened from `AUTO_KP = 6` / `AUTO_MAX_CORRECTION = 160` to `AUTO_KP = 2` / `AUTO_MAX_CORRECTION = 100`.

**Session 2026-06-11 Analysis & Fixes:**
- Analyzed robot logs: distance was always ≈0 even during clear motion. Gyro changed but distance feedback was broken.
- **Root Cause 1 - Motor Pair Encoder Bug:** Code called `motor_pair.pair()` then `motor_pair.move_tank()`, but then tried to read `motor.relative_position()` on individual motors. Motor pair APIs interfere with individual motor position reads, returning stale/zero data.
  - **Fix:** Replaced with `motor.run(port, speed)` for individual motor control. Removed `pair_drive_motors()` call.
  - **Result:** Individual encoder reads now work. Distance feedback restored to proportional steering control.
- **Root Cause 2 - Motor Direction Mismatch:** Manual arc-to-left push showed distance oscillating -1/0 instead of increasing smoothly. Both motors moved, gyro changed, but distance stayed wrong.
  - **Analysis:** RIGHT motor physically wired in opposite polarity to LEFT. Both had direction=1, so readings cancelled: `(+left + -right)/2 ≈ 0`.
  - **Fix:** Changed `RIGHT_DRIVE_MOTOR_DIRECTION` from `1` to `-1`.
  - **Result:** Distance calculation now works: `(+left + +right)/2 = true forward distance`.

## Merge Context

The local branch had the simple one-run workflow. The remote branch had better hub persistence, collector support, and improved encoder/gyro handling. The intended merged result keeps:

- one run at a time
- collector-generated CSV files in `code/logs/`
- tagged hub transfer lines for reliability
- plain console CSV fallback for manual copy/paste if the collector fails
- dense 1 ms loop delay
- hub-file backup
- robust motor and gyro helpers from the remote branch

## Git State Note

The user prefers to commit changes manually. Do not commit unless explicitly asked.

## Code Changes Session 2026-06-11

**File Modified:** `code/hub/main.py`

**Changes:**
1. Replaced `pair_drive_motors()` function with new `drive_motors(left_speed, right_speed)` function
   - Old: Used `motor_pair.pair()` and `motor_pair.move_tank()`
   - New: Uses `motor.run(port, speed)` for each motor individually
   - Motor direction multipliers now applied inside `drive_motors()` function

2. Updated `stop_drive_motors()` function
   - Old: Used `motor_pair.stop(DRIVE_PAIR)`
   - New: Uses `motor.stop(port)` for each motor individually

3. Updated `apply_proportional_drive()` function
   - Old: Applied direction multipliers, then called `motor_pair.move_tank()`
   - New: Calls `drive_motors(left_speed, right_speed)` which handles direction multipliers

4. Removed `pair_drive_motors()` call from `run_autonomous_navigation()`
   - No longer needed since individual motors are controlled directly

5. Changed motor direction configuration
   - `RIGHT_DRIVE_MOTOR_DIRECTION` changed from `1` to `-1`
   - Compensates for opposite physical wiring of the drive motors

## Session 2026-06-12 — Autonomous Navigation Precision Fix

**Bug Found:** `angle_error()` (line 706) was defined but never called. The `run_autonomous_navigation()` function computed `error = target_angle - current_angle` directly without wrap-around handling. When the hub gyro wraps at ±180° (which happens around distance ≈ 182 mm during a U-turn), the raw subtraction produces a massive error (~-311°) that saturates the correction limit and steers the robot the wrong direction.

**Fix Applied:**
- Changed line 864 from `error = target_angle - current_angle` to `error = angle_error(target_angle, current_angle)` — wraps error to [-180, 180] so the proportional controller always takes the shortest angular path.
- Added clarifying docstring to `raw_target_angle_for_distance()` noting x = distance_mm.
- Added comments distinguishing the _trendline_raw copy (speed ramping, x=percent) from `raw_target_angle_for_distance` (navigation, x=mm).

**Why this matters for exact polynomial tracking:**
Without wrap handling, when the robot's actual heading exceeds ±180°, the error term flips sign and the robot steers away from the target instead of toward it. This means the distance-angle trajectory diverges from the polynomial curve exactly when the robot needs the most guidance (the middle-to-end of a U-turn).

## Session 2026-06-12 — Autonomous Navigation Steering & Direction Fix

**Bug 1 — Backward Speed:**
`run_autonomous_navigation()` used `speed = -base_speed`, causing the robot to move backward. The polynomial equation (`target_angle_for_distance`) maps forward distance → target gyro angle, so forward movement is required. A backward-moving robot would traverse the path in reverse, producing incorrect position→angle mapping.

**Fix:** Changed `speed = -base_speed` to `speed = base_speed` (line 878).

**Bug 2 — Steering Direction Inverted:**
The correction was applied as `left = speed - correction`, `right = speed + correction`. A positive correction (need to turn right) would make left slower and right faster, producing a LEFT turn — exactly opposite of what was needed. Compare with the working `apply_proportional_drive()` (line 788) which correctly uses `left = base + correction`, `right = base - correction`.

**Fix:** Changed to `left = speed + correction`, `right = speed - correction` (lines 902-903), matching the `apply_proportional_drive` convention where positive correction → left faster → right turn.

**Why `angle_error()` works correctly with the wrapped gyro:**
The polynomial produces unbounded cumulative target angles (~792° at 300mm), while `GyroTracker.read_degrees()` returns a raw ±180° wrapped yaw. `angle_error()` correctly finds the shortest path by subtracting and wrapping to [-180,180], which naturally accounts for the robot's multi-revolution turns.

**Bug 3 — Equation Sign Mismatch (Right Turn vs Left Turn):**
The equation5.txt coefficients are all positive (`7.57 + 0.755x + ...`), producing POSITIVE target angles which command a RIGHT turn. However, the user's datalogging training data was a LEFT turn (counterclockwise). When the autonomous code ran, the positive equation + inverted steering (Bug 2) made the robot veer hard right and backward — exactly what the user reported as "robot moved backwards to the right."

**Fix:** Negated the return value of `raw_target_angle_for_distance()` (line 723) by wrapping in a leading `-()`. The navigation code now produces negative target angles → proportional controller steers left. The `_trendline_raw` function (speed ramping) is unchanged — its sign cancels out via the normalization ratio.

**Why negation works without affecting speed ramping:**
`_trendline_raw` is fed into `trendline_speed()` which computes `ratio = (raw - Y0) / YRANGE`. Negating all terms flips both numerator and denominator sign, producing the identical ratio. The speed ramping curve shape is preserved.

**Datalogging correctness verified:**
- `MotorTracker(LEFT, 1)` and `MotorTracker(RIGHT, -1)` correctly handle the differential-drive polarity (right motor encoder reads negative for forward movement; direction=-1 flips it to positive)
- `estimate_distance_mm((left_deg + right_deg) // 2)` gives positive distance for forward movement
- `GyroTracker.read_degrees()` returns raw wrapped yaw; correct for both datalogging and the `angle_error()` wrap handling in navigation

**Complete correction chain:**
| Issue | Before | After |
|-------|--------|-------|
| Speed direction | `speed = -base_speed` (backward) | `speed = base_speed` (forward) |
| Steering convention | `left=speed-correction, right=speed+correction` | `left=speed+correction, right=speed-correction` |
| Equation sign | Positive (right turn) | Negated (left turn) |

## Expected Behavior After Upload

1. **Manual Datalogging:** Push robot forward → distance increases smoothly (not 0/-1 bouncing)
2. **Arc Movement:** Push in arc → distance increases + gyro changes show curved path
3. **Autonomous:** Show red → robot moves **forward** following equation curve (not erratic, not backward)

---

## Session 2026-06-17 — Pybricks Datalogging Planning Direction

### Context Shift

The existing `code/hub/main.py` is built for stock SPIKE Prime MicroPython. A new direction has emerged: **create a Pybricks-based datalogger** that ports the datalogging infrastructure from `main.py` into `code/hub/pybricks_datalog.py`, adapting SPIKE API calls to Pybricks equivalents while preserving the exact same output format.

### Implementation Status

The Pybricks datalogger has been **implemented** in a separate repo location:
`FLL-Python-Library-/Pybricks-Code/pybricks_datalog.py`

See the companion context file at:
`FLL-Python-Library-/Pybricks-Code/context.md`

That file documents all implementation details, deviations from the plan, and the current state. This section (lines 270+) remains as the original planning analysis; the implementation context lives in the Pybricks-Code folder.

### Current `pybricks_datalog.py` (baseline)

- Simple linear script: 200 samples at 50ms intervals, 3 columns (`Time_ms`, `Distance_mm`, `Gyro_Heading`)
- Uses `DriveBase.distance()` and `hub.imu.heading()` directly
- No `DataLog` class, no buffering, no overflow protection, no dual-format dump, no navigation columns

### Analysis of `main.py`'s Datalogging Layered Architecture

The datalogging infrastructure in `code/hub/main.py` breaks down into 8 layers:

| Layer | Lines | Component | Hardware Dep? | Port? |
|-------|-------|-----------|---------------|-------|
| 0 | 51–103 | `DataLog` class + `csv_row`/`csv_value` | None (pure Python) | **Verbatim** |
| 1 | 492–493, 741–752, 685–687 | `elapsed_ms`, `limit`, `round_to_int`, `estimate_distance_mm` | `elapsed_ms` uses `time.ticks_ms` | **Verbatim** (elapsed → StopWatch); **drop `unwrap_delta`** (not needed) |
| 2 | 571–588 | `read_relative_position`, `read_absolute_position` | SPIKE `motor.relative_position()` / `motor.absolute_position()` | **Exclude** — replaced by `Motor.angle()` |
| 3 | 563–568 | `configure_motion_sensor` | SPIKE `motion_sensor.set_yaw_face()` | **Exclude** — no Pybricks equivalent |
| 4 | 600–683 | `MotorTracker`, `GyroTracker`, `UnwrappedYawTracker` | SPIKE motor + motion_sensor APIs | **Adapt:** MotorTracker simplifies (no absolute_position); GyroTracker simplifies to just `hub.imu.heading()` → -180..180 (no integration fallback, no multi-mode state); **drop `UnwrappedYawTracker`** (dead code in main.py) |
| 5 | 690–709 | `read_drive_state`, `log_drive_row` | None (DataLog API only) | **Verbatim**; **drop `log_navigation_row`** (only needed by autonomous navigation, which is excluded) |
| 6 | 540–547 | `make_drive_log` | None (DataLog constructor) | **Verbatim**; **drop `make_navigation_log`** (only needed by autonomous navigation) |
| 7 | 834–853 | `record_motion_log` | Async SPIKE button/light_matrix/runloop | **Adapt:** sync (wait), `hub.buttons.pressed()`, `hub.display.char()` |

### What main.py code is EXCLUDED from the Pybricks port (robot control, not datalogging)

- All PID drive functions (`pid_drive`, `pid_rampdrive`)
- All gyro turn functions (`gyro_turn`, `gyro_ramp_turn`, `gyro_ramp_turn_correction`)
- Basic drive functions (`drive_straight`, `drive_time`)
- Target angle equation (`target_angle_raw`, `trendline_*`, `target_angle_for_distance`, `angle_error`)
- Drive primitives (`_drive_tank`, `_drive_steering`, `_drive_stop`, `_deg_per_cm`)
- Autonomous navigation (`run_autonomous_navigation`)
- PID straight with logging (`run_pid_straight`)
- Motor control (`drive_motors`, `stop_drive_motors`, `apply_proportional_drive`)
- Button/color sensor logic (`left_pressed`, `right_pressed`, `both_pressed`, `wait_for_buttons_released`, `autonomous_start_seen`, `main()` loop)
- File persistence (`write_log_to_file`, `persist_log`, `clear_persisted_log`, `persisted_log_exists`, `dump_persisted_log`)
- All `AUTO_*` configuration constants and `SAMPLE_MS`, `MAX_ROWS_PER_LOG`, `LOG_FILE`
- `configure_motion_sensor`, `reset_sensors`
- `saved_log` global

**Additional exclusions identified during simplification review:**
- `unwrap_delta` — only used by SPIKE MotorTracker's absolute-position logic; Pybricks MotorTracker uses `Motor.angle()` directly
- `UnwrappedYawTracker` — defined but never called in main.py (dead code; `wait_for_gyro_settle()` referenced inside it is also undefined)
- `log_navigation_row` — only called by `run_autonomous_navigation()` and `run_pid_straight()`, which are both excluded
- `make_navigation_log` — same reason as `log_navigation_row`
- `motor.absolute_position()` / `read_absolute_position` — not available in Pybricks API

### API Mapping: SPIKE → Pybricks

| SPIKE Prime | Pybricks | Notes |
|---|---|---|---|
| `motor.relative_position(Port)` | `Motor.angle()` | Simplifies MotorTracker — no absolute_position needed |
| `motor.absolute_position(Port)` | N/A | **Exclude** — not available in Pybricks; MotorTracker drops all absolute-position logic |
| `motion_sensor.tilt_angles()[0]` (ddeg, -1800..1800 wraps) | `hub.imu.heading()` (deg, 0..360 wraps) | Convert to -180..180 range to match SPIKE's wrapped yaw; no accumulation needed |
| `motion_sensor.angular_velocity(False)` | `hub.imu.angular_velocity()` (deg/s tuple) | **Exclude** — integration fallback is overcomplicated for Pybricks; `hub.imu.heading()` is reliable |
| `motion_sensor.reset_yaw(0)` | `hub.imu.reset_heading(0)` | Same concept |
| `motor.reset_relative_position(port, 0)` | `Motor.reset_angle(0)` | Used for sensor zeroing |
| `motor.run(port, speed)` | `Motor.run(speed)` | Not needed for pure datalogging |
| `motor.stop(port, mode)` | `Motor.stop()` | Not needed |
| `runloop.sleep_ms(ms)` | `wait(ms)` | Sync vs async — all recording becomes synchronous |
| `time.ticks_ms()` / `time.ticks_diff()` | `StopWatch.time()` or `time.ticks_ms()` | Either works; StopWatch is idiomatic Pybricks |
| `button.pressed(button.LEFT)` | `hub.buttons.pressed()` | Returns which buttons are pressed |
| `light_matrix.write("R")` | `hub.display.char("R")` | Display feedback |
| `port.B`, `port.F` | `Port.B`, `Port.F` | Different module, same port names |
| `os.remove()` / `open()` | `os.remove()` / `open()` | File I/O similar if needed |

### Pybricks MotorTracker Simplification

The SPIKE MotorTracker uses both relative and absolute positions because SPIKE's relative position can reset mid-run. Pybricks `Motor.angle()` is internally continuous (32-bit signed integer since initialization/reset), so the absolute-position complexity drops:

```
SPIKE MotorTracker (24 lines):
  - constructor: stores motor_port, direction, absolute_previous, absolute_total
  - read_degrees():
    - reads relative AND absolute every call
    - unwraps absolute via unwrap_delta
    - falls back to absolute_total if relative is None or reset to 0
    - applies direction multiplier

Pybricks MotorTracker (~7 lines):
  - constructor: stores Motor object, direction
  - read_degrees():
    - return self.motor.angle() * self.direction
```

### Pybricks GyroTracker — Simplified to Range Conversion Only

SPIKE's `GyroTracker.read_degrees()` returns the raw wrapped yaw from `tilt_angles()[0] // 10` in the range -179..179 (no accumulation, no unwrapping). Pybricks `hub.imu.heading()` returns 0..359.

The Pybricks version does NOT need the SPIKE GyroTracker's complexity:
- **No integration fallback**: `hub.imu.heading()` is very reliable in Pybricks; the SPIKE fallback existed because `tilt_angles()` can occasionally throw on some firmware versions.
- **No `use_tilt_angles` state flag**: only one path.
- **No `last_ms` / `integrated_mdeg` tracking**: no integration state needed.
- **No `angular_velocity` import**: not needed.

The entire GyroTracker reduces to:
```
class GyroTracker:
    def read_degrees(self):
        heading = hub.imu.heading()
        if heading > 180:
            heading -= 360
        return heading
```

This produces the same wrapped -180..180 range as SPIKE's `tilt_angles()[0] // 10`.

### Planned Pybricks Datalogger Structure

```
# Robot Configuration (user-editable)
#   Pybricks Motor/Port assignments, wheel circumference, direction multipliers

# Layer 0: DataLog class + csv_row/csv_value (verbatim from main.py)

# Layer 1: Utilities: limit, round_to_int, estimate_distance_mm (verbatim)
#          elapsed_ms → StopWatch-based or time.ticks_ms helper
#          (unwrap_delta NOT ported — not needed)

# Layer 2: MotorTracker (simplified, wraps Motor.angle() + direction)
#          GyroTracker (simplified: hub.imu.heading() → -180..180 range conversion only;
#                       no integration fallback, no multi-mode state)

# Layer 3: read_drive_state, log_drive_row (verbatim)
#          make_drive_log (verbatim)
#          (log_navigation_row and make_navigation_log NOT ported — autonomous only)

# Layer 4: record_motion_log (sync version: wait() instead of runloop.sleep_ms,
#          hub.buttons.pressed() instead of button.pressed(),
#          hub.display.char() instead of light_matrix.write())

# Layer 5: main() — init hub + motors, button-triggered recording, log.dump()
```

### Key Behavioral Invariants (must match main.py)

- `DataLog.dump()` output format is identical (tagged CBLOG_* + raw CSV, same headers)
- `DataLog.log()` respects max_rows and tracks dropped rows
- `MotorTracker.read_degrees() * direction` produces same signed values
- `estimate_distance_mm()` uses `WHEEL_CIRCUMFERENCE_MM` same formula
- `log_drive_row` produces `(time, distance, gyro_angle)` columns
- Gyro output is in -180..180 wrapped degrees (same as SPIKE's `tilt_angles()[0] // 10`)
- `record_motion_log` samples at configurable interval, stops on button press, returns DataLog

### Not Yet Decided

- Whether to keep `DriveBase` or use individual motors (DriveBase gives composite distance, but loses per-motor raw data; for matching main.py exactly, individual motors are required)
- Whether to include file persistence (Pybricks can write files, but the original `.dump(print)` workflow is simpler for BLE collection)
- Whether to include a button-controlled recording loop or keep the script as a callable library
