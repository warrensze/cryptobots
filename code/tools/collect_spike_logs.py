#!/usr/bin/env python3
"""Collect SPIKE hub log dumps and save each log block as a CSV file.

Input can come from:

- a serial port, if your SPIKE setup exposes one
- stdin, if another tool is piping hub output
- a saved text file containing LOG_START / LOG_END blocks

It also tries to recover copied hub output that lost the LOG_START / LOG_END
markers, as long as the CSV header or numeric rows are still present.
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path
import re
import sys


DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


class SpikeLogCollector:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.current_name = None
        self.current_rows = []
        self.saved_files = []
        self.recovered_without_markers = False

    def handle_line(self, line):
        line = line.strip()
        if not line:
            return

        if is_noise_line(line):
            return

        fields = parse_csv_line(line)
        if not fields:
            return

        marker = fields[0]

        if marker == "LOG_START":
            self.current_name = fields[1] if len(fields) > 1 else "spike_log"
            self.current_rows = []
            self.recovered_without_markers = False
            return

        if marker == "LOG_END":
            name = fields[1] if len(fields) > 1 else self.current_name
            self._save_current_log(name)
            self.current_name = None
            self.current_rows = []
            self.recovered_without_markers = False
            return

        if marker in ("SESSION_START", "SESSION_END", "SESSION_DROPPED", "LOG_DROPPED"):
            print("info:", line)
            return

        if looks_like_header(fields):
            if self.current_name is None:
                self.current_name = "recovered_spike_log"
                self.current_rows = []
                self.recovered_without_markers = True
            self.current_rows.append(fields)
            return

        if looks_like_data_row(fields) and self.current_name is None:
            self.current_name = "recovered_spike_log"
            self.current_rows = [default_headers_for_row(fields)]
            self.recovered_without_markers = True

        if self.current_name is not None:
            if looks_like_data_row(fields):
                self.current_rows.append(fields)
            else:
                print("info: skipped noisy line inside log:", line[:80])

    def finish(self):
        if self.current_name is None:
            return

        if self.recovered_without_markers:
            print("warning: LOG_START/LOG_END markers were missing; saving recovered rows.")
        else:
            print("warning: LOG_END was missing; saving partial log.")

        self._save_current_log(self.current_name)
        self.current_name = None
        self.current_rows = []
        self.recovered_without_markers = False

    def _save_current_log(self, name):
        if not self.current_rows:
            print("warning: empty log skipped:", name)
            return

        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = safe_filename(name or self.current_name or "spike_log")
        path = unique_path(self.log_dir / (filename + "_" + stamp + ".csv"))

        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerows(self.current_rows)

        self.saved_files.append(path)
        print("saved:", path)


def parse_csv_line(line):
    try:
        return next(csv.reader([line]))
    except csv.Error:
        print("warning: could not parse line:", line)
        return []


def is_noise_line(line):
    text = line.lower()
    return (
        "error deserializing" in text
        or "[hubupload]" in text
        or "welcome to the lego hub log terminal" in text
    )


def looks_like_header(fields):
    return len(fields) >= 2 and fields[0] == "time_ms"


def looks_like_data_row(fields):
    if len(fields) < 2:
        return False

    try:
        int(fields[0])
    except ValueError:
        return False

    numeric_count = 0
    for value in fields[1:]:
        try:
            int(value)
            numeric_count += 1
        except ValueError:
            pass

    return numeric_count >= min(3, len(fields) - 1)


def default_headers_for_row(fields):
    if len(fields) == 3:
        return [
            "time_ms",
            "distance_mm",
            "gyro_angle_deg",
        ]

    if len(fields) == 8:
        return [
            "time_ms",
            "yaw_ddeg",
            "pitch_ddeg",
            "roll_ddeg",
            "x_rate_ddeg_s",
            "y_rate_ddeg_s",
            "z_rate_ddeg_s",
            "event",
        ]

    return ["column_" + str(index + 1) for index in range(len(fields))]


def safe_filename(name):
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "spike_log"


def unique_path(path):
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2

    while True:
        candidate = parent / (stem + "_" + str(counter) + suffix)
        if not candidate.exists():
            return candidate
        counter += 1


def read_from_file(path, collector):
    with Path(path).open("r", encoding="utf-8") as source:
        for line in source:
            collector.handle_line(line)


def read_from_stdin(collector):
    print("Listening on stdin. Press Ctrl-D or Ctrl-C to stop.")
    for line in sys.stdin:
        collector.handle_line(line)


def read_from_serial(port, baud, collector):
    try:
        import serial
    except ImportError:
        print("error: serial mode requires pyserial. Install it with:")
        print("  python3 -m pip install pyserial")
        return 2

    print("Listening on serial port", port, "at", baud, "baud. Press Ctrl-C to stop.")
    try:
        with serial.Serial(port, baudrate=baud, timeout=1) as connection:
            while True:
                raw = connection.readline()
                if raw:
                    collector.handle_line(raw.decode("utf-8", errors="replace"))
    except serial.SerialException as error:
        print("error: could not read from serial port", port)
        print("details:", error)
        print("")
        print("Try these checks:")
        print("  1. Make sure the hub is plugged in, powered on, and already running main.py.")
        print("  2. Start this collector before pressing the hub's left dump button.")
        print("  3. Close VS Code's hub terminal/connection if it is already using the port.")
        print("  4. Confirm the port in Windows Device Manager under Ports (COM & LPT).")
        print("  5. If COM7 is wrong, rerun with the correct COM port, such as COM3 or COM5.")
        return 3


def main():
    parser = argparse.ArgumentParser(description="Save SPIKE Prime LOG_START/LOG_END output as CSV files.")
    parser.add_argument("--port", help="Serial port, for example /dev/cu.usbmodemXXXX or COM5.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate. Default: 115200.")
    parser.add_argument("--file", help="Read log output from a saved text file.")
    parser.add_argument("--stdin", action="store_true", help="Read log output from stdin.")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR), help="Directory where CSV files are saved.")
    args = parser.parse_args()

    collector = SpikeLogCollector(args.log_dir)

    try:
        if args.file:
            read_from_file(args.file, collector)
        elif args.port:
            result = read_from_serial(args.port, args.baud, collector)
            if result:
                return result
        else:
            read_from_stdin(collector)
    except KeyboardInterrupt:
        print("")
        print("stopped")

    collector.finish()

    if collector.saved_files:
        print("saved", len(collector.saved_files), "file(s)")
    else:
        print("no complete logs found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
