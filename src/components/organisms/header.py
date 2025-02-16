import tkinter as tk
from typing import Optional, Callable
from ..atoms import ButtonComponent, TextComponent

class HeaderOrganism(tk.Frame):
    def __init__(self, parent, title: str, on_back: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)

        # Estilização do Frame
        self.configure(bg="#f0f0f0", height=50)
        self.grid_columnconfigure(0, weight=1)  # Centralizar o título

        # Botão Voltar (opcional)
        if on_back:
            back_button = ButtonComponent(
                parent=self,
                label="⬅ Back",
                size="small",
                onClick=on_back,
            )
            back_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Título da página
        title_label = TextComponent(title, font=("Arial", 16, "bold"))
        title_label.place(relx=0.5, rely=0.5, anchor="center")  # Centraliza o título

        # Espaço para logout ou outras ações (opcional)
        logout_button = ButtonComponent(
            parent=self,
            label="Logout",
            size="small",
            onClick=lambda: parent.show_page("LoginPage"),
        )
        logout_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")
