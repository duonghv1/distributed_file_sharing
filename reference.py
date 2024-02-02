import socket

def request_file(server_host, server_port, filename):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_host, server_port))
        s.sendall(filename.encode('utf-8'))
        response = s.recv(1024)
        if response:
            with open(filename, 'wb') as f:
                f.write(response)
            print(f"Received {filename}")
        else:
            print("File not found or error occurred")

# Example usage
server_host = '128.195.27.46'
server_port = 12345
filename = 'example.txt'
request_file(server_host, server_port, filename)


#######################################################################################
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
    message = b'Hello, peers!'
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.bind(('', my_port))  # Attempt to bind to the specified port
    except OSError as e:
        print(f"Error binding to port {my_port}: {e}")
        sock.close()  # Ensure the socket is closed before exiting
        return

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