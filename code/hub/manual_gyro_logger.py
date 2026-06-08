import time

from hub import button, light_matrix, motion_sensor
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


SAMPLE_MS = 50
MAX_ROWS = 1200


def right_pressed():
    return button.pressed(button.RIGHT) > 0


async def wait_for_right_released():
    while right_pressed():
        await runloop.sleep_ms(20)


def elapsed_ms(start_ms):
    return time.ticks_diff(time.ticks_ms(), start_ms)


def log_motion_row(log, start_ms, event):
    yaw, pitch, roll = motion_sensor.tilt_angles()
    x_rate, y_rate, z_rate = motion_sensor.angular_velocity(False)
    log.log(
        elapsed_ms(start_ms),
        yaw,
        pitch,
        roll,
        x_rate,
        y_rate,
        z_rate,
        event,
    )


async def main():
    log = DataLog(
        "time_ms",
        "yaw_ddeg",
        "pitch_ddeg",
        "roll_ddeg",
        "x_rate_ddeg_s",
        "y_rate_ddeg_s",
        "z_rate_ddeg_s",
        "event",
        name="manual_gyro",
        max_rows=MAX_ROWS,
    )

    await light_matrix.write("S")
    while not right_pressed():
        await runloop.sleep_ms(20)
    await wait_for_right_released()

    await light_matrix.write("R")
    motion_sensor.reset_yaw(0)
    start = time.ticks_ms()
    log_motion_row(log, start, "start")

    while not right_pressed():
        log_motion_row(log, start, "record")
        await runloop.sleep_ms(SAMPLE_MS)

    log_motion_row(log, start, "stop")
    await wait_for_right_released()

    await light_matrix.write("U")
    log.dump()
    await light_matrix.write("Y")


runloop.run(main())
