# routes.py
from components.pages.home import HomePage
from components.pages.login import LoginPage
from components.pages.register import RegisterPage
from components.pages.dashboard import DashboardPage

import tkinter as tk
from typing import Type
# from pages import HomePage, LoginPage, DashboardPage

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # application configs
        self.title("GameFlow Connect")
        self.geometry("900x600")
        
        # dictionary to save pages
        self.pages = {} 
        self.current_page = None

        # register pages in the application
        self.register_page("HomePage", HomePage)
        self.register_page("LoginPage", LoginPage)
        self.register_page("DashboardPage", DashboardPage)

        # show initial page
        self.show_page("HomePage")

    """
    Registers a new page to the application.

    This method initializes the page by creating an instance of the given `page_class`
    and stores it in the `pages` dictionary using the provided name as the key.
    The registered page is placed within the application window using the `grid` geometry manager
    and is set to occupy the full available space.

    Args:
        name (str): The name used to identify the page. It acts as the key
        in the `pages` dictionary.
        page_class (Type[tk.Frame]): The class of the page to be registered.
        This class should inherit from `tk.Frame` and implement its layout and logic.

    Returns:
        None

    Notes:
        - This method does not display the page immediately. Use `show_page` to bring a page to the front.
        - Pages should be designed to handle their own layout and logic internally.
    """
    def register_page(self, name: str, page_class: Type[tk.Frame]) -> None:
        frame = page_class(self)
        self.pages[name] = frame
        frame.grid(row=0, column=0, sticky="nsew")

    """
    Hides all widgets of the given page.
    Works regardless of the positioning method (pack, grid, or place).
    """
    def hide_page(self, page: tk.Frame) -> None:
        for widget in page.winfo_children():
            widget.pack_forget()
            widget.grid_forget()
            widget.place_forget()
        page.grid_remove()

    """
    Show the given `name` page if exsits.
    """
    def show_page(self, name: str) -> None:
        # debug mode == True > show listed pages
        # print(f"Available pages: {list(self.pages.keys())}")

        # if trying to access a page that doesn't exist throw error
        if name not in self.pages:
            raise ValueError(f"The page '{name}' does not exist in registered pages.")

        # set the current page to page to show
        self.current_page = name

        # hide all the others pages
        for page in self.pages.values():
            self.hide_page(page)

        # shwo current page
        self.pages[name].grid()
