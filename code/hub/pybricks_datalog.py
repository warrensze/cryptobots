# pipx run pybricksdev run ble --name "Pybricks Hub" pybricks_datalog.py > training_data.csv

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Button
from pybricks.tools import wait
import time

# ---------------------------------------------------------------------------
# ROBOT CONFIGURATION — edit these for your robot
# ---------------------------------------------------------------------------

LEFT_MOTOR_PORT = Port.A
RIGHT_MOTOR_PORT = Port.B
LEFT_MOTOR_DIRECTION = 1
RIGHT_MOTOR_DIRECTION = 1
WHEEL_CIRCUMFERENCE_MM = 176
SAMPLE_MS = 5
MAX_ROWS_PER_LOG = 8000

# ---------------------------------------------------------------------------
# Layer 0: DataLog + CSV helpers (from cryptobots/code/hub/main.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Layer 1: Utilities (from cryptobots/code/hub/main.py)
# ---------------------------------------------------------------------------

def elapsed_ms(start_ms):
    return time.ticks_diff(time.ticks_ms(), start_ms)


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


def estimate_distance_mm(left_deg, right_deg):
    average_degrees = (abs(left_deg) + abs(right_deg)) // 2
    return (average_degrees * WHEEL_CIRCUMFERENCE_MM) // 360


# ---------------------------------------------------------------------------
# Layer 2: Trackers (simplified for Pybricks)
# ---------------------------------------------------------------------------

class MotorTracker:
    def __init__(self, motor, direction):
        self.motor = motor
        self.direction = direction

    def read_degrees(self):
        return self.motor.angle() * self.direction


class GyroTracker:
    def read_degrees(self):
        heading = hub.imu.heading()
        if heading > 180:
            heading -= 360
        return heading


# ---------------------------------------------------------------------------
# Layer 3: State readers and log helpers
# ---------------------------------------------------------------------------

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


def make_drive_log(name):
    return DataLog(
        "time",
        "distance",
        "gyro_angle",
        name=name,
        max_rows=MAX_ROWS_PER_LOG,
    )


# ---------------------------------------------------------------------------
# Layer 4: Recording (sync version adapted for Pybricks)
# ---------------------------------------------------------------------------

def record_motion_log(name):
    while Button.RIGHT in hub.buttons.pressed():
        wait(20)
    hub.display.char("R")

    hub.imu.reset_heading(0)
    wait(100)
    left_motor.reset_angle(0)
    right_motor.reset_angle(0)

    log = make_drive_log(name)
    left_tracker = MotorTracker(left_motor, LEFT_MOTOR_DIRECTION)
    right_tracker = MotorTracker(right_motor, RIGHT_MOTOR_DIRECTION)
    gyro_tracker = GyroTracker()
    start = time.ticks_ms()
    log_drive_row(log, start, left_tracker, right_tracker, gyro_tracker)

    while True:
        if Button.RIGHT in hub.buttons.pressed():
            log_drive_row(log, start, left_tracker, right_tracker, gyro_tracker)
            while Button.RIGHT in hub.buttons.pressed():
                wait(20)
            return log

        log_drive_row(log, start, left_tracker, right_tracker, gyro_tracker)
        wait(SAMPLE_MS)


# ---------------------------------------------------------------------------
# Layer 5: Main
# ---------------------------------------------------------------------------

hub = PrimeHub()
left_motor = Motor(LEFT_MOTOR_PORT)
right_motor = Motor(RIGHT_MOTOR_PORT)

saved_log = None

hub.display.char("S")

while True:
    pressed = hub.buttons.pressed()

    if Button.RIGHT in pressed:
        while Button.RIGHT in hub.buttons.pressed():
            wait(20)
        saved_log = record_motion_log("robot_run")
        hub.display.char("1")

    elif Button.LEFT in pressed:
        while Button.LEFT in hub.buttons.pressed():
            wait(20)
        if saved_log is not None:
            hub.display.char("U")
            saved_log.dump()
            hub.display.char("1")
        else:
            hub.display.char("0")

    wait(50)
