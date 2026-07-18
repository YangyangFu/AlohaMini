#!/usr/bin/env python3
"""Forward Docker Desktop's TCP X11 traffic to the host X11 Unix socket."""

import socket
import threading


def copy(source: socket.socket, destination: socket.socket) -> None:
    try:
        while data := source.recv(65536):
            destination.sendall(data)
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            destination.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle(client: socket.socket) -> None:
    upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        upstream.connect("/tmp/.X11-unix/X0")
        first = threading.Thread(target=copy, args=(client, upstream), daemon=True)
        second = threading.Thread(target=copy, args=(upstream, client), daemon=True)
        first.start()
        second.start()
        first.join()
        second.join()
    finally:
        client.close()
        upstream.close()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 6000))
    server.listen()
    while True:
        connection, _ = server.accept()
        threading.Thread(target=handle, args=(connection,), daemon=True).start()
