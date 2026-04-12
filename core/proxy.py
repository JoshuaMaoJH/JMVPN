import ctypes
import winreg
from dataclasses import dataclass

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
_ENV_REG_PATH = r"Environment"
_ENV_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
             "http_proxy", "https_proxy", "all_proxy")
_INTERNET_OPTION_SETTINGS_CHANGED = 39
_INTERNET_OPTION_REFRESH = 37
_HWND_BROADCAST = 0xFFFF
_WM_SETTINGCHANGE = 0x001A

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

def _broadcast_env_change() -> None:
    """Broadcast WM_SETTINGCHANGE so other processes reload environment variables."""
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            _HWND_BROADCAST, _WM_SETTINGCHANGE, 0, "Environment", 0x0002, 5000, None
        )
    except Exception:
        pass

class SystemProxy:
    def __init__(self):
        self._original: _ProxyState | None = None
        self._saved_env: dict[str, str | None] = {}

    def _open_key(self, access=winreg.KEY_READ):
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, access)

    def _open_env_key(self, access=winreg.KEY_READ):
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ENV_REG_PATH, 0, access)

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

    def _set_env_vars(self, proxy_url: str) -> None:
        """Set user-level environment variables in the registry."""
        with self._open_env_key(winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            for var in _ENV_VARS:
                # Save original value (or None if not set)
                try:
                    self._saved_env[var] = winreg.QueryValueEx(key, var)[0]
                except FileNotFoundError:
                    self._saved_env[var] = None
                winreg.SetValueEx(key, var, 0, winreg.REG_SZ, proxy_url)
        _broadcast_env_change()

    def _restore_env_vars(self) -> None:
        """Restore user-level environment variables to their original values."""
        with self._open_env_key(winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            for var in _ENV_VARS:
                original = self._saved_env.get(var)
                if original is None:
                    try:
                        winreg.DeleteValue(key, var)
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(key, var, 0, winreg.REG_SZ, original)
        self._saved_env.clear()
        _broadcast_env_change()

    def enable(self, host: str, port: int) -> None:
        """Set system proxy and user environment variables to an HTTP CONNECT proxy."""
        self._original = self._read_current()
        self._write(_ProxyState(enabled=1, server=f"{host}:{port}"))
        self._set_env_vars(f"http://{host}:{port}")

    def restore(self) -> None:
        if self._original is not None:
            self._write(self._original)
            self._original = None
        else:
            self._write(_ProxyState(enabled=0, server=""))
        self._restore_env_vars()
