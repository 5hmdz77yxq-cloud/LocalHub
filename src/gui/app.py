import json
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from ..client.http_client import HttpClient
from ..server.handlers import LocalHubHandler
from ..server.http_server import HttpServer

logger = logging.getLogger(__name__)


class LocalHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LocalHub | HTTP Data Sharing")
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)
        self.client = HttpClient()
        self.server = None
        self.events = queue.Queue()
        self.history = []
        self.storage_dir = Path("shared_files")
        self._style()
        self._build()
        self._poll_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build(self):
        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="LocalHub", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="  Local HTTP data-sharing workspace", foreground="#64748b").pack(side="left")
        self.status_label = ttk.Label(header, text="● Server stopped", foreground="#dc2626")
        self.status_label.pack(side="right")
        tabs = ttk.Notebook(self.root)
        tabs.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.client_tab = ttk.Frame(tabs, padding=12)
        self.server_tab = ttk.Frame(tabs, padding=12)
        self.files_tab = ttk.Frame(tabs, padding=12)
        tabs.add(self.client_tab, text="HTTP Client")
        tabs.add(self.server_tab, text="HTTP Server")
        tabs.add(self.files_tab, text="Shared Files")
        self._build_client()
        self._build_server()
        self._build_files()

    def _build_client(self):
        f = self.client_tab
        ttk.Label(f, text="Request URL").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar(value="http://localhost:8080/")
        ttk.Entry(f, textvariable=self.url_var).grid(row=1, column=0, sticky="ew", pady=(4, 10))
        self.method_var = tk.StringVar(value="GET")
        ttk.Combobox(f, textvariable=self.method_var, values=("GET", "POST"), width=9, state="readonly").grid(row=1, column=1, padx=(8, 0), sticky="w")
        ttk.Label(f, text="Headers (one per line: Name: value)").grid(row=2, column=0, sticky="w")
        self.headers_text = tk.Text(f, height=4, wrap="none")
        self.headers_text.insert("1.0", "Content-Type: text/plain")
        self.headers_text.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(4, 10))
        ttk.Label(f, text="Request body").grid(row=4, column=0, sticky="w")
        self.body_text = tk.Text(f, height=7, wrap="word")
        self.body_text.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(4, 8))
        actions = ttk.Frame(f)
        actions.grid(row=6, column=0, columnspan=2, sticky="ew")
        self.send_btn = ttk.Button(actions, text="Send request", style="Accent.TButton", command=self._send_request)
        self.send_btn.pack(side="left")
        ttk.Button(actions, text="Clear", command=self._clear_client).pack(side="left", padx=8)
        ttk.Label(actions, text="Timeout (ms):").pack(side="left", padx=(20, 4))
        self.timeout_var = tk.StringVar(value="5000")
        ttk.Entry(actions, textvariable=self.timeout_var, width=8).pack(side="left")
        ttk.Label(f, text="Response").grid(row=7, column=0, sticky="w", pady=(12, 4))
        self.response_status = ttk.Label(f, text="No response yet", font=("Segoe UI", 10, "bold"))
        self.response_status.grid(row=8, column=0, columnspan=2, sticky="w")
        self.response_text = tk.Text(f, height=15, wrap="word", state="disabled")
        self.response_text.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(4, 0))
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=0)
        f.rowconfigure(5, weight=1)
        f.rowconfigure(9, weight=2)

    def _build_server(self):
        f = self.server_tab
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        ttk.Label(bar, text="Port:").pack(side="left")
        self.port_var = tk.StringVar(value="8080")
        ttk.Entry(bar, textvariable=self.port_var, width=9).pack(side="left", padx=6)
        self.start_btn = ttk.Button(bar, text="Start server", style="Accent.TButton", command=self._start_server)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(bar, text="Stop server", command=self._stop_server, state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        ttk.Button(bar, text="Open in browser", command=self._open_browser).pack(side="left", padx=10)
        ttk.Button(bar, text="Clear log", command=self._clear_log).pack(side="right")
        ttk.Label(f, text="Incoming requests").pack(anchor="w", pady=(18, 6))
        cols = ("time", "method", "path", "status", "ms")
        self.log_tree = ttk.Treeview(f, columns=cols, show="headings", height=22)
        for col, label, width in (("time","Time",100),("method","Method",90),("path","Path",420),("status","Status",90),("ms","Time (ms)",110)):
            self.log_tree.heading(col, text=label)
            self.log_tree.column(col, width=width, anchor="w")
        self.log_tree.pack(fill="both", expand=True)

    def _build_files(self):
        f = self.files_tab
        ttk.Label(f, text="Files shared by the LocalHub server", style="Title.TLabel").pack(anchor="w")
        ttk.Label(f, text=f"Storage folder: {self.storage_dir.resolve()}").pack(anchor="w", pady=(4, 12))
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Refresh list", command=self._refresh_files).pack(side="left")
        ttk.Button(bar, text="Upload file…", command=self._upload_file).pack(side="left", padx=8)
        ttk.Button(bar, text="Download selected…", command=self._download_file).pack(side="left")
        self.files_tree = ttk.Treeview(f, columns=("name", "size"), show="headings")
        self.files_tree.heading("name", text="Filename")
        self.files_tree.heading("size", text="Size (bytes)")
        self.files_tree.column("name", width=500)
        self.files_tree.column("size", width=150, anchor="e")
        self.files_tree.pack(fill="both", expand=True)

    def _parse_headers(self):
        result = {}
        for line in self.headers_text.get("1.0", "end").splitlines():
            if not line.strip():
                continue
            if ":" not in line:
                raise ValueError(f"Invalid header line: {line}")
            name, value = line.split(":", 1)
            name = name.strip()
            if not name or any(c in name for c in "\r\n:"):
                raise ValueError("Invalid header name")
            result[name] = value.strip()
        return result

    def _send_request(self):
        try:
            timeout = int(self.timeout_var.get())
            self.client.set_timeout(timeout)
            headers = self._parse_headers()
            method = self.method_var.get()
            url = self.url_var.get().strip()
            body = self.body_text.get("1.0", "end-1c")
        except Exception as exc:
            messagebox.showerror("Invalid input", str(exc))
            return
        self.send_btn.configure(state="disabled", text="Sending…")
        self.response_status.configure(text="Request in progress…")
        def worker():
            try:
                response = self.client.get(url, headers) if method == "GET" else self.client.post(url, body, headers.get("Content-Type", "text/plain"), headers)
                self.events.put(("response", response))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _show_response(self, response):
        self.send_btn.configure(state="normal", text="Send request")
        self.response_status.configure(text=f"HTTP {response.status} {response.reason}")
        header_text = "\n".join(f"{k}: {v}" for k, v in response.headers.items())
        try:
            body = response.body.decode("utf-8")
        except UnicodeDecodeError:
            body = f"[Binary body: {len(response.body)} bytes]"
        self._set_text(self.response_text, f"{header_text}\n\n{body}")
        self.history.append({"status": response.status, "body_bytes": len(response.body)})

    def _show_error(self, error):
        self.send_btn.configure(state="normal", text="Send request")
        self.response_status.configure(text="Request failed")
        self._set_text(self.response_text, error)

    @staticmethod
    def _set_text(widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def _clear_client(self):
        self._set_text(self.headers_text, "")
        self._set_text(self.body_text, "")
        self._set_text(self.response_text, "")
        self.response_status.configure(text="No response yet")

    def _start_server(self):
        try:
            port = int(self.port_var.get())
            if not 1 <= port <= 65535:
                raise ValueError("Port must be between 1 and 65535")
            handler = LocalHubHandler(self.storage_dir)
            self.server = HttpServer("127.0.0.1", port, handler,
                                     lambda item: self.events.put(("log", item)))
            self.server.start()
            self.status_label.configure(text="● Server running", foreground="#16a34a")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.port_var.set(str(port))
        except Exception as exc:
            messagebox.showerror("Server error", str(exc))

    def _stop_server(self):
        if self.server:
            self.server.stop()
            self.server = None
        self.status_label.configure(text="● Server stopped", foreground="#dc2626")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _open_browser(self):
        import webbrowser
        import tkinter.messagebox
        port = self.port_var.get()
        webbrowser.open(f"http://127.0.0.1:{port}/")

    def _clear_log(self):
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

    def _refresh_files(self):
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        self.storage_dir.mkdir(exist_ok=True)
        for path in sorted(self.storage_dir.iterdir()):
            if path.is_file():
                self.files_tree.insert("", "end", values=(path.name, path.stat().st_size))

    def _upload_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        source = Path(path)
        def worker():
            try:
                url = f"http://127.0.0.1:{self.port_var.get()}/upload"
                response = self.client.post(url, source.read_bytes(), "application/octet-stream",
                                            {"X-Filename": source.name})
                self.events.put(("file_result", response.status, f"Uploaded {source.name}"))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _download_file(self):
        selection = self.files_tree.selection()
        if not selection:
            messagebox.showinfo("Download", "Select a file first")
            return
        filename = self.files_tree.item(selection[0], "values")[0]
        destination = filedialog.asksaveasfilename(initialfile=filename)
        if not destination:
            return
        def worker():
            try:
                response = self.client.get(f"http://127.0.0.1:{self.port_var.get()}/download/{filename}")
                if response.status != 200:
                    raise RuntimeError(f"Download failed: HTTP {response.status}")
                Path(destination).write_bytes(response.body)
                self.events.put(("file_result", response.status, f"Downloaded to {destination}"))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "response":
                    self._show_response(event[1])
                elif event[0] == "error":
                    self._show_error(event[1])
                elif event[0] == "log":
                    item = event[1]
                    self.log_tree.insert("", "end", values=(item["time"], item["method"], item["path"], item["status"], item["ms"]))
                elif event[0] == "file_result":
                    messagebox.showinfo("File transfer", event[2])
                    self._refresh_files()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _on_close(self):
        self._stop_server()
        self.root.destroy()
