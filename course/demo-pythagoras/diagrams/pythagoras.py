"""Animated diagrams for the demo section — The Pythagorean Theorem.

Original Cyberdeck-styled scenes (no copyrighted source material):
  RightTriangle  — name the legs a, b and the hypotenuse c on a right triangle.
  SquaresOnSides — the geometric heart: the squares on the two legs (areas a^2, b^2)
                   exactly fill the square on the hypotenuse (area c^2).
  ThreeFourFive  — the worked 3-4-5 example: 9 + 16 = 25, so c = 5.

Uses only Text/Polygon/Line so it renders without a LaTeX install.
"""
import numpy as np

from manim_cyberdeck import *


# Shared right-triangle geometry (right angle at the origin).
R  = ORIGIN                      # right-angle vertex
B  = RIGHT * 1.6                 # end of horizontal leg a
A  = UP * 1.2                    # end of vertical leg b
NORMAL = np.array([0.6, 0.8, 0.0])   # outward unit normal of the hypotenuse
HYP_LEN = 2.0


def right_angle_marker(size=0.22):
    return Polygon(
        R + RIGHT * size, R + RIGHT * size + UP * size, R + UP * size,
        stroke_color=DIM, stroke_width=2.5, fill_opacity=0,
    )


class RightTriangle(CyberScene):
    """Name the parts: legs a and b meet at the right angle; c is the hypotenuse."""

    def construct(self):
        title = self.title("A right triangle: two legs and a hypotenuse")

        tri = Polygon(R, B, A, stroke_color=CYAN, stroke_width=4,
                      fill_color=CYAN, fill_opacity=0.08)
        sq = right_angle_marker()

        a_lbl = Text("a", font=MONO, color=GREEN).scale(0.6).next_to(Line(R, B), DOWN, buff=0.22)
        b_lbl = Text("b", font=MONO, color=AMBER).scale(0.6).next_to(Line(R, A), LEFT, buff=0.22)
        c_lbl = Text("c", font=MONO, color=MINT).scale(0.6).next_to(Line(A, B).get_center(), UR, buff=0.18)
        leg_note = Text("legs meet at the right angle  ·  c is opposite it",
                        font=MONO, color=FG).scale(0.4)

        group = VGroup(tri, sq, a_lbl, b_lbl, c_lbl, leg_note)
        leg_note.next_to(tri, DOWN, buff=0.9)
        self.safe_fit(group)

        self.play(Write(title))
        self.play(Create(tri), run_time=1.2)
        self.play(FadeIn(sq))
        self.play(FadeIn(a_lbl, shift=UP * 0.2), FadeIn(b_lbl, shift=RIGHT * 0.2))
        self.play(FadeIn(c_lbl, scale=0.6))
        self.play(FadeIn(leg_note, shift=UP * 0.2))
        self.wait(1.4)


class SquaresOnSides(CyberScene):
    """The squares on the legs (a^2 + b^2) equal the square on the hypotenuse (c^2)."""

    def construct(self):
        title = self.title("a squared plus b squared equals c squared")

        tri = Polygon(R, B, A, stroke_color=CYAN, stroke_width=4,
                      fill_color=CYAN, fill_opacity=0.08)

        sq_a = Polygon(R, B, B + DOWN * 1.6, R + DOWN * 1.6,
                       stroke_color=GREEN, stroke_width=3, fill_color=GREEN, fill_opacity=0.16)
        sq_b = Polygon(R, A, A + LEFT * 1.2, R + LEFT * 1.2,
                       stroke_color=AMBER, stroke_width=3, fill_color=AMBER, fill_opacity=0.16)
        sq_c = Polygon(A, B, B + NORMAL * HYP_LEN, A + NORMAL * HYP_LEN,
                       stroke_color=MINT, stroke_width=3, fill_color=MINT, fill_opacity=0.16)

        la = Text("a²", font=MONO, color=GREEN).scale(0.55).move_to(sq_a.get_center())
        lb = Text("b²", font=MONO, color=AMBER).scale(0.5).move_to(sq_b.get_center())
        lc = Text("c²", font=MONO, color=MINT).scale(0.6).move_to(sq_c.get_center())

        eq = Text("area(a²) + area(b²) = area(c²)", font=MONO, color=FG).scale(0.5)

        diagram = VGroup(sq_a, sq_b, sq_c, tri, la, lb, lc)
        group = VGroup(diagram, eq).arrange(DOWN, buff=0.55)
        self.safe_fit(group)

        self.play(Write(title))
        self.play(Create(tri), run_time=1.0)
        self.play(DrawBorderThenFill(sq_a), FadeIn(la))
        self.play(DrawBorderThenFill(sq_b), FadeIn(lb))
        self.wait(0.3)
        self.play(DrawBorderThenFill(sq_c), FadeIn(lc))
        self.play(Write(eq))
        self.wait(1.4)


class ThreeFourFive(CyberScene):
    """The 3-4-5 triangle: 3 squared plus 4 squared is 9 + 16 = 25, and 25 is 5 squared."""

    def construct(self):
        title = self.title("The 3-4-5 triangle")

        r, b, a = ORIGIN, RIGHT * 2.4, UP * 1.8   # 4:3 legs, hypotenuse 5
        tri = Polygon(r, b, a, stroke_color=CYAN, stroke_width=4,
                      fill_color=CYAN, fill_opacity=0.08)
        mark = Polygon(r + RIGHT * 0.28, r + RIGHT * 0.28 + UP * 0.28, r + UP * 0.28,
                       stroke_color=DIM, stroke_width=2.5, fill_opacity=0)

        l3 = Text("4", font=MONO, color=GREEN).scale(0.55).next_to(Line(r, b), DOWN, buff=0.2)
        l4 = Text("3", font=MONO, color=AMBER).scale(0.55).next_to(Line(r, a), LEFT, buff=0.2)
        l5 = Text("5", font=MONO, color=MINT).scale(0.6).next_to(Line(a, b).get_center(), UR, buff=0.18)

        steps = VGroup(
            Text("4² + 3²", font=MONO, color=FG).scale(0.6),
            Text("= 16 + 9", font=MONO, color=CYAN).scale(0.6),
            Text("= 25", font=MONO, color=GREEN).scale(0.6),
            Text("= 5²   →   c = 5", font=MONO, color=MINT).scale(0.6),
        ).arrange(DOWN, buff=0.28, aligned_edge=LEFT)

        left = VGroup(tri, mark, l3, l4, l5)
        group = VGroup(left, steps).arrange(RIGHT, buff=1.1)
        self.safe_fit(group)

        self.play(Write(title))
        self.play(Create(tri), FadeIn(mark), run_time=1.0)
        self.play(FadeIn(l3), FadeIn(l4), FadeIn(l5))
        for s in steps:
            self.play(FadeIn(s, shift=RIGHT * 0.3), run_time=0.7)
        self.wait(1.4)
