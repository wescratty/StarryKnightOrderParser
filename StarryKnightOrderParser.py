"""
Auther: Wes Cratty
Created: 1/18/2023
File: StarryKnightOrderParser.py

Description: Navigate ViZn .config files, UI is for navigating to where you need to go, shown in a label
Code may need extended to parse 'any'.xml. Currently hard coded path for ViZn Calibration.config files

Output:
excel.xlsm (included repo)

"""
from tkinter import filedialog
import utility_modules as um
from utility_modules import makeHtml as mHtml
import config


class OrderParser:
    """
    Creates a tkinter UI window and allows ease of use for end user

    show_html_nav: set to True will display additional tools to help for extending this app for other data
    files in the future
    """
    def __init__(self):
        self.show_html_nav = True  # change to True if wish to display html creation navigator
        self.geometry = '600x600'
        if not self.show_html_nav:
            self.geometry = '600x500'

        self.ask_file = filedialog.askopenfile
        self.file = um.fh()
        self.tk = um.stk()
        self.html = um.html()
        win_obj = self.tk.get_window(title='Order Organizer', geometry=self.geometry, scroll=self.show_html_nav)
        self.window = win_obj['window']
        self.scroll_area = win_obj['scroll_area']
        self.path_label = None
        self.path_set = False
        self.workspace_path = None
        self.user_label = None
        self.search_label = None
        self.var_info_label = None
        self.var_text_search = None
        self.var_text_path = None
        self.search_text = None
        self.export_file_str = ''
        self.stack_dict = dict()
        self.button_id_list = list()
        self.tree = dict()
        self.branch = dict()
        self.paths_that_end_with = list()
        self.cal_pairs_array = list()
        self.root = ''
        self.config_path = ''
        self.data_table = None
        self.xml_path = None
        self.num_dirs_to_show = -3  # save the last three items in the path to concatenate to the new path
        self.message_notify = ['lime', 'white', 'yellow', 'red']
        self.export_dir = r'C:\dev\esu_data'
        self.tree_html = 'tree.html'
        self.default_search_str = 'csv'
        self.template_location = 'esu_temp.xlsm'

    def re_init(self):
        """
        Clears objects for repeated searches
        """

        self.export_file_str = ''
        self.stack_dict = dict()
        self.button_id_list = list()
        self.tree = dict()
        self.branch = dict()

    def set_config_directory(self, btn_n):
        """
        """

        self.workspace_path = self.file.find_config_dir()
        self.display_label_to_user(message=self.workspace_path, urgency=2, reuse_lower_label=False)
        config.set_workspace_path(self.workspace_path)
        config.load_paths()
        config.initialize_app()

    def csv(self, btn_n):
        """
        CSV Button handler
        Default display button panel handler
        if btn_n (str number) = 0, dir chooser opened, select dir of files
        if btn_n (str number) = 1, parses found matching files and exports xlsm
        """

        if int(btn_n) == 0:
            search = None
            if self.search_text and hasattr(self.search_text, 'get'):
                search = len(self.search_text.get())
            text = self.search_text.get() if search else self.default_search_str
            print('searching for ', text)
            self.re_init()
            path = self.file.find_file()
            if path != '':
                self.paths_that_end_with.append(path)
                self.display_label_to_user(self.paths_that_end_with[0], 2, False)
                self.root = self.paths_that_end_with[0]
            else:
                self.display_label_to_user('Did not find anything', 3, False)

        elif int(btn_n) == 1:

            csv_tree = self.parse_csv()
            if csv_tree:
                orders, events = um.orderItem.parse_orders(
                    order_strings=csv_tree["Lineitem name"],
                    timestamps=csv_tree["Created at"],
                    quantities=csv_tree["Lineitem quantity"],
                    notes=csv_tree["Notes"],
                    orderNums=csv_tree["Name"]
                )

                for e in events:

                    msg = e.message

                    if e.orderNum:
                        msg = f"{e.orderNum} - {msg}"

                    self.display_label_to_user(
                        msg,
                        urgency=e.level,
                        reuse_lower_label=False
                    )

                mHtml.export_orders_html(orders)

    def parse_csv(self):
        """
        Main parser logic
        Cycles through found files that matched search string
        file.format_new_file_name: returns a file name to export
        file.get_dict_from_xml: returns parsed xml as dict
        travers:
        """

        if len(self.paths_that_end_with):
            for path in self.paths_that_end_with:
                self.re_init()
                self.export_file_str = self.file.format_new_file_name(path, self.num_dirs_to_show)
                self.tree = self.file.parse_csv_to_dict(path)

            return self.tree

        else:
            self.display_label_to_user('Please select a file: '
                                       'Press Find a File to look around', 2, False)

    def parse_csvs(self):
        """
        Main parser logic
        Cycles through found files that matched search string
        file.format_new_file_name: returns a file name to export
        file.get_dict_from_xml: returns parsed xml as dict
        travers:
        """

        tree_list = list()
        if len(self.paths_that_end_with):
            for path in self.paths_that_end_with:
                self.re_init()
                self.export_file_str = self.file.format_new_file_name(path, self.num_dirs_to_show)
                self.tree = self.file.parse_csv_to_dict(path)
                tree_list.append(self.file.parse_csv_to_dict(path))
            return tree_list

        else:
            self.display_label_to_user('Please select a directory: '
                                       'Press Find a File', 2, False)

    def display_label_to_user(self, message, urgency, reuse_lower_label):
        """
        Displays messages to user with color coded strings
        """

        fg = self.message_notify[urgency]
        if reuse_lower_label:
            if not self.var_info_label or not self.user_label:  # Singleton of sorts
                self.var_info_label = self.tk.get_str_var()
                self.tk.get_label(message, append_to=self.window, fg=fg, str_var=self.var_info_label).pack(anchor='w')
                self.user_label = self.tk.get_invoked()
            self.user_label.configure(fg=fg)
            self.var_info_label.set(message)
        else:
            self.tk.get_label(message, append_to=self.scroll_area, fg=fg, str_var=self.tk.get_str_var())\
                .pack(anchor='w')
        #self.tk.scroll_bottom(self.show_html_nav)

    def main(self):
        """
        Main UI setup
        Toggles on show_html_nav: displays advanced user options
        Adds button field sets
        """
        config.initialize_app()
        self.display_label_to_user('Navigate to your Active directory containing orders_export.csv file and press the'
                                   ' Export Data button',
                                   1, False)
        self.path_set = config.workspace_exists()
        if not self.path_set:
            self.tk.add_frame('Config Path', ['Set Config directory'],
                              self.set_config_directory, self.window, self.show_html_nav)
            self.display_label_to_user('Please select a configuration directory, anywhere you want to save orders to. '
                                       'Press Config Directory', 3, False)
        else:
            self.workspace_path = config.get_workspace_path()
            self.display_label_to_user('Please select a directory: '
                                       'Press Find a File', 2, False)

        self.tk.add_frame('CSV', ['Find a File', 'Export Data'],
                          self.csv, self.window, self.show_html_nav)

        self.window.mainloop()


if __name__ == '__main__':
    OrderParser().main()
