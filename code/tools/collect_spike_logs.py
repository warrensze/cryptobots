#!/usr/bin/env python3
"""Collect SPIKE hub log dumps and save each log block as a CSV file.

Input can come from:

- a serial port, if your SPIKE setup exposes one
- stdin, if another tool is piping hub output
- a saved text file containing LOG_START / LOG_END blocks
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

    def handle_line(self, line):
        line = line.strip()
        if not line:
            return

        fields = parse_csv_line(line)
        if not fields:
            return

        marker = fields[0]

        if marker == "LOG_START":
            self.current_name = fields[1] if len(fields) > 1 else "spike_log"
            self.current_rows = []
            return

        if marker == "LOG_END":
            name = fields[1] if len(fields) > 1 else self.current_name
            self._save_current_log(name)
            self.current_name = None
            self.current_rows = []
            return

        if marker in ("SESSION_START", "SESSION_END", "SESSION_DROPPED", "LOG_DROPPED"):
            print("info:", line)
            return

        if self.current_name is not None:
            self.current_rows.append(fields)

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
    with serial.Serial(port, baudrate=baud, timeout=1) as connection:
        while True:
            raw = connection.readline()
            if raw:
                collector.handle_line(raw.decode("utf-8", errors="replace"))


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

    if collector.saved_files:
        print("saved", len(collector.saved_files), "file(s)")
    else:
        print("no complete logs found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
