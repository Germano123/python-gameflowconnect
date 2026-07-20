import customtkinter as ctk
from typing import Optional, Callable
from ..atoms import ButtonComponent


class ModalDialog(ctk.CTkToplevel):
    """
    Molecule component: a modal confirmation dialog using customtkinter.

    Blocks interaction with the parent window until dismissed.

    Args:
        parent: The parent widget (window).
        title (str): Dialog title.
        message (str): Main message body.
        on_confirm (Callable, optional): Callback for the Confirm button.
        on_cancel (Callable, optional): Callback for the Cancel button.
        confirm_label (str): Label for the confirm button.
        cancel_label (str): Label for the cancel button.
    """
    def __init__(
        self,
        parent,
        title: str,
        message: str,
        on_confirm: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        confirm_label: str = "Confirmar",
        cancel_label: str = "Cancelar",
    ):
        super().__init__(parent)
        self._on_confirm = on_confirm
        self._on_cancel  = on_cancel

        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self.transient(parent)

        self._build(title, message, confirm_label, cancel_label)
        self._center(parent)

    def _build(self, title: str, message: str, confirm_label: str, cancel_label: str) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header ---
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#1e3743", height=52)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, pady=14, padx=20, sticky="w")

        # --- Message ---
        msg_frame = ctk.CTkFrame(self, fg_color="transparent")
        msg_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=20)

        ctk.CTkLabel(
            msg_frame,
            text=message,
            font=ctk.CTkFont(family="Arial", size=13),
            wraplength=340,
            justify="left",
        ).pack(anchor="w")

        # --- Separator ---
        ctk.CTkFrame(self, height=1, fg_color="gray30", corner_radius=0).grid(
            row=2, column=0, sticky="ew"
        )

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=12)

        ButtonComponent(
            parent=btn_frame,
            label=confirm_label,
            variant="success",
            size="small",
            width=110,
            onClick=self._handle_confirm,
        ).pack(side="right", padx=(8, 0))

        ButtonComponent(
            parent=btn_frame,
            label=cancel_label,
            variant="neutral",
            size="small",
            width=110,
            onClick=self._handle_cancel,
        ).pack(side="right")

    def _handle_confirm(self) -> None:
        self.destroy()
        if self._on_confirm:
            self._on_confirm()

    def _handle_cancel(self) -> None:
        self.destroy()
        if self._on_cancel:
            self._on_cancel()

    def _center(self, parent) -> None:
        """Centers the dialog over the parent window."""
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w  = self.winfo_width()
        h  = self.winfo_height()
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")
