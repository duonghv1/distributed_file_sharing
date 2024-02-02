import socket
import threading

def listen_for_broadcasts():
<<<<<<< HEAD
    """Listens for broadcast messages on the local network and responds to them."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', my_port))  # Listen on all interfaces, UDP port my_port
=======
    """Listens for broadcast messages on the local network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', 12345))  # Listen on all interfaces, UDP port 12345
>>>>>>> 7e7ccd6331fe45dc2400ef0217e08da0fae0f309

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received message from {addr}: {data.decode()}")

<<<<<<< HEAD
        # Extract the sender's port number from addr
        sender_port = addr[1]

        # Prepare and send the response message
        response_message = f"Hello {sender_port}, I am {my_port}".encode()
        sock.sendto(response_message, addr)  # Send response to the sender's address and port

=======
>>>>>>> 7e7ccd6331fe45dc2400ef0217e08da0fae0f309
def send_broadcast():
    """Sends a broadcast message on the local network."""
    message = b'Hello, peers!'
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(message, ('<broadcast>', 12345))

if __name__ == "__main__":
<<<<<<< HEAD
    my_port = 12345  # This is your port number for listening and responding
    listener_thread = threading.Thread(target=listen_for_broadcasts, args=(my_port,))
    listener_thread.start()

    # Optionally, send a broadcast message to discover peers
    send_broadcast()
=======
    listener_thread = threading.Thread(target=listen_for_broadcasts)
    listener_thread.start()

    # Optionally, send a broadcast message to discover peers
    send_broadcast()
>>>>>>> 7e7ccd6331fe45dc2400ef0217e08da0fae0f309
