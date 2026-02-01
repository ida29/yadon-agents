"""Speech bubble widget for Yadon Desktop Pet"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygon, QFont

from yadon_agents.config.ui import (
    BUBBLE_MAX_WIDTH, BUBBLE_MIN_WIDTH, BUBBLE_HEIGHT,
    BUBBLE_PADDING, BUBBLE_FONT_FAMILY, BUBBLE_FONT_SIZE,
)


class SpeechBubble(QWidget):
    def __init__(self, text, parent_widget, bubble_type='normal'):
        super().__init__()
        self.parent_widget = parent_widget
        self.text = text
        self.bubble_type = bubble_type

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        font = QFont(BUBBLE_FONT_FAMILY, BUBBLE_FONT_SIZE, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        self.setFont(font)

        metrics = self.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        if text_width > BUBBLE_MAX_WIDTH - 40:
            lines = []
            words = text.split(' ')
            current_line = ''
            for word in words:
                test_line = current_line + ' ' + word if current_line else word
                if metrics.horizontalAdvance(test_line) <= BUBBLE_MAX_WIDTH - 40:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            self.wrapped_text = '\n'.join(lines)
            num_lines = len(lines)
            bubble_width = BUBBLE_MAX_WIDTH
            bubble_height = max(BUBBLE_HEIGHT, num_lines * metrics.height() + 40)
        else:
            self.wrapped_text = text
            bubble_width = max(BUBBLE_MIN_WIDTH, text_width + 60)
            bubble_height = BUBBLE_HEIGHT

        self.setFixedSize(bubble_width, bubble_height)
        self.update_position()

        self.follow_timer = QTimer()
        self.follow_timer.timeout.connect(self.update_position)
        self.follow_timer.start(50)

    def update_position(self):
        if not self.parent_widget or not self.parent_widget.isVisible():
            self.close()
            return

        parent_geometry = self.parent_widget.frameGeometry()
        parent_x = parent_geometry.x()
        parent_y = parent_geometry.y()
        parent_width = parent_geometry.width()
        parent_height = parent_geometry.height()

        screen = QApplication.primaryScreen().geometry()

        bubble_x = parent_x + (parent_width - self.width()) // 2
        bubble_y = parent_y - self.height() - 10

        if bubble_y < 10:
            bubble_y = parent_y + parent_height + 10
            if bubble_y + self.height() > screen.height() - 10:
                if parent_x > screen.width() // 2:
                    bubble_x = parent_x - self.width() - 10
                    bubble_y = parent_y + (parent_height - self.height()) // 2
                else:
                    bubble_x = parent_x + parent_width + 10
                    bubble_y = parent_y + (parent_height - self.height()) // 2

        bubble_x = max(10, min(bubble_x, screen.width() - self.width() - 10))
        bubble_y = max(10, min(bubble_y, screen.height() - self.height() - 10))

        self.move(bubble_x, bubble_y)

    def close(self):
        if hasattr(self, 'follow_timer') and self.follow_timer:
            self.follow_timer.stop()
            self.follow_timer = None
        self.parent_widget = None
        super().close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self.bubble_type == 'hook':
            border_color = QColor(0, 0, 0)
            bg_color = QColor(200, 240, 255)
            shadow_color = QColor(100, 150, 180)
        else:
            border_color = QColor(0, 0, 0)
            bg_color = QColor(248, 248, 248)
            shadow_color = QColor(168, 168, 168)

        painter.setBrush(QBrush(shadow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        shadow_rect = self.rect().adjusted(8, 8, -2, -2)
        painter.drawRect(shadow_rect)

        painter.setBrush(QBrush(border_color))
        painter.drawRect(self.rect().adjusted(2, 2, -8, -8))

        painter.setBrush(QBrush(bg_color))
        inner_rect = self.rect().adjusted(4, 4, -10, -10)
        painter.drawRect(inner_rect)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(self.rect().adjusted(6, 6, -12, -12))

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2))
        tail = QPolygon([
            QPoint(25, self.height() - 12),
            QPoint(35, self.height() - 12),
            QPoint(30, self.height() - 6)
        ])
        painter.drawPolygon(tail)

        painter.setPen(QColor(48, 48, 48))
        painter.setFont(self.font())
        text_rect = self.rect().adjusted(BUBBLE_PADDING, 12, -BUBBLE_PADDING, -16)

        display_text = self.wrapped_text if hasattr(self, 'wrapped_text') else self.text
        if any(c.isascii() for c in display_text):
            display_text = display_text.upper()

        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            display_text,
        )
