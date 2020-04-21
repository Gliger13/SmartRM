import os

def convert_bytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f'{num:.1f} {x}'
        num /= 1024.0


def size(path: str) -> int:
    """
    Gets file or folder size recursively in bytes
    :param path: path to file or folder
    :return bytes: size of file or folder
    """
    if os.path.isdir(path):
        result = os.path.getsize(path)
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            result += size(file_path)
        return result
    else:
        return os.path.getsize(path)


