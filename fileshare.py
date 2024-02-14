
class FileShare:
    def __init__(self):
        self.file_to_size = {} # hash : size
        self.ip_to_files = {} # ip: [(hash, name), (hash, name)]
        self.hash_to_info = {}

    def __repr__(self):
        return self.refresh_data() # slow runtime

    def is_empty(self):
        return self.file_to_size == {}

    def receive_data(self, ip, files):
        file_lst = []
        for file in files:
            file_hash, file_name, file_size = file['hash'], file['file_name'], file['file_size']
            if file_hash not in self.file_to_size:
                self.file_to_size[file_hash] = file_size
            file_lst.append((file_hash, file_name))
        self.ip_to_files[ip] = file_lst

    def refresh_data(self):
        d = {} # hash: {size: #, names: {filenames}, ips: {ips}}
        for ip, files in self.ip_to_files.items():
            for fhash, fname in files:
                if fhash not in d:
                    d[fhash] = {'size': self.file_to_size[fhash], 'names': {fname}, 'ips': {ip}}
                else:
                    d[fhash]['names'].add(fname)
                    d[fhash]['ips'].add(ip)
        self.hash_to_info = d
        return d

    def get_peers_with_file(self, fhash):
        self.refresh_data() # can comment this out if we refresh it beforehand to print

        if fhash in self.hash_to_info:
            return self.hash_to_info[fhash]['ips']
        else:
            return set()