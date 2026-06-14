import time

from hub import button, light_matrix, motion_sensor, port
try:
    import color
    import color_sensor
except ImportError:
    color = None
    color_sensor = None
import motor
import motor_pair
import os
import runloop


# ---------------------------------------------------------------------------
# ROBOT CONFIGURATION
#
# Edit this section before uploading the program to the SPIKE hub.
# SPIKE Prime motor/sensor ports are: port.A, port.B, port.C, port.D, port.E,
# and port.F.
# ---------------------------------------------------------------------------

# Drive motors used to calculate the CSV "distance" column.
LEFT_DRIVE_MOTOR_PORT = port.B
RIGHT_DRIVE_MOTOR_PORT = port.F

# Change these if one wheel counts backward when the robot is pushed forward.
# Common configuration: motors are wired in opposite polarity, so directions differ.
LEFT_DRIVE_MOTOR_DIRECTION = -1
RIGHT_DRIVE_MOTOR_DIRECTION = 1

# Motor pair used by autonomous navigation.
DRIVE_PAIR = motor_pair.PAIR_1

# Color sensor used to start autonomous navigation.
AUTONOMOUS_START_SENSOR_PORT = port.D
AUTONOMOUS_START_COLOR = getattr(color, "RED", None) if color is not None else None

# Wheel circumference in millimeters. The default is close to a 56 mm wheel.
WHEEL_CIRCUMFERENCE_MM = 176

# If gyro_angle stays at 0 while turning, change this to another face:
# motion_sensor.FRONT, TOP, RIGHT, BOTTOM, BACK, or LEFT.
try:
    YAW_FACE = motion_sensor.TOP
except AttributeError:
    YAW_FACE = None


class DataLog:
    """Small CSV logger built into this single uploadable hub program."""

    def __init__(self, *headers, name="log", max_rows=300):
        self.name = name
        self.headers = headers
        self.max_rows = max_rows
        self.rows = []
        self.dropped_rows = 0

    def log(self, *values):
        if len(self.rows) < self.max_rows:
            self.rows.append(values)
        else:
            self.dropped_rows += 1

    def write_tagged_lines(self, writer):
        writer("LOG_START," + csv_value(self.name))
        if self.dropped_rows:
            writer("LOG_DROPPED," + str(self.dropped_rows))
        writer("CBLOG_HEADER," + csv_row(self.headers))
        for row in self.rows:
            writer("CBLOG_ROW," + csv_row(row))
        writer("LOG_END," + csv_value(self.name))

    def write_csv_lines(self, writer):
        writer("CSV_START")
        writer(csv_row(self.headers))
        for row in self.rows:
            writer(csv_row(row))
        writer("CSV_END")

    def write_dump_lines(self, writer):
        self.write_tagged_lines(writer)
        self.write_csv_lines(writer)

    def dump(self):
        self.write_dump_lines(print)


def csv_row(values):
    text = []
    for value in values:
        text.append(csv_value(value))
    return ",".join(text)


def csv_value(value):
    text = str(value)
    needs_quotes = "," in text or '"' in text or "\n" in text or "\r" in text
    if needs_quotes:
        text = '"' + text.replace('"', '""') + '"'
    return text


# Keep sampling as dense as practical for short 2-3 second FLL paths.
# The sensor reads and row storage add overhead, so the actual row spacing will
# usually be slower than 1 ms, but this keeps us close to the original DataLog.
SAMPLE_MS = 5
MAX_ROWS_PER_LOG = 8000
LOG_FILE = "robot_log.csv"

# Autonomous navigation settings.
# The target angle equation is defined in target_angle_raw() below.
# where x = distance_mm (0-300).
AUTO_TARGET_DISTANCE_MM = 300
AUTO_TREND_MIN_DISTANCE_MM = 0
AUTO_TREND_MAX_DISTANCE_MM = 300
AUTO_SAMPLE_MS = 5
AUTO_BASE_SPEED = 160
AUTO_KP = 3
AUTO_MAX_CORRECTION = 120
AUTO_MAX_SPEED = 400
AUTO_STEERING_DIRECTION = 1

BUTTON_RELEASE_CHECK_MS = 20
BUTTON_RELEASE_STABLE_READS = 3
GYRO_RESET_WAIT_MS = 100

# =============================
# TARGET ANGLE EQUATION — paste your equation here
# =============================
# Replace the return statement with your polynomial. Example:
#   target_angle = 0.105 + -0.0188*x + 1.39E-04*x*x + ...
def target_angle_raw(x):
    """Return the target angle for a given distance x (mm or percent)."""
    return -0.318 + 0.0213*x + -1.28E-05*x**2 + -5.39E-08*x**3 + 8.66E-11*x**4 + -3.54E-14*x**5


def _trendline_raw(x):
    return target_angle_raw(x)

_TRENDLINE_Y0 = _trendline_raw(0.0)
_TRENDLINE_Y100 = _trendline_raw(100.0)
_TRENDLINE_YRANGE = _TRENDLINE_Y100 - _TRENDLINE_Y0

def trendline_speed(progress, min_speed, max_speed):
    raw = _trendline_raw(progress * 100.0)
    if _TRENDLINE_YRANGE == 0:
        return (min_speed + max_speed) // 2
    ratio = (raw - _TRENDLINE_Y0) / _TRENDLINE_YRANGE
    return int(min_speed + ratio * (max_speed - min_speed))


def trendline_ramp(progress, min_speed, max_speed, ramp_up=0.2, ramp_down=0.3):
    if progress < ramp_up:
        p = progress / ramp_up
        return trendline_speed(p, min_speed, max_speed)
    elif progress > 1.0 - ramp_down:
        p = (progress - (1.0 - ramp_down)) / ramp_down
        return trendline_speed(1.0 - p, min_speed, max_speed)
    else:
        return max_speed


# =============================
# DRIVE HELPERS (direction-safe)
# =============================
# RIGHT_DRIVE_MOTOR_DIRECTION = -1 means the right motor is mechanically reversed.
# All drive functions must apply direction multipliers to individual motor.run() calls.

G_LOOP_MS = 10
G_RESET_WAIT_MS = 100
MAX_STEERING = 60


def _deg_per_cm():
    return 360.0 / (WHEEL_CIRCUMFERENCE_MM / 10.0)


def _drive_tank(left_speed, right_speed):
    motor.run(LEFT_DRIVE_MOTOR_PORT, left_speed * LEFT_DRIVE_MOTOR_DIRECTION)
    motor.run(RIGHT_DRIVE_MOTOR_PORT, right_speed * RIGHT_DRIVE_MOTOR_DIRECTION)


def _drive_steering(base_vel, steering):
    steer_factor = limit(steering, -MAX_STEERING, MAX_STEERING)
    ratio = steer_factor / MAX_STEERING
    left_v = int(base_vel * (1.0 + ratio))
    right_v = int(base_vel * (1.0 - ratio))
    left_v = limit(left_v, -abs(base_vel), abs(base_vel))
    right_v = limit(right_v, -abs(base_vel), abs(base_vel))
    _drive_tank(left_v, right_v)


def _drive_stop():
    motor.stop(LEFT_DRIVE_MOTOR_PORT, motor.BRAKE)
    motor.stop(RIGHT_DRIVE_MOTOR_PORT, motor.BRAKE)


# =============================
# PID GYRO-STRAIGHT DRIVE
# =============================

async def pid_drive(velocity, distance_cm, kp=2.0, ki=0.0, kd=0.0, feedforward=0, stop=True):
    configure_motion_sensor()
    motion_sensor.reset_yaw(0)
    await runloop.sleep_ms(G_RESET_WAIT_MS)
    motor.reset_relative_position(LEFT_DRIVE_MOTOR_PORT, 0)
    motor.reset_relative_position(RIGHT_DRIVE_MOTOR_PORT, 0)

    target_deg = int(abs(distance_cm) * _deg_per_cm())
    abs_vel = abs(velocity)
    drive_dir = 1 if velocity > 0 else -1

    error_last = 0.0
    error_integral = 0.0

    while True:
        left_pos = read_relative_position(LEFT_DRIVE_MOTOR_PORT)
        right_pos = read_relative_position(RIGHT_DRIVE_MOTOR_PORT)
        if left_pos is None or right_pos is None:
            break
        avg_pos = (abs(left_pos) + abs(right_pos)) // 2
        if avg_pos >= target_deg:
            break

        yaw_deg = motion_sensor.tilt_angles()[0] // 10
        error = yaw_deg
        error_derivative = error - error_last
        error_last = error
        error_integral = error_integral + error

        steering = error * kp + error_integral * ki + error_derivative * kd + feedforward
        steering = int(limit(steering, -MAX_STEERING, MAX_STEERING))
        _drive_steering(drive_dir * abs_vel, steering)
        await runloop.sleep_ms(G_LOOP_MS)

    if stop:
        _drive_stop()


async def pid_rampdrive(velocity, distance_cm, kp=2.0, ki=0.0, kd=0.0, feedforward=0,
                        ramp_up=0.2, ramp_down=0.3, min_vel=80, stop=True):
    configure_motion_sensor()
    motion_sensor.reset_yaw(0)
    await runloop.sleep_ms(G_RESET_WAIT_MS)
    motor.reset_relative_position(LEFT_DRIVE_MOTOR_PORT, 0)
    motor.reset_relative_position(RIGHT_DRIVE_MOTOR_PORT, 0)

    target_deg = int(abs(distance_cm) * _deg_per_cm())
    abs_vel = abs(velocity)
    drive_dir = 1 if velocity > 0 else -1

    error_last = 0.0
    error_integral = 0.0

    while True:
        left_pos = read_relative_position(LEFT_DRIVE_MOTOR_PORT)
        right_pos = read_relative_position(RIGHT_DRIVE_MOTOR_PORT)
        if left_pos is None or right_pos is None:
            break
        avg_pos = (abs(left_pos) + abs(right_pos)) // 2
        if avg_pos >= target_deg:
            break

        progress = avg_pos / target_deg
        current_vel = trendline_ramp(progress, min_vel, abs_vel, ramp_up, ramp_down)

        yaw_deg = motion_sensor.tilt_angles()[0] // 10
        error = yaw_deg
        error_derivative = error - error_last
        error_last = error
        error_integral = error_integral + error

        steering = error * kp + error_integral * ki + error_derivative * kd + feedforward
        steering = int(limit(steering, -MAX_STEERING, MAX_STEERING))
        _drive_steering(drive_dir * int(current_vel), steering)
        await runloop.sleep_ms(G_LOOP_MS)

    if stop:
        _drive_stop()


# =============================
# GYRO TURNS
# =============================

async def gyro_turn(turn_angle, turn_rate=250, spinturn=True, precision=None, stop=True):
    configure_motion_sensor()
    motion_sensor.reset_yaw(0)
    await runloop.sleep_ms(G_RESET_WAIT_MS)

    if precision is None:
        precision = max(1, abs(turn_rate) // 30)
        if precision > 12:
            precision = 12

    turn_abs = abs(turn_angle)
    turn_dir = 1 if turn_angle > 0 else -1
    target_yaw = turn_dir * turn_abs * 10
    max_ms = max(1500, turn_abs * 80)

    if spinturn:
        left_dir = -turn_dir
        right_dir = turn_dir
    else:
        if turn_angle > 0:
            left_dir = 0
            right_dir = 1
        else:
            left_dir = 1
            right_dir = 0

    abs_rate = abs(turn_rate)
    elapsed_ms = 0

    while elapsed_ms < max_ms:
        current_yaw = motion_sensor.tilt_angles()[0]
        if (current_yaw - target_yaw) * turn_dir >= -precision:
            break

        _drive_tank(int(left_dir * abs_rate), int(right_dir * abs_rate))
        await runloop.sleep_ms(G_LOOP_MS)
        elapsed_ms += G_LOOP_MS

    if elapsed_ms >= max_ms:
        print("gyro_turn: timed out at yaw", motion_sensor.tilt_angles()[0])

    if stop:
        _drive_stop()
        await runloop.sleep_ms(50)


async def gyro_ramp_turn(turn_angle, turn_rate=250, spinturn=True,
                         ramp_up=0.2, ramp_down=0.3, precision=None, stop=True):
    configure_motion_sensor()
    motion_sensor.reset_yaw(0)
    await runloop.sleep_ms(G_RESET_WAIT_MS)

    if precision is None:
        precision = max(1, abs(turn_rate) // 30)
        if precision > 12:
            precision = 12

    turn_abs = abs(turn_angle)
    turn_dir = 1 if turn_angle > 0 else -1
    target_yaw = turn_dir * turn_abs * 10
    max_ms = max(1500, turn_abs * 80)

    if spinturn:
        left_dir = -turn_dir
        right_dir = turn_dir
    else:
        if turn_angle > 0:
            left_dir = 0
            right_dir = 1
        else:
            left_dir = 1
            right_dir = 0

    abs_rate = abs(turn_rate)
    min_rate = 50
    elapsed_ms = 0

    while elapsed_ms < max_ms:
        current_yaw = motion_sensor.tilt_angles()[0]
        if (current_yaw - target_yaw) * turn_dir >= -precision:
            break

        angle_turned_abs = abs(current_yaw)
        angle_progress = angle_turned_abs / (turn_abs * 10) if (turn_abs * 10) > 0 else 1.0
        if angle_progress > 1.0:
            angle_progress = 1.0

        current_rate = trendline_ramp(angle_progress, min_rate, abs_rate, ramp_up, ramp_down)

        _drive_tank(int(left_dir * current_rate), int(right_dir * current_rate))
        await runloop.sleep_ms(G_LOOP_MS)
        elapsed_ms += G_LOOP_MS

    if elapsed_ms >= max_ms:
        print("gyro_ramp_turn: timed out at yaw", motion_sensor.tilt_angles()[0])

    if stop:
        _drive_stop()
        await runloop.sleep_ms(50)


async def gyro_ramp_turn_correction(turn_angle, turn_rate=250, spinturn=True,
                                    ramp_up=0.2, ramp_down=0.3, debug=False):
    await gyro_ramp_turn(turn_angle, turn_rate, spinturn, ramp_up, ramp_down, stop=True)
    await runloop.sleep_ms(200)
    angle_end1 = motion_sensor.tilt_angles()[0] // 10

    angle_abs = abs(turn_angle)
    turn_dir = 1 if turn_angle > 0 else -1
    target = turn_dir * angle_abs
    error1 = angle_end1 - target

    if debug:
        print("coarse angle:", angle_end1, "target:", target, "error1:", error1)

    await gyro_turn(-error1, turn_rate=50, spinturn=True, stop=True)
    await runloop.sleep_ms(200)
    angle_end2 = motion_sensor.tilt_angles()[0] // 10
    error2 = angle_end2 - target

    if debug:
        print("fine angle:", angle_end2, "error2:", error2)

    return error2


# =============================
# DRIVE HELPERS (distance / time based)
# =============================

async def drive_straight(velocity, distance_cm, stop=True):
    target_deg = int(abs(distance_cm) * _deg_per_cm())
    abs_vel = abs(velocity)
    drive_dir = 1 if velocity > 0 else -1

    motor.reset_relative_position(LEFT_DRIVE_MOTOR_PORT, 0)
    motor.reset_relative_position(RIGHT_DRIVE_MOTOR_PORT, 0)

    while True:
        left_pos = read_relative_position(LEFT_DRIVE_MOTOR_PORT)
        right_pos = read_relative_position(RIGHT_DRIVE_MOTOR_PORT)
        if left_pos is None or right_pos is None:
            break
        avg_pos = (abs(left_pos) + abs(right_pos)) // 2
        if avg_pos >= target_deg:
            break

        _drive_tank(drive_dir * abs_vel, drive_dir * abs_vel)
        await runloop.sleep_ms(G_LOOP_MS)

    if stop:
        _drive_stop()


async def drive_time(velocity, time_ms, stop=True):
    abs_vel = abs(velocity)
    drive_dir = 1 if velocity > 0 else -1
    elapsed = 0

    while elapsed < time_ms:
        _drive_tank(drive_dir * abs_vel, drive_dir * abs_vel)
        await runloop.sleep_ms(G_LOOP_MS)
        elapsed += G_LOOP_MS

    if stop:
        _drive_stop()


saved_log = None


def left_pressed():
    return button.pressed(button.LEFT) > 0


def right_pressed():
    return button.pressed(button.RIGHT) > 0


def both_pressed():
    return left_pressed() and right_pressed()


def autonomous_start_seen():
    if color_sensor is None or AUTONOMOUS_START_COLOR is None:
        return False

    try:
        return color_sensor.color(AUTONOMOUS_START_SENSOR_PORT) == AUTONOMOUS_START_COLOR
    except Exception:
        return False


async def wait_for_buttons_released():
    stable_reads = 0
    while stable_reads < BUTTON_RELEASE_STABLE_READS:
        if left_pressed() or right_pressed():
            stable_reads = 0
        else:
            stable_reads += 1
        await runloop.sleep_ms(BUTTON_RELEASE_CHECK_MS)


def elapsed_ms(start_ms):
    return time.ticks_diff(time.ticks_ms(), start_ms)


def write_log_to_file(path, log):
    with open(path, "w") as file:
        def write_line(line):
            file.write(line + "\n")
        log.write_dump_lines(write_line)


def persist_log(log):
    try:
        write_log_to_file(LOG_FILE, log)
    except Exception:
        pass


def clear_persisted_log():
    try:
        os.remove(LOG_FILE)
    except Exception:
        pass


def persisted_log_exists():
    try:
        with open(LOG_FILE, "r") as file:
            return bool(file.readline())
    except Exception:
        return False


def dump_persisted_log():
    try:
        with open(LOG_FILE, "r") as file:
            found_any = False
            while True:
                line = file.readline()
                if not line:
                    break
                found_any = True
                print(line.strip())
            return found_any
    except Exception:
        return False


def make_drive_log(name):
    return DataLog(
        "time",
        "distance",
        "gyro_angle",
        name=name,
        max_rows=MAX_ROWS_PER_LOG,
    )


def make_navigation_log(name):
    return DataLog(
        "time",
        "distance",
        "gyro_angle",
        "target_angle",
        "error",
        "correction",
        name=name,
        max_rows=MAX_ROWS_PER_LOG,
    )


def configure_motion_sensor():
    try:
        if YAW_FACE is not None and hasattr(motion_sensor, "set_yaw_face"):
            motion_sensor.set_yaw_face(YAW_FACE)
    except Exception:
        pass


def read_relative_position(motor_port):
    try:
        if hasattr(motor, "relative_position"):
            return motor.relative_position(motor_port)
        if hasattr(motor, "get_relative_position"):
            return motor.get_relative_position(motor_port)
    except Exception:
        pass
    return None


def read_absolute_position(motor_port):
    try:
        if hasattr(motor, "absolute_position"):
            return motor.absolute_position(motor_port)
    except Exception:
        pass
    return None


def unwrap_delta(current, previous):
    delta = current - previous
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360
    return delta


class MotorTracker:
    def __init__(self, motor_port, direction):
        self.motor_port = motor_port
        self.direction = direction
        self.absolute_previous = read_absolute_position(motor_port)
        self.absolute_total = 0

    def read_degrees(self):
        relative = read_relative_position(self.motor_port)
        absolute = read_absolute_position(self.motor_port)

        if absolute is not None and self.absolute_previous is not None:
            self.absolute_total += unwrap_delta(absolute, self.absolute_previous)
            self.absolute_previous = absolute
        elif absolute is not None:
            self.absolute_previous = absolute

        if relative is None:
            return self.absolute_total * self.direction

        if relative == 0 and self.absolute_total != 0:
            return self.absolute_total * self.direction

        return relative * self.direction


class UnwrappedYawTracker:
    """Tracks unwrapped yaw by detecting ±180° wraps in tilt_angles().
    This is critical for autonomous path following when total heading change > 180°."""

    def __init__(self):
        self.raw_ddeg = 0
        self.accumulated_deg = 0.0

    def reset(self):
        configure_motion_sensor()
        motion_sensor.reset_yaw(0)
        wait_for_gyro_settle()
        self.raw_ddeg = motion_sensor.tilt_angles()[0]
        self.accumulated_deg = 0.0

    def read_degrees(self):
        new_ddeg = motion_sensor.tilt_angles()[0]
        delta_ddeg = new_ddeg - self.raw_ddeg
        if delta_ddeg > 1800:
            delta_ddeg -= 3600
        elif delta_ddeg < -1800:
            delta_ddeg += 3600
        self.accumulated_deg += delta_ddeg / 10.0
        self.raw_ddeg = new_ddeg
        return round_to_int(self.accumulated_deg)


class GyroTracker:
    def __init__(self):
        self.last_ms = time.ticks_ms()
        self.integrated_mdeg = 0
        self.use_tilt_angles = True

    def read_degrees(self):
        if self.use_tilt_angles:
            try:
                yaw_ddeg = motion_sensor.tilt_angles()[0]
                self.last_ms = time.ticks_ms()
                return int(yaw_ddeg / 10)
            except Exception:
                self.use_tilt_angles = False

        now = time.ticks_ms()
        dt_ms = time.ticks_diff(now, self.last_ms)
        self.last_ms = now

        try:
            rates = motion_sensor.angular_velocity(False)
            yaw_rate = rates[0]
            for rate in rates:
                if abs(rate) > abs(yaw_rate):
                    yaw_rate = rate
            self.integrated_mdeg += yaw_rate * dt_ms
        except Exception:
            pass

        return int(self.integrated_mdeg / 1000)


def estimate_distance_mm(left_deg, right_deg):
    average_degrees = (abs(left_deg) + abs(right_deg)) // 2
    return (average_degrees * WHEEL_CIRCUMFERENCE_MM) // 360


def read_drive_state(left_tracker, right_tracker, gyro_tracker):
    left_deg = left_tracker.read_degrees()
    right_deg = right_tracker.read_degrees()
    return (
        estimate_distance_mm(left_deg, right_deg),
        gyro_tracker.read_degrees(),
    )


def log_drive_row(log, start_ms, left_tracker, right_tracker, gyro_tracker):
    distance, gyro_angle = read_drive_state(
        left_tracker,
        right_tracker,
        gyro_tracker,
    )
    log.log(
        elapsed_ms(start_ms),
        distance,
        gyro_angle,
    )


def raw_target_angle_for_distance(distance_mm):
    """Return the target angle from the equation at the given distance.
    
    The equation defines the desired gyro angle directly. Positive = right turn,
    negative = left turn, near-zero = straight.
    """
    x = distance_mm
    if x < AUTO_TREND_MIN_DISTANCE_MM:
        x = AUTO_TREND_MIN_DISTANCE_MM
    elif x > AUTO_TREND_MAX_DISTANCE_MM:
        x = AUTO_TREND_MAX_DISTANCE_MM
    return target_angle_raw(x)

AUTO_TARGET_ANGLE_OFFSET = raw_target_angle_for_distance(0)


def target_angle_for_distance(distance_mm):
    return raw_target_angle_for_distance(distance_mm) - AUTO_TARGET_ANGLE_OFFSET


def angle_error(target_angle, current_angle):
    error = target_angle - current_angle
    while error > 180:
        error -= 360
    while error < -180:
        error += 360
    return error


def limit(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def round_to_int(value):
    if value >= 0:
        return int(value + 0.5)
    return int(value - 0.5)


def reached_target_distance(distance_mm):
    if AUTO_TARGET_DISTANCE_MM >= 0:
        return distance_mm >= AUTO_TARGET_DISTANCE_MM
    return distance_mm <= AUTO_TARGET_DISTANCE_MM


def drive_motors(left_speed, right_speed):
    """Drive each motor individually (not as a pair) so encoder reads work correctly."""
    try:
        motor.run(LEFT_DRIVE_MOTOR_PORT, left_speed * LEFT_DRIVE_MOTOR_DIRECTION)
        motor.run(RIGHT_DRIVE_MOTOR_PORT, right_speed * RIGHT_DRIVE_MOTOR_DIRECTION)
    except Exception:
        pass


def stop_drive_motors():
    """Stop both drive motors."""
    try:
        motor.stop(LEFT_DRIVE_MOTOR_PORT, motor.BRAKE)
        motor.stop(RIGHT_DRIVE_MOTOR_PORT, motor.BRAKE)
    except TypeError:
        motor.stop(LEFT_DRIVE_MOTOR_PORT)
        motor.stop(RIGHT_DRIVE_MOTOR_PORT)
    except Exception:
        pass


def apply_proportional_drive(error):
    correction = round_to_int(error * AUTO_KP * AUTO_STEERING_DIRECTION)
    correction = limit(correction, -AUTO_MAX_CORRECTION, AUTO_MAX_CORRECTION)

    left_speed = limit(
        AUTO_BASE_SPEED + correction,
        -AUTO_MAX_SPEED,
        AUTO_MAX_SPEED,
    )
    right_speed = limit(
        AUTO_BASE_SPEED - correction,
        -AUTO_MAX_SPEED,
        AUTO_MAX_SPEED,
    )

    drive_motors(left_speed, right_speed)
    return correction


def log_navigation_row(
    log,
    start_ms,
    distance,
    current_angle,
    target_angle,
    error,
    correction,
):
    log.log(
        elapsed_ms(start_ms),
        distance,
        current_angle,
        round_to_int(target_angle),
        round_to_int(error),
        correction,
    )


async def reset_sensors():
    configure_motion_sensor()
    try:
        motion_sensor.reset_yaw(0)
    except Exception:
        pass
    await runloop.sleep_ms(GYRO_RESET_WAIT_MS)
    try:
        motor.reset_relative_position(LEFT_DRIVE_MOTOR_PORT, 0)
        motor.reset_relative_position(RIGHT_DRIVE_MOTOR_PORT, 0)
    except Exception:
        pass


async def record_motion_log(name):
    await wait_for_buttons_released()
    await light_matrix.write("R")

    await reset_sensors()
    log = make_drive_log(name)
    left_tracker = MotorTracker(LEFT_DRIVE_MOTOR_PORT, LEFT_DRIVE_MOTOR_DIRECTION)
    right_tracker = MotorTracker(RIGHT_DRIVE_MOTOR_PORT, RIGHT_DRIVE_MOTOR_DIRECTION)
    gyro_tracker = GyroTracker()
    start = time.ticks_ms()
    log_drive_row(log, start, left_tracker, right_tracker, gyro_tracker)

    while True:
        if right_pressed():
            log_drive_row(log, start, left_tracker, right_tracker, gyro_tracker)
            await wait_for_buttons_released()
            return log

        log_drive_row(log, start, left_tracker, right_tracker, gyro_tracker)
        await runloop.sleep_ms(SAMPLE_MS)


async def run_autonomous_navigation(name):
    await wait_for_buttons_released()
    await light_matrix.write("A")

    # Diagnostic: print the equation curve at key distances
    print("=== EQUATION DIAG ===")
    for d in [0, 50, 100, 150, 200, 250, 300]:
        t = target_angle_for_distance(d)
        print("nav target at", d, "mm:", round(t, 2))
    print("=== END EQUATION DIAG ===")

    await reset_sensors()
    log = make_navigation_log(name)
    left_tracker = MotorTracker(LEFT_DRIVE_MOTOR_PORT, LEFT_DRIVE_MOTOR_DIRECTION)
    right_tracker = MotorTracker(RIGHT_DRIVE_MOTOR_PORT, RIGHT_DRIVE_MOTOR_DIRECTION)
    gyro_tracker = GyroTracker()
    start = time.ticks_ms()

    base_speed = 200
    kp = 3
    max_correction = 120
    max_speed = 400
    target_distance_mm = AUTO_TARGET_DISTANCE_MM
    speed = base_speed
    last_print_ms = -1000

    try:
        while True:
            left_rel = read_relative_position(LEFT_DRIVE_MOTOR_PORT)
            right_rel = read_relative_position(RIGHT_DRIVE_MOTOR_PORT)
            if left_rel is None or right_rel is None:
                print("ABORT: motor read failed")
                break

            avg_deg = (abs(left_rel) + abs(right_rel)) // 2
            distance_mm = (avg_deg * WHEEL_CIRCUMFERENCE_MM) // 360
            current_angle = gyro_tracker.read_degrees()

            if distance_mm >= target_distance_mm:
                print("DONE: reached", distance_mm, "mm")
                break

            target_angle = target_angle_for_distance(distance_mm)
            error = angle_error(target_angle, current_angle)
            raw_correction = error * kp * AUTO_STEERING_DIRECTION
            correction = int(limit(
                raw_correction,
                -max_correction,
                max_correction,
            ))
            saturated = abs(raw_correction) > max_correction

            left_speed = int(limit(speed + correction, -max_speed, max_speed))
            right_speed = int(limit(speed - correction, -max_speed, max_speed))
            drive_motors(left_speed, right_speed)

            log_navigation_row(
                log, start, distance_mm, current_angle,
                target_angle, error, correction,
            )

            now_ms = elapsed_ms(start)
            if now_ms - last_print_ms >= 200:
                print("t:", now_ms, "d:", distance_mm, "tgt:", round(target_angle, 1),
                      "cur:", current_angle, "err:", round(error, 1),
                      "corr:", correction, "sat!" if saturated else "")
                last_print_ms = now_ms

            if left_pressed() or right_pressed():
                print("ABORT: button pressed")
                break

            await runloop.sleep_ms(AUTO_SAMPLE_MS)
    finally:
        stop_drive_motors()

    await wait_for_buttons_released()
    return log


async def run_pid_straight(name, velocity, distance_cm, kp=2.0, ki=0.0, kd=0.0,
                           min_vel=80, stop=True):
    await wait_for_buttons_released()
    await light_matrix.write("P")

    await reset_sensors()
    log = make_navigation_log(name)
    left_tracker = MotorTracker(LEFT_DRIVE_MOTOR_PORT, LEFT_DRIVE_MOTOR_DIRECTION)
    right_tracker = MotorTracker(RIGHT_DRIVE_MOTOR_PORT, RIGHT_DRIVE_MOTOR_DIRECTION)
    gyro_tracker = GyroTracker()
    start = time.ticks_ms()

    target_deg = int(abs(distance_cm) * _deg_per_cm())
    abs_vel = abs(velocity)
    drive_dir = 1 if velocity > 0 else -1

    error_last = 0.0
    error_integral = 0.0

    try:
        while True:
            distance, current_angle = read_drive_state(
                left_tracker, right_tracker, gyro_tracker,
            )

            left_pos = read_relative_position(LEFT_DRIVE_MOTOR_PORT)
            right_pos = read_relative_position(RIGHT_DRIVE_MOTOR_PORT)
            avg_pos = 0
            if left_pos is not None and right_pos is not None:
                avg_pos = (abs(left_pos) + abs(right_pos)) // 2

            if avg_pos >= target_deg:
                break

            progress = avg_pos / target_deg if target_deg > 0 else 1.0
            current_vel = trendline_ramp(progress, min_vel, abs_vel)

            error = current_angle
            error_derivative = error - error_last
            error_last = error
            error_integral = error_integral + error

            steering = error * kp + error_integral * ki + error_derivative * kd
            steering = int(limit(steering, -MAX_STEERING, MAX_STEERING))

            _drive_steering(drive_dir * int(current_vel), steering)

            log_navigation_row(
                log, start, distance, current_angle,
                0, error, steering,
            )

            if left_pressed() or right_pressed():
                break

            await runloop.sleep_ms(AUTO_SAMPLE_MS)

        if stop:
            _drive_stop()
    finally:
        stop_drive_motors()

    await wait_for_buttons_released()
    return log


async def main():
    global saved_log

    autonomous_start_armed = True
    await light_matrix.write("S")

    while True:
        color_start_seen = autonomous_start_seen()

        if both_pressed():
            await wait_for_buttons_released()
            if saved_log is not None or persisted_log_exists():
                await light_matrix.write("1")
            else:
                await light_matrix.write("0")

        elif color_start_seen and autonomous_start_armed:
            autonomous_start_armed = False
            await light_matrix.write("A")
            saved_log = None
            clear_persisted_log()
            saved_log = await run_autonomous_navigation("autonomous_robot")
            persist_log(saved_log)
            await light_matrix.write("1")

        elif left_pressed():
            await wait_for_buttons_released()
            if saved_log is None:
                if dump_persisted_log():
                    await light_matrix.write("1")
                else:
                    await light_matrix.write("0")
            else:
                await light_matrix.write("U")
                saved_log.dump()
                await light_matrix.write("1")

        elif right_pressed():
            saved_log = None
            clear_persisted_log()
            saved_log = await record_motion_log("log_robot")
            persist_log(saved_log)
            await light_matrix.write("1")

        elif not color_start_seen:
            autonomous_start_armed = True

        await runloop.sleep_ms(25)


runloop.run(main())
