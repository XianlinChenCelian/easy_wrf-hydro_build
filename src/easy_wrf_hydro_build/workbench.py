"""Local browser workbench for the domain and parameter workflows."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from secrets import compare_digest, token_urlsafe
from threading import Lock
import traceback
import webbrowser
from zipfile import BadZipFile

from .atmosphere import ATMOSPHERE_PROFILES
from .domain import ROUTING_DEFAULTS, geogrid_domain, prepare_domain_from_geogrid
from .parameters import apply_parameter_changes, list_parameters

ASSET_DIR = Path(__file__).with_name("ui")
ASSETS = {"/": ("index.html", "text/html"), "/workbench.css": ("workbench.css", "text/css"),
          "/workbench.js": ("workbench.js", "application/javascript")}
INPUT_ERRORS = (ModuleNotFoundError, ValueError, OSError, KeyError, TypeError, RuntimeError, OverflowError, BadZipFile)


def _local_path(data, key):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"请选择路径（{key}）。")
    path = Path(value.strip()).expanduser()
    # Keep the final path component so the workflow can reject dangling output links.
    return path.parent.resolve() / path.name if path.name else path.resolve()


def _browse(data):
    path = _local_path(data, "path") if data.get("path") else Path.cwd()
    extensions = data.get("extensions", [])
    if not isinstance(extensions, list) or not all(isinstance(item, str) for item in extensions):
        raise ValueError("文件类型无效。")
    files = []
    for item in path.iterdir():
        if item.name.startswith("."):
            continue
        directory = item.is_dir()
        if directory or item.suffix.lower() in extensions:
            files.append({"name": item.name, "path": str(item), "directory": directory})
    files.sort(key=lambda item: (not item["directory"], item["name"].casefold()))
    shortcuts = [Path.home(), Path.cwd(), Path("/Volumes"), Path("/mnt")]
    return {"path": str(path), "parent": str(path.parent), "entries": files,
            "shortcuts": [str(item) for item in dict.fromkeys(shortcuts) if item.is_dir()]}


def _error(exc):
    if isinstance(exc, ModuleNotFoundError):
        return f"缺少 {exc.name}。请激活流域制备环境，或为参数试验安装项目的 parameters 依赖。"
    if isinstance(exc, PermissionError):
        return f"当前账号无法访问该路径。请检查权限，或选择自己可写的位置。{exc}"
    return str(exc)


class WorkbenchServer(ThreadingHTTPServer):
    def __init__(self, port, executor):
        self.token = token_urlsafe(32)
        self.executor = executor
        self.processing = Lock()
        self.state_lock = Lock()
        self.jobs = {}
        super().__init__(("127.0.0.1", port), WorkbenchHandler)

    def status(self, kind):
        with self.state_lock:
            return self.jobs.get(kind, {}).copy()

    def map_path(self, request_path):
        parts = request_path.split("/")
        if len(parts) != 4:
            return None
        _, _, gallery, filename = parts
        job = self.status("calibration")
        summary = job.get("summary", {})
        if summary.get("gallery") != gallery:
            return None
        maps = summary["parameter_maps"]
        if filename not in {entry["file"] for entry in maps["images"].values()}:
            return None
        folder = Path(job["output"]) / maps["directory"]
        image = folder / filename
        if folder.is_symlink() or image.is_symlink():
            return None
        return image

    def submit(self, kind, data):
        output = _local_path(data, "output")
        options = {}
        if output.exists() or output.is_symlink():
            raise ValueError(f"请选择一个尚未存在的输出目录：{output}")
        if kind == "domain":
            routing = {"dem": str(_local_path(data, "dem")), "ratio": data.get("ratio"),
                       "threshold_cells": data.get("threshold_cells")}
            for name in ("reach", "lakes", "mask_to_stations"):
                if type(data.get(name)) is not bool:
                    raise ValueError(f"{name} 必须为开关选项。")
                routing[name] = data[name]
            if data.get("stations"):
                routing["stations"] = str(_local_path(data, "stations"))
            if routing["lakes"]:
                routing["lake_polygons"] = str(_local_path(data, "lake_polygons"))
            args = (_local_path(data, "geogrid"), data.get("version"), _local_path(data, "gis"),
                    _local_path(data, "tables"), data.get("month"), routing, output)
        else:
            args = (_local_path(data, "template"), data.get("changes"), output)
            if "forcing_dir" in data:
                options["forcing_dir"] = _local_path(data, "forcing_dir")
        if not self.processing.acquire(blocking=False):
            raise ValueError("已有任务正在运行。请等它完成后再试。")
        with self.state_lock:
            self.jobs[kind] = {"state": "running", "output": str(output), "stage": ""}
        self.executor.submit(self._run, kind, args, options)
        return self.status(kind)

    def _run(self, kind, args, options):
        def update(**values):
            with self.state_lock:
                self.jobs[kind].update(values)

        def progress(stage):
            update(stage=stage)

        try:
            if kind == "domain":
                report = prepare_domain_from_geogrid(*args, progress=progress)
                summary = {**report["routing_grid"], "lake_count": len(report.get("lake_ids", [])),
                           "stations": len(report.get("station_ids", []))}
            else:
                report = apply_parameter_changes(*args, **options, maps=True,
                                                 map_progress=lambda: progress("maps"))
                summary = {"edits": report["edits"], "forcing_target": report["forcing_target"],
                           "parameter_maps": report["parameter_maps"], "gallery": token_urlsafe(18)}
            update(state="done", summary=summary)
        except INPUT_ERRORS as exc:
            update(state="error", error=_error(exc))
        except Exception as exc:
            traceback.print_exc()
            update(state="error", error=f"任务中断。详情见启动终端。{exc}")
        finally:
            self.processing.release()

    def dispatch(self, route, data):
        if route == "/api/browse":
            return _browse(data)
        if route == "/api/options":
            return {"defaults": ROUTING_DEFAULTS, "versions": list(ATMOSPHERE_PROFILES)}
        if route in {"/api/geogrid", "/api/parameters"}:
            if not self.processing.acquire(blocking=False):
                raise ValueError("已有任务正在运行。请等它完成后再读取输入。")
            try:
                if route == "/api/geogrid":
                    return geogrid_domain(_local_path(data, "path"))
                return list_parameters(_local_path(data, "template"))
            finally:
                self.processing.release()
        if route in {"/api/run/domain", "/api/run/calibration"}:
            return self.submit(route.rsplit("/", 1)[-1], data)
        if route in {"/api/status/domain", "/api/status/calibration"}:
            return self.status(route.rsplit("/", 1)[-1])
        raise ValueError("未知操作。")


class WorkbenchHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(10)
        super().setup()

    def log_message(self, *_):
        pass

    def _host_allowed(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _send(self, status, body, content_type):
        self.send_response(status)
        mime = content_type if content_type.startswith("image/") else content_type + "; charset=utf-8"
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, data):
        self._send(status, json.dumps(data).encode(), "application/json")

    def do_GET(self):
        if not self._host_allowed():
            self._json(403, {"error": "请使用终端打印的本机地址。"})
            return
        if self.path.startswith("/parameter-maps/"):
            image = self.server.map_path(self.path)
            try:
                body = image.read_bytes() if image is not None else None
            except OSError:
                body = None
            if body is None:
                self._json(404, {"error": "此参数图已不存在。"})
            else:
                self._send(200, body, "image/png")
            return
        if self.path not in ASSETS:
            self._json(404, {"error": "页面不存在。"})
            return
        file, content_type = ASSETS[self.path]
        body = (ASSET_DIR / file).read_bytes()
        if self.path == "/":
            body = body.replace(b"EWHB_SESSION_TOKEN", self.server.token.encode())
        self._send(200, body, content_type)

    def do_POST(self):
        token = self.headers.get("X-EWHB-Session", "")
        origin = self.headers.get("Origin")
        if (not self._host_allowed() or origin not in (None, "http://" + self.headers["Host"])
                or not token.isascii() or not compare_digest(token, self.server.token)):
            self._json(403, {"error": "工作台会话已失效。请重新打开本机页面。"})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "请求格式无效。"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("请求大小无效。")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("请求必须是 JSON 对象。")
            result = self.server.dispatch(self.path, data)
        except INPUT_ERRORS as exc:
            self._json(400, {"error": _error(exc)})
            return
        self._json(200, result)


def serve_workbench(port, *, open_browser=True):
    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535.")
    with ThreadPoolExecutor(max_workers=1) as executor, WorkbenchServer(port, executor) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"WRF-Hydro 工作台 · {url}", flush=True)
        print("保持此终端运行。按 Ctrl+C 关闭页面服务。", flush=True)
        if open_browser:
            try:
                webbrowser.open(url)
            except webbrowser.Error:
                pass
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            if server.processing.locked():
                print("页面服务已停止，等待当前任务保存结果。", flush=True)
