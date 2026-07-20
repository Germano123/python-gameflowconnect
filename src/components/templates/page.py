import customtkinter as ctk


class PageComponent(ctk.CTkFrame):
    """
    Base class for standalone pages (not using DefaultLayout).

    Provides a standard CTkFrame base and grid_remove()-based hide mechanism
    compatible with the App router in routes.py.
    """
    def __init__(self, parent, *args, **kwargs):
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, *args, **kwargs)
