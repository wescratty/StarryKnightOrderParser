"""
Auther: Wes Cratty
Created: 1/19/2023
File: traverseTree.py

Description: With given object (list or dict), traverse tree, track path and when no longer a list or dict
and arrive at primitive data, create html tabel or organize object for consumption to export file.

Output:
html of tables
Cleaned object with organized data

"""
import copy


class Traverse:
    """
    Recursive class that returns html string or data object from given object
    """

    def __init__(self):
        self.key_path = list()
        self.html_str = ''
        self.depth_array = list()
        self.depth_to_check = 3

    @staticmethod
    def get_iter(root):
        """
        Returns correct iterator for object
        """

        if isinstance(root, dict):
            return root.keys()
        elif isinstance(root, list):
            return range(len(root))

    @staticmethod
    def clean(data):
        """
        Handles None type or empty string data in object
        """

        if data is not None and len(data):
            return '<td>' + data + '</td>'
        else:
            return '<td></td>'

    @staticmethod
    def verify_path_in_tree(tree, path_array, depth):
        """
        Occasionally a file will have the incorrect file structure per naming convention for Calibration.config
        This method verifies that the file is structured correctly without causing an exception
        """

        temp = copy.copy(tree)
        check = True
        for i in range(depth):
            if path_array[i] in temp.keys():
                temp = temp[path_array[i]]
            else:
                print('Bad file found')
                check = False
        return check

    def get_html_data(self, root):
        """
        Recursively traverses object until primitive data is reached
        Return html string
        """

        header = '<tr>'
        cells = '<tr>'
        _iter = self.get_iter(root)
        if _iter:
            for i in _iter:
                header += '<th>' + str(i) + '</th>'
                cells += self.clean(self.get_html_data(root[i]))
            return '<table>' + header + '</tr><tr>' + cells + '</tr></table>'
        else:
            return root

    def get_obj_data(self, root, path_array):
        """
        Recursively traverses object until primitive data is reached
        Return object
        """

        if len(path_array):
            key = path_array.pop(0)
            ret_array = list()
            if isinstance(key, int):
                _iter = self.get_iter(root)
                for i in _iter:
                    c = copy.copy(path_array)
                    ret_array.append(self.get_obj_data(root[i], c))

            else:
                c = copy.copy(path_array)
                ret_array = self.get_obj_data(root[key], c)
            return ret_array
        else:
            return root

    def traverse(self, root, path_array, return_array):
        """
        Staring point for get_obj_data
        """

        if self.verify_path_in_tree(root, path_array, self.depth_to_check):
            return_array.append(self.get_obj_data(root, path_array))
            return return_array.pop(0)
        else:
            return return_array
