import socket
import threading
import time
import os

def broadcast_presence(broadcast_port, server_port, interval=10):
    """
    Broadcasts this server's presence to the network every 'interval' seconds.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            message = f"DISCOVER:{server_port}".encode('utf-8')
            s.sendto(message, ('<broadcast>', broadcast_port))
            print(f"Broadcasted presence on port {broadcast_port}")
            time.sleep(interval)

broadcast_port = 12346  # Port used for discovery broadcasts

def listen_for_peers(broadcast_port):
    """
    Listens for broadcast messages from other peers to discover them.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('', broadcast_port))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while True:
            data, addr = s.recvfrom(1024)
            message = data.decode('utf-8')
            if message.startswith("DISCOVER:"):
                server_port = message.split(":")[1]
                print(f"Discovered peer at {addr[0]}:{server_port}")

# Start the discovery listener
threading.Thread(target=listen_for_peers, args=(broadcast_port,)).start()


def handle_client(conn, addr, base_directory):
    print(f"Connection from {addr}")
    try:
        # Receive file request
        filename = conn.recv(1024).decode('utf-8')
        filepath = os.path.join(base_directory, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                data = f.read()
                conn.sendall(data)
            print(f"Sent {filename} to {addr}")
        else:
            conn.sendall(b'File not found')
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def start_server(host, port, base_directory):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Listening on {host}:{port}")
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr, base_directory))
            client_thread.start()

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

if __name__ == "__main__":
    base_directory = '/shared/'
    host = '0.0.0.0'
    server_port = 12345  # Port for serving files
    broadcast_port = 12346  # Port for discovery broadcasts
    
    # Start server to serve files
    threading.Thread(target=start_server, args=(host, server_port, base_directory)).start()
    
    # Start broadcasting presence
    threading.Thread(target=broadcast_presence, args=(broadcast_port, server_port)).start()
    
    # Start listening for peers
    listen_for_peers(broadcast_port)
