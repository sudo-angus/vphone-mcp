"""Low-level client for the vphone-cli host control Unix socket."""

import json
import socket
from pathlib import Path


class VPhoneClient:
    """Sends JSON commands to the vphone.sock Unix domain socket."""

    def __init__(self, socket_path: str | Path):
        self.socket_path = str(socket_path)

    def _send(self, msg: dict, timeout: float = 30.0) -> dict:
        """Connect, send one JSON line, read one JSON line, disconnect."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_path)
            payload = json.dumps(msg) + "\n"
            sock.sendall(payload.encode())

            # Read response
            sock.settimeout(timeout)
            chunks: list[bytes] = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
                if b"\n" in data:
                    break

            raw = b"".join(chunks).strip()
            return json.loads(raw) if raw else {"ok": False, "error": "empty response"}
        except FileNotFoundError:
            return {"ok": False, "error": f"socket not found: {self.socket_path}"}
        except ConnectionRefusedError:
            return {"ok": False, "error": "connection refused — is vphone-cli running?"}
        finally:
            sock.close()

    def screenshot(self, path: str | None = None) -> dict:
        msg: dict = {"t": "screenshot"}
        if path:
            msg["path"] = path
        return self._send(msg)

    def tap(self, x: float, y: float) -> dict:
        return self._send({"t": "tap", "x": x, "y": y})

    def swipe(
        self, x1: float, y1: float, x2: float, y2: float, ms: int = 300
    ) -> dict:
        return self._send({"t": "swipe", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "ms": ms})

    def key(self, name: str) -> dict:
        return self._send({"t": "key", "name": name})

    # -- App management --

    def app_list(self, filter: str = "all") -> dict:
        return self._send({"t": "app_list", "filter": filter})

    def app_launch(self, bundle_id: str, url: str | None = None) -> dict:
        msg: dict = {"t": "app_launch", "bundle_id": bundle_id}
        if url:
            msg["url"] = url
        return self._send(msg)

    def app_terminate(self, bundle_id: str) -> dict:
        return self._send({"t": "app_terminate", "bundle_id": bundle_id})

    # -- URL --

    def open_url(self, url: str) -> dict:
        return self._send({"t": "open_url", "url": url})

    # -- Clipboard --

    def clipboard_set(self, text: str) -> dict:
        return self._send({"t": "clipboard_set", "text": text})

    def clipboard_get(self) -> dict:
        return self._send({"t": "clipboard_get"})

    # -- File operations --

    def file_list(self, path: str) -> dict:
        return self._send({"t": "file_list", "path": path})

    def file_push(self, local_path: str, remote_path: str, perm: str = "644") -> dict:
        return self._send(
            {"t": "file_push", "local_path": local_path, "remote_path": remote_path, "perm": perm},
            timeout=180.0,
        )

    def file_pull(self, remote_path: str, local_path: str) -> dict:
        return self._send(
            {"t": "file_pull", "remote_path": remote_path, "local_path": local_path},
            timeout=180.0,
        )

    def file_mkdir(self, path: str) -> dict:
        return self._send({"t": "file_mkdir", "path": path})

    def file_delete(self, path: str) -> dict:
        return self._send({"t": "file_delete", "path": path})

    # -- IPA install --

    def ipa_install(self, path: str) -> dict:
        return self._send({"t": "ipa_install", "path": path}, timeout=180.0)
