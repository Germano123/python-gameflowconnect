import tkinter as tk
from typing import Optional, Callable
from ..atoms import ButtonComponent, TextComponent
from ..organisms import HeaderOrganism

class HomePage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # creating layout
        main_text = TextComponent("GameFlow Connect", font=("Arial", 40, "bold"))
        subtitle_text = TextComponent("Uma ferramenta para integração para artistas e programadores", font=("Arial", 14))
        button = ButtonComponent(
            parent=self,
            label="Login",
            size="medium",
            onClick=lambda: parent.show_page("LoginPage"),
        )
        # centering components
        main_text.place(relx=0.5, rely=0.3, anchor="center")
        subtitle_text.place(relx=0.5, rely=0.4, anchor="center")
        button.place(relx=0.5, rely=0.5, anchor="center")
