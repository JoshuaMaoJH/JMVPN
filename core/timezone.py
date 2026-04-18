import subprocess


def get_current_timezone() -> str:
    """Return the current Windows timezone ID (e.g. 'China Standard Time')."""
    r = subprocess.run(["tzutil", "/g"], capture_output=True, text=True)
    return r.stdout.strip()


def get_all_timezones() -> list[str]:
    """Return all available Windows timezone IDs."""
    r = subprocess.run(["tzutil", "/l"], capture_output=True, text=True,
                       encoding="gbk", errors="replace")
    lines = r.stdout.strip().split("\n")
    # Timezone IDs are every 3rd line starting at index 1
    # Format: description \n ID \n blank \n description \n ID \n ...
    ids = []
    for i in range(1, len(lines), 3):
        tz = lines[i].strip()
        if tz:
            ids.append(tz)
    return ids


class TimezoneManager:
    """Switch Windows timezone on connect, restore on disconnect."""

    def __init__(self):
        self._original: str | None = None

    def switch(self, tz_id: str) -> bool:
        """Switch to the given timezone. Returns True on success."""
        if not tz_id:
            return False
        self._original = get_current_timezone()
        if self._original == tz_id:
            self._original = None
            return True
        r = subprocess.run(["tzutil", "/s", tz_id],
                           capture_output=True, text=True)
        return r.returncode == 0

    def restore(self) -> None:
        """Restore the timezone saved before the last switch()."""
        if self._original:
            subprocess.run(["tzutil", "/s", self._original],
                           capture_output=True, text=True)
            self._original = None
