"""
Draws MedTimer's pictures with Python's REAL turtle module.

Run on a computer with a screen:   py turtle_demo.py smiley     (or trophy, seedling, pill)

The web app cannot open a turtle window on Streamlit Cloud (the server has no screen), so it runs the very same
drawing functions on MiniTurtle, a small class with the same commands that draws to an image. Here they run on
the real turtle.
"""
import sys
import turtle

import core

DRAWINGS = {"smiley": core.draw_smiley, "trophy": core.draw_trophy, "seedling": core.draw_seedling, "pill": core.draw_pill}


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "smiley"
    if kind not in DRAWINGS:
        sys.exit(f"Choose one of: {', '.join(DRAWINGS)}")
    screen = turtle.Screen()
    screen.setup(420, 420)
    screen.bgcolor(core.SKY)
    screen.title(f"MedTimer turtle drawing: {kind}")
    pen = turtle.Turtle()
    pen.hideturtle()
    pen.speed(0)
    screen.tracer(3)  # redraw every 3 steps so the drawing builds up smoothly
    DRAWINGS[kind](pen)
    screen.update()
    turtle.done()


if __name__ == "__main__":
    main()
