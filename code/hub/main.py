import time

from hub import button, light_matrix, motion_sensor, port
import motor
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
        print("LOG_START," + csv_value(self.name))
        if self.dropped_rows:
            print("LOG_DROPPED," + str(self.dropped_rows))
        print(csv_row(self.headers))
        for row in self.rows:
            print(csv_row(row))
        print("LOG_END," + csv_value(self.name))


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
        print("SESSION_START," + str(len(self.logs)))
        if self.dropped_logs:
            print("SESSION_DROPPED," + str(self.dropped_logs))
        for datalog in self.logs:
            datalog.dump()
        print("SESSION_END," + str(len(self.logs)))


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

# Match the team's SPIKE Prime drive configuration.
LEFT_MOTOR = port.B
RIGHT_MOTOR = port.F
WHEEL_CIRCUMFERENCE_MM = 176

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


def make_gyro_log(name):
    return DataLog(
        "time_ms",
        "distance_mm",
        "gyro_angle_deg",
        name=name,
        max_rows=MAX_ROWS_PER_LOG,
    )


def safe_motor_position(motor_port):
    try:
        return motor.relative_position(motor_port)
    except Exception:
        return 0


def estimate_distance_mm(left_deg, right_deg):
    average_degrees = (abs(left_deg) + abs(right_deg)) // 2
    return (average_degrees * WHEEL_CIRCUMFERENCE_MM) // 360


def log_motion_row(log, start_ms):
    left_deg = safe_motor_position(LEFT_MOTOR)
    right_deg = safe_motor_position(RIGHT_MOTOR)
    log.log(
        elapsed_ms(start_ms),
        estimate_distance_mm(left_deg, right_deg),
        motion_sensor.tilt_angles()[0] // 10,
    )


async def record_motion_log(name):
    await wait_for_buttons_released()
    await light_matrix.write("R")

    try:
        motion_sensor.reset_yaw(0)
    except Exception:
        pass
    try:
        motor.reset_relative_position(LEFT_MOTOR, 0)
        motor.reset_relative_position(RIGHT_MOTOR, 0)
    except Exception:
        pass

    log = make_gyro_log(name)
    start = time.ticks_ms()
    log_motion_row(log, start)

    while True:
        if right_pressed():
            log_motion_row(log, start)
            await wait_for_buttons_released()
            return log

        log_motion_row(log, start)
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
        if both_pressed():
            session.clear()
            recording_number = 1
            await wait_for_buttons_released()
            await light_matrix.write("0")

        elif left_pressed():
            await wait_for_buttons_released()
            await light_matrix.write("U")
            session.dump_all()
            await show_saved_count()

        elif right_pressed():
            name = "manual_gyro_" + str(recording_number)
            recording_number += 1
            log = await record_motion_log(name)
            session.add(log)
            await show_saved_count()

        await runloop.sleep_ms(25)


runloop.run(main())
