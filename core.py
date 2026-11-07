"""
MedTimer core: constants, the MiniTurtle drawing engine, drawings, and the logic
(dose status, adherence, streaks, badges, ACB lookup, reports, notification data).
The pages live in app.py and the outside services (NVIDIA, maps) in services.py.

Note on Turtle: Python's built-in `turtle` module needs a desktop window, which
does not exist on Streamlit Cloud. MiniTurtle offers the same commands
(forward, left, circle, begin_fill ...) but renders to an image instead.
"""
import html
import base64
import io
import math
import random
import struct
import time
import wave
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

# ----------------------------------------------------------------------------
# 1. CONSTANTS
# ----------------------------------------------------------------------------
INK, SKY, SEA = "#12343B", "#EAF4F7", "#2E9E6B"
COLORS = {"taken": "#2E9E6B", "due": "#F2C230", "upcoming": "#F2C230", "missed": "#D64545"}
PILL_TEXT = {"taken": "#FFFFFF", "due": "#12343B", "upcoming": "#12343B", "missed": "#FFFFFF"}
LABELS = {"taken": "Taken", "due": "Due now", "upcoming": "Upcoming", "missed": "Missed"}

TIPS = [
    "Taking medicine at the same time each day makes it easier to remember.",
    "Keep your medicines somewhere you see every morning, like next to your toothbrush.",
    "A missed dose is not the end of the world. Just take the next one on time.",
    "Never double a dose to catch up. Ask your pharmacist if you are unsure.",
    "Small steps every day add up. You are doing well.",
    "Take a sip of water with each tablet unless your doctor says otherwise.",
    "Share this week's report with your family or doctor. It helps them help you.",
    "Consistency beats perfection. Look at how far you have come this week.",
    "Every dose you take is a small act of caring for yourself.",
    "Progress, not perfection. One steady day at a time.",
    "You showed up today, and that counts.",
    "Healthy habits are built from small, calm, repeated steps.",
    "Be proud of every dose. Your future self will thank you.",
    "A good routine is a gift you give to the people who love you.",
]
TIMEZONES = ["Asia/Kolkata", "UTC", "Europe/London", "America/New_York", "Asia/Dubai", "Asia/Singapore"]


# ----------------------------------------------------------------------------
# 2. MINI TURTLE (turtle-style commands, renders to an animated GIF)
# ----------------------------------------------------------------------------
class MiniTurtle:
    """Subset of Python's turtle API. (0, 0) is the centre of the canvas.
    Every few drawn segments it records a frame (with a little turtle cursor),
    so the finished drawing can be played back as an animation."""

    def __init__(self, size=320, bg=SKY, every=5):
        self.size, self.every, self._count = size, every, 0
        self.img = Image.new("RGB", (size, size), bg)
        self.canvas = ImageDraw.Draw(self.img)
        self.x = self.y = 0.0
        self.heading = 0.0
        self.pen = True
        self.color = "black"
        self.fill = "white"
        self.width = 3
        self._fill_points = None
        self.frames = []

    def _px(self, x, y):
        return (self.size / 2 + x, self.size / 2 - y)

    def penup(self): self.pen = False
    def pendown(self): self.pen = True
    def pensize(self, w): self.width = w
    def pencolor(self, c): self.color = c
    def fillcolor(self, c): self.fill = c
    def setheading(self, a): self.heading = a
    def left(self, a): self.heading += a
    def right(self, a): self.heading -= a

    def _segment(self, x, y):
        if self.pen:
            self.canvas.line([self._px(self.x, self.y), self._px(x, y)], fill=self.color, width=self.width)
            self._count += 1
        self.x, self.y = x, y
        if self._fill_points is not None:
            self._fill_points.append((x, y))
        if self.pen and self._count % self.every == 0:
            self.snap()

    def goto(self, x, y):
        """Straight lines are drawn in small steps so they animate smoothly."""
        n = max(1, int(math.hypot(x - self.x, y - self.y) / 8)) if self.pen else 1
        x0, y0 = self.x, self.y
        for i in range(1, n + 1):
            self._segment(x0 + (x - x0) * i / n, y0 + (y - y0) * i / n)

    def forward(self, dist):
        r = math.radians(self.heading)
        self.goto(self.x + dist * math.cos(r), self.y + dist * math.sin(r))

    def backward(self, dist): self.forward(-dist)

    def circle(self, radius, extent=360, steps=72):
        """Positive radius curves left (anticlockwise), negative curves right."""
        sign = 1 if radius >= 0 else -1
        angle = sign * extent / steps
        chord = 2 * abs(radius) * math.sin(math.radians(abs(angle) / 2))
        self.left(angle / 2)
        for _ in range(steps):
            self.forward(chord)
            self.left(angle)
        self.left(-angle / 2)

    def begin_fill(self): self._fill_points = [(self.x, self.y)]

    def end_fill(self):
        pts = [self._px(*p) for p in self._fill_points]
        self._fill_points = None
        if len(pts) > 2:
            self.canvas.polygon(pts, fill=self.fill)
            self.canvas.line(pts + [pts[0]], fill=self.color, width=self.width)
        self.snap()

    def snap(self):
        """Record a frame with the turtle cursor drawn on top."""
        frame = self.img.copy()
        r, (px, py) = math.radians(self.heading), self._px(self.x, self.y)
        tip = (px + 11 * math.cos(r), py - 11 * math.sin(r))
        a = (px + 7 * math.cos(r + 2.4), py - 7 * math.sin(r + 2.4))
        b = (px + 7 * math.cos(r - 2.4), py - 7 * math.sin(r - 2.4))
        ImageDraw.Draw(frame).polygon([tip, a, b], fill=SEA, outline=INK)
        self.frames.append(frame)

    def finish(self):
        self.frames.append(self.img.copy())  # last frame has no cursor


# ----------------------------------------------------------------------------
# 3. DRAWINGS (built from turtle commands)
# ----------------------------------------------------------------------------
def _jump(t, x, y, heading=0):
    t.penup(); t.goto(x, y); t.setheading(heading); t.pendown()


def _disc(t, cx, cy, r, fill, edge=None, steps=40):
    t.fillcolor(fill); t.pencolor(edge or fill)
    _jump(t, cx, cy - r); t.begin_fill(); t.circle(r, steps=steps); t.end_fill()


def _poly(t, pts):
    _jump(t, *pts[0]); t.begin_fill()
    for p in pts[1:] + [pts[0]]:
        t.goto(*p)
    t.end_fill()


def _sparkle(t, x, y, r, fill="#FFFFFF", edge="#C98A00"):
    t.pensize(2); t.pencolor(edge); t.fillcolor(fill)
    k = 0.3
    _poly(t, [(x, y + r), (x + r * k, y + r * k), (x + r, y), (x + r * k, y - r * k),
              (x, y - r), (x - r * k, y - r * k), (x - r, y), (x - r * k, y + r * k)])


def _confetti(t):
    colours = ["#D64545", "#2E9E6B", "#4F8FD9", "#F2994A", "#9B6BD6"]
    spots = [(-135, 120), (-110, 60), (-140, -20), (-120, -110), (130, 110), (112, 40), (140, -40), (118, -118),
             (-70, 140), (70, 138), (0, 148)]
    for i, (x, y) in enumerate(spots):
        _disc(t, x, y, 5, colours[i % len(colours)], steps=12)


def draw_smiley(t):
    t.pensize(4); _disc(t, 0, 0, 100, "#FFD84D", "#8A6D00", steps=72)
    t.pensize(1)
    for x in (-62, 62):
        _disc(t, x, -8, 13, "#F6A5A5", steps=24)
    for x in (-38, 38):
        _disc(t, x, 34, 12, INK, steps=30)
    for x in (-34, 42):
        _disc(t, x, 38, 4, "#FFFFFF", steps=16)
    t.pencolor(INK); t.pensize(5)
    _jump(t, -58, 60, 12); t.forward(34)
    _jump(t, 24, 68, -12); t.forward(34)
    t.pensize(6); _jump(t, -52, -22, -60); t.circle(60, 120)
    _sparkle(t, -128, 70, 16); _sparkle(t, 125, 80, 13); _sparkle(t, 118, -85, 10)
    _confetti(t)


def draw_trophy(t):
    t.pencolor("#8A6D00"); t.pensize(4); t.fillcolor("#FFC933")
    _poly(t, [(-60, 80), (60, 80), (36, 10), (-36, 10)])
    t.pensize(7)
    _jump(t, -50, 62, 270); t.circle(-15, 180)
    _jump(t, 50, 62, 270); t.circle(15, 180)
    t.pensize(4); t.fillcolor("#FFC933"); t.pencolor("#8A6D00")
    _poly(t, [(-9, 10), (9, 10), (9, -35), (-9, -35)])
    _poly(t, [(-45, -35), (45, -35), (45, -62), (-45, -62)])
    t.fillcolor("#D64545"); _poly(t, [(-30, -45), (30, -45), (30, -55), (-30, -55)])
    _sparkle(t, 0, 48, 22)
    _sparkle(t, -118, 90, 16); _sparkle(t, 118, 100, 14); _sparkle(t, 100, -20, 10); _sparkle(t, -105, -30, 10)
    _confetti(t)


def draw_seedling(t):
    _disc(t, -105, 105, 22, "#FFD84D", "#E0A800")  # sun
    t.pencolor("#E0A800"); t.pensize(3)
    for k in range(8):
        a = math.radians(k * 45)
        _jump(t, -105 + 28 * math.cos(a), 105 + 28 * math.sin(a), k * 45); t.forward(12)
    t.pencolor("#8A5A33"); t.pensize(3); t.fillcolor("#C98B5B")
    _poly(t, [(-55, -100), (55, -100), (40, -142), (-40, -142)])
    t.pencolor("#1F6F4A"); t.pensize(6)
    _jump(t, 0, -100, 90); t.forward(120)
    t.pensize(3); t.fillcolor("#7BCB8F")
    _jump(t, 0, -55, 15); t.begin_fill(); t.circle(55, 70); t.left(110); t.circle(55, 70); t.end_fill()
    _jump(t, 0, -55, 165); t.begin_fill(); t.circle(-55, 70); t.right(110); t.circle(-55, 70); t.end_fill()
    for k in range(6):  # a little flower bud on top
        a = math.radians(k * 60)
        _disc(t, 22 * math.cos(a), 28 + 22 * math.sin(a), 12, "#F6A5C0", "#D86A92", steps=24)
    _disc(t, 0, 28, 11, "#FFD84D", "#E0A800", steps=24)


def draw_pill(t):
    t.pensize(5); _disc(t, 0, 0, 78, "#FFFFFF", "#12343B", steps=72)
    t.pensize(3); _disc(t, 0, 0, 62, "#DDF1E6", "#2E9E6B", steps=60)
    t.pencolor("#12343B"); t.pensize(5)
    _jump(t, -78, 0, 0); t.forward(156)
    t.pencolor("#2E9E6B"); t.pensize(10)
    _jump(t, 0, 20, 90); t.forward(30)
    _jump(t, -15, 35, 0); t.forward(30)
    _sparkle(t, -108, 95, 16); _sparkle(t, 108, 88, 12); _sparkle(t, 102, -98, 14); _sparkle(t, -100, -90, 10)
    _confetti(t)


DRAW = {"trophy": draw_trophy, "smiley": draw_smiley, "seedling": draw_seedling, "pill": draw_pill}


@st.cache_data(show_spinner=False)
def build_art(kind, tweak=0):
    """Return an animated GIF (bytes) of the turtle drawing. `tweak` lets Replay restart the animation."""
    t = MiniTurtle(320, every=5)
    DRAW[kind](t)
    t.finish()
    frames = [f.convert("P", palette=Image.ADAPTIVE, colors=96) for f in t.frames]
    durations = [45] * (len(frames) - 1) + [3000 + tweak]
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=durations)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def static_art(kind):
    """The finished drawing as a still PNG (used in calm mode, where nothing moves)."""
    t = MiniTurtle(320, every=10 ** 9)
    DRAW[kind](t)
    buf = io.BytesIO()
    t.img.save(buf, format="PNG")
    return buf.getvalue()


# ----------------------------------------------------------------------------
# PIXEL-ART BACKGROUNDS (drawn with turtle commands on a tiny canvas, then scaled up without smoothing)
# ----------------------------------------------------------------------------
def _b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _tile_turtle(t, x, y, shell, edge, skin):
    """A little top-view turtle: four legs, head, tail and a patterned shell."""
    t.pensize(1)
    for dx, dy in ((-9, 7), (9, 7), (-9, -7), (9, -7)):
        _disc(t, x + dx, y + dy, 3, skin, edge, steps=12)
    _disc(t, x, y + 13, 4, skin, edge, steps=14)
    _disc(t, x, y - 12, 2, skin, edge, steps=10)
    _disc(t, x, y, 10, shell, edge, steps=24)
    _disc(t, x, y, 5, shell, edge, steps=16)


def _tile_plus(t, x, y, r, colour):
    t.pencolor(colour); t.pensize(2)
    _jump(t, x - r, y, 0); t.forward(2 * r)
    _jump(t, x, y - r, 90); t.forward(2 * r)


def _tile_pill(t, x, y, fill, edge):
    t.pensize(1); _disc(t, x, y, 5, fill, edge, steps=16)
    t.pencolor(edge); _jump(t, x - 5, y, 0); t.forward(10)


def _tile_sparkle(t, x, y, r, colour):
    t.pencolor(colour); t.fillcolor(colour); t.pensize(1)
    k = 0.34
    _poly(t, [(x, y + r), (x + r * k, y + r * k), (x + r, y), (x + r * k, y - r * k),
              (x, y - r), (x - r * k, y - r * k), (x - r, y), (x - r * k, y + r * k)])


def _tile_leaf(t, x, y, heading, fill, edge):
    t.pencolor(edge); t.fillcolor(fill); t.pensize(1)
    _jump(t, x, y, heading); t.begin_fill(); t.circle(9, 70, steps=14); t.left(110); t.circle(9, 70, steps=14); t.end_fill()


@st.cache_data(show_spinner=False)
def pixel_tile(dark=False):
    """A seamless 512px pixel-art tile (as base64 PNG): turtles, pills, plus signs, leaves and sparkles."""
    if dark:
        base, shell, edge, plus, pill_f, pill_e, spark = "#12343B", "#1A4C55", "#2A6B76", "#2A6B76", "#1E5760", "#2F7782", "#3A8793"
    else:
        base, shell, edge, plus, pill_f, pill_e, spark = SKY, "#D9EDE0", "#BDDFCB", "#C7E1E8", "#F1E8D4", "#E1D3B0", "#FFFFFF"
    t = MiniTurtle(128, bg=base, every=10 ** 9)
    _tile_turtle(t, -34, 30, shell, edge, shell)
    _tile_turtle(t, 36, -34, shell, edge, shell)
    for x, y, r in ((34, 38, 4), (-44, -40, 4), (-6, -2, 3)):
        _tile_plus(t, x, y, r, plus)
    _tile_pill(t, 8, 46, pill_f, pill_e); _tile_pill(t, -52, -6, pill_f, pill_e)
    for x, y, r in ((52, 6, 5), (-14, -52, 4), (12, 12, 3)):
        _tile_sparkle(t, x, y, r, spark)
    _tile_leaf(t, 46, -6, 15, shell, edge); _tile_leaf(t, -6, -26, 165, shell, edge)
    return _b64(t.img.resize((512, 512), Image.NEAREST))


@st.cache_data(show_spinner=False)
def walker_sheet():
    """Two animation frames of a pixel turtle walking right (96x64 each), as one base64 PNG sprite sheet."""
    outline, shell, light, skin = "#0E3B2B", "#2E9E6B", "#7BCB8F", "#9BD56B"
    frames = []
    for legs in ((5, 12), (8, 9)):
        im = Image.new("RGBA", (24, 16), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for x in legs:
            d.rectangle((x, 10, x + 3, 15), fill=skin, outline=outline)
        d.polygon([(4, 7), (1, 9), (4, 10)], fill=skin, outline=outline)
        d.ellipse((4, 1, 17, 12), fill=shell, outline=outline)
        d.ellipse((7, 3, 14, 9), outline=light)
        d.line((10, 2, 10, 11), fill=light)
        d.ellipse((16, 5, 22, 11), fill=skin, outline=outline)
        d.point((20, 7), fill="#12343B")
        frames.append(im)
    sheet = Image.new("RGBA", (48, 16), (0, 0, 0, 0))
    sheet.paste(frames[0], (0, 0)); sheet.paste(frames[1], (24, 0))
    return _b64(sheet.resize((192, 64), Image.NEAREST))


@st.cache_data(show_spinner=False)
def pixel_clouds():
    """A seamless strip of pixel-art clouds (base64 PNG, 1024x256) that scrolls slowly across the page."""
    im = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    white, shade = (255, 255, 255, 235), (205, 226, 233, 255)

    def cloud(x, y, s):
        for box in ((x, y + 8 * s, x + 26 * s, y + 18 * s), (x + 8 * s, y, x + 24 * s, y + 14 * s),
                    (x + 18 * s, y + 5 * s, x + 36 * s, y + 18 * s)):
            d.ellipse(box, fill=white)
        d.rectangle((x + 10 * s, y + 12 * s, x + 28 * s, y + 18 * s), fill=white)
        d.line((x + 4 * s, y + 19 * s, x + 33 * s, y + 19 * s), fill=shade)

    for x, y, s in ((10, 8, 1.0), (92, 26, 0.8), (158, 6, 1.1), (214, 30, 0.7)):
        cloud(x, y, s)
    return _b64(im.resize((1024, 256), Image.NEAREST))


def beep_wav():
    rate, n = 22050, 11025
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(11000 * math.sin(2 * math.pi * 880 * i / rate))) for i in range(n)))
    return buf.getvalue()


# ----------------------------------------------------------------------------
# 4. LOGIC
#    Each medicine is one dictionary, and the whole list is st.session_state.meds:
#    medicine = {"id": int, "name": str, "dose": str, "time": datetime.time,
#                "start": date it was added, "log": set of ISO dates on which the dose was taken}
#    Storing the days a dose was taken (instead of one True/False flag) lets us
#    build a weekly score, a streak and a report from the same data.
# ----------------------------------------------------------------------------
def now_local():
    """Current date and time in the time zone the user chose (so 'missed' is judged correctly)."""
    return datetime.now(ZoneInfo(st.session_state.tz))


def dose_status(med, now, grace):
    """taken / upcoming / due (within `grace` minutes after the time) / missed.
    This is the rule behind the green / yellow / red colours."""
    if now.date().isoformat() in med["log"]:  # already ticked off today
        return "taken"
    scheduled = datetime.combine(now.date(), med["time"], tzinfo=now.tzinfo)
    if now < scheduled:  # the time has not come yet
        return "upcoming"
    # the time has passed: still "due" during the grace period, "missed" after it
    return "due" if now <= scheduled + timedelta(minutes=grace) else "missed"


def day_counts(meds, day, now, grace):
    """(taken, scheduled) for one day. Today's doses only count once taken or missed,
    so a dose that is still to come never lowers the score unfairly."""
    taken = scheduled = 0
    for m in meds:
        if m["start"] > day:  # the medicine did not exist yet on that day
            continue
        done = day.isoformat() in m["log"]
        if day == now.date() and not done and dose_status(m, now, grace) in ("upcoming", "due"):
            continue  # still pending today: do not count it yet
        scheduled += 1
        taken += done  # True counts as 1, False as 0
    return taken, scheduled


def weekly_summary(meds, now, grace):
    """Returns (weekly score or None, list of (date, percent or None)) for the last 7 days.
    Score = doses taken / doses scheduled over the week, as a percentage."""
    daily, total_taken, total_sched = [], 0, 0
    for back in range(6, -1, -1):  # oldest day first, today last
        d = now.date() - timedelta(days=back)
        tk, sc = day_counts(meds, d, now, grace)
        total_taken += tk
        total_sched += sc
        daily.append((d, round(100 * tk / sc) if sc else None))  # None = nothing scheduled that day
    score = round(100 * total_taken / total_sched) if total_sched else None
    return score, daily


def current_streak(meds, now, grace):
    """Consecutive perfect days (every scheduled dose taken). Today counts only if
    every dose is already taken; otherwise today is skipped without breaking the streak."""
    streak = 0
    for back in range(0, 60):
        d = now.date() - timedelta(days=back)
        tk, sc = day_counts(meds, d, now, grace)
        if back == 0:  # today
            if sc and tk == sc and all(d.isoformat() in m["log"] for m in meds if m["start"] <= d):
                streak += 1
            continue
        if sc and tk == sc:  # a perfect earlier day extends the streak
            streak += 1
        else:  # the first imperfect day ends it
            break
    return streak


def earned_badges(meds, now, grace, score, streak):
    """Badge rules, used to celebrate small wins:
    first dose today, all doses today, a 3+ day streak, and a 90%+ week."""
    badges = []
    today_taken = [m for m in meds if now.date().isoformat() in m["log"]]
    if today_taken:
        badges.append("First step today")
    if meds and len(today_taken) == len(meds):
        badges.append("Perfect day")
    if streak >= 3:
        badges.append(f"{streak}-day streak")
    if score is not None and score >= 90:
        badges.append("Week warrior")
    return badges


def art_for(score):
    """Which Turtle drawing to show: trophy for 95%+, smiley for 75%+, otherwise a growing seedling."""
    if score is None:
        return None
    return "trophy" if score >= 95 else "smiley" if score >= 75 else "seedling"


def score_message(score):
    """A short, kind sentence that matches the weekly score (never blames the user)."""
    if score is None:
        return "Add a medicine to start your week."
    if score >= 95: return "Outstanding. Your routine is working beautifully."
    if score >= 75: return "Great work. You are building a steady routine."
    if score >= 50: return "Good effort. A little more consistency and you will be there."
    return "Every day is a fresh start. Let's take it one dose at a time."


def add_medicine(name, dose, t):
    """Create one medicine dictionary and append it to the list."""
    ss = st.session_state
    ss.meds.append({"id": ss.next_id, "name": name.strip(), "dose": dose.strip(), "time": t,
                    "start": now_local().date(), "log": set()})
    ss.next_id += 1  # every medicine gets its own id


def toggle_taken(med_id):
    """Mark today's dose as taken, or undo it. symmetric_difference adds the date if missing and removes it if present."""
    today = now_local().date().isoformat()
    for m in st.session_state.meds:
        if m["id"] == med_id:
            m["log"].symmetric_difference_update({today})


def delete_medicine(med_id):
    """Keep every medicine except the one with this id."""
    st.session_state.meds = [m for m in st.session_state.meds if m["id"] != med_id]


def load_demo():
    """Sample data: three medicines with six days of realistic history (fixed random seed, so it is repeatable)."""
    rng = random.Random(7)
    today = now_local().date()
    st.session_state.meds, st.session_state.next_id = [], 1
    for name, dose, hh in [("Metformin", "500 mg", 8), ("Vitamin D", "1 tablet", 13), ("Blood pressure tablet", "5 mg", 20)]:
        add_medicine(name, dose, dtime(hh, 0))
        med = st.session_state.meds[-1]
        med["start"] = today - timedelta(days=6)
        for back in range(1, 7):
            if rng.random() < 0.88:  # about 88% of past doses were taken
                med["log"].add((today - timedelta(days=back)).isoformat())


def build_report(meds, now, grace, score, streak):
    """The downloadable CSV for family or doctors: a summary header, then one row per medicine for the last 7 days."""
    days = [now.date() - timedelta(days=b) for b in range(6, -1, -1)]
    rows = []
    for m in meds:
        row = {"Medicine": m["name"], "Dose": m["dose"], "Time": m["time"].strftime("%I:%M %p")}
        for d in days:
            if m["start"] > d: mark = "-"  # not added yet
            elif d.isoformat() in m["log"]: mark = "Taken"
            elif d == now.date() and dose_status(m, now, grace) in ("upcoming", "due"): mark = "Pending"
            else: mark = "Missed"
            row[d.strftime("%a %d %b")] = mark
        rows.append(row)
    head = f"MedTimer weekly report,{now.strftime('%d %b %Y')}\nWeekly adherence,{score if score is not None else 'n/a'}%\nCurrent streak (days),{streak}\n\n"
    return head + pd.DataFrame(rows).to_csv(index=False)


def upcoming_doses(meds, now):
    """Untaken doses later today, as dicts for the browser notification script."""
    out = []
    for m in meds:
        if now.date().isoformat() in m["log"]:
            continue
        when = datetime.combine(now.date(), m["time"], tzinfo=now.tzinfo)
        ms = int((when - now).total_seconds() * 1000)
        if ms > 0:
            out.append({"id": m["id"], "name": m["name"], "label": m["time"].strftime("%I:%M %p"),
                        "day": now.date().isoformat(), "ms": ms})
    return out


# ----------------------------------------------------------------------------
# 5. DATA FOR CHARTS
# ----------------------------------------------------------------------------
def day_state(med, day, now, grace):
    """Taken / Missed / Pending / Not scheduled for one medicine on one day."""
    if med["start"] > day:
        return "Not scheduled"
    if day.isoformat() in med["log"]:
        return "Taken"
    if day == now.date() and dose_status(med, now, grace) in ("upcoming", "due"):
        return "Pending"
    return "Missed"


def heatmap_rows(meds, now, grace):
    rows = []
    for m in meds:
        for back in range(6, -1, -1):
            d = now.date() - timedelta(days=back)
            rows.append({"Medicine": m["name"], "Day": d.strftime("%a %d"), "State": day_state(m, d, now, grace)})
    return rows


def per_med_stats(meds, now, grace):
    rows = []
    for m in meds:
        states = [day_state(m, now.date() - timedelta(days=b), now, grace) for b in range(7)]
        taken, missed = states.count("Taken"), states.count("Missed")
        rows.append({"Medicine": m["name"], "Adherence %": round(100 * taken / (taken + missed)) if taken + missed else 0})
    return rows


def today_counts(meds, now, grace):
    counts = {"Taken": 0, "Pending": 0, "Missed": 0}
    for m in meds:
        state = day_state(m, now.date(), now, grace)
        if state in counts:
            counts[state] += 1
    return counts


def time_of_day_counts(meds):
    buckets = {"Morning": 0, "Afternoon": 0, "Evening": 0, "Night": 0}
    for m in meds:
        h = m["time"].hour
        key = "Morning" if 5 <= h < 12 else "Afternoon" if 12 <= h < 17 else "Evening" if 17 <= h < 21 else "Night"
        buckets[key] += 1
    return buckets
