"""Pixel data builder for Yadoran Desktop Pet.

Yadoran is Yadon's evolution — similar body but standing more upright,
with a Shellder (purple-grey) clamped on its tail.
16x16 pixel art representation.
"""

from yadon_agents.config.ui import YADORAN_COLORS


def build_yadoran_pixel_data():
    """Build 16x16 pixel data for Yadoran."""
    c = YADORAN_COLORS
    W = "#FFFFFF"  # transparent
    K = "#000000"  # outline
    B = c['body']
    H = c['head']
    S = c['shellder']
    SL = c['shellder_light']
    SD = c['shellder_spike']

    pixel_data = [
        # Row 0: ears
        [W,  W,  K,  K,  K,  W,  W,  W,  W,  W,  K,  K,  K,  W,  W,  W],
        # Row 1: ear inner + head top
        [W,  K,  H,  H,  H,  K,  K,  K,  K,  K,  H,  H,  H,  K,  W,  W],
        # Row 2: head with eyes
        [W,  K,  H,  K,  H,  H,  H,  H,  H,  H,  H,  K,  H,  K,  W,  W],
        # Row 3: forehead to body
        [W,  K,  K,  B,  B,  B,  H,  H,  H,  B,  B,  B,  K,  K,  W,  W],
        # Row 4: eyes
        [W,  W,  K,  B,  K,  B,  H,  H,  H,  B,  K,  B,  K,  W,  W,  W],
        # Row 5: face bottom
        [W,  W,  K,  B,  B,  B,  H,  H,  H,  B,  B,  B,  K,  W,  W,  W],
        # Row 6: neck
        [W,  K,  B,  B,  B,  B,  B,  B,  B,  B,  B,  B,  B,  K,  W,  W],
        # Row 7: mouth
        [W,  K,  B,  B,  K,  K,  K,  K,  K,  K,  K,  B,  B,  K,  W,  W],
        # Row 8: chin
        [W,  W,  K,  B,  B,  B,  B,  B,  B,  B,  B,  B,  K,  W,  W,  W],
        # Row 9: body top
        [W,  W,  W,  K,  K,  K,  K,  K,  K,  K,  K,  K,  W,  W,  W,  W],
        # Row 10: body + shellder start
        [W,  W,  W,  K,  H,  H,  H,  H,  H,  H,  K,  W,  K,  K,  K,  W],
        # Row 11: body + shellder
        [W,  W,  W,  K,  H,  H,  H,  H,  H,  K,  W,  K,  S,  SL, K,  W],
        # Row 12: body wider + shellder
        [W,  W,  K,  H,  H,  H,  H,  H,  H,  K,  K,  SD, S,  SL, SD, K],
        # Row 13: body + shellder spikes
        [W,  W,  K,  H,  H,  H,  H,  H,  H,  K,  K,  S,  S,  S,  S,  K],
        # Row 14: feet + shellder bottom
        [W,  W,  W,  K,  H,  H,  K,  K,  K,  H,  K,  K,  SD, S,  K,  W],
        # Row 15: ground
        [W,  W,  W,  W,  K,  K,  W,  W,  W,  K,  K,  W,  K,  K,  W,  W],
    ]

    return pixel_data
