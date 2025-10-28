from __future__ import annotations  # Enable postponed evaluation of type hints (faster imports, fewer circulars).

# Qt core/widget imports: these are our “DOM + events” building blocks in Qt.
from PySide6.QtCore import Signal        # Signal is Qt’s typed event emitter (CustomEvent analogue).
from PySide6.QtWidgets import (          # Widgets are native UI elements (window, container, button, etc.).
    QMainWindow,                         # Top-level window frame with a central area.
    QWidget,                             # Generic container (like a <div>).
    QVBoxLayout,                         # Vertical layout manager (like CSS flex-direction: column).
    QPushButton,                         # Clickable button (like <button>).
    QMessageBox,                         # Simple modal dialog for info/error popups.
)


class MainWindow(QMainWindow):           # Define a subclassed main window to host our UI.
    create_user_requested = Signal()     # Public signal emitted when the user clicks "Create User".

    def __init__(self) -> None:          # Constructor for the main window.
        super().__init__()               # Initialize the QMainWindow base class (native window setup).
        self.setWindowTitle("D-Bus Service Studio")  # Set the window title (visible in frame/taskbar).
        self._build_ui()                 # Build and assemble child widgets and layouts.
        self._wire_signals()             # Connect widget events (signals) to handler methods (slots).

    def _build_ui(self) -> None:         # Create the UI tree and apply layout rules.
        central = QWidget(self)          # Root content widget that lives inside the main window.
        layout = QVBoxLayout(central)    # Vertical layout to stack children (button now, more later).
        layout.setContentsMargins(24, 24, 24, 24)  # Outer padding around content (like CSS padding).
        layout.setSpacing(16)            # Gap between stacked widgets (like CSS gap).

        self.btn_create_user = QPushButton("Create User", central)  # Primary CTA button.
        layout.addWidget(self.btn_create_user)  # Insert button into layout so it gets measured/placed.

        central.setLayout(layout)        # Ensure the central widget owns the layout manager.
        self.setCentralWidget(central)   # Install central widget into the QMainWindow content area.
        self.resize(420, 240)            # Give a comfortable initial size so the window isn’t tiny.

    def _wire_signals(self) -> None:     # Connect internal widget signals to our handlers.
        # Button’s built-in 'clicked' SIGNAL → our private slot method.
        self.btn_create_user.clicked.connect(self._on_create_user_clicked)

    def _on_create_user_clicked(self) -> None:  # Private slot: react to button click.
        # Re-emit a semantic, high-level signal that the controller layer can subscribe to.
        self.create_user_requested.emit()

    def show_info(self, text: str, title: str = "Info") -> None:  # Convenience UI helper for info popups.
        QMessageBox.information(self, title, text)  # Show an informational dialog owned by this window.

    def show_error(self, text: str, title: str = "Error") -> None:  # Convenience UI helper for error popups.
        QMessageBox.critical(self, title, text)     # Show an error dialog owned by this window.
