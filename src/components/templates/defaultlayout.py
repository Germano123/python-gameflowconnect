import tkinter as tk
from ..organisms import HeaderOrganism

class DefaultLayout(tk.Frame):
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, **kwargs)

        # Configuração do layout
        self.grid_rowconfigure(1, weight=1)  # Conteúdo central se expande
        self.grid_columnconfigure(0, weight=1)

        # Header fixo
        self.header = HeaderOrganism(
            self,
            title=title,
            on_back=lambda: parent.show_page("HomePage")  # Volta para a HomePage como exemplo
        )
        self.header.grid(row=0, column=0, sticky="nsew")

        # Frame para conteúdo dinâmico
        self.content_frame = tk.Frame(self, bg="white")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
