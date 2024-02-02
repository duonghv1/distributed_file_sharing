import socket
import threading

def listen_for_broadcasts():
    """Listens for broadcast messages on the local network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', 12345))  # Listen on all interfaces, UDP port 12345

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received message from {addr}: {data.decode()}")

def send_broadcast():
    """Sends a broadcast message on the local network."""
    message = b'Hello, peers!'
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(message, ('<broadcast>', 12345))

if __name__ == "__main__":
    listener_thread = threading.Thread(target=listen_for_broadcasts)
    listener_thread.start()

    # Optionally, send a broadcast message to discover peers
    send_broadcast()