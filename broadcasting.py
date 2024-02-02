import socket
import struct
import time

multicast_group = '224.3.29.71'  # An arbitrarily chosen multicast group address
multicast_port = 10000

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set the time-to-live for messages to 1 so they do not go past the local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

try:
    while True:
        # Send a "discovery" message to the multicast group
        message = 'PEER_DISCOVERY'
        print(f'Sending: {message}')
        sent = sock.sendto(message.encode(), (multicast_group, multicast_port))

        # Wait for a short period before sending the next message
        time.sleep(2)
finally:
    print('Closing socket')
    sock.close()
