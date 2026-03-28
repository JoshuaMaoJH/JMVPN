import ctypes
import winreg
from dataclasses import dataclass

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
_INTERNET_OPTION_SETTINGS_CHANGED = 39
_INTERNET_OPTION_REFRESH = 37

@dataclass
class _ProxyState:
    enabled: int
    server: str

def _notify_windows() -> None:
    """Tell WinINet that proxy settings have changed so all apps pick it up."""
    try:
        wininet = ctypes.windll.wininet
        wininet.InternetSetOptionW(0, _INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        wininet.InternetSetOptionW(0, _INTERNET_OPTION_REFRESH, 0, 0)
    except Exception:
        pass

class SystemProxy:
    def __init__(self):
        self._original: _ProxyState | None = None

    def _open_key(self, access=winreg.KEY_READ):
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, access)

    def _read_current(self) -> _ProxyState:
        with self._open_key() as key:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            try:
                server, _ = winreg.QueryValueEx(key, "ProxyServer")
            except FileNotFoundError:
                server = ""
        return _ProxyState(enabled=enabled, server=server)

    def _write(self, state: _ProxyState) -> None:
        with self._open_key(winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, state.enabled)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, state.server)
        _notify_windows()

    def enable(self, host: str, port: int) -> None:
        self._original = self._read_current()
        # Use per-protocol format so SOCKS5 is recognised by Windows
        self._write(_ProxyState(enabled=1, server=f"socks={host}:{port}"))

    def restore(self) -> None:
        if self._original is not None:
            self._write(self._original)
            self._original = None
        else:
            self._write(_ProxyState(enabled=0, server=""))
