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
        print(csv_row(self.headers))
        for row in self.rows:
            print(csv_row(row))


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

# Change these if the drive motors are plugged into different ports.
LEFT_MOTOR = port.A
RIGHT_MOTOR = port.B

# Change these if one wheel counts backward when the robot is pushed forward.
LEFT_MOTOR_DIRECTION = 1
RIGHT_MOTOR_DIRECTION = 1

# Change this to match your wheel. Common SPIKE/FLL wheels are 56 mm.
WHEEL_DIAMETER_MM = 56

saved_log = None


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


def make_drive_log(name):
    return DataLog(
        "time",
        "distance",
        "gyro_angle",
        name=name,
        max_rows=MAX_ROWS_PER_LOG,
    )


def safe_motor_position(motor_port):
    try:
        return motor.relative_position(motor_port)
    except Exception:
        return 0


def reset_sensors():
    try:
        motor.reset_relative_position(LEFT_MOTOR, 0)
        motor.reset_relative_position(RIGHT_MOTOR, 0)
    except Exception:
        pass

    try:
        motion_sensor.reset_yaw(0)
    except Exception:
        pass


def distance_mm():
    left_degrees = safe_motor_position(LEFT_MOTOR) * LEFT_MOTOR_DIRECTION
    right_degrees = safe_motor_position(RIGHT_MOTOR) * RIGHT_MOTOR_DIRECTION
    average_degrees = (left_degrees + right_degrees) // 2
    return (average_degrees * WHEEL_DIAMETER_MM * 314) // 36000


def gyro_angle_degrees():
    return motion_sensor.tilt_angles()[0] // 10


def log_drive_row(log, start_ms):
    log.log(elapsed_ms(start_ms), distance_mm(), gyro_angle_degrees())


async def record_motion_log(name):
    await wait_for_buttons_released()
    await light_matrix.write("R")

    reset_sensors()
    await runloop.sleep_ms(50)

    log = make_drive_log(name)
    start = time.ticks_ms()
    log_drive_row(log, start)

    while True:
        if right_pressed():
            log_drive_row(log, start)
            await wait_for_buttons_released()
            return log

        log_drive_row(log, start)
        await runloop.sleep_ms(SAMPLE_MS)


async def main():
    global saved_log

    await light_matrix.write("S")

    while True:
        if both_pressed():
            saved_log = None
            await wait_for_buttons_released()
            await light_matrix.write("0")

        elif left_pressed():
            await wait_for_buttons_released()
            if saved_log is None:
                await light_matrix.write("0")
            else:
                await light_matrix.write("U")
                saved_log.dump()
                await light_matrix.write("1")

        elif right_pressed():
            saved_log = await record_motion_log("log_robot")
            await light_matrix.write("1")

        await runloop.sleep_ms(25)


runloop.run(main())
