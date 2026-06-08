"""Reference logger code.

The current SPIKE hub workflow can only upload one program file, so
`cryptobots/code/hub/main.py` includes its own copy of these classes. Keep this
file as a readable reference for the logger design, not as an extra hub upload.
"""


class DataLog:
    """Small CSV logger for LEGO SPIKE Prime MicroPython.

    Store rows in memory while the robot moves. Call dump() after the run, or
    add the log to a LogSession and dump all logs when the computer is attached.
    """

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

    def clear(self):
        self.rows = []
        self.dropped_rows = 0

    def count(self):
        return len(self.rows)

    def dump(self):
        print("LOG_START," + _csv_value(self.name))
        if self.dropped_rows:
            print("LOG_DROPPED," + str(self.dropped_rows))
        print(_csv_row(self.headers))
        for row in self.rows:
            print(_csv_row(row))
        print("LOG_END," + _csv_value(self.name))


class LogSession:
    """Hold several completed DataLog objects until download time."""

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


def _csv_row(values):
    text = []
    for value in values:
        text.append(_csv_value(value))
    return ",".join(text)


def _csv_value(value):
    text = str(value)
    needs_quotes = "," in text or '"' in text or "\n" in text or "\r" in text
    if needs_quotes:
        text = '"' + text.replace('"', '""') + '"'
    return text
