import customtkinter as ctk
from typing import Optional, Callable


class InputField(ctk.CTkFrame):
    """
    Molecule component: a label paired with a CTkEntry (native placeholder support).

    Args:
        parent: The parent widget.
        label (str): Descriptive label displayed above the input.
        placeholder (str): Placeholder text shown when the field is empty.
        show (str, optional): Character to mask input (e.g. "*" for passwords).
        on_change (Callable, optional): Callback invoked whenever the text changes.
        **kwargs: Additional keyword arguments forwarded to ctk.CTkFrame.
    """
    def __init__(
        self,
        parent,
        label: str = "",
        placeholder: str = "",
        show: Optional[str] = None,
        on_change: Optional[Callable] = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self._on_change = on_change
        self._show_char = show

        # --- Label ---
        if label:
            self._label = ctk.CTkLabel(
                self,
                text=label,
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                anchor="w",
            )
            self._label.pack(fill="x", pady=(0, 4))

        # --- CTkEntry with native placeholder ---
        entry_kwargs = dict(
            master=self,
            placeholder_text=placeholder if not show else "",
            font=ctk.CTkFont(family="Arial", size=13),
            height=42,
            corner_radius=8,
            border_width=2,
        )
        if show:
            entry_kwargs["show"] = show

        self._entry = ctk.CTkEntry(**entry_kwargs)
        self._entry.pack(fill="x")

        if on_change:
            self._entry.bind("<KeyRelease>", lambda _: on_change(self.get()))

    # ------------------------------------------------------------------ #
    # Public API — same interface as before
    # ------------------------------------------------------------------ #

    def get(self) -> str:
        """Returns current field value."""
        return self._entry.get()

    def set(self, value: str) -> None:
        """Sets the field value programmatically."""
        self._entry.delete(0, "end")
        self._entry.insert(0, value)

    def clear(self) -> None:
        """Clears the field content."""
        self._entry.delete(0, "end")

    def focus(self) -> None:
        """Sets keyboard focus to the entry widget."""
        self._entry.focus_set()
