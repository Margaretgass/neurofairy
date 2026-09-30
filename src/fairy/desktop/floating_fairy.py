import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QEnterEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from fairy.desktop.geometry import clamp_position, snap_x


class FloatingFairy(QWidget):
    clicked = Signal()
    DRAG_THRESHOLD = 5

    def __init__(self) -> None:
        super().__init__()

        self._press_global_position: QPoint | None = None
        self._window_start_position: QPoint | None = None
        self._dragging = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        asset_path = Path(__file__).resolve().parents[3] / "uiux" / "assets" / "fairy-full.png"
        pixmap = QPixmap(str(asset_path))

        if pixmap.isNull():
            raise FileNotFoundError(f"Failed to load pixmap from {asset_path}")

        scaled_pixmap = pixmap.scaledToHeight(
            120,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._image_label = QLabel(self)
        self._image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._image_label.setPixmap(scaled_pixmap)
        self._image_label.adjustSize()
        self.resize(self._image_label.size())

        self._hover_peek = QLabel(self)
        self._hover_peek.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Tool
        )
        self._hover_peek.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._hover_peek.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self._hover_peek.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._hover_peek.setText("Next: one visible task\n25:00 left")
        self._hover_peek.setStyleSheet(
            """
            QLabel {
                background: #FAF6EE;
                color: #35214F;
                border: 1px solid #705584;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
            }
            """
        )
        self._hover_peek.adjustSize()
        self._hover_peek.hide()

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(650)
        self._hover_timer.timeout.connect(self._show_hover_peek)

        screen = QApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No available screen was found")

        bounds = screen.availableGeometry()
        left = bounds.x()
        top = bounds.y()
        right = left + bounds.width()
        bottom = top + bounds.height()

        x, y = clamp_position(
            x=right - self.width(),
            y=bottom - self.height(),
            width=self.width(),
            height=self.height(),
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )
        self.move(x, y)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hover_timer.start()
        super().enterEvent(event)

    def _show_hover_peek(self) -> None:
        screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No available screen was found")

        bounds = screen.availableGeometry()
        gap = 8
        if self.frameGeometry().center().x() <= bounds.center().x():
            desired_x = self.x() + self.width() + gap
        else:
            desired_x = self.x() - self._hover_peek.width() - gap
        desired_y = self.y() + (self.height() - self._hover_peek.height()) // 2

        x, y = clamp_position(
            x=desired_x,
            y=desired_y,
            width=self._hover_peek.width(),
            height=self._hover_peek.height(),
            left=bounds.x(),
            top=bounds.y(),
            right=bounds.x() + bounds.width(),
            bottom=bounds.y() + bounds.height(),
        )
        self._hover_peek.move(x, y)
        self._hover_peek.show()

    def leaveEvent(self, event: QEvent) -> None:
        self._hide_hover_peek()
        super().leaveEvent(event)

    def _hide_hover_peek(self) -> None:
        self._hover_timer.stop()
        self._hover_peek.hide()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._hide_hover_peek()
            self._press_global_position = event.globalPosition().toPoint()
            self._window_start_position = self.pos()
            self._dragging = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return

        press_position = self._press_global_position
        window_position = self._window_start_position
        if press_position is None or window_position is None:
            return

        if not self._dragging:
            distance = (event.globalPosition().toPoint() - press_position).manhattanLength()
            if distance >= self.DRAG_THRESHOLD:
                self._dragging = True

        if self._dragging:
            delta = event.globalPosition().toPoint() - press_position
            self.move(window_position + delta)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._press_global_position is None:
            return

        if self._dragging:
            self.move_to_screen_edge()
        else:
            self.clicked.emit()

        self._press_global_position = None
        self._window_start_position = None
        self._dragging = False

    def move_to_screen_edge(self) -> None:
        screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No available screen was found")

        bounds = screen.availableGeometry()
        left = bounds.x()
        top = bounds.y()
        right = left + bounds.width()
        bottom = top + bounds.height()

        snapped_x = snap_x(self.x(), self.width(), left, right)
        x, y = clamp_position(
            x=snapped_x,
            y=self.y(),
            width=self.width(),
            height=self.height(),
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )
        self.move(x, y)


def main() -> None:
    app = QApplication([])

    if sys.platform == "darwin":
        from AppKit import NSApp, NSApplicationActivationPolicyAccessory

        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    fairy = FloatingFairy()
    fairy.show()
    app.exec()


if __name__ == "__main__":
    main()
