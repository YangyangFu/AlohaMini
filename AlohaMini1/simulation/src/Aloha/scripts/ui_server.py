#!/usr/bin/env python3
"""Serve the operator UI and lightweight MJPEG previews from ROS images."""

from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import threading
import time
from urllib.parse import parse_qs, urlparse

from ament_index_python.packages import get_package_share_directory
from PIL import Image
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image as RosImage


CAMERA_TOPICS = (
    "/cameras/chest/image_raw",
    "/cameras/head/image_raw",
    "/cameras/rear/image_raw",
)


class FrameStore:
    def __init__(self):
        self.condition = threading.Condition()
        self.frames = {}

    def update(self, topic, jpeg):
        with self.condition:
            sequence = self.frames.get(topic, (0, None))[0] + 1
            self.frames[topic] = (sequence, jpeg)
            self.condition.notify_all()

    def wait_for_frame(self, topic, last_sequence, timeout=5.0):
        with self.condition:
            self.condition.wait_for(
                lambda: self.frames.get(topic, (0, None))[0] != last_sequence,
                timeout=timeout,
            )
            return self.frames.get(topic, (last_sequence, None))

    def available_topics(self):
        with self.condition:
            return sorted(self.frames)


class UiHttpServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class UiRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, frame_store, **kwargs):
        self.frame_store = frame_store
        super().__init__(*args, **kwargs)

    def end_headers(self):
        # The operator panel is under active development and its JavaScript
        # defines command ranges and units. Never let a browser keep an older
        # control contract after the container has been rebuilt.
        if urlparse(self.path).path not in {"/stream", "/health"}:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        request = urlparse(self.path)
        if request.path == "/stream":
            topic = parse_qs(request.query).get("topic", [""])[0]
            self._stream(topic)
            return
        if request.path == "/health":
            payload = json.dumps(
                {"status": "ok", "camera_topics": self.frame_store.available_topics()}
            ).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def _stream(self, topic):
        if topic not in CAMERA_TOPICS:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown camera topic")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        sequence = 0
        try:
            while True:
                sequence, jpeg = self.frame_store.wait_for_frame(topic, sequence)
                if jpeg is None:
                    continue
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format_string, *args):
        # Avoid one log line per MJPEG request/frame. ROS startup logs still
        # report the address and port explicitly.
        if self.path.startswith("/stream"):
            return
        super().log_message(format_string, *args)


class UiServer(Node):
    def __init__(self):
        super().__init__("ui_server")
        self.declare_parameter("address", "127.0.0.1")
        self.declare_parameter("port", 8000)
        self.declare_parameter("jpeg_quality", 75)
        self.declare_parameter("preview_max_rate", 10.0)

        self.address = str(self.get_parameter("address").value)
        self.port = int(self.get_parameter("port").value)
        self.jpeg_quality = min(
            max(int(self.get_parameter("jpeg_quality").value), 20), 95
        )
        self.minimum_period = 1.0 / max(
            float(self.get_parameter("preview_max_rate").value), 0.1
        )
        self.frame_store = FrameStore()
        self.last_encoded = {topic: 0.0 for topic in CAMERA_TOPICS}
        self.unsupported_encodings = set()

        self._subscriptions = [
            self.create_subscription(
                RosImage,
                topic,
                partial(self._image_callback, topic),
                qos_profile_sensor_data,
            )
            for topic in CAMERA_TOPICS
        ]

        web_root = f"{get_package_share_directory('aloha')}/web"
        handler = partial(
            UiRequestHandler,
            directory=web_root,
            frame_store=self.frame_store,
        )
        self.http_server = UiHttpServer((self.address, self.port), handler)
        self.http_thread = threading.Thread(
            target=self.http_server.serve_forever,
            name="aloha-ui-http",
            daemon=True,
        )
        self.http_thread.start()
        self.get_logger().info(
            f"Operator UI listening on http://{self.address}:{self.port}"
        )

    def _image_callback(self, topic, message):
        now = time.monotonic()
        if now - self.last_encoded[topic] < self.minimum_period:
            return
        self.last_encoded[topic] = now

        encoding_map = {
            "rgb8": ("RGB", "RGB"),
            "bgr8": ("RGB", "BGR"),
            "rgba8": ("RGBA", "RGBA"),
            "bgra8": ("RGBA", "BGRA"),
            "mono8": ("L", "L"),
        }
        if message.encoding not in encoding_map:
            if message.encoding not in self.unsupported_encodings:
                self.unsupported_encodings.add(message.encoding)
                self.get_logger().warning(
                    f"Cannot preview unsupported image encoding {message.encoding!r}"
                )
            return

        mode, raw_mode = encoding_map[message.encoding]
        try:
            image = Image.frombuffer(
                mode,
                (message.width, message.height),
                bytes(message.data),
                "raw",
                raw_mode,
                message.step,
                1,
            )
            if mode != "RGB":
                image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="JPEG", quality=self.jpeg_quality)
            self.frame_store.update(topic, output.getvalue())
        except (TypeError, ValueError, OSError) as error:
            self.get_logger().warning(f"Failed to encode {topic}: {error}")

    def close(self):
        self.http_server.shutdown()
        self.http_server.server_close()
        self.http_thread.join(timeout=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = UiServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
