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
LEFT_DRIVE_MOTOR_DIRECTION = 1
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
# These values follow code/logs/equation.txt:
#   6.31 + -0.147x + 0.0542x^2 + -1.15E-03x^3 + 1.11E-05x^4 + -4.02E-08x^5
# x is distance in millimeters.
AUTO_TARGET_DISTANCE_MM = 100
AUTO_SAMPLE_MS = 10
AUTO_BASE_SPEED = 220
AUTO_KP = 2
AUTO_MAX_CORRECTION = 100
AUTO_MAX_SPEED = 400
AUTO_STEERING_DIRECTION = 1

BUTTON_RELEASE_CHECK_MS = 20
BUTTON_RELEASE_STABLE_READS = 3
GYRO_RESET_WAIT_MS = 100

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
    average_degrees = (left_deg + right_deg) // 2
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
    x = distance_mm
    return (
        6.31
        + (-0.147 * x)
        + (0.0542 * x * x)
        + (-0.00115 * x * x * x)
        + (0.0000111 * x * x * x * x)
        + (-0.0000000402 * x * x * x * x * x)
    )


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


def pair_drive_motors():
    try:
        motor_pair.pair(
            DRIVE_PAIR,
            LEFT_DRIVE_MOTOR_PORT,
            RIGHT_DRIVE_MOTOR_PORT,
        )
    except Exception:
        pass


def stop_drive_motors():
    try:
        motor_pair.stop(DRIVE_PAIR, stop=motor.BRAKE)
    except TypeError:
        motor_pair.stop(DRIVE_PAIR)
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

    left_speed *= LEFT_DRIVE_MOTOR_DIRECTION
    right_speed *= RIGHT_DRIVE_MOTOR_DIRECTION
    motor_pair.move_tank(DRIVE_PAIR, left_speed, right_speed)
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

    await reset_sensors()
    pair_drive_motors()
    log = make_navigation_log(name)
    left_tracker = MotorTracker(LEFT_DRIVE_MOTOR_PORT, LEFT_DRIVE_MOTOR_DIRECTION)
    right_tracker = MotorTracker(RIGHT_DRIVE_MOTOR_PORT, RIGHT_DRIVE_MOTOR_DIRECTION)
    gyro_tracker = GyroTracker()
    start = time.ticks_ms()

    try:
        while True:
            distance, current_angle = read_drive_state(
                left_tracker,
                right_tracker,
                gyro_tracker,
            )
            target_angle = target_angle_for_distance(distance)
            error = angle_error(target_angle, current_angle)
            correction = apply_proportional_drive(error)
            log_navigation_row(
                log,
                start,
                distance,
                current_angle,
                target_angle,
                error,
                correction,
            )

            if reached_target_distance(distance) or left_pressed() or right_pressed():
                break

            await runloop.sleep_ms(AUTO_SAMPLE_MS)
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
