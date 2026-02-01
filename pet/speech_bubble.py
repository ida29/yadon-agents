"""Speech bubble widget for Yadon Desktop Pet"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPolygon, QFont

from config import (
    BUBBLE_MAX_WIDTH, BUBBLE_MIN_WIDTH, BUBBLE_HEIGHT,
    BUBBLE_PADDING, BUBBLE_FONT_FAMILY, BUBBLE_FONT_SIZE
)


class SpeechBubble(QWidget):
    def __init__(self, text, parent_widget, bubble_type='normal'):
        super().__init__()
        self.parent_widget = parent_widget
        self.text = text
        self.bubble_type = bubble_type  # 'normal' or 'hook'

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Bigger Pokemon style monospace font
        font = QFont(BUBBLE_FONT_FAMILY, BUBBLE_FONT_SIZE, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)  # Pixelated look
        self.setFont(font)

        # Calculate size based on text with word wrapping
        metrics = self.fontMetrics()

        # Calculate required height for wrapped text
        text_width = metrics.horizontalAdvance(text)
        if text_width > BUBBLE_MAX_WIDTH - 40:  # Account for padding
            # Need word wrapping
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

        # Set bubble size
        self.setFixedSize(bubble_width, bubble_height)

        # Position above parent
        self.update_position()

        # Timer to continuously update position during animation
        self.follow_timer = QTimer()
        self.follow_timer.timeout.connect(self.update_position)
        self.follow_timer.start(50)  # Update every 50ms for smooth following

    def update_position(self):
        if not self.parent_widget or not self.parent_widget.isVisible():
            # Parent widget is gone, close the bubble
            self.close()
            return

        parent_geometry = self.parent_widget.frameGeometry()
        parent_x = parent_geometry.x()
        parent_y = parent_geometry.y()
        parent_width = parent_geometry.width()
        parent_height = parent_geometry.height()

        # Get screen geometry
        screen = QApplication.primaryScreen().geometry()

        # Default position: above parent
        bubble_x = parent_x + (parent_width - self.width()) // 2
        bubble_y = parent_y - self.height() - 10

        # Smart positioning based on screen location
        if bubble_y < 10:
            # No room above, try below
            bubble_y = parent_y + parent_height + 10

            if bubble_y + self.height() > screen.height() - 10:
                # No room below either, show to the side
                if parent_x > screen.width() // 2:
                    # Parent on right side, show bubble on left
                    bubble_x = parent_x - self.width() - 10
                    bubble_y = parent_y + (parent_height - self.height()) // 2
                else:
                    # Parent on left side, show bubble on right
                    bubble_x = parent_x + parent_width + 10
                    bubble_y = parent_y + (parent_height - self.height()) // 2

        # Final bounds check with margin
        bubble_x = max(10, min(bubble_x, screen.width() - self.width() - 10))
        bubble_y = max(10, min(bubble_y, screen.height() - self.height() - 10))

        self.move(bubble_x, bubble_y)

    def close(self):
        if hasattr(self, 'follow_timer') and self.follow_timer:
            self.follow_timer.stop()
            self.follow_timer = None
        self.parent_widget = None  # Clear parent reference
        super().close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Pixelated look

        # Pokemon-style text box colors
        if self.bubble_type == 'hook':
            # Hook messages - light blue/cyan background
            border_color = QColor(0, 0, 0)  # Black border
            bg_color = QColor(200, 240, 255)  # Light cyan background
            shadow_color = QColor(100, 150, 180)  # Blue-gray shadow
        else:
            # Normal messages - white background
            border_color = QColor(0, 0, 0)  # Black border
            bg_color = QColor(248, 248, 248)  # Almost white background
            shadow_color = QColor(168, 168, 168)  # Gray shadow

        # Draw shadow (offset by 2 pixels)
        painter.setBrush(QBrush(shadow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        shadow_rect = self.rect().adjusted(8, 8, -2, -2)
        painter.drawRect(shadow_rect)

        # Draw main box with double border (Pokemon style)
        # Outer border (black)
        painter.setBrush(QBrush(border_color))
        painter.drawRect(self.rect().adjusted(2, 2, -8, -8))

        # Inner white area
        painter.setBrush(QBrush(bg_color))
        inner_rect = self.rect().adjusted(4, 4, -10, -10)
        painter.drawRect(inner_rect)

        # Second border (inside)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(self.rect().adjusted(6, 6, -12, -12))

        # Draw tail (simple triangle)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2))
        tail = QPolygon([
            QPoint(25, self.height() - 12),
            QPoint(35, self.height() - 12),
            QPoint(30, self.height() - 6)
        ])
        painter.drawPolygon(tail)

        # Draw text in Pokemon style (all caps, monospace)
        painter.setPen(QColor(48, 48, 48))  # Dark gray text
        painter.setFont(self.font())
        text_rect = self.rect().adjusted(BUBBLE_PADDING, 12, -BUBBLE_PADDING, -16)

        # Use wrapped text if available
        display_text = self.wrapped_text if hasattr(self, 'wrapped_text') else self.text
        # Convert to uppercase for English text
        if any(c.isascii() for c in display_text):
            display_text = display_text.upper()

        # Draw text with word wrap support
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, display_text)
