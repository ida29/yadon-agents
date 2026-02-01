"""Pixel data builder for Yadoran Desktop Pet.

Yadoran is Yadon's evolution — similar body but standing more upright,
with a Shellder (purple-grey bivalve) clamped on its tail.
16x16 pixel art representation.

Shellder design: vertically symmetric bivalve shell with spikes,
white eye with black pupil, red tongue poking out at the bite point.
"""

from __future__ import annotations

from yadon_agents.config.ui import YADORAN_COLORS


def build_yadoran_pixel_data() -> list[list[str]]:
    """Build 16x16 pixel data for Yadoran.

    Layout:
      - Rows 0-8: head + face (same as Yadon)
      - Rows 9-15: body (cols 2-8) + Shellder on tail (cols 9-15)

    Shellder (cols 9-15, rows 9-15):
      Row 9 :        spike tips
      Row 10:  tail─┐ upper spikes base
      Row 11:       │ upper shell (light edge, body, light edge)
      Row 12:  bite─┤ center: tongue, eye, pupil
      Row 13:       │ lower shell (light edge, body, light edge)
      Row 14:  tail─┘ lower spikes base
      Row 15:        spike tips
    """
    c = YADORAN_COLORS
    W = "#FFFFFF"  # transparent
    K = "#000000"  # outline
    B = c['body']
    H = c['head']
    S = c['shellder']
    SL = c['shellder_light']
    SD = c['shellder_spike']
    T = c['shellder_tongue']
    E = c['shellder_eye']

    pixel_data = [
        # Row 0: ears
        [W,  W,  K,  K,  K,  W,  W,  W,  W,  W,  K,  K,  K,  W,  W,  W],
        # Row 1: ear inner + head top
        [W,  K,  H,  H,  H,  K,  K,  K,  K,  K,  H,  H,  H,  K,  W,  W],
        # Row 2: head
        [W,  K,  H,  K,  H,  H,  H,  H,  H,  H,  H,  K,  H,  K,  W,  W],
        # Row 3: forehead
        [W,  K,  K,  B,  B,  B,  H,  H,  H,  B,  B,  B,  K,  K,  W,  W],
        # Row 4: eyes
        [W,  W,  K,  B,  K,  B,  H,  H,  H,  B,  K,  B,  K,  W,  W,  W],
        # Row 5: cheeks
        [W,  W,  K,  B,  B,  B,  H,  H,  H,  B,  B,  B,  K,  W,  W,  W],
        # Row 6: neck
        [W,  K,  B,  B,  B,  B,  B,  B,  B,  B,  B,  B,  B,  K,  W,  W],
        # Row 7: mouth
        [W,  K,  B,  B,  K,  K,  K,  K,  K,  K,  K,  B,  B,  K,  W,  W],
        # Row 8: chin
        [W,  W,  K,  B,  B,  B,  B,  B,  B,  B,  B,  B,  K,  W,  W,  W],
        # Row 9: body top + shellder spike tips (top)
        [W,  W,  W,  K,  K,  K,  K,  K,  K,  K,  W,  K,  K,  K,  W,  W],
        # Row 10: body + tail → shellder upper spikes
        [W,  W,  W,  K,  H,  H,  H,  H,  H,  K,  K,  SD, S,  SD, K,  W],
        # Row 11: body + shellder upper shell
        [W,  W,  W,  K,  H,  H,  H,  H,  K,  K,  SL, S,  S,  SL, K,  W],
        # Row 12: body wider + bite point: tongue, eye+pupil
        [W,  W,  K,  H,  H,  H,  H,  H,  K,  T,  S,  E,  K,  S,  K,  W],
        # Row 13: body + shellder lower shell
        [W,  W,  K,  H,  H,  H,  H,  H,  K,  K,  SL, S,  S,  SL, K,  W],
        # Row 14: feet + shellder lower spikes
        [W,  W,  W,  K,  H,  H,  K,  K,  K,  K,  K,  SD, S,  SD, K,  W],
        # Row 15: ground + shellder spike tips (bottom)
        [W,  W,  W,  W,  K,  K,  W,  W,  W,  K,  W,  K,  K,  K,  W,  W],
    ]

    return pixel_data
