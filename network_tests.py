import asyncio
import os
import naive_node
import kademlia_node
import multiprocessing
import subprocess
import shutil
import time
from src.file_store import File
from sys import platform


async def async_runner(node, command_queue, result_queue):
    while True:
        if not command_queue.empty():
            func, args = command_queue.get()
            result = await getattr(node, func)(*args)
            result_queue.put(result)
        await asyncio.sleep(0.1)


async def run_node(node, startup_time):
    await asyncio.sleep(startup_time)
    await node.run()


async def start_async_node(node, command_queue, result_queue, startup_time):
    await asyncio.gather(
        run_node(node, startup_time),
        async_runner(node, command_queue, result_queue)
    )


def start_async_node_process(node, command_queue, result_queue, startup_time):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_async_node(node, command_queue, result_queue, startup_time))
    loop.close()


async def launch_nodes(number_of_nodes, base_directory='./test_files/', base_port=9000, base_server_port=8000, node_type='Naive', download_rate=1024*100):
    """
    Create and runs a number of peer nodes from the naive network.
    """
    nodes = []
    queues = []
    for i in range(1, number_of_nodes + 1):
        node_dir = os.path.join(base_directory, str(i))
        if not os.path.exists(node_dir):
            os.makedirs(node_dir, exist_ok=True)
        if node_type == "naive":
            node = naive_node.PeerNetwork(node_dir, base_port + i, base_server_port + i, 33333, cmd_line=False, download_rate=download_rate)
        elif node_type == "kademlia":
            node = kademlia_node.PeerNetwork(node_dir, base_port + i, base_server_port + i, ('0.0.0.0', 9001), cmd_line=False, download_rate=download_rate)
        else:
            raise ValueError("Invalid node type")
        command_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=start_async_node_process, args=(node, command_queue, result_queue, 1+i*0.5))
        process.start()
        nodes.append(process)
        queues.append((command_queue, result_queue))
    return nodes, queues


async def terminate_nodes(nodes, delay=0):
    await asyncio.sleep(delay)
    print(f"Terminating {len(nodes)} node(s)...")
    for proc in nodes:
        if proc:
            proc.terminate()
    await asyncio.sleep(1)
    for proc in nodes:
        if proc:
            proc.join()


async def call_function(queue, func, *args):
    command_queue, result_queue = queue
    command_queue.put((func, args))
    result = result_queue.get()
    return result


def create_nettop_task(pids, n_nodes, node_type):
    if platform == "darwin":
        return asyncio.create_task(run_nettop(pids, n_nodes, node_type))
    return asyncio.create_task(asyncio.sleep(0))


async def run_nettop(pids, n_samples, node_type):
    await asyncio.sleep(1)
    cmd = ['nettop'] + [f'-p {p}' for p in pids] + [f'-L {n_samples}'] + ['-s 1'] + ['-J bytes_in,bytes_out']
    output = []
    print(f"Monitoring network activity for {n_samples} seconds...")
    nettop_proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE)
    line_num = 0
    try:
        while True:
            output_chunk = await nettop_proc.stdout.readline()
            if not output_chunk:
                break
            line = output_chunk.decode('utf8', errors='strict').strip()
            output.append(line.replace('\n', ''))
            line_num += 1
    except asyncio.CancelledError:
        pass
    # for i in range(len(output)-1, 0, -1):
    #     if output[i].startswith('Python.' + str(pids[0])):
    #         start = i
    #         break
    return output


def parse_nettop_output(output, pids):
    if platform != "darwin" or not output:
        return None
    pids_to_nodes = {str(pid): pids.index(pid)+1 for pid in sorted(pids)}
    traffic_data = {}
    total_bytes = {'bytes_in': 0, 'bytes_out': 0}
    cleaned_output = {}
    proc_name = None
    for line in output:
        name, bytes_in, bytes_out, _ = line.split(',')
        if not name:
            continue
        if name.startswith('Python'):
            proc_name = name
            cleaned_output[proc_name] = [line]
        else:
            cleaned_output[proc_name].append(line)
    output = [line for name in sorted(cleaned_output) for line in cleaned_output[name]]
    for line in output:
        name, bytes_in, bytes_out, _ = line.split(',')
        if not bytes_in:
            bytes_in = 0
        if not bytes_out:
            bytes_out = 0
        bytes_data = {'bytes_in': bytes_in, 'bytes_out': bytes_out}
        total_bytes['bytes_in'] += int(bytes_in)
        total_bytes['bytes_out'] += int(bytes_out)
        if name.startswith('Python'):
            node_id = pids_to_nodes[name.split('.')[1]]
            traffic_data[node_id] = bytes_data
    traffic_data['total'] = total_bytes
    return traffic_data


def create_unique_file(filename, bytes):
    with open(filename, 'wb') as file:
        while file.tell() < bytes:
            file.write(os.urandom(1024))


def init_files(n_files, base_directory='./test_files/'):
    files = {}
    if not os.path.exists(base_directory):
        os.makedirs(base_directory, exist_ok=True)
    for file_name in [('A', 1024), ('B', 1024*1024), ('C', 1024*1024*100)]:
        if not os.path.exists(os.path.join(base_directory, file_name[0])):
            create_unique_file(os.path.join(base_directory, file_name[0]), file_name[1])
        files[file_name[0]] = File(os.path.join(base_directory, file_name[0])).hash()
    for i in range(1, n_files + 1):
        dir = os.path.join(base_directory, f'{i}')
        if not os.path.exists(dir):
            os.makedirs(dir, exist_ok=True)
        for file_name in os.listdir(dir):
            if file_name not in ['A', 'B', 'C'] or i == 1:
                os.remove(os.path.join(dir, file_name))
        if i != 1:
            if not os.path.exists(os.path.join(dir, 'A')):
                shutil.copy(os.path.join(base_directory, 'A'), os.path.join(dir, 'A'))
            if not os.path.exists(os.path.join(dir, 'B')):
                shutil.copy(os.path.join(base_directory, 'B'), os.path.join(dir, 'B'))
            if not os.path.exists(os.path.join(dir, 'C')):
                shutil.copy(os.path.join(base_directory, 'C'), os.path.join(dir, 'C'))
    return files


def bytes_to_str(num_bytes):
    num_bytes = int(num_bytes)
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024**2:
        return f"{num_bytes / 1024:.2f} KB"
    elif num_bytes < 1024**3:
        return f"{num_bytes / 1024**2:.2f} MB"
    elif num_bytes < 1024**4:
        return f"{num_bytes / 1024**3:.2f} GB"


def log(msg):
    with open('test_log.txt', 'a') as f:
        f.write(msg + '\n')
    print(msg)


def format_stats(stats):
    # subheader = " " * 21 + "node 1" + " " * 27 + "total network\n"
    # columns = "   nodes    time    bytes_recv    bytes_sent       bytes_recv    bytes_sent\n"
    formatted_str = "\n"
    f = '    {0:>10}   {1:<10} {2:<14} {3:<14} {4:<14} {5:<14}'
    formatted_str += f.format("", "", "Node 1 Traffic", "", "Total Traffic", "") + '\n'
    formatted_str += f.format("nodes", "time", "bytes_recv", "bytes_sent", "bytes_recv", "bytes_sent") + '\n'
    n_type = None
    for stat in stats:
        node_type, n_nodes, time_elapsed, traffic_data = stat
        if n_type != node_type:
            formatted_str += f"{node_type.capitalize():>8}\n"
            n_type = node_type
        n1_bytes_recv = bytes_to_str(traffic_data[1]['bytes_in'])
        n1_bytes_sent = bytes_to_str(traffic_data[1]['bytes_out'])
        total_bytes_recv = bytes_to_str(traffic_data['total']['bytes_in'])
        total_bytes_sent = bytes_to_str(traffic_data['total']['bytes_out'])
        formatted_str += f.format(n_nodes, str(round(time_elapsed, 3))+' sec', n1_bytes_recv, n1_bytes_sent, total_bytes_recv, total_bytes_sent) + '\n'
    return formatted_str


class TestRunner():
    def __init__(self, n_nodes, node_type, nettop_samples=5):
        self.n_nodes = n_nodes
        self.node_type = node_type
        self.nettop_samples = nettop_samples
        self.nodes = None
        self.pids = None
        self.nettop_task = None
        self.files = None

    async def start(self):
        self.files = init_files(self.n_nodes)
        self.nodes, queues = await launch_nodes(self.n_nodes, node_type=self.node_type)
        self.pids = [node.pid for node in self.nodes]
        await asyncio.sleep(self.n_nodes+5)
        self.nettop_task = create_nettop_task(self.pids, self.nettop_samples, self.node_type)
        await asyncio.sleep(1)
        return queues

    async def terminate(self):
        traffic_data = parse_nettop_output(await self.nettop_task, self.pids)
        await terminate_nodes(self.nodes)
        return traffic_data


async def run_tests(node_sizes, func, nettop_samples=5):
    stats = []
    for n in node_sizes:
        stats.append(await func(n, "naive", nettop_samples))
        await asyncio.sleep(5)
    for n in node_sizes:
        stats.append(await func(n, "kademlia", nettop_samples))
        await asyncio.sleep(5)
    return format_stats(stats)


async def test_ls_remote(n_nodes, node_type, nettop_samples):
    test = TestRunner(n_nodes, node_type, nettop_samples)
    queues = await test.start()
    await asyncio.sleep(1)

    print("Executing ls remote...")
    start_time = time.time()
    if node_type == "naive":
        await call_function(queues[0], "find_hash", "index:0", n_nodes-1)
    elif node_type == "kademlia":
        await call_function(queues[0], "find_hash", "index:0")
    time_elapsed = time.time() - start_time

    traffic_data = await test.terminate()
    return node_type, n_nodes, time_elapsed, traffic_data


async def test_find_hash(n_nodes, node_type, nettop_samples):
    test = TestRunner(n_nodes, node_type, nettop_samples)
    queues = await test.start()
    await asyncio.sleep(1)

    print("Executing find...")
    start_time = time.time()
    if node_type == "naive":
        await call_function(queues[0], "find_hash", test.files['A'], n_nodes-1)
    elif node_type == "kademlia":
        await call_function(queues[0], "find_hash", test.files['A'])
    time_elapsed = time.time() - start_time

    traffic_data = await test.terminate()
    return node_type, n_nodes, time_elapsed, traffic_data


async def test_download(n_nodes, node_type, nettop_samples):
    """
    Test download of file C (100 MB) from remote nodes
    Nodes upload/download files at 100 KB/s
    """
    test = TestRunner(n_nodes, node_type, nettop_samples)
    queues = await test.start()
    await asyncio.sleep(5)

    print("Executing download...")
    start_time = time.time()
    if node_type == "naive":
        await call_function(queues[0], "download_file", test.files['C'], n_nodes-1)
    elif node_type == "kademlia":
        await call_function(queues[0], "download_file", test.files['C'])
    time_elapsed = time.time() - start_time

    traffic_data = await test.terminate()
    return node_type, n_nodes, time_elapsed, traffic_data


def main():
    open('test_log.txt', 'w').close()  # Clear log
    nodes_sizes = [2, 4, 8, 16]
    log("Benchmarks:")
    log("\nls remote - retrieve files from remote nodes")
    stats = asyncio.run(run_tests(nodes_sizes, test_ls_remote, 10))
    log(stats)
    log("\nfind hash - search for file hash from remote nodes")
    stats = asyncio.run(run_tests(nodes_sizes, test_find_hash, 10))
    log(stats)
    log("\ndownload 100 MB file - download file from remote nodes at 100 KB/s")
    stats = asyncio.run(run_tests(nodes_sizes, test_download, 40))
    log(stats)


if __name__ == "__main__":
    main()
