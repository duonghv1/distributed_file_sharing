import asyncio
import signal
import sys

buffer = ""
# Register SIGINT handler
def __sigint_handler(signum, frame):
    print("Received SIGINT. Exiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, __sigint_handler)


def read_func_producer():
    if sys.platform == "win32":
        import msvcrt

        async def read_input():
            global buffer
            input_buffer = ""
            while True:
                if msvcrt.kbhit():
                    char = msvcrt.getch().decode()
                    print(char, flush=True, end="")
                    # If the Enter key is pressed, return the input
                    if char == "\r":
                        print()
                        buffer = input_buffer
                        return
                    elif char == "\x08":  # Backspace key
                        if input_buffer:  # Check if input_buffer is not empty
                            # Move cursor back one character, overwrite the character with a space,
                            print(" \b", end="")
                            input_buffer = input_buffer[:-1]  # Remove the last character from input_buffer
                    else:
                        input_buffer += char  # Append the character to the input buffer

                await asyncio.sleep(0.01)  # Sleep briefly to avoid busy-waiting
        return read_input

    else:  # For Unix-like systems
        import select
        async def read_input():
            global buffer
            while True:
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    user_input = sys.stdin.readline().strip()
                    buffer = user_input
                    return user_input
                await asyncio.sleep(0.01)  # Sleep briefly to avoid busy-waiting
        return read_input


async def nonblocking_read():
    read_input_func = read_func_producer() # Get the appropriate read_input() function based on the platform
    await read_input_func() # Start reading input asynchronously

    
def nb_read_input(prompt):
    print(prompt, flush=True, end="")
    asyncio.run(nonblocking_read())
    return buffer


if __name__ == "__main__":
    while True:
        value = nb_read_input("your name : ")
        print(value)

