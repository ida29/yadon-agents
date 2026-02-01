"""BasePet — ヤドン/ヤドランの共通ペットロジック

draggable window, face animation, random actions, speech bubble, context menu,
macOS window elevation を全て共通化。
"""

from __future__ import annotations

import random

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QRect, QEvent
from PyQt6.QtGui import QPainter, QColor, QMouseEvent, QFont

from yadon_agents.config.ui import (
    PIXEL_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT,
    FACE_ANIMATION_INTERVAL,
    RANDOM_ACTION_MIN_INTERVAL, RANDOM_ACTION_MAX_INTERVAL,
    MOVEMENT_DURATION,
    TINY_MOVEMENT_RANGE, SMALL_MOVEMENT_RANGE, TINY_MOVEMENT_PROBABILITY,
    BUBBLE_DISPLAY_TIME, PID_FONT_FAMILY, PID_FONT_SIZE,
)
from yadon_agents.gui.macos import mac_set_top_nonactivating
from yadon_agents.gui.speech_bubble import SpeechBubble
from yadon_agents.gui.pokemon_menu import PokemonMenu
from yadon_agents.gui.pet_socket_server import PetSocketServer
from yadon_agents.gui.agent_thread import AgentThread
from yadon_agents.gui.utils import log_debug


class BasePet(QWidget):
    """共通ペット基盤。サブクラスで pixel_data, label_text, messages 等を設定する。"""

    _active_menu = None

    def __init__(self, label_text: str, pixel_data: list, messages: list):
        super().__init__()
        self.label_text = label_text
        self.pixel_data = pixel_data
        self.messages = messages

        self.face_offset = 0
        self.animation_direction = 1
        self.drag_position = None
        self.bubble = None
        self.pokemon_menu = None

        # サブクラスで設定
        self.pet_socket_server: PetSocketServer | None = None
        self.agent_thread: AgentThread | None = None

        self._init_ui()
        self._setup_animation()
        self._setup_random_actions()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_servers(
        self, pet_socket_path: str, agent_thread: AgentThread,
    ) -> None:
        """ソケットサーバーとエージェントスレッドを起動する。"""
        self.pet_socket_server = PetSocketServer(pet_socket_path)
        self.pet_socket_server.message_received.connect(self._on_external_message)
        self.pet_socket_server.start()

        self.agent_thread = agent_thread
        self.agent_thread.bubble_request.connect(self._on_external_message)
        self.agent_thread.start()

    def closeEvent(self, event):
        if self.bubble:
            self.bubble.close()
            self.bubble = None
        if self.pokemon_menu:
            self.pokemon_menu.close()
            self.pokemon_menu = None
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'action_timer'):
            self.action_timer.stop()
        if self.pet_socket_server:
            self.pet_socket_server.stop()
        if self.agent_thread:
            self.agent_thread.stop()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _init_ui(self):
        self.setWindowTitle(self.label_text)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        if hasattr(Qt.WidgetAttribute, 'WA_AlwaysStackOnTop'):
            self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Window
        )
        if hasattr(Qt.WindowType, 'WindowDoesNotAcceptFocus'):
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)

        self.show()
        self.raise_()
        QTimer.singleShot(0, lambda: mac_set_top_nonactivating(self))
        self._top_keepalive = QTimer(self)
        self._top_keepalive.timeout.connect(lambda: mac_set_top_nonactivating(self))
        self._top_keepalive.start(5000)

    def _setup_animation(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._animate_face)
        self.timer.start(FACE_ANIMATION_INTERVAL)

    def _setup_random_actions(self):
        self.action_timer = QTimer()
        self.action_timer.timeout.connect(self._random_action)
        self.action_timer.start(
            random.randint(RANDOM_ACTION_MIN_INTERVAL, RANDOM_ACTION_MAX_INTERVAL)
        )

    # ------------------------------------------------------------------
    # External message handling
    # ------------------------------------------------------------------

    def _on_external_message(self, text: str, bubble_type: str, duration: int):
        log_debug("pet", f"External message for {self.label_text}: {text!r}")
        self.show_bubble(text, bubble_type=bubble_type, display_time=duration)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _animate_face(self):
        self.face_offset += self.animation_direction
        if self.face_offset >= 1:
            self.animation_direction = -1
        elif self.face_offset <= -1:
            self.animation_direction = 1
        self.update()

    def paintEvent(self, event):
        if not self.pixel_data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        pixel_size = PIXEL_SIZE

        for y in range(16):
            for x in range(16):
                color_hex = self.pixel_data[y][x]

                if y < 10:
                    draw_x = x * pixel_size + self.face_offset
                else:
                    draw_x = x * pixel_size

                draw_y = y * pixel_size

                if color_hex != "#FFFFFF":
                    color = QColor(color_hex)
                    painter.fillRect(draw_x, draw_y, pixel_size, pixel_size, color)

        # Draw label
        label = self.label_text
        font = QFont(PID_FONT_FAMILY, PID_FONT_SIZE)
        font.setBold(True)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(label)
        text_height = metrics.height()

        bg_rect = QRect(
            (self.width() - text_width - 4) // 2, 66,
            text_width + 4, text_height + 2,
        )
        painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
        painter.setPen(QColor(0, 0, 0))
        painter.drawRect(bg_rect)

        painter.setPen(QColor(0, 0, 0))
        painter.drawText(
            self.rect().adjusted(0, 68, 0, 0),
            Qt.AlignmentFlag.AlignHCenter, label,
        )

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            try:
                QApplication.setActiveWindow(None)
            except Exception:
                pass
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            event.accept()

    def focusInEvent(self, event):
        try:
            self.clearFocus()
            QApplication.setActiveWindow(None)
        except Exception:
            pass
        event.ignore()

    def event(self, e):
        if e.type() in (QEvent.Type.WindowActivate, QEvent.Type.ActivationChange, QEvent.Type.FocusIn):
            try:
                self.clearFocus()
                QApplication.setActiveWindow(None)
            except Exception:
                pass
            return True
        return super().event(e)

    # ------------------------------------------------------------------
    # Context menu (サブクラスでオーバーライド可能)
    # ------------------------------------------------------------------

    def _build_menu_items(self, menu: PokemonMenu) -> None:
        """メニュー項目を追加する。サブクラスでオーバーライド。"""
        menu.add_item('とじる', 'close')

    def _handle_menu_action(self, action_id: str) -> None:
        """メニューアクションを処理する。サブクラスでオーバーライド。"""
        pass

    def _show_context_menu(self):
        if BasePet._active_menu:
            BasePet._active_menu.close()
            BasePet._active_menu = None

        if self.pokemon_menu:
            self.pokemon_menu.close()
            self.pokemon_menu = None

        self.pokemon_menu = PokemonMenu(self)
        BasePet._active_menu = self.pokemon_menu

        self._build_menu_items(self.pokemon_menu)
        self.pokemon_menu.action_triggered.connect(self._handle_menu_action)

        menu_x = self.x() + self.width() + 5
        menu_y = self.y()

        screen = QApplication.primaryScreen().geometry()
        if menu_x + 200 > screen.width():
            menu_x = self.x() - 200 - 5
        if menu_y + 100 > screen.height():
            menu_y = screen.height() - 100

        self.pokemon_menu.show_at(QPoint(menu_x, menu_y))

    # ------------------------------------------------------------------
    # Random actions
    # ------------------------------------------------------------------

    def _random_action(self):
        action = random.choice([
            'nothing', 'nothing', 'nothing',
            'speak', 'speak',
            'move', 'move_and_speak',
        ])

        if action in ['move', 'move_and_speak']:
            self._random_move()

        if action in ['speak', 'move_and_speak']:
            self._show_random_message()

        self.action_timer.stop()
        self.action_timer.start(
            random.randint(RANDOM_ACTION_MIN_INTERVAL, RANDOM_ACTION_MAX_INTERVAL)
        )

    def _random_move(self):
        screen = QApplication.primaryScreen().geometry()
        current_pos = self.pos()

        if random.random() < TINY_MOVEMENT_PROBABILITY:
            new_x = current_pos.x() + random.randint(-TINY_MOVEMENT_RANGE, TINY_MOVEMENT_RANGE)
            new_y = current_pos.y() + random.randint(-TINY_MOVEMENT_RANGE, TINY_MOVEMENT_RANGE)
        else:
            new_x = current_pos.x() + random.randint(-SMALL_MOVEMENT_RANGE, SMALL_MOVEMENT_RANGE)
            new_y = current_pos.y() + random.randint(-SMALL_MOVEMENT_RANGE, SMALL_MOVEMENT_RANGE)

        new_x = max(0, min(new_x, screen.width() - self.width()))
        new_y = max(0, min(new_y, screen.height() - self.height()))

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(MOVEMENT_DURATION)
        self.animation.setStartValue(current_pos)
        self.animation.setEndValue(QPoint(int(new_x), int(new_y)))
        self.animation.start()

    def _show_random_message(self):
        message = random.choice(self.messages)
        self.show_bubble(message, 'normal')

    # ------------------------------------------------------------------
    # Bubble / move
    # ------------------------------------------------------------------

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.bubble and self.bubble.isVisible():
            self.bubble.update_position()
        if self.pokemon_menu and self.pokemon_menu.isVisible():
            menu_x = self.x() + self.width() + 5
            menu_y = self.y()
            screen = QApplication.primaryScreen().geometry()
            if menu_x + 200 > screen.width():
                menu_x = self.x() - 200 - 5
            if menu_y + 100 > screen.height():
                menu_y = screen.height() - 100
            self.pokemon_menu.move(menu_x, menu_y)

    def show_bubble(self, message: str, bubble_type: str = 'normal', display_time: int | None = None):
        """Display a speech bubble with the given message."""
        if self.bubble:
            self.bubble.close()
            self.bubble = None

        self.bubble = SpeechBubble(message, self, bubble_type=bubble_type)
        self.bubble.show()

        if display_time is None:
            display_time = BUBBLE_DISPLAY_TIME

        def close_bubble():
            if self.bubble:
                self.bubble.close()
                self.bubble = None
        QTimer.singleShot(display_time, close_bubble)
