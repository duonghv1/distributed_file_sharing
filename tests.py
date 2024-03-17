import asyncio
import os
import naive_node
import multiprocessing
import subprocess
import re

async def async_runner(node, queue):
    while True:
        # Check if there is any function call in the queue
        if not queue.empty():
            # Get the function call and its arguments from the queue
            func, args = queue.get()
            # Call the function with arguments
            await getattr(node, func)(*args)  # Call the function dynamically
        # Sleep briefly to avoid consuming too much CPU
        await asyncio.sleep(0.1)


async def run_node(node):
    await asyncio.sleep(2)
    await node.run()


async def start_async_node(node, queue):
    await asyncio.gather(
        run_node(node),
        async_runner(node, queue)
    )


def start_async_node_process(node, queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_async_node(node, queue))
    loop.close()


async def launch_peer_nodes(number_of_nodes, base_directory='./files/', base_port=9000, base_server_port=8000, broadcast_port=33333):
    """
    Create and runs a number of peer nodes from the naive network.
    """
    nodes = []
    queues = []
    for i in range(1, number_of_nodes + 1):
        node_dir = os.path.join(base_directory, str(i))
        if not os.path.exists(node_dir):
            os.makedirs(node_dir, exist_ok=True)
        node = naive_node.PeerNetwork(node_dir, base_port + i, base_server_port + i, broadcast_port, cmd_line=False)
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=start_async_node_process, args=(node, queue))
        process.start()
        nodes.append(process)
        queues.append(queue)
    return nodes, queues


async def terminate_nodes(nodes):
    for proc in nodes:
        proc.terminate()
    await asyncio.gather(*(proc.wait() for proc in nodes))


def call_function(queue, func, *args):
    queue.put((func, args))



async def test():
    # Launch peer nodes and allow them to operate
    nodes, queues = await launch_peer_nodes(3)
    pids = [node.pid for node in nodes]
    await asyncio.sleep(3)

    call_function(queues[0], "find_hash", "index:0")
    print("Called function")
    pid = nodes[0].pid




    print("Terminating nodes")
    # Terminate the nodes
    # await terminate_nodes(nodes)

def main():
    asyncio.run(test())

if __name__ == "__main__":
    main()
