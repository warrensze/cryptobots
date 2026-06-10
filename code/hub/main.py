import time

from hub import button, light_matrix, motion_sensor, port
import motor
import os
import runloop


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

    def dump(self):
        for line in self.lines():
            print(line)

    def lines(self):
        output = ["LOG_START," + csv_value(self.name)]
        if self.dropped_rows:
            output.append("LOG_DROPPED," + str(self.dropped_rows))
        output.append("CBLOG_HEADER," + csv_row(self.headers))
        for row in self.rows:
            output.append("CBLOG_ROW," + csv_row(row))
        output.append("LOG_END," + csv_value(self.name))
        return output


class LogSession:
    """Hold completed logs in memory until the user downloads them."""

    def __init__(self, max_logs=5):
        self.max_logs = max_logs
        self.logs = []
        self.dropped_logs = 0

    def add(self, datalog):
        if len(self.logs) < self.max_logs:
            self.logs.append(datalog)
        else:
            self.dropped_logs += 1

    def clear(self):
        self.logs = []
        self.dropped_logs = 0

    def count(self):
        return len(self.logs)

    def dump_all(self):
        for line in self.lines():
            print(line)

    def lines(self):
        output = [
            "SESSION_START," + str(len(self.logs)),
            "HUB_LOG_COUNT," + str(len(self.logs)),
        ]
        if self.dropped_logs:
            output.append("SESSION_DROPPED," + str(self.dropped_logs))
        for datalog in self.logs:
            output.extend(datalog.lines())
        output.append("SESSION_END," + str(len(self.logs)))
        return output


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


# 5 ms is the target sampling interval. Actual timing can be a little slower
# depending on how fast the hub can read sensors and store rows.
SAMPLE_MS = 5
MAX_ROWS_PER_LOG = 3000
MAX_SAVED_LOGS = 5
LOG_FILE = "robot_logs.txt"

# Match the team's SPIKE Prime drive configuration.
LEFT_MOTOR = port.B
RIGHT_MOTOR = port.F
WHEEL_CIRCUMFERENCE_MM = 176
GYRO_RESET_WAIT_MS = 100

# If gyro angle stays at 0 while turning, change this to another face:
# motion_sensor.FRONT, TOP, RIGHT, BOTTOM, BACK, or LEFT.
try:
    YAW_FACE = motion_sensor.TOP
except AttributeError:
    YAW_FACE = None

session = LogSession(max_logs=MAX_SAVED_LOGS)
recording_number = 1


def left_pressed():
    return button.pressed(button.LEFT) > 0


def right_pressed():
    return button.pressed(button.RIGHT) > 0


def both_pressed():
    return left_pressed() and right_pressed()


async def wait_for_buttons_released():
    while left_pressed() or right_pressed():
        await runloop.sleep_ms(20)


def elapsed_ms(start_ms):
    return time.ticks_diff(time.ticks_ms(), start_ms)


def write_lines_to_file(path, lines):
    with open(path, "w") as file:
        for line in lines:
            file.write(line + "\n")


def persist_session():
    try:
        write_lines_to_file(LOG_FILE, session.lines())
    except Exception:
        pass


def clear_persisted_logs():
    try:
        os.remove(LOG_FILE)
    except Exception:
        pass


def dump_persisted_logs():
    try:
        with open(LOG_FILE, "r") as file:
            found_any = False
            found_log_row = False
            while True:
                line = file.readline()
                if not line:
                    break
                found_any = True
                text = line.strip()
                if text.startswith("CBLOG_ROW,"):
                    found_log_row = True
                print(text)
            return found_any and found_log_row
    except Exception:
        return False


def dump_no_logs():
    print("SESSION_START,0")
    print("HUB_LOG_COUNT,0")
    print("NO_LOGS,record_with_right_button_before_dumping")
    print("SESSION_END,0")


def make_gyro_log(name):
    return DataLog(
        "time_ms",
        "distance_mm",
        "gyro_angle_deg",
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
    def __init__(self, motor_port):
        self.motor_port = motor_port
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
            return self.absolute_total

        if relative == 0 and self.absolute_total != 0:
            return self.absolute_total

        return relative


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
    average_degrees = (abs(left_deg) + abs(right_deg)) // 2
    return (average_degrees * WHEEL_CIRCUMFERENCE_MM) // 360


def log_motion_row(log, start_ms, left_tracker, right_tracker, gyro_tracker):
    left_deg = left_tracker.read_degrees()
    right_deg = right_tracker.read_degrees()
    log.log(
        elapsed_ms(start_ms),
        estimate_distance_mm(left_deg, right_deg),
        gyro_tracker.read_degrees(),
    )


async def record_motion_log(name):
    await wait_for_buttons_released()
    await light_matrix.write("R")

    configure_motion_sensor()
    try:
        motion_sensor.reset_yaw(0)
    except Exception:
        pass
    await runloop.sleep_ms(GYRO_RESET_WAIT_MS)
    try:
        motor.reset_relative_position(LEFT_MOTOR, 0)
        motor.reset_relative_position(RIGHT_MOTOR, 0)
    except Exception:
        pass

    log = make_gyro_log(name)
    left_tracker = MotorTracker(LEFT_MOTOR)
    right_tracker = MotorTracker(RIGHT_MOTOR)
    gyro_tracker = GyroTracker()
    start = time.ticks_ms()
    log_motion_row(log, start, left_tracker, right_tracker, gyro_tracker)

    while True:
        if right_pressed():
            log_motion_row(log, start, left_tracker, right_tracker, gyro_tracker)
            await wait_for_buttons_released()
            return log

        log_motion_row(log, start, left_tracker, right_tracker, gyro_tracker)
        await runloop.sleep_ms(SAMPLE_MS)


async def show_saved_count():
    count = session.count()
    if count < 10:
        await light_matrix.write(str(count))
    else:
        await light_matrix.write("9")


async def main():
    global recording_number

    await light_matrix.write("S")

    while True:
        if left_pressed():
            await wait_for_buttons_released()
            await light_matrix.write("U")
            if session.count():
                session.dump_all()
                await light_matrix.write("Y")
            elif not dump_persisted_logs():
                dump_no_logs()
                await light_matrix.write("0")
            else:
                await light_matrix.write("Y")

        elif both_pressed():
            session.clear()
            clear_persisted_logs()
            recording_number = 1
            await wait_for_buttons_released()
            await light_matrix.write("0")

        elif right_pressed():
            name = "manual_gyro_" + str(recording_number)
            recording_number += 1
            log = await record_motion_log(name)
            session.add(log)
            persist_session()
            await show_saved_count()

        await runloop.sleep_ms(25)


runloop.run(main())
