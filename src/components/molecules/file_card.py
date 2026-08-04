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
        status_text: Optional[str] = None,
        on_click: Optional[Callable] = None,
        on_sync: Optional[Callable] = None,
        on_rename: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
        on_categorize: Optional[Callable] = None,
        category: Optional[str] = None,
        is_uploading: bool = False,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("border_width", 1)
        if is_uploading:
            kwargs["fg_color"] = "#0e1d25"
            kwargs["border_color"] = "#162c38"
        super().__init__(parent, **kwargs)

        self._on_click = on_click
        self._on_sync = on_sync
        self._on_rename = on_rename
        self._on_delete = on_delete
        self._on_categorize = on_categorize
        self._build(name, mime_type, size, modified, status_text, category, is_uploading)

        if on_click and not is_uploading:
            self._bind_click(self)

    def _build(self, name: str, mime_type: str, size: Optional[str], modified: Optional[str], status_text: Optional[str], category: Optional[str], is_uploading: bool) -> None:
        self.grid_columnconfigure(1, weight=1)

        # Icon label
        icon = self._get_icon(mime_type)
        icon_lbl = ctk.CTkLabel(
            self,
            text=icon,
            font=ctk.CTkFont(size=22),
            text_color="gray45" if is_uploading else self.ACCENT,
            width=36,
        )
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=10, sticky="ns")

        # File name layout frame to align name and badge
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(8, 0))

        name_lbl = ctk.CTkLabel(
            name_frame,
            text=name,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color="gray50" if is_uploading else "#ffffff",
            anchor="w",
        )
        name_lbl.pack(side="left")

        if category and not is_uploading:
            if category == "art":
                bg_color = "#8a2be2"  # Roxo
                label_text = "Arte"
            elif category == "programming":
                bg_color = "#00bbf9"  # Azul
                label_text = "Programação"
            elif category == "design":
                bg_color = "#fb5607"  # Laranja
                label_text = "Design"
            else:
                bg_color = "gray"
                label_text = category.capitalize()

            badge = ctk.CTkFrame(name_frame, fg_color=bg_color, corner_radius=4, height=18)
            badge.pack(side="left", padx=(10, 0))
            badge_lbl = ctk.CTkLabel(
                badge, 
                text=label_text, 
                font=ctk.CTkFont(size=9, weight="bold"), 
                text_color="#ffffff",
                height=14
            )
            badge_lbl.pack(padx=6, pady=1)

        # Metadata row
        meta_parts = []
        if size:
            meta_parts.append(size)
        if modified:
            meta_parts.append(modified)
        if status_text:
            meta_parts.append(f"[{status_text}]")

        meta_text = "  ·  ".join(meta_parts) if meta_parts else mime_type

        meta_lbl = ctk.CTkLabel(
            self,
            text=meta_text,
            font=ctk.CTkFont(family="Arial", size=10),
            anchor="w",
            text_color="gray40" if is_uploading else ("#7fa8c0" if status_text == "SYNCHRONIZED" else "gray60"),
        )
        meta_lbl.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))

        # Action buttons on the right (disabled during upload)
        if not is_uploading and (self._on_sync or self._on_rename or self._on_delete or self._on_categorize):
            actions_frame = ctk.CTkFrame(self, fg_color="transparent")
            actions_frame.grid(row=0, column=2, rowspan=2, padx=(4, 10), pady=8, sticky="e")

            if self._on_categorize:
                categorize_btn = ctk.CTkButton(
                    actions_frame,
                    text="🏷️",
                    font=ctk.CTkFont(size=12),
                    fg_color="#1a3743",
                    hover_color="#2d5266",
                    height=26,
                    width=30,
                    command=self._on_categorize,
                )
                categorize_btn.pack(side="left", padx=2)

            if self._on_rename:
                rename_btn = ctk.CTkButton(
                    actions_frame,
                    text="✏️",
                    font=ctk.CTkFont(size=12),
                    fg_color="#1a3743",
                    hover_color="#2d5266",
                    height=26,
                    width=30,
                    command=self._on_rename,
                )
                rename_btn.pack(side="left", padx=2)

            if self._on_delete:
                delete_btn = ctk.CTkButton(
                    actions_frame,
                    text="🗑️",
                    font=ctk.CTkFont(size=12),
                    fg_color="#3e1c1c",
                    hover_color="#5e2c2c",
                    height=26,
                    width=30,
                    command=self._on_delete,
                )
                delete_btn.pack(side="left", padx=2)

            if self._on_sync:
                is_synced = status_text == "SYNCHRONIZED"
                btn_text = "✓ Na Engine" if is_synced else "📥 Sincronizar"
                btn_color = "#1a4a28" if is_synced else "#00aa00"
                btn_hover = "#1e3743" if is_synced else "#008800"

                sync_btn = ctk.CTkButton(
                    actions_frame,
                    text=btn_text,
                    font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
                    fg_color=btn_color,
                    hover_color=btn_hover,
                    height=26,
                    width=90,
                    command=self._on_sync,
                )
                sync_btn.pack(side="left", padx=2)

    def _get_icon(self, mime_type: str) -> str:
        if mime_type in ["application/vnd.google-apps.folder", "folder/directory"]:
            return "📁"
        category = mime_type.split("/")[0]
        return self._ICONS.get(category, "📄")

    def _bind_click(self, widget) -> None:
        """Recursively binds click and hover to the card and all children, avoiding buttons."""
        if isinstance(widget, ctk.CTkButton):
            return
        widget.bind("<Button-1>", lambda _: self._on_click())
        widget.bind("<Enter>", lambda _: self.configure(border_color="#00aa00"))
        widget.bind("<Leave>", lambda _: self.configure(border_color="gray30"))
        for child in widget.winfo_children():
            self._bind_click(child)



