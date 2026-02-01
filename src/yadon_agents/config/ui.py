"""UI設定（ピクセルサイズ、フォント、色、アニメーション等）"""

COLOR_SCHEMES = {
    "normal": {"body": "#F3D599", "head": "#D32A38", "accent": "#F3D599"},
    "shiny": {"body": "#FFCCFF", "head": "#FF99CC", "accent": "#FFCCFF"},
    "galarian": {"body": "#F3D599", "head": "#D32A38", "accent": "#FFD700"},
    "galarian_shiny": {"body": "#FFD700", "head": "#FFA500", "accent": "#FFD700"},
}

YADORAN_COLORS = {
    "body": "#F3D599",
    "head": "#D32A38",
    "shellder": "#8B7D9B",
    "shellder_light": "#B0A0C0",
    "shellder_spike": "#6B5D7B",
}

PIXEL_SIZE = 4
WINDOW_WIDTH = 16 * PIXEL_SIZE
WINDOW_HEIGHT = 16 * PIXEL_SIZE + 20

BUBBLE_MAX_WIDTH = 320
BUBBLE_MIN_WIDTH = 250
BUBBLE_HEIGHT = 80
BUBBLE_PADDING = 20
BUBBLE_DISPLAY_TIME = 4000

BUBBLE_FONT_FAMILY = "Monaco"
BUBBLE_FONT_SIZE = 14
PID_FONT_FAMILY = "Arial"
PID_FONT_SIZE = 12

FACE_ANIMATION_INTERVAL = 500
FACE_ANIMATION_INTERVAL_FAST = 250

RANDOM_ACTION_MIN_INTERVAL = 3000000
RANDOM_ACTION_MAX_INTERVAL = 4200000

MOVEMENT_DURATION = 15000
TINY_MOVEMENT_RANGE = 20
SMALL_MOVEMENT_RANGE = 80
TINY_MOVEMENT_PROBABILITY = 0.95

DEBUG_LOG = "/tmp/yadon_pet_agents_debug.log"
