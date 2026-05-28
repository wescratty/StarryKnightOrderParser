"""
Auther: Wes Cratty
Created: 1/18/2023
File: tkinterface.py

Description: Handles all tk interface creation objects
"""

from tkinter import filedialog, ttk
import tkinter as tk


class SuperTk:
    def __init__(self):
        self.opacity = 0.90
        self.bg = 'black'
        self.fg = "#00FF00"
        self.padx = 10
        self.pady = 10
        self.tk = tk
        self.ttk = ttk
        self.id_counter = 1
        self.invoked = {}

        self.window = None
        self.scroll_area = None
        self.scrollbar = None
        self.canvas = None
        self.canvas_frame = None

        self._initialized = False

    # --------------------------
    # safe mouse wheel
    # --------------------------
    def _on_mousewheel(self, event):

        if not self.canvas:
            return

        delta = int(-1 * (event.delta / 120))
        self.canvas.yview_scroll(delta, 'units')

    # --------------------------
    # main window builder
    # --------------------------
    def get_window(self, title='App', geometry='500x1000', scroll=False):

        if self._initialized:
            return {
                'window': self.window,
                'scroll_area': self.scroll_area
            }

        self._initialized = True

        window = self.tk.Tk()
        window.attributes('-alpha', self.opacity)
        window.title(title)
        window.config(bg=self.bg)
        window.geometry(geometry)

        self.window = window

        # --------------------------
        # SCROLL MODE
        # --------------------------
        if scroll:

            main_frame = tk.Frame(
                window,
                background=self.bg
            )
            main_frame.pack(fill='both', expand=1)

            self.scrollbar = ttk.Scrollbar(main_frame, orient='vertical')
            self.scrollbar.pack(side='right', fill='y')

            self.canvas = tk.Canvas(
                main_frame,
                background=self.bg,
                yscrollcommand=self.scrollbar.set
            )
            self.canvas.pack(side='left', fill='both', expand=1)

            self.scrollbar.config(command=self.canvas.yview)

            self.scroll_area = tk.Frame(
                self.canvas,
                background=self.bg
            )

            self.canvas_frame = self.canvas.create_window(
                (0, 0),
                window=self.scroll_area,
                anchor='nw'
            )

            # scroll region update
            def configure_scrollregion(event):
                self.canvas.configure(
                    scrollregion=self.canvas.bbox("all")
                )

            self.scroll_area.bind("<Configure>", configure_scrollregion)

            self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        else:

            self.scroll_area = tk.Frame(window, background=self.bg)

        return {
            'window': self.window,
            'scroll_area': self.scroll_area
        }
        
    def get_label(self, text=None, bg=None, fg=None, width=None, append_to=None, str_var=None):
        """
        Creates and returns label
        """

        if not append_to:
            append_to = self.scroll_area
        if str_var is None:
            var_text = self.get_str_var()
        else:
            var_text = str_var
        var_text.set(text)
        bg = self.bg if bg is None else bg
        fg = self.fg if fg is None else fg
        label = self.store(
            self.tk.Label(append_to, textvariable=var_text, width=width, bg=bg, fg=fg, anchor=tk.W, justify='left'))
        return label

    def get_str_var(self):
        """
        Creates and returns string variable for ui access
        """
        str_var = self.tk.StringVar()
        return self.store(str_var, 'strvar')

    def get_entry_box(self, str_var, append_to=None, width=30):
        """
        Creates and returns entry box
        """

        append_to = append_to if append_to else self.scroll_area
        tb = self.tk.Entry(append_to, textvariable=str_var, width=width, bg=self.bg, fg=self.fg)
        tb.config(insertbackground=self.fg)
        return self.store(tb, 'entrybox')

    def pack_in(self, item):
        """
        Packs ui items into window horizontally
        """

        item.pack(side=tk.LEFT, fill=tk.X, expand=tk.TRUE, pady=self.pady, padx=self.padx)

    def pack_stack(self, item):
        """
        Packs ui items into window vertically
        """

        item.pack(side=tk.TOP, expand=tk.TRUE, pady=self.pady, padx=self.padx)

    def get_label_frame(self, title, append_to):
        """
        Creates and returns field set frame
        """

        append_to = append_to if append_to else self.window
        return self.store(self.tk.LabelFrame(append_to, text=title, bg=self.bg, fg=self.fg), 'lableframe')

    def gen_lframe_of_cb(self, title, cb_names, call_back, append_to):
        """
        Creates and returns field set frame with checkboxes included
        """

        ret_obj = {'lf': self.get_label_frame(title, append_to), 'cb_list': list(), 'var': self.get_str_var()}
        ret_obj['var'].set(None)
        ret_obj['var_list'] = list()

        def pack():
            i = 1
            for _rb in ret_obj['cb_list']:
                self.pack_in(_rb)
                i += 1

        ret_obj['pack'] = pack

        for rb in cb_names:
            var = self.get_str_var()
            var.set(None)
            ret_obj['var_list'].append(var)
            ret_obj['cb_list'].append(self.get_check_box(ret_obj['lf'], rb, var, call_back))
        return ret_obj

    def gen_lframe_of_rb(self, title, rb_names, call_back, append_to):
        """
        Creates and returns field set frame with radio buttons included
        """

        ret_obj = {'lf': self.get_label_frame(title, append_to), 'rb_list': list(), 'var': self.get_str_var()}
        ret_obj['var'].set(None)

        def pack():
            for _rb in ret_obj['rb_list']:
                self.pack_in(_rb)

        ret_obj['pack'] = pack

        val = 0
        for rb in rb_names:
            ret_obj['rb_list'].append(self.get_radio_button(ret_obj['lf'], rb, ret_obj['var'], val, call_back))
            val += 1
        return ret_obj

    def gen_lframe_of_b(self, title, b_names, call_back, append_to):
        """
        Creates and returns field set frame with buttons included
        """

        ret_obj = {'lf': self.get_label_frame(title, append_to), 'b_list': list(), 'var': self.get_str_var()}
        ret_obj['var'].set(None)

        def pack():
            for _b in ret_obj['b_list']:
                self.pack_stack(_b)

        ret_obj['pack'] = pack

        val = 0
        for b in b_names:
            ret_obj['b_list'].append(self.get_button(ret_obj['lf'], b, lambda m=val: call_back(str(m))))
            val += 1
        return ret_obj

    def get_button(self, frame, name, func):
        """
        Creates and returns button
        """

        return self.store(self.tk.Button(
            frame,
            text=name,
            width=45,
            height=2,
            bg='#808080',
            fg=self.fg,
            command=func
        ), 'button')

    def get_radio_button(self, frame, text, var, value, func):
        """
        Creates and returns radio button
        """

        return self.store(
            self.tk.Radiobutton(frame, text=text, variable=var, bg=self.bg, fg=self.fg, value=value, command=func),
            'radio')

    def get_check_box(self, frame, text, var, func):
        """
        Creates and returns checkbox
        """

        return self.store(
            self.tk.Checkbutton(frame, text=text, variable=var, bg=self.bg, fg=self.fg, onvalue=1, offvalue=0,
                                command=func), 'ckeckbox')

    def get_invoked(self):
        """
        Returns last created object
        """

        keys = list(self.invoked.keys())
        return self.invoked[keys[len(keys)-1]]

    def get_new_id(self):
        """
        Creates id
        """

        self.id_counter += 1
        return '_id_' + str(self.id_counter)

    def store(self, obj, name=None):
        """
        Stores created item
        """

        if name:
            name = name + self.get_new_id()
        else:
            name = self.get_new_id()
        self.invoked[name] = obj
        return obj

    def add_frame(self, tag_name, children_list, call_back, append_to, show_html_nav):
        """
        Adds frame and buttons to UI
        """

        frame = self.gen_lframe_of_b(tag_name, children_list, call_back, append_to)
        frame['pack']()
        frame['lf'].pack(pady=10)
        self.scroll_bottom(show_html_nav)
        return frame['b_list']

    def scroll_bottom(self, show_html_nav):

        if not show_html_nav:
            return

        def _do_scroll():

            self.canvas.update_idletasks()

            bbox = self.canvas.bbox("all")

            if bbox:
                self.canvas.configure(scrollregion=bbox)

            self.canvas.yview_moveto(1.0)

        self.window.after_idle(_do_scroll)

    def set_theme(self, dark):
        """
        Toggles light and dark ui themes
        """

        if not int(dark):
            self.fg = 'black'
            self.bg = 'white'
            self.opacity = 1

        else:
            self.fg = "#00FF00"
            self.bg = 'black'
            self.opacity = 0.90
