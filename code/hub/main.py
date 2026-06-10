import time

from hub import button, light_matrix, motion_sensor, port
import motor
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

    def lines(self):
        output = ["LOG_START," + csv_value(self.name)]
        if self.dropped_rows:
            output.append("LOG_DROPPED," + str(self.dropped_rows))
        output.append("CBLOG_HEADER," + csv_row(self.headers))
        for row in self.rows:
            output.append("CBLOG_ROW," + csv_row(row))
        output.append("LOG_END," + csv_value(self.name))
        return output

    def csv_lines(self):
        output = ["CSV_START", csv_row(self.headers)]
        for row in self.rows:
            output.append(csv_row(row))
        output.append("CSV_END")
        return output

    def dump_lines(self):
        return self.lines() + self.csv_lines()

    def dump(self):
        for line in self.dump_lines():
            print(line)


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
SAMPLE_MS = 1
MAX_ROWS_PER_LOG = 8000
LOG_FILE = "robot_log.csv"

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


def write_lines_to_file(path, lines):
    with open(path, "w") as file:
        for line in lines:
            file.write(line + "\n")


def persist_log(log):
    try:
        write_lines_to_file(LOG_FILE, log.dump_lines())
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

    def read_degrees(self):
        yaw_ddeg = 0
        try:
            yaw_ddeg = motion_sensor.tilt_angles()[0]
        except Exception:
            pass

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

        yaw_deg = yaw_ddeg // 10
        integrated_deg = self.integrated_mdeg // 1000
        if yaw_deg == 0 and integrated_deg != 0:
            return integrated_deg
        return yaw_deg


def estimate_distance_mm(left_deg, right_deg):
    average_degrees = (left_deg + right_deg) // 2
    return (average_degrees * WHEEL_CIRCUMFERENCE_MM) // 360


def log_drive_row(log, start_ms, left_tracker, right_tracker, gyro_tracker):
    left_deg = left_tracker.read_degrees()
    right_deg = right_tracker.read_degrees()
    log.log(
        elapsed_ms(start_ms),
        estimate_distance_mm(left_deg, right_deg),
        gyro_tracker.read_degrees(),
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


async def main():
    global saved_log

    await light_matrix.write("S")

    while True:
        if both_pressed():
            await wait_for_buttons_released()
            if saved_log is not None or persisted_log_exists():
                await light_matrix.write("1")
            else:
                await light_matrix.write("0")

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

        await runloop.sleep_ms(25)


runloop.run(main())
