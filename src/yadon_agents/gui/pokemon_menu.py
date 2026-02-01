"""Pokemon-style retro menu widget for Yadon Desktop Pet"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QPainter, QColor, QFont, QKeyEvent, QMouseEvent, QPen


class PokemonMenu(QWidget):
    """A retro Pokemon Red/Blue style menu widget"""

    action_triggered = pyqtSignal(str)  # action_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.selected_index = 0
        self.item_height = 24
        self.padding = 8
        self.border_width = 2
        self.cursor_blink_timer = QTimer()
        self.cursor_visible = True

        self.bg_color = QColor(255, 255, 255)
        self.border_color = QColor(0, 0, 0)
        self.text_color = QColor(0, 0, 0)
        self.cursor_color = QColor(0, 0, 0)
        self.red_color = QColor(255, 0, 0)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.cursor_blink_timer.timeout.connect(self._toggle_cursor)
        self.cursor_blink_timer.start(500)

        if parent:
            parent.installEventFilter(self)

    def _toggle_cursor(self):
        self.cursor_visible = not self.cursor_visible
        self.update()

    def add_item(self, text, action_id, color=None):
        self.items.append((text, action_id, color))
        self._update_size()

    def clear_items(self):
        self.items.clear()
        self.selected_index = 0
        self._update_size()

    def _update_size(self):
        if not self.items:
            return
        font = QFont("monospace", 12)
        font.setPixelSize(12)
        metrics = self.fontMetrics()

        max_width = 0
        for text, _, _ in self.items:
            max_width = max(max_width, metrics.horizontalAdvance(text))
        max_width += 20

        width = max_width + 2 * self.padding + 2 * self.border_width
        height = len(self.items) * self.item_height + 2 * self.padding + 2 * self.border_width
        self.setFixedSize(int(width), int(height))

    def show_at(self, global_pos):
        self.move(global_pos)
        self.show()
        self.raise_()
        self.selected_index = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        painter.fillRect(self.rect(), self.bg_color)

        pen = QPen(self.border_color, self.border_width)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        painter.drawRect(2, 2, self.width() - 5, self.height() - 5)

        font = QFont("monospace", 12)
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)

        painter.setPen(self.text_color)
        y = self.padding + self.border_width

        for i, (text, _, color) in enumerate(self.items):
            x = self.padding + self.border_width + 16

            if i == self.selected_index and self.cursor_visible:
                cursor_x = self.padding + self.border_width + 4
                cursor_y = y + self.item_height // 2 - 6
                painter.setPen(self.cursor_color)
                painter.drawText(cursor_x, cursor_y + 10, "\u25b6")

            if color:
                painter.setPen(color)
            else:
                painter.setPen(self.text_color)
            text_rect = QRect(x, y, self.width() - x - self.padding, self.item_height)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

            y += self.item_height

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Up:
            self.selected_index = (self.selected_index - 1) % len(self.items)
            self.cursor_visible = True
            self.update()
        elif event.key() == Qt.Key.Key_Down:
            self.selected_index = (self.selected_index + 1) % len(self.items)
            self.cursor_visible = True
            self.update()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._trigger_current_action()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            y = event.position().y()
            item_y = self.padding + self.border_width
            for i in range(len(self.items)):
                if item_y <= y <= item_y + self.item_height:
                    self.selected_index = i
                    self._trigger_current_action()
                    break
                item_y += self.item_height

    def _trigger_current_action(self):
        if 0 <= self.selected_index < len(self.items):
            _, action_id, _ = self.items[self.selected_index]
            self.action_triggered.emit(action_id)
            if hasattr(self.parent(), '__class__'):
                parent_class = self.parent().__class__
                if hasattr(parent_class, '_active_menu') and parent_class._active_menu == self:
                    parent_class._active_menu = None
            self.close()

    def eventFilter(self, source, event):
        if self.isVisible() and event.type() == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True
        return super().eventFilter(source, event)

    def closeEvent(self, event):
        self.cursor_blink_timer.stop()
        if hasattr(self.parent(), '__class__'):
            parent_class = self.parent().__class__
            if hasattr(parent_class, '_active_menu') and parent_class._active_menu == self:
                parent_class._active_menu = None
        super().closeEvent(event)
