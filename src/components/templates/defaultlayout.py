import customtkinter as ctk
from typing import Optional, Callable
from ..organisms import HeaderOrganism


class DefaultLayout(ctk.CTkFrame):
    """
    Template: default page layout with a fixed header and a content area.

    Args:
        parent: The parent widget (typically the App root).
        title (str): Page title shown in the header.
        on_back (Callable, optional): Callback for the Back button.
        on_logout (Callable, optional): Callback for the Logout button.
        **kwargs: Additional keyword arguments forwarded to ctk.CTkFrame.
    """
    def __init__(
        self,
        parent,
        title: str,
        on_back: Optional[Callable] = None,
        on_logout: Optional[Callable] = None,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Fixed header ---
        self.header = HeaderOrganism(
            self,
            title=title,
            on_back=on_back,
            on_logout=on_logout,
        )
        self.header.grid(row=0, column=0, sticky="ew")

        # --- Dynamic content frame ---
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
