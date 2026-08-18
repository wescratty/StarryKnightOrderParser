#!/usr/bin/env python3
"""
utility_modules/fileHelper.py

File I/O helpers: Tkinter file/directory pickers and CSV reading
(FileHelper.parse_csv_to_dict, used to load the Shopify orders_export.csv).
"""

from tkinter import filedialog
import csv


class FileHelper:
    """Tkinter file/directory picker wrappers plus CSV reading."""

    def __init__(self):
        self.ask_directory = filedialog.askdirectory
        self.ask_file = filedialog.askopenfile

    def find_config_dir(self):
        """Opens a directory picker and returns the chosen path (used for first-run workspace setup)."""

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
