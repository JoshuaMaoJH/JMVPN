import atexit, threading
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

from core.config import ConfigManager
from core.tunnel import TunnelManager, TunnelStatus
from core.proxy import SystemProxy
from ui.connect_panel import ConnectPanel
from ui.log_panel import LogPanel

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JMVPN")
        self.geometry("420x480")
        self.minsize(380, 400)

        self._config = ConfigManager()
        self._proxy = SystemProxy()
        self._tunnel = TunnelManager(
            on_log=self._on_log,
            on_status_change=self._on_status_change,
        )

        self._log_panel = LogPanel(self)
        self._connect_panel = ConnectPanel(
            self,
            config=self._config,
            tunnel_manager=self._tunnel,
            system_proxy=self._proxy,
            on_log=self._on_log,
        )
        self._connect_panel.pack(fill="x", padx=8, pady=(8, 0))
        self._log_panel.pack(fill="both", expand=True, padx=8, pady=8)

        self.protocol("WM_DELETE_WINDOW", self._on_close_btn)
        self._tray: pystray.Icon | None = None
        self._setup_tray()
        atexit.register(self._cleanup)

    def _on_log(self, message: str, level: str = "info"):
        self.after(0, lambda: self._log_panel.add_message(message, level))

    def _on_status_change(self, status: TunnelStatus):
        def _update():
            self._connect_panel.set_status(status)
            if status == TunnelStatus.CONNECTED:
                if self._connect_panel._mode.get() == "socks5":
                    port = int(self._connect_panel._socks_port_var.get())
                    self._proxy.enable("127.0.0.1", port)
                    self._on_log(f"System proxy enabled → 127.0.0.1:{port}")
            elif status == TunnelStatus.DISCONNECTED:
                self._proxy.restore()
            self._update_tray_icon(status)
        self.after(0, _update)

    def _make_tray_image(self, connected: bool) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = "#00BB00" if connected else "#888888"
        draw.ellipse([8, 8, 56, 56], fill=color)
        return img

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._show_window),
            pystray.MenuItem("Quit", self._quit_app),
        )
        img = self._make_tray_image(False)
        self._tray = pystray.Icon("JMVPN", img, "JMVPN", menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _update_tray_icon(self, status: TunnelStatus):
        if self._tray:
            self._tray.icon = self._make_tray_image(status == TunnelStatus.CONNECTED)

    def _on_close_btn(self):
        self.withdraw()

    def _show_window(self, *_):
        self.after(0, self.deiconify)

    def _quit_app(self, *_):
        self._cleanup()
        self.after(0, self.destroy)

    def _cleanup(self):
        self._tunnel.disconnect()
        self._proxy.restore()
        if self._tray:
            self._tray.stop()
