import os
import math

def file_chunking(filepath, chunk_size, chunk_ind):
    # return the requested chunk based on chunk index of the specified file path in bytes
    filesize = os.path.getsize(filepath)
    chunk_start_pos = chunk_ind * chunk_size
    with open(filepath, "rb") as f:
        f.seek(chunk_start_pos)  
        data = f.read(chunk_size)
    return data


def combine_chunks(dir_loc, filename, file_ext, chunks):
    """ need to be updated later to sort the chunks based on some sort of meta data.
     For now, assume chunks in bytes are sorted
     """
    combined = b''.join(chunks)
    filepath = dir_loc + filename + '.' + file_ext
    with open(filepath, "wb") as f:
        f.write(combined)


def decode_data(binary_data, file_format):
    if file_format == "txt":
        return binary_data.decode('utf-8')
    elif file_format == "pdf":
        return 
    else:
        return None

filepath = r"C:\Users\thuyd\OneDrive\Desktop\school\cs230\distributed_file_sharing\files\lab5_diagram.pdf"
test_dir = r"C:\Users\thuyd\OneDrive\Desktop\school\cs230\distributed_file_sharing\files"
bin_data = []
chunk_size = 10000
number_chunks = math.ceil( os.path.getsize(filepath) / chunk_size )

for i in range(number_chunks):
    bin_data.append(file_chunking(filepath, chunk_size, i))

final_bin = combine_chunks(test_dir, "output", "pdf", bin_data)


        
        
        

