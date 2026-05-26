#!/usr/bin/env python3
"""
Auther: Wes Cratty
Created: 1/18/2023
File: fileHelper.py

Description: util class handling file io

"""

import os
import webbrowser
from tkinter import filedialog
import xmltodict
import utility_modules as um
import csv


class FileHelper:
    """
    Utility Class assisting in file read and write
    """
    def __init__(self):
        self.ask_directory = filedialog.askdirectory
        self.ask_file = filedialog.askopenfile
        self.paths_that_end_with = list()
        self.travers = um.t()
        self.html_table_style = '<style>table, th, td {border: 1px solid black;table-layout: auto;width: auto;}</style>'
        self.sheets = ['Sheet1', 'Sheet2', 'Sheet3', 'Sheet4', 'Sheet5', 'Sheet6']

    @staticmethod
    def get_dict_from_xml(file_selected):
        """
        Opens file and returns python dictionary
        """

        path = file_selected
        if os.path.isfile(path):
            with open(path) as fd:
                return xmltodict.parse(fd.read(), process_namespaces=True)
        else:
            print('Path does not work', path)


    @staticmethod
    def write_file(contents, path, output, encoding):
        """
        Open file path and write contents and closes file after:
        path: path to file
        """

        encoding = encoding if encoding else 'utf-8'
        output = output if output else 'w'
        out_file = open(path, output, encoding=encoding)
        out_file.write(contents)
        out_file.close()


    @staticmethod
    def verify_export_dir(directory):
        """
        If path does not exist, create directory chain
        """

        if not os.path.isdir(directory):
            os.makedirs(directory)

    def find_all_files_ends_with(self, search_str):
        """
        Opens file explorer, input point for future search string
        """

        root = self.ask_directory()
        self.paths_that_end_with = list()
        self.travers_file_tree(root, search_str)
        return {'message': 'Found ' + str(len(self.paths_that_end_with)) + ' file(s) ending in ' + search_str,
                'paths_that_end_with': self.paths_that_end_with, 'root': root}

    def find_file_ends_with(self, search_str):
        """
        Opens file explorer, input point for future search string
        """
        ret = self.ask_file()
        name = ''
        if hasattr(ret, 'name'):
            name = ret.name
        return name

    def travers_file_tree(self, root, search_str):
        """
        Recursively dig down and find all the matching files
        """

        if os.path.isdir(root):
            dir_list = os.listdir(root)
            for item in dir_list:
                path = os.path.join(root, item)
                print(path)
                self.travers_file_tree(path, search_str)
        else:
            if root.endswith(search_str):
                self.paths_that_end_with.append(root)

    @staticmethod
    def format_new_file_name(path, num_dirs_to_show):
        """
        Pulls out all the odd unicode chars in path
        """

        path = os.path.normpath(path)
        path_array = path.split(os.sep)
        # slice off the last num_dirs_to_show, map remaining array items to string and joins
        return ''.join(map(str, path_array[num_dirs_to_show:]))

    def write_csv_to_excel(self, export_dir, export_file_name_str, stack_dict, template_location):
        """
        Prepares file name for export and confirms path
        Attempts to write to excel workbook
        Alerts user if error occurs
        """

        file_name = export_file_name_str + '_.xlsm'
        self.verify_export_dir(export_dir)
        full_path = os.path.join(export_dir, file_name)
        success = self.write_to_specific_excel_file(stack_dict, full_path, template_location)
        return 1 if success else 0

    def display_current_data(self, root, export_dir, tree_html):
        """
        Calls traverse tree
        Collects leave object data
        Returns html and creates html file
        """

        if root and (hasattr(root, 'keys') or len(root)):
            html_str = self.html_table_style
            html_str += '<table><tr>'
            html_str += self.travers.get_html_data(root)
            self.verify_export_dir(export_dir)
            full_path = os.path.join(export_dir, tree_html)
            self.write_file(html_str, full_path, False, False)
            webbrowser.open(full_path)  # opens the newly created html for user

    @staticmethod
    def parse_csv_to_dict(filename):
        """
        """

        ret = {}

        with open(filename, 'r', newline='', encoding='utf-8') as data:
            reader = csv.DictReader(data)

            # Initialize keys from headers
            for field in reader.fieldnames:
                ret[field] = []

            # Fill lists
            for row in reader:
                for field in reader.fieldnames:
                    ret[field].append(row[field])

        return ret
