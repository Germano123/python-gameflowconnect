"""
routes.py — Application router.

Defines the App class (customtkinter root window) and manages page registration
and navigation between pages using a grid-stacking strategy.
"""
import customtkinter as ctk
from typing import Type

from components.pages.home import HomePage
from components.pages.login import LoginPage
from components.pages.register import RegisterPage
from components.pages.dashboard import DashboardPage
from components.pages.workspaces import WorkspacesPage
from components.pages.integrations import IntegrationsPage
from components.pages.settings import SettingsPage
from components.pages.profile import ProfilePage

# ------------------------------------------------------------------ #
# Global CTk theme configuration
# ------------------------------------------------------------------ #
ctk.set_appearance_mode("dark")          # "dark" | "light" | "system"
ctk.set_default_color_theme("blue")      # base theme (overridden by our palette)


class App(ctk.CTk):
    """
    Root application window.

    Manages page registration and navigation.
    All pages are stacked on top of each other via grid row=0, col=0,
    and shown/hidden by calling tkraise() / grid_remove().
    """
    WIDTH  = 1100
    HEIGHT = 700
    MIN_W  = 860
    MIN_H  = 560

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("GameFlow Connect")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(self.MIN_W, self.MIN_H)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.WIDTH)  // 2
        y = (self.winfo_screenheight() - self.HEIGHT) // 2
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        # Grid fills window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Page registry
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.current_page: str | None = None

        # Register all pages
        self.register_page("HomePage",         HomePage)
        self.register_page("LoginPage",        LoginPage)
        self.register_page("RegisterPage",     RegisterPage)
        self.register_page("DashboardPage",    DashboardPage)
        self.register_page("WorkspacesPage",   WorkspacesPage)
        self.register_page("IntegrationsPage", IntegrationsPage)
        self.register_page("SettingsPage",     SettingsPage)
        self.register_page("ProfilePage",      ProfilePage)


        # Show initial page
        self.show_page("HomePage")


    def register_page(self, name: str, page_class: Type[ctk.CTkFrame]) -> None:
        """
        Instantiates a page and places it in the grid stack.

        Args:
            name (str): Unique page identifier used by show_page().
            page_class: A class inheriting from ctk.CTkFrame.
        """
        frame = page_class(self)
        self.pages[name] = frame
        frame.grid(row=0, column=0, sticky="nsew")

    def show_page(self, name: str) -> None:
        """
        Brings the named page to the front, hiding all others.

        Args:
            name (str): The page to display.

        Raises:
            ValueError: If the page name has not been registered.
        """
        if name not in self.pages:
            raise ValueError(f"Page '{name}' is not registered. Available: {list(self.pages)}")

        self.current_page = name

        # Hide all pages
        for page in self.pages.values():
            page.grid_remove()

        # Show the target page
        self.pages[name].grid(row=0, column=0, sticky="nsew")
        self.pages[name].tkraise()

        # Notify the page it has been shown (optional lifecycle hook)
        page = self.pages[name]
        if hasattr(page, "on_show") and callable(page.on_show):
            self.after(80, page.on_show)

