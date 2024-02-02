import socket
import threading
import time

def listen_for_broadcasts(my_port):
    """Listens for broadcast messages on the local network and responds to them."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', my_port))  # Listen on all interfaces, UDP port my_port

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received message from {addr}: {data.decode()}")

        # Extract the sender's port number from addr
        sender_port = addr[1]

        # Prepare and send the response message
        response_message = f"Hello {sender_port}, I am {my_port}".encode()
        sock.sendto(response_message, addr)  # Send response to the sender's address and port

def send_broadcast(my_port, target_port):
    """Sends a broadcast message on the local network from a specific port."""
    message = b'Hello, peers!'
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Bind the socket to a specific port number
    sock.bind(('', my_port))  # Bind to my_port for sending
    
    # Send the message to the target_port on all devices in the broadcast address
    sock.sendto(message, ('<broadcast>', target_port))
    sock.close()

if __name__ == "__main__":
    my_port = 12345  # Port from which to send messages
    target_port = 12345  # Target port to which messages are sent
    listener_thread = threading.Thread(target=listen_for_broadcasts, args=(target_port,))
    listener_thread.start()

    # Wait a moment for the listener to be ready (optional)
    time.sleep(1)

    # Send a broadcast message
    send_broadcast(my_port, target_port)