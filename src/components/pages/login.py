import tkinter as tk
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TextComponent

class LoginPage(DefaultLayout):
    def __init__(self, parent):
        super().__init__(parent, title="Login")

        # Expande para ocupar toda a tela
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Conteúdo específico da página de login
        login_label = TextComponent("Faça login para continuar", font=("Arial", 24, "bold"))
        login_label.pack(in_=self.content_frame, pady=20)

        login_button = ButtonComponent(
            parent=self.content_frame,
            label="Entrar",
            size="medium",
            onClick=lambda: parent.show_page("DashboardPage"),
        )
        login_button.pack(pady=10)

        # Centralizar elementos dentro do frame de conteúdo
        self.content_frame.grid_propagate(False)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Adiciona padding para espaçamento
        self.content_frame.config(padx=20, pady=20)
