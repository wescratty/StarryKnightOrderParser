#!/usr/bin/env python3
"""
Auther: Wes Cratty
Created: 1/18/2023
File: fileHelper.py

Description: util class handling file io

"""

import os
from tkinter import filedialog
import xmltodict
import csv


class FileHelper:
    """
    Utility Class assisting in file read and write
    """
    def __init__(self):
        self.ask_directory = filedialog.askdirectory
        self.ask_file = filedialog.askopenfile
        self.paths_that_end_with = list()
        self.html_table_style = '<style>table, th, td {border: 1px solid black;table-layout: auto;width: auto;}</style>'
        self.sheets = ['Sheet1', 'Sheet2', 'Sheet3', 'Sheet4', 'Sheet5', 'Sheet6']

    def find_config_dir(self):
        """
        """
        return self.ask_directory()

    def find_file(self):
        """
        Opens file explorer, input point for future search string
        """
        ret = self.ask_file()
        name = ''
        if hasattr(ret, 'name'):
            name = ret.name
        return name

    @staticmethod
    def format_new_file_name(path, num_dirs_to_show):
        """
        Pulls out all the odd unicode chars in path
        """

        path = os.path.normpath(path)
        path_array = path.split(os.sep)
        # slice off the last num_dirs_to_show, map remaining array items to string and joins
        return ''.join(map(str, path_array[num_dirs_to_show:]))

    @staticmethod
    def parse_csv_to_dict(filename):
        """
        Reads a CSV into a dict of column -> list of values.
        Returns an empty dict (falsy) if the file can't be read or parsed,
        so callers can check `if not csv_tree:` rather than catching
        exceptions themselves.
        """

        ret = {}

        try:
            # utf-8-sig transparently strips a BOM if the file picked one up
            # from being re-saved in Excel; plain utf-8 files are unaffected.
            with open(filename, 'r', newline='', encoding='utf-8-sig') as data:
                reader = csv.DictReader(data)

                if not reader.fieldnames:
                    print(f"CSV has no header row: {filename}")
                    return {}

                # Initialize keys from headers
                for field in reader.fieldnames:
                    ret[field] = []

                # Fill lists
                for row in reader:
                    for field in reader.fieldnames:
                        ret[field].append(row.get(field))

        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            print(f"Failed to read CSV {filename}: {exc}")
            return {}

        return ret
