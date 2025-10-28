from __future__ import annotations  # Postpone type evaluation for faster imports and flexibility.

from PySide6.QtCore import Signal                             # Qt typed event emitter (CustomEvent analogue).
from PySide6.QtWidgets import (                               # Qt Widgets = native UI controls.
    QMainWindow,                                              # Top-level window with a central area.
    QWidget,                                                  # Generic container (like a <div>).
    QVBoxLayout,                                              # Vertical layout manager (CSS flex-column analogue).
    QFormLayout,                                              # Label–field layout (like <label> + <input> rows).
    QLineEdit,                                                # Single-line text input (for username/realname/password).
    QPushButton,                                              # Clickable button (CTA).
    QMessageBox,                                              # Modal info/error dialogs.
)


class MainWindow(QMainWindow):                                # Our top-level “page component”.
    create_user_requested = Signal()                           # High-level intent emitted when user clicks CTA.

    def __init__(self) -> None:                               # Constructor.
        super().__init__()                                     # Initialize native window plumbing.
        self.setWindowTitle("D-Bus Service Studio")            # Window title shown in frame/taskbar.
        self._build_ui()                                       # Create widgets and layout.
        self._wire_signals()                                   # Connect low-level events to handlers.

    def _build_ui(self) -> None:                               # Build the UI tree and apply layout rules.
        central = QWidget(self)                                # Root content container (like <div id="root">).
        root = QVBoxLayout(central)                            # Stack sections vertically (padding + spacing).
        root.setContentsMargins(24, 24, 24, 24)                # Outer padding around content.
        root.setSpacing(16)                                     # Gap between stacked sections.

        form = QFormLayout()                                   # Two-column form: labels on the left, fields on the right.
        form.setSpacing(10)                                    # Gap between rows.

        # Username field -------------------------------------------------------
        self.inp_username = QLineEdit(central)                 # Input for Linux login name.
        self.inp_username.setPlaceholderText("e.g., alice")    # Hint text (not persisted).
        form.addRow("Username", self.inp_username)              # Label + field row.

        # Real name field ------------------------------------------------------
        self.inp_realname = QLineEdit(central)                 # Input for the human-friendly full name.
        self.inp_realname.setPlaceholderText("e.g., Alice Liddell")
        form.addRow("Real name", self.inp_realname)             # Label + field row.

        # Password field -------------------------------------------------------
        self.inp_password = QLineEdit(central)                 # Input for password (will be hashed in-memory).
        self.inp_password.setEchoMode(QLineEdit.Password)      # Hide characters while typing.
        self.inp_password.setPlaceholderText("Password (will be hashed)")
        form.addRow("Password", self.inp_password)              # Label + field row.

        root.addLayout(form)                                    # Place the form above the CTA button.

        # Primary action button ------------------------------------------------
        self.btn_create_user = QPushButton("Create User", central)  # CTA; triggers the high-level intent.
        root.addWidget(self.btn_create_user)                    # Add button under the form.

        central.setLayout(root)                                 # Ensure central owns the layout manager.
        self.setCentralWidget(central)                          # Install central widget into the window.
        self.resize(520, 300)                                   # Comfortable default size.

    def _wire_signals(self) -> None:                            # Connect widget signals to our slots.
        self.btn_create_user.clicked.connect(self._on_create_user_clicked)  # Button click → private slot.

    def _on_create_user_clicked(self) -> None:                   # Private slot: translate low-level click → high-level intent.
        self.create_user_requested.emit()                        # Re-emit as a clean domain event (view → controller).

    # --- Convenience getters for the launcher/controller ------------------------------------
# strip will remove leading/trailing spaces
    def get_username(self) -> str:                              # Read current username value from the field.
        return self.inp_username.text().strip()

    def get_realname(self) -> str:                              # Read current real name value from the field.
        return self.inp_realname.text().strip()

    def get_password(self) -> str:                              # Read current password value from the field.
        return self.inp_password.text()

    # --- UI-owned helpers for popups ---------------------------------------------------------

    def show_info(self, text: str, title: str = "Info") -> None:  # Show informational dialog.
        QMessageBox.information(self, title, text)

    def show_error(self, text: str, title: str = "Error") -> None: # Show error dialog.
        QMessageBox.critical(self, title, text)
