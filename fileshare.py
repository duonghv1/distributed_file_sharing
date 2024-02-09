
class FileShare:
    def __init__(self):
        self.file_to_size = {} # hash : size
        self.ip_to_files = {} # ip: [(hash, name), (hash, name)]

    def receive_data(self, ip, files):
        file_lst = []
        for file in files:
            file_hash, file_name, file_size = file['hash'], file['file_name'], file['file_size']
            if file_hash not in self.file_to_size:
                self.file_to_size[file_hash] = file_size
            file_lst.append((file_hash, file_name))
        self.ip_to_files[ip] = file_lst

    def return_data(self):
        d = {} # hash: {size: #, names: {filenames}, ips: {ips}}
        for ip, files in self.ip_to_files.items():
            for fhash, fname in files:
                if fhash not in d:
                    d[fhash] = {'size': file_to_size[fhash], 'names': {fname}, 'ips': {ip}}
                else:
                    d[fhash]['names'].add(fname)
                    d[fhash]['ips'].add(ip)
        return d