import socket
import ssl
import time
import threading

class AmiClient:
    def __init__(self, host: str, port: int, username: str, password: str, use_tls: bool=False, timeout: int=10):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout
        self.sock = None
        self._buf = b""

    def connect(self):
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        if self.use_tls:
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        self.sock = s
        self.sock.settimeout(self.timeout)

        # read banner
        self._read_until(b"\r\n\r\n")
        self.login()

    def login(self):
        action = (
            "Action: Login\r\n"
            f"Username: {self.username}\r\n"
            f"Secret: {self.password}\r\n"
            "Events: on\r\n\r\n"
        )
        self.send(action)
        resp = self.read_message()
        if "Success" not in resp.get("Response",""):
            raise RuntimeError(f"AMI login failed: {resp}")

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        finally:
            self.sock = None

    def send(self, data: str):
        if not self.sock:
            raise RuntimeError("AMI not connected")
        self.sock.sendall(data.encode("utf-8"))

    def _read_until(self, marker: bytes) -> bytes:
        while marker not in self._buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            self._buf += chunk
        idx = self._buf.find(marker)
        if idx == -1:
            data = self._buf
            self._buf = b""
            return data
        data = self._buf[:idx+len(marker)]
        self._buf = self._buf[idx+len(marker):]
        return data

    def read_raw_message(self) -> bytes:
        return self._read_until(b"\r\n\r\n")

    def read_message(self) -> dict:
        raw = self.read_raw_message()
        text = raw.decode("utf-8", errors="ignore").strip()
        msg = {}
        for line in text.split("\r\n"):
            if ":" in line:
                k,v = line.split(":",1)
                msg[k.strip()] = v.strip()
        return msg
