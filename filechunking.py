import os

def get_file_chunk(filepath, chunk_size, chunk_ind):
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
    filepath = dir_loc + filename + file_ext
    with open(filepath, "wb") as f:
        f.write(combined)
    return filepath


def decode_data(binary_data, file_format):
    if file_format == "txt":
        return binary_data.decode('utf-8')
    elif file_format == "pdf":
        return 
    else:
        return None



        
        
        

