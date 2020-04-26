#!/usr/bin/python3.7
# -*- coding: utf-8 -*-
import argparse

from remover import remover


def argparser(trash_can: remover.SmartRM):
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
        try:
            trash_can.move_to_bin(args.path)
        except FileExistsError as err:
            print(err)
        else:
            print(f'File {args.path} moved to can')
    elif args.restore:
        if not args.path:
            print('Name of trash in can not entering')
            return
        try:
            trash_can.restore(args.path)
        except FileExistsError as err:
            print(err)
            print('What are you want to do?. Failed to restore. Restore path unavailable')
        else:
            print(f'File {args.path} restored from can')

    elif args.clear:
        if not args.path:
            print('Name of trash in can not entering')
            return
        try:
            trash_can.remove(args.path)
        except FileExistsError as err:
            print(err)
        else:
            print(f'File {args.path} removed from can')
    elif args.clearall:
        try:
            trash_can.clear_can()
        except FileExistsError as err:
            print(err)
        else:
            print('Trash can cleared')
    elif args.info:
        print(trash_can.trash_can_info())


if __name__ == '__main__':
    my_trash_can = remover.SmartRM()
    argparser(my_trash_can)
