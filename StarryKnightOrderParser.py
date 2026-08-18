"""
StarryKnightOrderParser.py

Tkinter GUI entry point. Wires up the one-screen workflow: pick a
workspace directory (first run only), set/clear the last-processed-order
timestamp, and load a Shopify orders_export.csv -- which parses it
(utility_modules.orderItem.parse_orders), renders the HTML report
(utility_modules.makeHtml.export_orders_html), and archives the CSV
(config.archive_csv_file).

Run directly: `python StarryKnightOrderParser.py`
"""

import utility_modules as um
from utility_modules import makeHtml as mHtml
import config


REQUIRED_CSV_COLUMNS = ["Lineitem name", "Created at", "Lineitem quantity", "Notes", "Name"]


def get_missing_required_columns(csv_tree):
    """
    Returns the list of REQUIRED_CSV_COLUMNS not present as keys in csv_tree
    (e.g. the dict returned by FileHelper.parse_csv_to_dict). Empty list
    means the CSV has everything load_csv needs.
    """

    return [col for col in REQUIRED_CSV_COLUMNS if col not in csv_tree]


class OrderParser:
    """Builds and drives the app's single Tkinter window."""

    def __init__(self):
        self.path_set = config.workspace_exists()
        self.geometry = '600x700'
        if not self.path_set:
            self.geometry = '600x800'

        self.file = um.fh()
        self.tk = um.stk()
        win_obj = self.tk.get_window(title='Order Organizer', geometry=self.geometry, scroll=True)
        self.window = win_obj['window']
        self.scroll_area = win_obj['scroll_area']
        self.path_set = False
        self.workspace_path = None
        self.user_label = None
        self.search_label = None
        self.var_info_label = None
        self.var_text_search = None
        self.search_text = None
        self.root = ''
        self.processed_time_stamp = ''
        self.message_notify = ['#00FF00', 'white', 'yellow', 'red', 'blue']
        self.set_button_instance = None

    def set_config_directory(self, btn_n):
        """Handler for the first-run "Set Config directory" button: opens a directory picker and initializes the workspace there."""

        self.workspace_path = self.file.find_config_dir()
        self.display_label_to_user(message=self.workspace_path, urgency=2, reuse_lower_label=False)
        config.set_workspace_path(self.workspace_path)
        config.load_paths()
        config.initialize_app()

    def set_date_clear(self):
        """Handler for the "Clear" button next to the Last Processed Order Timestamp field."""

        ret = config.clear_last_processed_timestamp()
        self.display_label_to_user(message=ret["message"], urgency=2, reuse_lower_label=False)
        self.search_text.delete(0, "end")

    def set_date_range(self):
        """Handler for the "Set" button next to the Last Processed Order Timestamp field -- validates and persists the entered timestamp."""

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
        self.set_button_instance.config(bg=self.tk.bg)

    def load_csv(self, btn_n):
        """
        Full CSV load + parse + export pipeline: file picker -> read CSV
        -> validate required columns -> parse_orders() -> display any
        parse warnings/errors -> export_orders_html() -> display any
        report warnings -> archive the source CSV -> refresh the
        Last Processed Order Timestamp field.
        """

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
        # validate required columns
        # ----------------------------------------

        missing_columns = get_missing_required_columns(csv_tree)

        if missing_columns:
            self.display_label_to_user(
                "CSV is missing required column(s): " + ", ".join(missing_columns),
                3,
                False
            )
            return

        # ----------------------------------------
        # convert to domain objects
        # ----------------------------------------

        batch, events = um.orderItem.parse_orders(
            order_strings=csv_tree["Lineitem name"],
            timestamps=csv_tree["Created at"],
            quantities=csv_tree["Lineitem quantity"],
            notes=csv_tree["Notes"],
            order_nums=csv_tree["Name"]
        )

        # ----------------------------------------
        # display events
        # ----------------------------------------

        for e in events:

            msg = e.message

            if e.order_num:
                msg = f"{e.order_num} - {msg}"

            self.display_label_to_user(
                msg,
                urgency=e.level,
                reuse_lower_label=False
            )

        # ----------------------------------------
        # export HTML
        # ----------------------------------------

        user_notify_list = mHtml.export_orders_html(batch)
        for notify in user_notify_list:
            msg = notify.message

            if notify.order_num:
                msg = f"{notify.order_num} - {msg}"

            self.display_label_to_user(
                msg,
                urgency=notify.level,
                reuse_lower_label=False
            )

        config.archive_csv_file(path)
        self.processed_time_stamp = config.get_last_processed_timestamp_string()
        self.search_text.delete(0, "end")
        self.search_text.insert(0, self.processed_time_stamp)

    def display_label_to_user(self, message, urgency, reuse_lower_label):
        """
        Displays a color-coded status message. urgency indexes
        self.message_notify for the text color (0=green, 1=white,
        2=yellow, 3=red, 4=blue). reuse_lower_label=True updates a single
        persistent status label in place; False appends a new line to the
        scrollable log instead.
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
        """Highlights the timestamp field/Set button green while the timestamp text is being edited, as a visual "unsaved change" cue."""

        text = self.var_text_search.get()

        if text:

            self.search_text.config(bg="green")
            self.set_button_instance.config(bg="green")

    def main(self):
        """
        Builds out the rest of the window: first-run setup instructions
        (if no workspace is configured yet) or the normal "here's where to
        put your CSV" instructions, the Last Processed Order Timestamp
        field + Set/Clear buttons, and the Load CSV Order button. Then
        blocks on the Tkinter event loop.
        """

        config.initialize_app()

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
                'Next: Download the orders_export.csv from shopify to yourFolder\\INPUT_CSV\\ACTIVE',
                2, False)
            self.display_label_to_user('Finally: Press Load CSV Order and navigate to '
                                       'yourFolder\\INPUT_CSV\\ACTIVE\\orders_export.csv '
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
                'Download the orders_export.csv from shopify to yourFolder\\INPUT_CSV\\ACTIVE',
                0, False)

            self.display_label_to_user('Next: Press Load CSV Order and navigate to \n'
                                       '' + str(self.workspace_path) +
                                       '\\INPUT_CSV\\ACTIVE\\orders_export.csv \n'
                                       'and select open from the file chooser ',
                                       0, False)

        self.processed_time_stamp = config.get_last_processed_timestamp_string()
        self.display_label_to_user('Last Processed Order Timestamp' + self.processed_time_stamp,
                                   0, False)

        self.search_label = self.tk.get_label('Last Processed Order Timestamp', append_to=self.window).pack()

        row = self.tk.tk.Frame(self.window, height=3, background=self.tk.bg)
        row.pack()
        self.var_text_search = self.tk.get_str_var()
        self.search_text = self.tk.get_entry_box(append_to=row, str_var=self.var_text_search).pack(side=self.tk.tk.LEFT)
        self.search_text = self.tk.get_invoked()

        self.tk.get_button(row, "Set", self.set_date_range, 3, 1).pack(side=self.tk.tk.LEFT, padx=5)
        self.set_button_instance = self.tk.get_invoked()
        self.tk.get_button(row, "Clear", self.set_date_clear, 4, 1).pack(side=self.tk.tk.LEFT, padx=5)

        if self.processed_time_stamp:
            self.search_text.insert(0, self.processed_time_stamp)

        else:

            self.search_text.insert(
                0,
                "2026-05-07 22:33:43"
            )

        self.tk.add_frame('CSV', ['Load CSV Order'],
                          self.load_csv, self.window, True)

        self.var_text_search.trace_add(
            "write",
            self.on_change
        )
        self.window.mainloop()


if __name__ == '__main__':
    OrderParser().main()
