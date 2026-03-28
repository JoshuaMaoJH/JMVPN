import socket, threading, time
import customtkinter as ctk
from core.config import ConfigManager, ServerConfig
from core.tunnel import TunnelManager, TunnelStatus
from core.proxy import SystemProxy

_STATUS_COLORS = {
    TunnelStatus.DISCONNECTED: ("gray60", "gray40"),
    TunnelStatus.CONNECTING:   ("#FFA500", "#CC8400"),
    TunnelStatus.CONNECTED:    ("#00BB00", "#007700"),
    TunnelStatus.ERROR:        ("#CC0000", "#880000"),
}
_STATUS_LABELS = {
    TunnelStatus.DISCONNECTED: "未连接",
    TunnelStatus.CONNECTING:   "连接中...",
    TunnelStatus.CONNECTED:    "已连接",
    TunnelStatus.ERROR:        "错误",
}

class ConnectPanel(ctk.CTkFrame):
    def __init__(self, master, config: ConfigManager,
                 tunnel_manager: TunnelManager,
                 system_proxy: SystemProxy,
                 on_log, **kwargs):
        super().__init__(master, **kwargs)
        self._config = config
        self._tunnel = tunnel_manager
        self._proxy = system_proxy
        self._on_log = on_log
        self._latency_thread: threading.Thread | None = None
        self._latency_running = False
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 4}

        # Server selector row
        srv_row = ctk.CTkFrame(self, fg_color="transparent")
        srv_row.pack(fill="x", **pad)
        ctk.CTkLabel(srv_row, text="服务器", width=60, anchor="w").pack(side="left")
        self._server_var = ctk.StringVar()
        self._server_menu = ctk.CTkOptionMenu(srv_row, variable=self._server_var,
                                               values=["(无)"], width=180,
                                               command=self._on_server_change)
        self._server_menu.pack(side="left", padx=4)
        self._add_btn = ctk.CTkButton(srv_row, text="+", width=28,
                                       command=self._open_add_dialog)
        self._add_btn.pack(side="left", padx=2)
        self._edit_btn = ctk.CTkButton(srv_row, text="编辑", width=46,
                                        command=self._open_edit_dialog)
        self._edit_btn.pack(side="left", padx=2)
        self._del_btn = ctk.CTkButton(srv_row, text="删除", width=46,
                                       fg_color="#CC3333",
                                       command=self._delete_server)
        self._del_btn.pack(side="left", padx=2)

        # Mode selector
        mode_row = ctk.CTkFrame(self, fg_color="transparent")
        mode_row.pack(fill="x", **pad)
        ctk.CTkLabel(mode_row, text="模式", width=60, anchor="w").pack(side="left")
        self._mode = ctk.StringVar(value="socks5")
        ctk.CTkRadioButton(mode_row, text="SOCKS5全局代理",
                            variable=self._mode, value="socks5",
                            command=self._on_mode_change).pack(side="left", padx=4)
        ctk.CTkRadioButton(mode_row, text="端口转发",
                            variable=self._mode, value="forward",
                            command=self._on_mode_change).pack(side="left")

        # SOCKS5 port row (shown only in socks5 mode)
        self._socks_row = ctk.CTkFrame(self, fg_color="transparent")
        self._socks_row.pack(fill="x", **pad)
        ctk.CTkLabel(self._socks_row, text="SOCKS5端口", width=80, anchor="w").pack(side="left")
        self._socks_port_var = ctk.StringVar(value="1080")
        ctk.CTkEntry(self._socks_row, textvariable=self._socks_port_var, width=80).pack(side="left")

        # Connect button + status
        ctrl_row = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_row.pack(fill="x", **pad)
        self._status_dot = ctk.CTkLabel(ctrl_row, text="●", text_color="gray60", width=20)
        self._status_dot.pack(side="left")
        self._status_label = ctk.CTkLabel(ctrl_row, text="未连接", width=80, anchor="w")
        self._status_label.pack(side="left")
        self._connect_btn = ctk.CTkButton(ctrl_row, text="连接", width=80,
                                           command=self._on_connect_click)
        self._connect_btn.pack(side="right")

        # Latency
        lat_row = ctk.CTkFrame(self, fg_color="transparent")
        lat_row.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(lat_row, text="延迟", width=60, anchor="w").pack(side="left")
        self._latency_label = ctk.CTkLabel(lat_row, text="--", anchor="w")
        self._latency_label.pack(side="left")

        self.refresh_server_list()

    def _on_mode_change(self):
        if self._mode.get() == "socks5":
            self._socks_row.pack(fill="x", padx=10, pady=4)
        else:
            self._socks_row.pack_forget()

    def refresh_server_list(self):
        servers = self._config.list()
        names = [s.name for s in servers] if servers else ["(无)"]
        self._server_menu.configure(values=names)
        if servers:
            self._server_var.set(servers[0].name)
        else:
            self._server_var.set("(无)")

    def _get_selected_server(self) -> ServerConfig | None:
        name = self._server_var.get()
        return next((s for s in self._config.list() if s.name == name), None)

    def _on_server_change(self, _):
        server = self._get_selected_server()
        if server:
            self._socks_port_var.set(str(server.socks5_port))

    def _open_add_dialog(self):
        from ui.server_panel import ServerEditDialog
        ServerEditDialog(self, self._config, on_save=self.refresh_server_list)

    def _open_edit_dialog(self):
        server = self._get_selected_server()
        if not server:
            return
        from ui.server_panel import ServerEditDialog
        ServerEditDialog(self, self._config, server=server, on_save=self.refresh_server_list)

    def _delete_server(self):
        server = self._get_selected_server()
        if server:
            self._config.delete(server.id)
            self.refresh_server_list()

    def _on_connect_click(self):
        if self._tunnel.status in (TunnelStatus.CONNECTED, TunnelStatus.CONNECTING):
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        server = self._get_selected_server()
        if not server:
            self._on_log("请先选择服务器", "warn")
            return
        try:
            port = int(self._socks_port_var.get())
            server.socks5_port = port
        except ValueError:
            pass
        mode = self._mode.get()
        self._tunnel.connect(server, mode)

    def _do_disconnect(self):
        self._tunnel.disconnect()
        self._proxy.restore()
        self._on_log("已断开连接")

    def set_status(self, status: TunnelStatus):
        colors = _STATUS_COLORS[status]
        self._status_dot.configure(text_color=colors[0])
        self._status_label.configure(text=_STATUS_LABELS[status])
        if status == TunnelStatus.CONNECTED:
            self._connect_btn.configure(text="断开")
            self._start_latency_probe()
        else:
            self._connect_btn.configure(text="连接")
            self._stop_latency_probe()
            self._latency_label.configure(text="--")

    def _start_latency_probe(self):
        self._latency_running = True
        self._latency_thread = threading.Thread(target=self._latency_loop, daemon=True)
        self._latency_thread.start()

    def _stop_latency_probe(self):
        self._latency_running = False

    def _latency_loop(self):
        server = self._get_selected_server()
        if not server:
            return
        while self._latency_running:
            start = time.monotonic()
            try:
                with socket.create_connection((server.host, server.port), timeout=3):
                    pass
                ms = int((time.monotonic() - start) * 1000)
                self.after(0, lambda m=ms: self._latency_label.configure(text=f"{m} ms"))
            except OSError:
                self.after(0, lambda: self._latency_label.configure(text="超时"))
            time.sleep(5)
