import json
import logging
import os
import queue
import threading
import time
from typing import Any, Optional

import websockets.sync.client

logger = logging.getLogger(__name__)
DEFAULT_WS_URL = "ws://127.0.0.1:8080"


class SwarmPublisher:
    """Non-blocking background WebSocket publisher with bounded queue and auto-reconnect."""

    def __init__(self, ws_url: Optional[str] = None, max_queue_size: int = 100, target_hz: float = 30.0):
        self.ws_url = ws_url or os.environ.get("WS_URL", DEFAULT_WS_URL)
        self.queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.target_interval = 1.0 / target_hz
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.connected = False
        self.dropped_frames = 0
        self.sent_frames = 0

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

    def publish(self, message: dict[str, Any]) -> bool:
        """Enqueue message for publication. If full, drops oldest frame to never block."""
        try:
            self.queue.put_nowait(message)
            return True
        except queue.Full:
            try:
                self.queue.get_nowait()
                self.dropped_frames += 1
            except queue.Empty:
                pass
            try:
                self.queue.put_nowait(message)
                return True
            except queue.Full:
                self.dropped_frames += 1
                return False

    def _worker_loop(self) -> None:
        backoff = 0.5
        while self.running:
            try:
                with websockets.sync.client.connect(self.ws_url, close_timeout=1.0) as ws:
                    self.connected = True
                    backoff = 0.5
                    # Register as publisher
                    reg_msg = {"type": "register", "role": "publisher"}
                    ws.send(json.dumps(reg_msg))

                    while self.running:
                        try:
                            msg = self.queue.get(timeout=0.05)
                        except queue.Empty:
                            continue

                        payload = json.dumps(msg, separators=(",", ":"))
                        ws.send(payload)
                        self.sent_frames += 1

            except Exception as e:
                self.connected = False
                if self.running:
                    time.sleep(backoff)
                    backoff = min(backoff * 1.5, 5.0)

        self.connected = False
