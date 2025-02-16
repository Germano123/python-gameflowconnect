import tkinter as tk
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TextComponent

class DashboardPage(DefaultLayout):
    def __init__(self, parent):
        super().__init__(parent, title="Dashboard")

        # Conteúdo específico do dashboard
        welcome_label = TextComponent("Bem-vindo ao Dashboard!", font=("Arial", 18))
        welcome_label.pack(in_=self.content_frame, pady=20)

        logout_button = ButtonComponent(
            parent=self.content_frame,
            label="Logout",
            size="medium",
            onClick=lambda: parent.show_page("LoginPage"),
        )
        logout_button.pack(pady=10)
