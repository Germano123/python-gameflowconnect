import tkinter as tk

class PageComponent(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        """
        Base class for pages. Each page is a frame with its own widgets.
        """
        super().__init__(parent, *args, **kwargs)
        self.widgets = []  # List to store references to all widgets of the page

    def register_widget(self, widget: tk.Widget):
        """
        Registers a widget to this page, so it can be hidden or manipulated later.
        """
        self.widgets.append(widget)

    def hide(self):
        """
        Hides all registered widgets on this page.
        """
        for widget in self.widgets:
            widget.pack_forget()
            widget.grid_forget()
            widget.place_forget()
        self.grid_remove()  # Hides the frame itself
