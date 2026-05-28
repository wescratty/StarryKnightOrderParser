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
        self.path_set = config.workspace_exists()
        self.geometry = '600x700'
        if not self.path_set:
            self.geometry = '600x800'

        self.ask_file = filedialog.askopenfile
        self.file = um.fh()
        self.tk = um.stk()
        win_obj = self.tk.get_window(title='Order Organizer', geometry=self.geometry, scroll=True)
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
        self.processed_time_stamp = ''
        self.data_table = None
        self.xml_path = None
        self.num_dirs_to_show = -3  # save the last three items in the path to concatenate to the new path
        self.message_notify = ['#00FF00', 'white', 'yellow', 'red', 'blue']
        self.export_dir = r'C:\dev\esu_data'
        self.tree_html = 'tree.html'
        self.default_search_str = 'csv'
        self.template_location = 'esu_temp.xlsm'
        self.set_button_instance = None

    def re_init(self):
        """
        Clears objects for repeated searches
        """

        self.stack_dict = dict()
        self.button_id_list = list()

    def set_config_directory(self, btn_n):
        """
        """

        self.workspace_path = self.file.find_config_dir()
        self.display_label_to_user(message=self.workspace_path, urgency=2, reuse_lower_label=False)
        config.set_workspace_path(self.workspace_path)
        config.load_paths()
        config.initialize_app()

    def set_date_range(self, btn_n):
        """
        """

        if int(btn_n) == 0:
            validation = config.set_last_processed_timestamp(self.search_text.get())
            self.processed_time_stamp = config.get_last_processed_timestamp_string()

            if validation["success"]:

                self.display_label_to_user(
                    'Set last processed time stamp to ' + self.processed_time_stamp, 1, False)
            else:
                self.display_label_to_user(
                    validation["message"], 1, False)
                self.search_text.delete(0, "end")
                self.search_text.insert(0, self.processed_time_stamp)
            self.search_text.config(bg="black")
            self.set_button_instance.config(bg="#808080")

        elif int(btn_n) == 1:
            ret = config.clear_last_processed_timestamp()
            self.display_label_to_user(message=ret["message"], urgency=2, reuse_lower_label=False)
            self.search_text.delete(0, "end")

    def load_csv(self, btn_n):
        """
        Full CSV load + parse + export pipeline
        """

        self.re_init()

        path = self.file.find_file()

        if not path:
            self.display_label_to_user(
                'Did not find anything',
                3,
                False
            )
            return

        # ----------------------------------------
        # store path
        # ----------------------------------------

        self.paths_that_end_with = [path]
        self.root = path

        self.display_label_to_user(path, 2, False)

        # ----------------------------------------
        # parse csv
        # ----------------------------------------

        csv_tree = self.file.parse_csv_to_dict(path)

        if not csv_tree:
            self.display_label_to_user(
                "CSV parsing failed",
                3,
                False
            )
            return

        # ----------------------------------------
        # convert to domain objects
        # ----------------------------------------

        orders, events = um.orderItem.parse_orders(
            order_strings=csv_tree["Lineitem name"],
            timestamps=csv_tree["Created at"],
            quantities=csv_tree["Lineitem quantity"],
            notes=csv_tree["Notes"],
            orderNums=csv_tree["Name"]
        )

        # ----------------------------------------
        # display events
        # ----------------------------------------

        for e in events:

            msg = e.message

            if e.orderNum:
                msg = f"{e.orderNum} - {msg}"

            self.display_label_to_user(
                msg,
                urgency=e.level,
                reuse_lower_label=False
            )

        # ----------------------------------------
        # export HTML
        # ----------------------------------------

        mHtml.export_orders_html(orders)
        config.archive_csv_file(path)
        self.processed_time_stamp = config.get_last_processed_timestamp_string()
        self.search_text.delete(0, "end")
        self.search_text.insert(0, self.processed_time_stamp)

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
            self.tk.get_label(message, append_to=self.scroll_area, fg=fg, str_var=self.tk.get_str_var()) \
                .pack(anchor='w')
        self.tk.scroll_bottom(True)

    def on_change(self, *args):

        text = self.var_text_search.get()

        if text:

            self.search_text.config(bg="green")
            self.set_button_instance.config(bg="green")

    def main(self):
        """
        Main UI setup
        Toggles on show_html_nav: displays advanced user options
        Adds button field sets
        """
        config.initialize_app()
        self.tk.set_theme(1)


        self.path_set = config.workspace_exists()
        if not self.path_set:
            self.tk.add_frame('Config Path', ['Set Config directory'],
                              self.set_config_directory, self.window, True)

            self.display_label_to_user(
                'READ ME First time setup: \nPlease select a configuration directory, anywhere you want to save orders'
                ' to. \n'
                'Press Set Config Directory', 2, False)

            self.display_label_to_user('The file structure will be built for you.', 2, False)
            self.display_label_to_user(
                'Next: Download the orders_export.csv from shopify to yourFolder\INPUT_CSV\ACTIVE',
                2, False)
            self.display_label_to_user('Finally: Press Load CSV Order and navigate to '
                                       'yourFolder\INPUT_CSV\ACTIVE\orders_export.csv '
                                       'and select open from the file chooser. \n'
                                       'On next load you can skip these steps. ',
                                       2, False)

            self.display_label_to_user('Order Date Range: You can edit Last Processed order, '
                                       'dont worry it has format checking.',
                                       0, False)
        else:
            self.workspace_path = config.get_workspace_path()
            self.display_label_to_user('Workspace path' + str(self.workspace_path), 4, False)
            self.display_label_to_user(
                'Download the orders_export.csv from shopify to yourFolder\INPUT_CSV\ACTIVE',
                0, False)

            self.display_label_to_user('Next: Press Load CSV Order and navigate to \n'
                                       '' + str(self.workspace_path) +
                                       '\INPUT_CSV\ACTIVE\orders_export.csv \n'
                                       'and select open from the file chooser ',
                                       0, False)

        self.processed_time_stamp = config.get_last_processed_timestamp_string()
        self.display_label_to_user('Last Processed Order Timestamp' + self.processed_time_stamp,
                                   0, False)

        self.search_label = self.tk.get_label('Last Processed Order Timestamp', append_to=self.window).pack()
        self.var_text_search = self.tk.get_str_var()
        self.search_text = self.tk.get_entry_box(append_to=self.window, str_var=self.var_text_search).pack()
        self.search_text = self.tk.get_invoked()
        if self.processed_time_stamp:
            self.search_text.insert(0, self.processed_time_stamp)

        else:

            self.search_text.insert(
                0,
                "2026-05-07 22:33:43"
            )

        b_list = self.tk.add_frame('Order Date Range', ['Set', 'Clear'],
                          self.set_date_range, self.window, True)
        self.set_button_instance = b_list[0]

        self.tk.add_frame('CSV', ['Load CSV Order'],
                          self.load_csv, self.window, True)

        self.var_text_search.trace_add(
            "write",
            self.on_change
        )

        self.window.mainloop()


if __name__ == '__main__':
    OrderParser().main()
