import subprocess
import asyncio
import time
import os
import naive_node
import psutil


async def launch_peer_nodes(number_of_nodes, base_directory='./files/', base_port=9000, base_server_port=8000, broadcast_port=33333):
    """
    Create and runs a number of peer nodes from the naive network.
    """
    nodes = []
    tasks = []
    for i in range(1, number_of_nodes + 1):
        node_dir = os.path.join(base_directory, str(i))
        node = naive_node.PeerNetwork(
            base_directory=node_dir,
            port=base_port + i,
            server_port=base_server_port + i,
            broadcast_port=broadcast_port,
            timeout=1,
            cmd_line=False
        )
        task = asyncio.create_task(node.run())
        nodes.append(node)
        tasks.append(task)
    return nodes, tasks





async def terminate_nodes(nodes):
    terminate_tasks = [node.terminate() for node in nodes]
    await asyncio.gather(*terminate_tasks)

async def monitor_network_usage(duration):
    """
    Monitors the network usage for the specified duration and returns the total bytes sent and received.
    This is an async wrapper around the synchronous psutil monitoring to allow it to fit into the async flow.
    """
    start_time = time.time()
    python_processes = get_python_processes()

    # Snapshot of network stats at the beginning
    start_net_io = {p.pid: p.net_io_counters() for p in python_processes if hasattr(p, 'net_io_counters')}

    # Wait for the specified duration
    await asyncio.sleep(duration)

    # Snapshot of network stats at the end
    end_net_io = {p.pid: psutil.Process(p.pid).net_io_counters() for p in python_processes if psutil.pid_exists(p.pid) and hasattr(psutil.Process(p.pid), 'net_io_counters')}

    # Calculate the total bytes sent and received
    total_bytes_sent = sum(end_net_io[pid].bytes_sent - start_net_io[pid].bytes_sent for pid in end_net_io if pid in start_net_io)
    total_bytes_recv = sum(end_net_io[pid].bytes_recv - start_net_io[pid].bytes_recv for pid in end_net_io if pid in start_net_io)

    return total_bytes_sent, total_bytes_recv

def get_python_processes():
    """
    Returns a list of all running Python processes.
    """
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if process name or cmdline indicates a Python process
            if 'python' in proc.info['name'].lower():
                python_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return python_processes

async def test():
    # Start monitoring network usage in a background task
    monitor_task = asyncio.create_task(monitor_network_usage(5))

    # Launch peer nodes and allow them to operate
    # nodes, tasks = await launch_peer_nodes(3)
    # await asyncio.sleep(5)  # Let the nodes run for a bit

    # Terminate the nodes
    # await terminate_nodes(nodes)

    # Wait for the network monitoring task to complete
    bytes_sent, bytes_recv = await monitor_task
    print(f"Total bytes sent: {bytes_sent}, Total bytes received: {bytes_recv}")
    print(get_python_processes())

    monitor_task = asyncio.create_task(monitor_network_usage(5))

    # Launch peer nodes and allow them to operate
    nodes, tasks = await launch_peer_nodes(3)
    x = [n.find_hash('index:0') for n in nodes]
    await asyncio.gather(*x)
    print("s")
    await asyncio.sleep(4)  # Let the nodes run for a bit

    # Terminate the nodes
    await terminate_nodes(nodes)

    # Wait for the network monitoring task to complete
    bytes_sent, bytes_recv = await monitor_task
    print(f"Total bytes sent: {bytes_sent}, Total bytes received: {bytes_recv}")




def main():
    asyncio.run(test())


if __name__ == "__main__":
    main()
