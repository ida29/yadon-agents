#!/usr/bin/env python3
"""Yadoran Desktop Pet for yadon-agents.

Yadoran (task manager) as a desktop pet with embedded agent daemon.
Receives tasks via Unix domain socket at /tmp/yadon-agent-yadoran.sock.
Pet bubble display via /tmp/yadon-pet-yadoran.sock.
"""
import sys
import random
import signal
import argparse
import ctypes
import sys as _sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QRect, QEvent
from PyQt6.QtGui import QPainter, QColor, QMouseEvent, QFont, QCursor
from pokemon_menu import PokemonMenu

from config import (
    PIXEL_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT,
    FACE_ANIMATION_INTERVAL,
    RANDOM_ACTION_MIN_INTERVAL, RANDOM_ACTION_MAX_INTERVAL,
    MOVEMENT_DURATION,
    TINY_MOVEMENT_RANGE, SMALL_MOVEMENT_RANGE, TINY_MOVEMENT_PROBABILITY,
    BUBBLE_DISPLAY_TIME, PID_FONT_FAMILY, PID_FONT_SIZE,
    YADORAN_MESSAGES, YADORAN_WELCOME_MESSAGES,
)
from speech_bubble import SpeechBubble
from socket_server import PetSocketServer
from yadoran_agent_socket_server import YadoranAgentSocketServer
from yadoran_pixel_data import build_yadoran_pixel_data
from utils import log_debug


def _log_debug(msg: str):
    log_debug('yadoran_pet', msg)


def _mac_set_top_nonactivating(widget: QWidget):
    """macOS: force window to status/floating level without stealing focus."""
    try:
        if _sys.platform != 'darwin':
            return
        view_ptr = int(widget.winId())
        if not view_ptr:
            return
        objc = ctypes.cdll.LoadLibrary('/usr/lib/libobjc.A.dylib')
        cg = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')

        sel_registerName = objc.sel_registerName
        sel_registerName.restype = ctypes.c_void_p
        sel = lambda name: sel_registerName(name)

        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        window = objc.objc_msgSend(ctypes.c_void_p(view_ptr), sel(b'window'))
        if not window:
            return

        cg.CGWindowLevelForKey.argtypes = [ctypes.c_int]
        cg.CGWindowLevelForKey.restype = ctypes.c_int
        KEYS = {
            'floating': 3,
            'modal': 8,
            'status': 18,
            'popup': 101
        }
        levels = {name: int(cg.CGWindowLevelForKey(ctypes.c_int(val))) for name, val in KEYS.items()}
        level = max(levels.values())

        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        objc.objc_msgSend(window, sel(b'setLevel:'), ctypes.c_long(int(level)))

        try:
            behavior = ctypes.c_ulong(1)
            objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
            objc.objc_msgSend(window, sel(b'setCollectionBehavior:'), behavior)
        except Exception:
            pass

    except Exception as e:
        _log_debug("macOS elevate failed: %s" % e)


class YadoranPet(QWidget):
    _active_menu = None

    def __init__(self):
        super().__init__()

        # Build yadoran pixel data
        self.pixel_data = build_yadoran_pixel_data()

        self.face_offset = 0
        self.animation_direction = 1
        self.drag_position = None

        self.bubble = None
        self.pokemon_menu = None

        self.label_text = "ヤドラン"

        # Socket server for external bubble messages
        self.socket_server = PetSocketServer("/tmp/yadon-pet-yadoran.sock")
        self.socket_server.message_received.connect(self._on_external_message)
        self.socket_server.start()

        # Agent socket server (yadoran daemon functionality)
        import os
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.agent_server = YadoranAgentSocketServer(project_dir)
        self.agent_server.bubble_request.connect(self._on_external_message)
        self.agent_server.start()

        self.init_ui()
        self.setup_animation()
        self.setup_random_actions()

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
        if self.socket_server:
            self.socket_server.stop()
        if self.agent_server:
            self.agent_server.stop()
        super().closeEvent(event)

    def init_ui(self):
        self.setWindowTitle('Yadoran Pet')
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
        QTimer.singleShot(0, lambda: _mac_set_top_nonactivating(self))
        self._top_keepalive = QTimer(self)
        self._top_keepalive.timeout.connect(lambda: _mac_set_top_nonactivating(self))
        self._top_keepalive.start(5000)

    def setup_animation(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_face)
        self.timer.start(FACE_ANIMATION_INTERVAL)

    def setup_random_actions(self):
        self.action_timer = QTimer()
        self.action_timer.timeout.connect(self.random_action)
        self.action_timer.start(random.randint(RANDOM_ACTION_MIN_INTERVAL, RANDOM_ACTION_MAX_INTERVAL))

    # ------------------------------------------------------------------
    # External message handling
    # ------------------------------------------------------------------

    def _on_external_message(self, text: str, bubble_type: str, duration: int):
        _log_debug("External message for ヤドラン: %s" % repr(text))
        self._show_bubble(text, bubble_type=bubble_type, display_time=duration)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def animate_face(self):
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

        bg_rect = QRect((self.width() - text_width - 4) // 2, 66, text_width + 4, text_height + 2)
        painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
        painter.setPen(QColor(0, 0, 0))
        painter.drawRect(bg_rect)

        painter.setPen(QColor(0, 0, 0))
        painter.drawText(self.rect().adjusted(0, 68, 0, 0), Qt.AlignmentFlag.AlignHCenter, label)

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
            self.show_context_menu(event.globalPosition().toPoint())
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
    # Context menu
    # ------------------------------------------------------------------

    def show_context_menu(self, global_pos):
        if YadoranPet._active_menu:
            YadoranPet._active_menu.close()
            YadoranPet._active_menu = None

        if self.pokemon_menu:
            self.pokemon_menu.close()
            self.pokemon_menu = None

        self.pokemon_menu = PokemonMenu(self)
        YadoranPet._active_menu = self.pokemon_menu

        self.pokemon_menu.add_item('とじる', 'close')

        self.pokemon_menu.show_at(QPoint(
            self.x() + self.width() + 5,
            self.y(),
        ))

    # ------------------------------------------------------------------
    # Random actions
    # ------------------------------------------------------------------

    def random_action(self):
        action = random.choice(['nothing', 'nothing', 'nothing', 'speak', 'speak', 'move', 'move_and_speak'])

        if action in ['move', 'move_and_speak']:
            self.random_move()

        if action in ['speak', 'move_and_speak']:
            self.show_message()

        self.action_timer.stop()
        self.action_timer.start(random.randint(RANDOM_ACTION_MIN_INTERVAL, RANDOM_ACTION_MAX_INTERVAL))

    def random_move(self):
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

    def show_message(self):
        message = random.choice(YADORAN_MESSAGES)
        self._show_bubble(message, 'normal')

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

    def _show_bubble(self, message, bubble_type='normal', display_time=None):
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


def signal_handler(sig, frame):
    QApplication.quit()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Yadoran Desktop Pet for yadon-agents')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app = QApplication(sys.argv)

    # Dummy timer to allow signal processing
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    # Screen positioning
    screen_obj = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    screen = screen_obj.geometry()

    pet = YadoranPet()

    # Position: bottom-right, to the left of yadon-1
    margin = 20
    spacing = 10
    # Place yadoran at position 5 (left of all 4 yadons)
    x_pos = screen.width() - margin - (WINDOW_WIDTH + spacing) * 5
    y_pos = screen.height() - margin - WINDOW_HEIGHT
    pet.move(x_pos, y_pos)

    _log_debug("Started ヤドラン pos=(%d,%d)" % (x_pos, y_pos))

    # Show welcome
    pet._show_bubble(random.choice(YADORAN_WELCOME_MESSAGES), 'normal')

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
