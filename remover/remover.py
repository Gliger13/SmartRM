import datetime
import json
import logging
import os
import threading
import zipfile
from functools import wraps
from pathlib import Path

from tools import tools

module_logger = logging.getLogger('SmartRM')
thread_lock = threading.Lock()


def check_path(func):
    @wraps(func)
    def inner(obj, *args):
        some_path, *args = args
        module_logger.debug('Checking path')
        if not os.path.exists(some_path):
            raise FileExistsError(f'File with path {some_path} not founded')
        # Test of change file access
        if not os.access(some_path, os.W_OK):
            raise FileExistsError(f'No access to change file {some_path}')
        if os.path.isabs(some_path):
            return func(obj, some_path, *args)
        else:
            some_path = os.path.abspath(some_path)
            return func(obj, some_path, *args)

    return inner


class RemovedFile:
    def __init__(self, removal_path, current_path):
        self.name = os.path.basename(removal_path)
        self.removal_path = os.path.split(removal_path)[0]
        self.removal_time = datetime.datetime.now().strftime("%d-%m-%Y,%H:%M:%S")
        self.current_path = current_path
        self.size = tools.size(removal_path)
        module_logger.debug('Create removed file')

    def information(self):
        file_information = {
            'file_name': self.name,
            'removal_path': self.removal_path,
            'removal_time': self.removal_time,
            'size': tools.convert_bytes(self.size)
        }
        return file_information


class SmartRM:
    ACCESS_RIGHTS = 0o777

    def __init__(self):
        home = str(Path.home())
        self.trash_can_path = os.path.join(home, 'TrashCan')
        if not os.path.exists(self.trash_can_path):
            os.mkdir(self.trash_can_path)
            os.chmod(self.trash_can_path, self.ACCESS_RIGHTS)
            self.trash_can_path = os.path.abspath(self.trash_can_path)
            module_logger.info(f'Trash can not found. Can created on {self.trash_can_path}')

    def _save_information(self, trash: RemovedFile):
        save_path = os.path.join(self.trash_can_path, '.trash_information.json')
        old_data = {}
        # Open save file if that exist
        if os.path.exists(save_path):
            with open(save_path) as file:
                if not os.path.getsize(save_path) == 0:
                    old_data.update(json.load(file))
        # Rewrite save file
        thread_lock.acquire()
        with open(save_path, 'w') as file:
            old_data[f'{trash.name}'] = trash.information()
            json.dump(old_data, file)
            module_logger.debug('Save information about the deleted file')
        thread_lock.release()

    @check_path
    def _move(self, path, path_to_move):
        module_logger.debug('Start move file')
        if os.path.isdir(path):
            # Create a directory in trash can
            dir_name = os.path.basename(path)
            new_dir_path = os.path.join(path_to_move, dir_name)
            if not os.path.exists(new_dir_path):
                os.mkdir(new_dir_path)
            module_logger.debug(f'Create new directory in can {new_dir_path}')
            list_of_files = os.listdir(path)
            for file in list_of_files:
                file_path = os.path.join(path, file)
                module_logger.debug('Find file in dir - call self')
                self._move(file_path, new_dir_path)
            # Now directory is empty. Remove
            os.rmdir(path)
            module_logger.debug('Dir is empty - remove')
        else:
            name_of_file = os.path.basename(path)
            file_path = os.path.join(path_to_move, name_of_file)
            os.replace(path, file_path)
            module_logger.debug('Find file - replace in can')

    @check_path
    def _remove(self, path):
        if os.path.isdir(path):
            list_of_files = os.listdir(path)
            for file in list_of_files:
                file_path = os.path.join(path, file)
                self._remove(file_path)
            module_logger.debug('Remove empty directory')
            os.rmdir(path)
        else:
            module_logger.debug('Remove file')
            os.remove(path)

    def _compress(self, name_of_trash: str):
        module_logger.debug(f'Compressing file {name_of_trash}')
        trash_path = os.path.join(self.trash_can_path, name_of_trash)
        thread_lock.acquire()
        with zipfile.ZipFile(trash_path + '.zip', 'w', allowZip64=True) as zip_file:
            for root, dirs, files in os.walk(trash_path):
                for file in files:
                    zip_file.write(os.path.join(root, file),
                                   os.path.relpath(os.path.join(root, file), self.trash_can_path))
        thread_lock.release()
        module_logger.debug(f'File {name_of_trash} compressed')
        self._remove(trash_path)

    def _decompress(self, name_of_trash):
        module_logger.debug(f'Decompressing file {name_of_trash}')
        trash_path = os.path.join(self.trash_can_path, name_of_trash)
        with zipfile.ZipFile(trash_path + '.zip') as zip_file:
            zip_file.extractall(os.path.split(trash_path)[0])
        module_logger.debug(f'File {name_of_trash} decompressed')
        self._remove(trash_path + '.zip')

    def load_information(self) -> dict:
        save_path = os.path.join(self.trash_can_path, '.trash_information.json')
        data = {}
        if os.path.exists(save_path):
            with open(save_path) as file:
                if not os.path.getsize(save_path) == 0:
                    data.update(json.load(file))
                return data
        else:
            raise FileExistsError('File to restore was not found')

    def update_information(self, rm_name):
        save_path = os.path.join(self.trash_can_path, '.trash_information.json')
        module_logger.debug(f'Information about trash updated')
        thread_lock.acquire()
        old_data = self.load_information()
        old_data.pop(rm_name)
        with open(save_path, 'w') as file:
            json.dump(old_data, file)
        thread_lock.release()

    @check_path
    def move_to_bin(self, path):
        module_logger.debug(f'Start file moving to trash can {path}')
        name_of_trash = os.path.basename(path)
        # If the user used a similarity path to 'dir/'
        if not name_of_trash:
            for file in os.listdir(path):
                trash_path = os.path.join(path, file)
                self.move_to_bin(trash_path)
            return
        new_trash_path = os.path.join(self.trash_can_path, name_of_trash)
        trash = RemovedFile(path, new_trash_path)
        # Checking free space
        disk_space = os.statvfs(self.trash_can_path).f_bfree
        if disk_space < trash.size:
            raise FileExistsError(f'No free disk space. {disk_space} left. {trash.size} needed')
        self._move(path, self.trash_can_path)
        self._compress(name_of_trash)
        self._save_information(trash)
        module_logger.info('File has been moved to trash can')

    def restore(self, name_of_trash: str):
        module_logger.debug(f'Start restoring {name_of_trash}')
        data = self.load_information()
        if data and name_of_trash in data:
            # Get information about file in trash can
            new_data = data.pop(name_of_trash)
            path_of_file = os.path.join(self.trash_can_path, name_of_trash)
            path_to_restore = new_data['removal_path']
            self._decompress(name_of_trash)
            self._move(path_of_file, path_to_restore)
            self.update_information(name_of_trash)
            module_logger.info('File restored')
        else:
            raise FileExistsError(f'Trash {name_of_trash} was not found in trash can')

    def remove(self, name_of_trash: str):
        trash_path = os.path.join(self.trash_can_path, name_of_trash)
        data = self.load_information()
        if data and name_of_trash in data:
            self._remove(trash_path + '.zip')
            module_logger.info(f'File deleted {name_of_trash}')
            # Update information
            data.pop(f'{name_of_trash}')
            self.update_information(name_of_trash)
        else:
            raise FileExistsError(f'Trash {name_of_trash} was not found in trash can')

    def trash_can_info(self):
        save_path = os.path.join(self.trash_can_path, '.trash_information.json')
        if not os.path.exists(save_path):
            return 'Trash can is empty'
        more_trash = '-' * 31 + '+' + '-' * 12 + '+' + '-' * 30 + '\n'
        information = (f"Trash can information:\n"
                       f"{'name':^30} | {'size':^10} | {'removal time':^30}\n" + more_trash)
        with open(save_path) as file:
            data = json.load(file)
            if not data:
                return 'Trash can is empty'
            for files in data:
                info = data[files]
                information += (f"{info['file_name']:^30} | "
                                f"{info['size']:^10} | "
                                f"{info['removal_time']:^30}\n")
        module_logger.debug('Send information about trash')
        return information

    def clear_can(self):
        module_logger.debug('Start cleaning trash can')
        file_list = os.listdir(self.trash_can_path)
        for file in file_list:
            if file == '.trash_information.json':
                continue
            remover = threading.Thread(target=self.remove, args=(file[:-4],))
            remover.start()
        module_logger.info('Trash can cleared')
