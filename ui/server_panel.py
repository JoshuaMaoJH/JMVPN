import customtkinter as ctk
from tkinter import filedialog
from core.config import ServerConfig, ForwardRule, ConfigManager
from utils.keyring_helper import set_credential, delete_credential

class ServerEditDialog(ctk.CTkToplevel):
    """Dialog for adding or editing a server profile."""

    def __init__(self, master, config: ConfigManager,
                 server: ServerConfig | None = None,
                 on_save=None):
        super().__init__(master)
        self.title("Edit Server" if server else "Add Server")
        self.resizable(False, False)
        self.grab_set()
        self._config = config
        self._server = server
        self._on_save = on_save
        self._forward_rows: list[dict] = []
        self._build_form()
        if server:
            self._populate(server)

    def _build_form(self):
        pad = {"padx": 10, "pady": 4}
        fields = [
            ("Name", "name"), ("Host", "host"), ("SSH Port", "port"),
            ("Username", "username"), ("SOCKS5 Port", "socks5_port"),
        ]
        self._vars: dict[str, ctk.StringVar] = {}
        for label, key in fields:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", **pad)
            ctk.CTkLabel(row, text=label, width=80, anchor="w").pack(side="left")
            var = ctk.StringVar()
            ctk.CTkEntry(row, textvariable=var, width=220).pack(side="left")
            self._vars[key] = var

        # Auth type
        auth_row = ctk.CTkFrame(self, fg_color="transparent")
        auth_row.pack(fill="x", **pad)
        ctk.CTkLabel(auth_row, text="Auth", width=80, anchor="w").pack(side="left")
        self._auth_type = ctk.StringVar(value="password")
        ctk.CTkRadioButton(auth_row, text="Password", variable=self._auth_type,
                           value="password", command=self._on_auth_change).pack(side="left", padx=4)
        ctk.CTkRadioButton(auth_row, text="Key File", variable=self._auth_type,
                           value="key", command=self._on_auth_change).pack(side="left")

        # Password field
        self._pass_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._pass_frame.pack(fill="x", **pad)
        ctk.CTkLabel(self._pass_frame, text="Password", width=80, anchor="w").pack(side="left")
        self._password_var = ctk.StringVar()
        ctk.CTkEntry(self._pass_frame, textvariable=self._password_var,
                     show="*", width=220).pack(side="left")

        # Key path field
        self._key_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self._key_frame, text="Key Path", width=80, anchor="w").pack(side="left")
        self._key_path_var = ctk.StringVar()
        ctk.CTkEntry(self._key_frame, textvariable=self._key_path_var, width=180).pack(side="left")
        ctk.CTkButton(self._key_frame, text="...", width=30,
                      command=self._browse_key).pack(side="left", padx=2)
        self._passphrase_var = ctk.StringVar()
        ctk.CTkLabel(self._key_frame, text="Passphrase", width=70, anchor="w").pack(side="left", padx=(8,0))
        ctk.CTkEntry(self._key_frame, textvariable=self._passphrase_var,
                     show="*", width=120).pack(side="left")

        # Port forwards section
        ctk.CTkLabel(self, text="Port Forwarding Rules", anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        self._fwd_container = ctk.CTkFrame(self)
        self._fwd_container.pack(fill="x", padx=10)
        ctk.CTkButton(self, text="+ Add Rule", command=self._add_forward_row).pack(anchor="w", padx=10, pady=4)

        # Save / Cancel
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_row, text="Save", command=self._save).pack(side="right", padx=4)
        ctk.CTkButton(btn_row, text="Cancel", fg_color="gray",
                      command=self.destroy).pack(side="right")

        self._on_auth_change()

    def _on_auth_change(self):
        if self._auth_type.get() == "password":
            self._pass_frame.pack(fill="x", padx=10, pady=4)
            self._key_frame.pack_forget()
        else:
            self._pass_frame.pack_forget()
            self._key_frame.pack(fill="x", padx=10, pady=4)

    def _browse_key(self):
        path = filedialog.askopenfilename(title="Select Private Key File")
        if path:
            self._key_path_var.set(path)

    def _add_forward_row(self, local="", remote_host="localhost", remote_port=""):
        row_frame = ctk.CTkFrame(self._fwd_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        lport = ctk.StringVar(value=str(local))
        rhost = ctk.StringVar(value=remote_host)
        rport = ctk.StringVar(value=str(remote_port))
        ctk.CTkLabel(row_frame, text="Local Port", width=60).pack(side="left")
        ctk.CTkEntry(row_frame, textvariable=lport, width=60).pack(side="left", padx=2)
        ctk.CTkLabel(row_frame, text="→", width=20).pack(side="left")
        ctk.CTkEntry(row_frame, textvariable=rhost, width=100).pack(side="left", padx=2)
        ctk.CTkLabel(row_frame, text=":", width=10).pack(side="left")
        ctk.CTkEntry(row_frame, textvariable=rport, width=60).pack(side="left", padx=2)
        row_data = {"frame": row_frame, "lport": lport, "rhost": rhost, "rport": rport}
        self._forward_rows.append(row_data)
        ctk.CTkButton(row_frame, text="✕", width=28,
                      command=lambda: self._remove_forward_row(row_data)).pack(side="left", padx=4)

    def _remove_forward_row(self, row_data: dict):
        row_data["frame"].destroy()
        self._forward_rows.remove(row_data)

    def _populate(self, server: ServerConfig):
        self._vars["name"].set(server.name)
        self._vars["host"].set(server.host)
        self._vars["port"].set(str(server.port))
        self._vars["username"].set(server.username)
        self._vars["socks5_port"].set(str(server.socks5_port))
        self._auth_type.set(server.auth_type)
        self._key_path_var.set(server.key_path)
        self._on_auth_change()
        for rule in server.forwards:
            self._add_forward_row(rule.local_port, rule.remote_host, rule.remote_port)

    def _save(self):
        forwards = []
        for row in self._forward_rows:
            try:
                forwards.append(ForwardRule(
                    local_port=int(row["lport"].get()),
                    remote_host=row["rhost"].get(),
                    remote_port=int(row["rport"].get()),
                ))
            except ValueError:
                continue

        auth_type = self._auth_type.get()
        if self._server:
            self._config.update(
                self._server.id,
                name=self._vars["name"].get(),
                host=self._vars["host"].get(),
                port=int(self._vars["port"].get() or "22"),
                username=self._vars["username"].get(),
                auth_type=auth_type,
                key_path=self._key_path_var.get(),
                socks5_port=int(self._vars["socks5_port"].get() or "1080"),
                forwards=forwards,
            )
            server_id = self._server.id
        else:
            s = ServerConfig(
                name=self._vars["name"].get(),
                host=self._vars["host"].get(),
                port=int(self._vars["port"].get() or "22"),
                username=self._vars["username"].get(),
                auth_type=auth_type,
                key_path=self._key_path_var.get(),
                socks5_port=int(self._vars["socks5_port"].get() or "1080"),
                forwards=forwards,
            )
            self._config.add(s)
            server_id = s.id

        # Store credential
        if auth_type == "password":
            secret = self._password_var.get()
        else:
            secret = self._passphrase_var.get()
        if secret:
            set_credential(server_id, secret)
        elif not self._server:
            delete_credential(server_id)

        if self._on_save:
            self._on_save()
        self.destroy()
