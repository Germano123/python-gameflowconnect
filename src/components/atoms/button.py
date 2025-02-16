import tkinter as tk
from tkinter import ttk

class ButtonComponent:
    def __init__(
    self,
    parent,
    label="Button",
    onClick=None,
    variant="primary",
    disabled=False,
    icon=None,
    size="medium"):
        self.button = ttk.Button(
            parent,
            text=label,
            command=onClick,
            state="disabled" if disabled else "normal")
        self.style_button(variant, size)

        if icon:
            self.add_icon(icon)

    def style_button(self, variant, size):
        # Aplica estilos ao botão
        style = ttk.Style()
        style.configure("primary.TButton", background="#007BFF", foreground="white")
        style.configure("secondary.TButton", background="#6C757D", foreground="white")
        style.configure("danger.TButton", background="#DC3545", foreground="white")
        style.configure("small.TButton", padding=2)
        style.configure("medium.TButton", padding=5)
        style.configure("large.TButton", padding=10)

        # Estilo baseado na variante
        style_name = f"{variant}.{size}.TButton"
        style.configure(style_name)
        self.button.configure(style=style_name)

    def add_icon(self, icon_path):
        # Adiciona um ícone ao botão
        icon_image = tk.PhotoImage(file=icon_path)
        self.button.configure(image=icon_image)
        self.button.image = icon_image  # Evita garbage collection

    def pack(self, **kwargs):
        self.button.pack(**kwargs)

    def grid(self, **kwargs):
        self.button.grid(**kwargs)

    def place(self, **kwargs):
        self.button.place(**kwargs)
