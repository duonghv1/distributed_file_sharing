from scapy.all import sniff

# Initialize counters
bytes_sent = 0
bytes_received = 0

def packet_callback(packet):
    global bytes_sent, bytes_received
    # Since we're not filtering by TCP/UDP in the sniff function,
    # we need to determine the direction based on IP layer information.
    print(packet)
    if packet.haslayer("IP"):
        if packet["IP"].dport == 9000:
            # Increment bytes_received for incoming packets to the port
            bytes_received += len(packet)
        elif packet["IP"].sport == 9000:
            # Increment bytes_sent for outgoing packets from the port
            bytes_sent += len(packet)


def monitor_network(port=9000, duration=10):
    # Monitor all traffic on the specified port, regardless of the protocol
    print(f"Monitoring all protocols on port {port} for {duration} seconds...")
    sniff(filter=f"port {port}", prn=packet_callback, store=False, timeout=duration)

    # Output the total bytes sent and received
    print(f"Total bytes sent: {bytes_sent}")
    print(f"Total bytes received: {bytes_received}")

if __name__ == "__main__":
    monitor_network(port=9000, duration=10)
