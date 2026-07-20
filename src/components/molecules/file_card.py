import customtkinter as ctk
from typing import Optional, Callable


class FileCard(ctk.CTkFrame):
    """
    Molecule component: displays metadata for a single file or repository asset.

    Args:
        parent: The parent widget.
        name (str): File/repo name.
        mime_type (str): MIME type string (used to determine icon).
        size (str, optional): Human-readable file size (e.g. "1.2 MB").
        modified (str, optional): Last modified date string (YYYY-MM-DD).
        on_click (Callable, optional): Callback invoked when the card is clicked.
        **kwargs: Additional keyword arguments forwarded to ctk.CTkFrame.
    """
    ACCENT = "#00aa00"

    _ICONS = {
        "image":       "🖼",
        "audio":       "🎵",
        "video":       "🎬",
        "application": "📄",
        "text":        "📝",
        "folder":      "📁",
    }

    def __init__(
        self,
        parent,
        name: str,
        mime_type: str = "application/octet-stream",
        size: Optional[str] = None,
        modified: Optional[str] = None,
        on_click: Optional[Callable] = None,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("border_width", 1)
        super().__init__(parent, **kwargs)

        self._on_click = on_click
        self._build(name, mime_type, size, modified)

        if on_click:
            self._bind_click(self)

    def _build(self, name: str, mime_type: str, size: Optional[str], modified: Optional[str]) -> None:
        self.grid_columnconfigure(1, weight=1)

        # Icon label
        icon = self._get_icon(mime_type)
        icon_lbl = ctk.CTkLabel(
            self,
            text=icon,
            font=ctk.CTkFont(size=22),
            text_color=self.ACCENT,
            width=36,
        )
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=10, sticky="ns")

        # File name
        name_lbl = ctk.CTkLabel(
            self,
            text=name,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            anchor="w",
        )
        name_lbl.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(8, 0))

        # Metadata row
        meta_parts = []
        if size:
            meta_parts.append(size)
        if modified:
            meta_parts.append(modified)
        meta_text = "  ·  ".join(meta_parts) if meta_parts else mime_type

        meta_lbl = ctk.CTkLabel(
            self,
            text=meta_text,
            font=ctk.CTkFont(family="Arial", size=10),
            anchor="w",
            text_color="gray60",
        )
        meta_lbl.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))

    def _get_icon(self, mime_type: str) -> str:
        category = mime_type.split("/")[0]
        return self._ICONS.get(category, "📄")

    def _bind_click(self, widget) -> None:
        """Recursively binds click and hover to the card and all children."""
        widget.bind("<Button-1>", lambda _: self._on_click())
        widget.bind("<Enter>", lambda _: self.configure(border_color="#00aa00"))
        widget.bind("<Leave>", lambda _: self.configure(border_color="gray30"))
        for child in widget.winfo_children():
            self._bind_click(child)
