import time

from hub import light_matrix, motion_sensor, port
import color_sensor
import motor
import motor_pair
import runloop


class DataLog:
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


LEFT_MOTOR = port.A
RIGHT_MOTOR = port.B
LEFT_COLOR = port.C
RIGHT_COLOR = port.D
DRIVE_PAIR = motor_pair.PAIR_1


def elapsed_ms(start_ms):
    return time.ticks_diff(time.ticks_ms(), start_ms)


def safe_reflection(sensor_port):
    try:
        return color_sensor.reflection(sensor_port)
    except Exception:
        return -1


async def main():
    await light_matrix.write("D")

    motor.reset_relative_position(LEFT_MOTOR, 0)
    motor.reset_relative_position(RIGHT_MOTOR, 0)
    motion_sensor.reset_yaw(0)
    motor_pair.pair(DRIVE_PAIR, LEFT_MOTOR, RIGHT_MOTOR)

    log = DataLog(
        "time_ms",
        "yaw_ddeg",
        "left_deg",
        "right_deg",
        "left_speed",
        "right_speed",
        "left_ref",
        "right_ref",
        name="drive_example",
        max_rows=300,
    )

    start = time.ticks_ms()
    motor_pair.move_tank(DRIVE_PAIR, 360, 360)

    while elapsed_ms(start) < 3000:
        log.log(
            elapsed_ms(start),
            motion_sensor.tilt_angles()[0],
            motor.relative_position(LEFT_MOTOR),
            motor.relative_position(RIGHT_MOTOR),
            motor.velocity(LEFT_MOTOR),
            motor.velocity(RIGHT_MOTOR),
            safe_reflection(LEFT_COLOR),
            safe_reflection(RIGHT_COLOR),
        )
        await runloop.sleep_ms(50)

    motor_pair.stop(DRIVE_PAIR, stop=motor.BRAKE)
    await light_matrix.write("U")
    log.dump()
    await light_matrix.write("Y")


runloop.run(main())
