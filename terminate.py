import psutil
import os
import time

def terminate_python_processes():
    node_sizes = [16]
    while True:
        processes = []
        for process in psutil.process_iter(['name']):
            if process.info['name'] == 'Python' and process.pid != os.getpid():
                processes.append(process)
        print(len(processes))
        if len(processes)-2 in node_sizes:
            pids = sorted([process.pid for process in processes])
            pids = pids[2:]
            pids = pids[len(pids)//2:]
            time.sleep((len(processes)-2)+11+2)
            print('Terminating processes')
            for pid in pids:
                os.system(f'kill -9 {pid}')
                print('kill?')
        time.sleep(0.1)


if __name__ == "__main__":
    terminate_python_processes()
