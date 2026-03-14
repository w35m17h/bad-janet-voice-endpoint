#!/usr/bin/env python3
import socket
import subprocess
import threading

HOST = '127.0.0.1'
PORT = 9999

OPENCLAW = '/path/to/openclaw'  # Update to your OpenClaw binary path

def handle_client(conn):
    with conn:
        data = conn.recv(1024).decode().strip()
        if data:
            print(f"Received: {data}")
            result = subprocess.run(
                [OPENCLAW, 'agent', '--agent', 'badjanet', '--message', data],
                capture_output=True, text=True
            )
            print(f"Result: {result.stdout}")
            conn.sendall(result.stdout.encode('utf-8'))

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"BadJanet listener running on {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn,)).start()
