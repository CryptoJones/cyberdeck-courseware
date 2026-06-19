#!/usr/bin/env python3
"""Cyberdeck styling + reusable builders for the course's Manim diagram scenes.

Diagram scenes do `from manim_cyberdeck import *` and subclass CyberScene. This
sets the 1280x720/30fps frame, the near-black background, and exposes the neon
palette + helpers (neon axes, bars that grow, a normal curve, etc.) so every
animated figure matches the slide deck.
"""
from manim import *  # noqa: F401,F403

config.background_color = "#07090f"
config.pixel_width = 1280
config.pixel_height = 720
config.frame_rate = 30

# Cyberdeck palette (mirrors pipeline/cyberdeck.css :root tokens)
BG = "#07090f"
CYAN = "#27d4ff"
GREEN = "#55ff99"
MINT = "#9fffe0"
FG = "#cfd8e3"
DIM = "#5a6678"
RED = "#ff4f4f"
AMBER = "#ff9b3d"
VIOLET = "#b8a8ff"
MONO = "Menlo"

# Safe drawing area (with bleed). The Manim frame is ~14.22 x 8 units; keep diagram
# content inside this box so nothing is clipped at the frame edge (and so a slide-style
# zoom would still have margin). Title lives in the top strip above SAFE_H/2.
SAFE_W = 12.6
SAFE_H = 5.9


class CyberScene(Scene):
    """Base scene: dark Cyberdeck background + mono font default."""

    def title(self, text, color=CYAN):
        t = Text(text, font=MONO, color=color, weight=BOLD).scale(0.6)
        t.to_edge(UP, buff=0.5)
        return t

    def safe_fit(self, group, max_w=SAFE_W, max_h=SAFE_H, dy=-0.4):
        """Scale a mobject group down to the safe area and centre it below the title.

        Call after building (and connecting) every part of a diagram, BEFORE
        animating it in — scaling the whole group keeps arrows attached to nodes.
        """
        if group.height > max_h:
            group.scale_to_fit_height(max_h)
        if group.width > max_w:
            group.scale_to_fit_width(max_w)
        group.move_to(UP * dy)
        return group


def neon_axes(x_range, y_range, x_label="", y_label="", width=9.0, height=5.0):
    """A dark-styled Axes in the cyberdeck palette."""
    ax = Axes(
        x_range=x_range,
        y_range=y_range,
        x_length=width,
        y_length=height,
        axis_config={"color": DIM, "stroke_width": 2, "include_tip": False,
                     "font_size": 22},
        tips=False,
    )
    labels = VGroup()
    if x_label:
        labels.add(Text(x_label, font=MONO, color=FG).scale(0.4).next_to(ax.x_axis, DOWN, buff=0.3))
    if y_label:
        labels.add(Text(y_label, font=MONO, color=FG).scale(0.4).rotate(PI / 2).next_to(ax.y_axis, LEFT, buff=0.3))
    return ax, labels


def growing_bars(ax, heights, colors=None, x0=0, width_ratio=0.82):
    """Build histogram/bar rectangles sitting on the x-axis, ready to .grow.

    Returns a VGroup of Rectangles already positioned; animate with
    GrowFromEdge(bar, DOWN) so each bar rises from the axis.
    """
    colors = colors or [CYAN, GREEN, MINT]
    bars = VGroup()
    unit = ax.x_axis.unit_size
    bar_w = unit * width_ratio
    for i, h in enumerate(heights):
        top = ax.c2p(x0 + i + 0.5, h)
        base = ax.c2p(x0 + i + 0.5, 0)
        height = abs(top[1] - base[1])
        rect = Rectangle(width=bar_w, height=max(height, 1e-3),
                         stroke_color=colors[i % len(colors)], stroke_width=2.5,
                         fill_color=colors[i % len(colors)], fill_opacity=0.35)
        rect.move_to(base, aligned_edge=DOWN)
        bars.add(rect)
    return bars
