#!/usr/bin/python3.7
# -*- coding: utf-8 -*-
import argparse
import datetime
import json
import logging
import os
from functools import wraps
from pathlib import Path

from tools import logger
from tools import tools

module_logger = logging.getLogger('SmartRM')


def make_abs_path(func):
    @wraps(func)
    def inner(obj, *args):
        some_path, *args = args
        if os.path.exists(some_path):
            if os.path.abspath(some_path):
                return func(obj, some_path, *args)
            else:
                some_path = os.path.abspath(some_path)
                return func(obj, some_path, *args)
        else:
            return False
    return inner


class RemovedFile:
    def __init__(self, removal_path, current_path):
        self.name = os.path.basename(removal_path)
        self.removal_path = os.path.split(removal_path)[0]
        self.removal_time = datetime.datetime.now().strftime("%d-%m-%Y,%H:%M:%S")
        self.current_path = current_path
        self.size = tools.convert_bytes(tools.size(removal_path))
        module_logger.debug('Create removed file')

    def information(self):
        file_information = {
            'file_name': self.name,
            'removal_path': self.removal_path,
            'removal_time': self.removal_time,
            'size': self.size
        }
        return file_information


class SmartRM:
    ACCESS_RIGHTS = 0o777

    def __init__(self):
        home = str(Path.home())
        self.trash_can_path = os.path.join(home, 'Trash_can')
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
            with open(save_path, 'r') as file:
                if not os.path.getsize(save_path) == 0:
                    old_data.update(json.load(file))
        # Rewrite save file
        with open(save_path, 'w') as file:
            old_data[f'{trash.name}'] = trash.information()
            json.dump(old_data, file)
            module_logger.debug('Save information about the deleted file')

    @make_abs_path
    def _move(self, path, path_to_move):
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

    @make_abs_path
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

    def load_information(self) -> dict or bool:
        save_path = os.path.join(self.trash_can_path, '.trash_information.json')
        data = {}
        if os.path.exists(save_path):
            with open(save_path, 'r') as file:
                if not os.path.getsize(save_path) == 0:
                    data.update(json.load(file))
                return data
        else:
            module_logger.debug('File to restore not founded')
            return False

    def update_information(self, data: dict):
        save_path = os.path.join(self.trash_can_path, '.trash_information.json')
        with open(save_path, 'w') as file:
            json.dump(data, file)

    @make_abs_path
    def move_to_bin(self, path):
        name_of_trash = os.path.basename(path)
        if not name_of_trash:
            for file in os.listdir(path):
                trash_path = os.path.join(path, file)
                self.move_to_bin(trash_path)
            return True
        new_trash_path = os.path.join(self.trash_can_path, name_of_trash)
        trash = RemovedFile(path, new_trash_path)
        self._move(path, self.trash_can_path)
        self._save_information(trash)
        module_logger.info('File has been moved to trash can')
        return True

    def restore(self, name_of_trash: str) -> bool:
        data = self.load_information()
        if data and name_of_trash in data:
            new_data = data.pop(f'{name_of_trash}')
            self.update_information(data)
            path_to_restore = new_data['removal_path']
            path_of_file = os.path.join(self.trash_can_path, name_of_trash)
            self._move(path_of_file, path_to_restore)
            module_logger.info('File restored')
            return True
        return False

    def remove(self, name_of_trash: str) -> bool:
        trash_path = os.path.join(self.trash_can_path, name_of_trash)
        data = self.load_information()
        if data and name_of_trash in data:
            self._remove(trash_path)
            module_logger.info('File deleted')
            # Update information
            data.pop(f'{name_of_trash}')
            self.update_information(data)
            return True
        return False

    def trash_can_info(self):
        save_path = os.path.join(self.trash_can_path, '.trash_information.json')
        if not os.path.exists(save_path):
            return 'Trash can is empty'
        more_trash = '-' * 62 + '\n'
        information = (f"Trash can information:\n"
                       f"{'name':30} | {'size':6} | {'removal time':10}\n" + more_trash)
        with open(save_path) as file:
            data = json.load(file)
            for files in data:
                info = data[files]
                information += (f"{info['file_name']:30} | "
                                f"{info['size']:6} | "
                                f"{info['removal_time']:10}\n")
        module_logger.debug('Get information about trash')
        return information

    def clear_can(self):
        file_list = os.listdir(self.trash_can_path)
        for file in file_list:
            if file == '.trash_information.json':
                continue
            self.remove(file)
            module_logger.info('Trash can cleared')


def argparser(trash_can: SmartRM):
    parser = argparse.ArgumentParser(description='SmartRM for deleting files')
    parser.add_argument('path', type=str, nargs='?', help='The path to the file or')
    path_group = parser.add_mutually_exclusive_group(required=False)
    path_group.add_argument('-rm', '--remove', action='store_true', help='Move trash in can')
    name_group = parser.add_mutually_exclusive_group(required=False)
    name_group.add_argument('-rs', '--restore', action='store_true', help='Move trash from can')
    name_group.add_argument('-c', '--clear', action='store_true', help='Remove trash from can')
    additional_group = parser.add_mutually_exclusive_group(required=False)
    additional_group.add_argument('-ca', '--clearall', action='store_true', help='Remove all trash from can')
    additional_group.add_argument('-i', '--info', action='store_true', help='Show all information about files in can')
    args = parser.parse_args()

    if args.remove:
        if not args.path:
            print('Path not entering')
            return
        result = trash_can.move_to_bin(args.path)
        if result:
            print(f'File {args.path} moved to can')
        else:
            print(f'File {args.path} not founded')
    elif args.restore:
        if not args.path:
            print('Name of trash in can not entering')
            return
        result = trash_can.restore(args.path)
        if result:
            print(f'File {args.path} restored from can')
        else:
            print('What are you want to do?. Failed to restore. Restore path unavailable')
    elif args.clear:
        if not args.path:
            print('Name of trash in can not entering')
            return
        trash_can.remove(args.path)
        print(f'File {args.path} removed from can')
    elif args.clearall:
        trash_can.clear_can()
        print('Trash can cleared')
    elif args.info:
        print(trash_can.trash_can_info())


if __name__ == '__main__':
    my_trash_can = SmartRM()
    argparser(my_trash_can)
