"""
MedTimer - a calm, large-print daily medicine companion (Summative Assessment, Scenario 2).

Run with:  streamlit run app.py
Files: app.py (pages) | core.py (logic, drawings) | acb.py (ACB scale) | services.py (NVIDIA, maps)
"""
import html
import inspect
import json
import math
import time
from datetime import time as dtime
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import acb
import services as sv
from core import (COLORS, INK, LABELS, PILL_TEXT, SEA, SKY, TIMEZONES, TIPS, add_medicine, art_for, build_art,
                  build_report, static_art, pixel_tile, pixel_clouds, walker_sheet, current_streak, delete_medicine, dose_status, earned_badges, heatmap_rows, load_demo,
                  now_local, per_med_stats, score_message, time_of_day_counts, today_counts, toggle_taken,
                  upcoming_doses, weekly_summary, beep_wav)

VERSION = "v3.4"
# Compatibility: older Streamlit versions do not know some newer options, so check once and adapt.
_BUTTON = inspect.signature(st.button).parameters
STRETCH = {"width": "stretch"} if "width" in _BUTTON else {"use_container_width": True}
HAS_ICON = "icon" in _BUTTON
NAV = {
    "Track": [("Dashboard", ":material/dashboard:"), ("Insights", ":material/monitoring:")],
    "Understand": [("Medji", ":material/smart_toy:"), ("Anticholinergic check", ":material/psychology:"),
                   ("Compare medicines", ":material/compare_arrows:"), ("Learn", ":material/menu_book:")],
    "Help": [("Find a pharmacy", ":material/local_pharmacy:"), ("SOS", ":material/emergency:")],
}
PAGES = [name for group in NAV.values() for name, _ in group]
ss = st.session_state

st.set_page_config(page_title="MedTimer", page_icon="💊", layout="wide")
DEFAULTS = {"meds": [], "next_id": 1, "tip": 0, "last_art": None, "replay": 0, "tz": TIMEZONES[0], "grace": 30,
            "sound": False, "contrast": False, "page": PAGES[0], "chat": [], "notified": set(), "sig": None,
            "country": "India", "contact_name": "", "contact_phone": "", "pharm": None, "pending": "", "calm": False, "celebrated": "", "intro_done": False}
for _k, _v in DEFAULTS.items():
    ss.setdefault(_k, _v)
    ss[_k] = ss[_k]  # keeps settings alive when their widget is not on the current page


def page_title(text):
    st.title(text)
    st.markdown("<div class='hero'></div>", unsafe_allow_html=True)


def typewriter(text, delay=0.015):
    """Yields a reply word by word so it appears to be typed."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


def say(text):
    """Show text with a typing effect (plain text in calm mode or on old Streamlit)."""
    if hasattr(st, "write_stream") and not ss.calm:
        st.write_stream(typewriter(text))
    else:
        st.markdown(text)


def thinking(label):
    """Animated bouncing dots while we wait for a service. Call .empty() on the result when done."""
    holder = st.empty()
    holder.markdown(f"<div class='thinking'>{label} <span class='dots'><i></i><i></i><i></i></span></div>", unsafe_allow_html=True)
    return holder


def go(page):
    ss.page = page


def ask_medji(question):
    """Send a question to the Medji page."""
    ss.pending, ss.page = question, "Medji"


def embed_html(markup, height):
    """st.iframe in current Streamlit; falls back to components.html on older versions."""
    if hasattr(st, "iframe"):
        st.iframe(markup, height=height)
    else:
        components.html(markup, height=height)


def embed_url(url, height):
    if hasattr(st, "iframe"):
        st.iframe(url, height=height)
    else:
        components.iframe(url, height=height)


def show_chart(chart):
    try:
        st.altair_chart(chart, **STRETCH)
    except TypeError:
        st.altair_chart(chart)


# ----------------------------------------------------------------------------
# Style: palette, large print, animations, dark sidebar
# ----------------------------------------------------------------------------
bg, fg = ("#FFFFFF", "#000000") if ss.contrast else (SKY, INK)
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Silkscreen:wght@400;700&display=swap');
@keyframes rise { from {opacity:0; transform:translateY(14px);} to {opacity:1; transform:none;} }
@keyframes pulse { 0%,100% {box-shadow:0 0 0 0 rgba(242,194,48,.8);} 50% {box-shadow:0 0 0 10px rgba(242,194,48,0);} }
@keyframes glow { 0%,100% {box-shadow:0 0 0 0 rgba(214,69,69,.7);} 50% {box-shadow:0 0 0 9px rgba(214,69,69,0);} }
@keyframes slideIn { from {opacity:0; transform:translateX(-18px);} to {opacity:1; transform:none;} }
@keyframes flow { 0% {background-position:0% 50%;} 100% {background-position:300% 50%;} }
@keyframes shine { 0% {background-position:-200% 0;} 100% {background-position:200% 0;} }
@keyframes popin { 0% {transform:scale(.5); opacity:0;} 70% {transform:scale(1.15);} 100% {transform:scale(1); opacity:1;} }
@keyframes flicker { 0%,100% {transform:scale(1) rotate(-4deg);} 50% {transform:scale(1.2) rotate(4deg);} }
@keyframes swing { 0%,100% {transform:rotate(-35deg);} 50% {transform:rotate(-12deg);} }
@keyframes shimmer { from {background-position:0 0;} to {background-position:40px 0;} }
@keyframes drift { from {background-position:0 0, 0 0;} to {background-position:2048px 0, 512px 512px;} }
@keyframes driftSide { from {background-position:0 0, 0 0;} to {background-position:0 0, 512px 512px;} }
@keyframes walk { 0% {left:0; transform:scaleX(1);} 49.9% {left:calc(100% - 96px); transform:scaleX(1);} 50% {left:calc(100% - 96px); transform:scaleX(-1);} 99.9% {left:0; transform:scaleX(-1);} 100% {left:0; transform:scaleX(1);} }
@keyframes legs { 0% {background-position:0 0;} 50% {background-position:-96px 0;} }
@keyframes grow { from {transform:scaleY(0);} }
@keyframes crawl { from {left:-110px;} to {left:100vw;} }
@keyframes bounce { 0%,100% {transform:translateY(0);} 50% {transform:translateY(-9px);} }
@keyframes wave { 0%,60%,100% {transform:rotate(0);} 10%,30% {transform:rotate(16deg);} 20%,40% {transform:rotate(-8deg);} 50% {transform:rotate(14deg);} }
@keyframes flashGreen { 0% {background:#BFEBD3;} 100% {background:#FFFFFF;} }
@keyframes blinkBar { 50% {opacity:.45;} }
@keyframes medjiGlow { 0%,100% {box-shadow:0 0 0 0 rgba(159,227,192,0);} 50% {box-shadow:0 0 12px 2px rgba(159,227,192,.6);} }
@keyframes typing { to {width:8ch;} }
@keyframes blink { 50% {border-color:transparent;} }
@keyframes introFade { 0%,72% {opacity:1; visibility:visible;} 100% {opacity:0; visibility:hidden;} }
@keyframes wiggle { 0%,100% {transform:rotate(0);} 25% {transform:rotate(-16deg);} 75% {transform:rotate(16deg);} }
@keyframes activeglow { 0%,100% {box-shadow:inset 4px 0 0 #fff, 0 0 0 0 rgba(159,227,192,0);} 50% {box-shadow:inset 4px 0 0 #fff, 0 0 14px 3px rgba(159,227,192,.55);} }

/* page: pixel-art turtle background */
.stApp { background-color:__BG__; isolation:isolate; }
.stApp::before { content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background:url(data:image/png;base64,__CLOUDS__) 0 0 / 1024px 256px repeat-x, url(data:image/png;base64,__TILE__) 0 0 / 512px 512px;
  image-rendering:pixelated; animation:drift 120s linear infinite; }
.stApp::after { content:""; position:fixed; left:-110px; bottom:8px; width:96px; height:64px; z-index:-1; pointer-events:none; opacity:.9;
  background:url(data:image/png;base64,__WALKER__) 0 0 / 192px 64px; image-rendering:pixelated; animation:crawl 55s linear infinite, legs .6s steps(1,end) infinite; }
[data-testid="stHeader"], [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:transparent !important; }
__HC__
.stApp, .stApp p, .stApp label, .stApp li, .stApp button, .stApp input { font-family:'Atkinson Hyperlegible',sans-serif !important; font-size:1.15rem; color:__FG__; }
.stApp h1 { font-family:'Silkscreen','Atkinson Hyperlegible',monospace !important; font-size:2.3rem !important; letter-spacing:.02em; color:__FG__; animation:rise .6s ease both; }
.stApp h2, .stApp h3 { font-size:1.8rem !important; color:__FG__; animation:rise .7s ease both; }
.stButton button, .stDownloadButton button, .stLinkButton a { min-height:3rem; border-radius:6px; font-weight:700; box-shadow:3px 3px 0 rgba(18,52,59,.32); transition:transform .12s, box-shadow .12s; }
.stButton button:active, .stDownloadButton button:active { transform:translate(2px,2px); box-shadow:1px 1px 0 rgba(18,52,59,.32); }
[data-testid="stBaseButton-primary"] { background:#2E9E6B; border-color:#2E9E6B; color:#fff; }
.hero { height:6px; margin:-8px 0 16px; background:linear-gradient(90deg,#2E9E6B,#4F8FD9,#9B6BD6,#F2994A,#2E9E6B); background-size:300% 100%; animation:flow 8s linear infinite; }
.med { padding:14px 18px; border-radius:6px; margin-bottom:6px; background:#FFFFFF; color:#12343B; box-shadow:4px 4px 0 rgba(18,52,59,.22); animation:rise .5s ease both; transition:transform .2s, box-shadow .2s; }
.med:hover { transform:translateY(-3px); box-shadow:6px 8px 0 rgba(18,52,59,.22); }
.med-name { font-size:1.45rem; font-weight:700; } .med-time { font-size:1.1rem; margin-top:4px; }
.pill { display:inline-block; padding:2px 14px; border-radius:20px; font-weight:700; margin-left:8px; }
.pill.due { animation:pulse 1.6s infinite; } .pill.taken { animation:popin .5s ease both; }
.badge { display:inline-block; padding:6px 16px; margin:4px 6px 4px 0; border-radius:6px; background-color:#2E9E6B; color:#fff; font-weight:700;
  background-image:linear-gradient(110deg,rgba(255,255,255,0) 35%,rgba(255,255,255,.45) 50%,rgba(255,255,255,0) 65%); background-size:200% 100%;
  animation:rise .7s ease both, shine 3.5s ease-in-out infinite; box-shadow:3px 3px 0 rgba(18,52,59,.25); }
.flame { display:inline-block; animation:flicker 1.1s ease-in-out infinite; transform-origin:50% 90%; }
[data-testid="stProgress"] div[role="progressbar"] > div { background-image:repeating-linear-gradient(45deg,rgba(255,255,255,.28) 0 10px,rgba(255,255,255,0) 10px 20px); background-size:40px 40px; animation:shimmer 1s linear infinite; }
a.sos { display:block; text-align:center; padding:22px 10px; margin:10px 0; border-radius:6px; background:#D64545; color:#fff !important; font-size:1.7rem; font-weight:700; text-decoration:none; animation:glow 2s infinite; box-shadow:4px 4px 0 rgba(18,52,59,.35); }
a.sos.alt { background:#12343B; animation:none; }

/* sidebar: dark pixel-art panel with bright text */
[data-testid="stSidebar"] { background:linear-gradient(180deg,rgba(18,52,59,.93) 0%,rgba(27,85,96,.93) 100%), url(data:image/png;base64,__DTILE__);
  background-size:100% 100%, 512px 512px; image-rendering:pixelated; animation:driftSide 100s linear infinite; }
[data-testid="stSidebarContent"], [data-testid="stSidebarHeader"] { background:transparent !important; }
.stApp [data-testid="stSidebar"], .stApp [data-testid="stSidebar"] * { color:#FFFFFF !important; }
.stApp [data-testid="stSidebar"] .group { color:#9FE3C0 !important; margin:18px 0 4px; font-family:'Silkscreen','Atkinson Hyperlegible',monospace; font-size:.85rem; letter-spacing:.08em; text-transform:uppercase; animation:slideIn .6s ease both; }
.stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"], .stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color:#CFEFE0 !important; }
.stApp [data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.3) !important; }
[data-testid="stSidebar"] .brand { display:flex; align-items:center; gap:12px; font-family:'Silkscreen','Atkinson Hyperlegible',monospace; font-size:1.6rem; font-weight:700; margin:4px 0 2px; text-shadow:3px 3px 0 rgba(0,0,0,.35); }
[data-testid="stSidebar"] .logo { width:44px; height:22px; border-radius:22px; background:linear-gradient(90deg,#2E9E6B 50%,#FFFFFF 50%); transform:rotate(-35deg); box-shadow:0 0 0 2px #FFFFFF; animation:swing 3.2s ease-in-out infinite; }
[data-testid="stSidebar"] .stButton button { justify-content:flex-start; background:transparent; border:0; box-shadow:none; padding-left:12px; border-radius:4px; transition:background .2s, transform .2s, box-shadow .2s; }
[data-testid="stSidebar"] .stButton button:hover { background:rgba(255,255,255,.16); transform:translateX(5px); box-shadow:inset 4px 0 0 #9FE3C0; }
[data-testid="stSidebar"] .stButton button:hover [data-testid="stIconMaterial"] { animation:wiggle .5s ease; }
[data-testid="stSidebar"] .stButton button:active { transform:translateX(5px) scale(.97); }
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] { background:#2E9E6B; font-weight:700; animation:activeglow 2.4s ease-in-out infinite; }
[data-testid="stSidebar"] .st-key-nav_sos button { background:#D64545 !important; font-weight:700; margin-top:6px; }
[data-testid="stSidebar"] .st-key-nav_medji button { border:2px solid rgba(255,255,255,.45); }
.sidegraph { margin:14px 0 4px; padding:10px 12px 8px; border:3px solid rgba(255,255,255,.4); background:rgba(0,0,0,.22); animation:rise .7s ease both; }
.sg-title { display:flex; justify-content:space-between; font-family:'Silkscreen','Atkinson Hyperlegible',monospace; font-size:.95rem; margin-bottom:8px; }
.sg-bars { display:flex; align-items:flex-end; gap:6px; }
.sg-col { flex:1; display:flex; flex-direction:column; align-items:center; }
.sg-bw { height:58px; width:100%; display:flex; align-items:flex-end; }
.sg-bar { width:100%; transform-origin:bottom; animation:grow .9s steps(8) both; background-image:repeating-linear-gradient(to top, rgba(0,0,0,0) 0 6px, rgba(0,0,0,.3) 6px 8px); }
.sg-day { font-size:.75rem; margin-top:3px; }
.lane { position:relative; height:70px; margin-top:12px; overflow:hidden; border-bottom:4px solid #2E9E6B; }
.walker { position:absolute; bottom:0; width:96px; height:64px; background:url(data:image/png;base64,__WALKER__) 0 0 / 192px 64px; image-rendering:pixelated; animation:walk 14s linear infinite, legs .6s steps(1,end) infinite; }
.wave { display:inline-block; transform-origin:70% 70%; animation:wave 2.6s ease-in-out infinite; }
.med.taken { animation:rise .5s ease both, flashGreen 1.2s ease; }
.thinking { font-weight:700; padding:6px 0; }
.dots i { display:inline-block; width:9px; height:9px; margin:0 3px; background:#2E9E6B; animation:bounce 1s infinite; }
.dots i:nth-child(2) { animation-delay:.15s; } .dots i:nth-child(3) { animation-delay:.3s; }
[data-testid="stMetric"] { animation:rise .6s ease both; transition:transform .2s; } [data-testid="stMetric"]:hover { transform:translateY(-3px); }
[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"], [data-testid="stBarChart"], [data-testid="stAreaChart"] { animation:rise .8s ease both; }
[data-baseweb="tab-panel"], [data-testid="stChatMessage"] { animation:rise .5s ease both; }
[data-testid="stImage"] img { transition:transform .3s; } [data-testid="stImage"] img:hover { transform:rotate(-2deg) scale(1.04); }
[data-testid="stSidebar"] .st-key-nav_medji button { animation:medjiGlow 3s ease-in-out infinite 1s; }
.sg-col:last-child .sg-bar { animation:grow .9s steps(8) both, blinkBar 1.6s step-end 1.2s infinite; }
.intro { position:fixed; inset:0; z-index:99999; background:#12343B; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:22px; pointer-events:none; animation:introFade 3.4s ease forwards; }
.intro .lane { width:min(520px,70vw); border-bottom-color:#9FE3C0; } .intro .walker { animation:walk 3s linear infinite, legs .6s steps(1,end) infinite; }
.intro-title { font-family:'Silkscreen',monospace; font-size:2.6rem; color:#FFFFFF; }
.intro-title .typed { display:inline-block; overflow:hidden; white-space:nowrap; width:0; border-right:5px solid #9FE3C0; animation:typing 1.4s steps(8) .4s forwards, blink .6s step-end infinite; }
.intro-sub { color:#9FE3C0; font-size:1.1rem; }
__STAGGER__
@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } .intro { display:none !important; } }
</style>
"""
STAGGER = "".join(f".st-key-nav_{n.lower().replace(' ', '_')} {{ animation:slideIn .5s ease both; animation-delay:{i * 0.07:.2f}s; }}"
                  for i, n in enumerate(PAGES))
HC = ".stApp::before, .stApp::after { display:none; }" if ss.contrast else ""
CALM = "<style>* { animation:none !important; transition:none !important; } .intro { display:none !important; }</style>" if ss.calm else ""
st.markdown(CSS.replace("__BG__", bg).replace("__FG__", fg).replace("__CLOUDS__", pixel_clouds()).replace("__TILE__", pixel_tile(False)).replace("__DTILE__", pixel_tile(True))
            .replace("__WALKER__", walker_sheet()).replace("__STAGGER__", STAGGER).replace("__HC__", HC) + CALM, unsafe_allow_html=True)

if not ss.intro_done and not ss.calm:  # a short welcome animation, shown only once per visit
    st.markdown("<div class='intro'><div class='lane'><div class='walker'></div></div>"
                "<div class='intro-title'><span class='typed'>MedTimer</span></div>"
                "<div class='intro-sub'>Getting your day ready...</div></div>", unsafe_allow_html=True)
ss.intro_done = True

now = now_local()
grace = ss.grace

# ----------------------------------------------------------------------------
# Sidebar: brand, grouped menu, SOS
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div class='brand'><span class='logo'></span>MedTimer</div>", unsafe_allow_html=True)
    st.caption("Your daily medicine companion")
    for group, items in NAV.items():
        st.markdown(f"<div class='group'>{group}</div>", unsafe_allow_html=True)
        for name, icon in items:
            slug = name.lower().replace(" ", "_")
            if name == "SOS":
                st.button("SOS: emergency help", key="nav_sos", on_click=go, args=(name,), **STRETCH, **({"icon": icon} if HAS_ICON else {}))
            else:
                st.button(name, key=f"nav_{slug}", on_click=go, args=(name,), **STRETCH,
                          type="primary" if ss.page == name else "secondary", **({"icon": icon} if HAS_ICON else {}))


# ----------------------------------------------------------------------------
# Medji in-app reminders: checks every 30 seconds on every page
# ----------------------------------------------------------------------------
def _every_30s(func):
    """Runs the check every 30 seconds where Streamlit supports it; otherwise on each interaction."""
    try:
        return st.fragment(run_every="30s")(func)
    except (AttributeError, TypeError):
        return func


@_every_30s
def due_watcher():
    t = now_local()
    stats = {m["id"]: dose_status(m, t, ss.grace) for m in ss.meds}
    for m in ss.meds:
        key = (m["id"], t.date().isoformat())
        if stats[m["id"]] == "due" and key not in ss.notified:
            ss.notified.add(key)
            st.toast(f"Medji: time to take {m['name']} ({m['time'].strftime('%I:%M %p')})", icon="💊")
            if ss.sound:
                st.audio(beep_wav(), format="audio/wav", autoplay=True)
    sig = tuple(sorted(stats.items()))
    changed = ss.sig is not None and sig != ss.sig
    ss.sig = sig
    if changed:
        st.rerun()  # refresh colours on the page


due_watcher()

meds = sorted(ss.meds, key=lambda m: m["time"])
numbers = sv.EMERGENCY_NUMBERS[ss.country]


def sidebar_graph():
    """Little pixel bar chart of the last 7 days, shown in the sidebar."""
    if not meds:
        return ("<div class='sidegraph'><div class='sg-title'><span>This week</span></div>"
                "<div style='font-size:.95rem'>Add a medicine to see your week here.</div></div>")
    score, daily = weekly_summary(meds, now, grace)
    cols = ""
    for d, p in daily:
        colour = "#5F7F86" if p is None else "#2E9E6B" if p >= 75 else "#F2C230" if p >= 50 else "#D64545"
        height = max(4, round((p or 0) * 0.58))
        tip = f"{d:%a %d}: {'no doses' if p is None else str(p) + '%'}"
        cols += (f"<div class='sg-col'><div class='sg-bw'><div class='sg-bar' title='{tip}' "
                 f"style='height:{height}px;background-color:{colour}'></div></div><span class='sg-day'>{d:%a}</span></div>")
    shown = "--" if score is None else f"{score}%"
    return f"<div class='sidegraph'><div class='sg-title'><span>This week</span><span>{shown}</span></div><div class='sg-bars'>{cols}</div></div>"


with st.sidebar:
    st.markdown(sidebar_graph(), unsafe_allow_html=True)
    st.markdown("<div class='lane'><div class='walker'></div></div>", unsafe_allow_html=True)
    st.divider()
    st.caption(f"MedTimer {VERSION}. A reminder and learning tool, not medical advice.")


def notify_html(doses, show_button=True):
    """Browser (device) notifications. Works while this tab stays open."""
    data = json.dumps(doses).replace("<", "\\u003c")
    return """
<div style="font-family:sans-serif;display:__SHOW__">
<button id="b" style="font-size:18px;padding:10px 18px;border-radius:10px;border:0;background:#2E9E6B;color:#fff;cursor:pointer">Turn on Medji notifications</button>
<span id="s" style="margin-left:10px;font-size:16px;color:#12343B"></span></div>
<script>
const doses = __DOSES__;
const P = window.parent || window;
const N = P.Notification || window.Notification;
const S = document.getElementById('s'), B = document.getElementById('b');
function show(){
  if(!N){S.textContent='This browser does not support notifications.';B.style.display='none';return;}
  if(N.permission==='granted'){S.textContent='Notifications are on. Keep this tab open.';B.style.display='none';}
  else if(N.permission==='denied'){S.textContent='Notifications are blocked in your browser settings.';B.style.display='none';}
}
B.onclick = () => { try { N.requestPermission().then(show); } catch(e) { S.textContent='Could not ask for permission here.'; } };
show();
function fire(d){
  const key='medji_'+d.id+'_'+d.day;
  try{ if(P.sessionStorage.getItem(key)) return; P.sessionStorage.setItem(key,'1'); }catch(e){}
  if(N && N.permission==='granted'){ try{ new N('Medji: time for your medicine',{body:d.name+' at '+d.label,requireInteraction:true}); }catch(e){} }
}
doses.forEach(d => { if(d.ms>0 && d.ms<86400000) setTimeout(()=>fire(d), d.ms); });
</script>""".replace("__DOSES__", data).replace("__SHOW__", "block" if show_button else "none")


embed_html(notify_html(upcoming_doses(meds, now), show_button=False), 1)  # schedules device alerts on every page


def ring_html(score, animate=True):
    """Progress ring for the weekly score. The ring draws itself and the number counts up."""
    pct = 0 if score is None else score
    colour = "#2E9E6B" if pct >= 75 else "#E0A800" if pct >= 50 else "#D64545"
    c = 2 * math.pi * 54
    label = "--" if score is None else f"{score}%"
    anim = ("@keyframes draw{from{stroke-dashoffset:%.1f}} .ring{animation:draw 1.5s ease-out}"
            "@keyframes pop{from{opacity:0;transform:scale(.6)}to{opacity:1;transform:none}} .num{animation:pop .8s ease-out .3s both;transform-origin:70px 70px}"
            % c) if animate else ""
    if animate and pct >= 95:
        anim += ("@keyframes glowRing{0%,100%{filter:drop-shadow(0 0 0 #2E9E6B)}50%{filter:drop-shadow(0 0 7px #2E9E6B)}} "
                 ".ring{animation:draw 1.5s ease-out,glowRing 2.2s ease-in-out 1.6s infinite}")
    counter = ("<script>const n=document.getElementById('n');const end=%d;let s=null;"
               "function step(t){if(!s)s=t;const p=Math.min((t-s)/1500,1);n.textContent=Math.round(end*p)+'%%';if(p<1)requestAnimationFrame(step);}"
               "requestAnimationFrame(step);</script>" % pct) if animate and score is not None else ""
    return (f"<style>body{{margin:0;font-family:sans-serif;background:transparent}}{anim}</style>"
            f"<svg width='190' height='190' viewBox='0 0 140 140'>"
            f"<circle cx='70' cy='70' r='54' fill='none' stroke='#CFE3E8' stroke-width='14'/>"
            f"<circle class='ring' cx='70' cy='70' r='54' fill='none' stroke='{colour}' stroke-width='14' stroke-linecap='round' "
            f"stroke-dasharray='{c:.1f}' stroke-dashoffset='{c * (1 - pct / 100):.1f}' transform='rotate(-90 70 70)'/>"
            f"<text id='n' class='num' x='70' y='72' text-anchor='middle' font-size='30' font-weight='700' fill='#12343B'>{label}</text>"
            f"<text class='num' x='70' y='92' text-anchor='middle' font-size='11' fill='#12343B'>weekly adherence</text></svg>{counter}")


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_dashboard():
    # All the numbers on this page come from the logic functions in core.py
    score, daily = weekly_summary(meds, now, grace)  # weekly adherence score and the 7 daily percentages
    streak = current_streak(meds, now, grace)  # consecutive perfect days
    statuses = {m["id"]: dose_status(m, now, grace) for m in meds}  # taken / upcoming / due / missed for each medicine

    page_title("Dashboard")
    hour = now.hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    c1, c2 = st.columns([3, 2])
    c1.markdown(f"<span class='wave'>👋</span> <b>{greeting}.</b> Today is {now.strftime('%A, %d %B')}, and it is {now.strftime('%I:%M %p')}.",
                unsafe_allow_html=True)
    c2.selectbox("Time zone", TIMEZONES, key="tz")

    with st.form("ask_form", clear_on_submit=True):
        q1, q2 = st.columns([5, 1.4])
        question = q1.text_input("Ask Medji", placeholder="Ask Medji about any medicine, e.g. 'Can I take paracetamol on an empty stomach?'",
                                 label_visibility="collapsed")
        if q2.form_submit_button("Ask Medji", **STRETCH) and question.strip():
            ask_medji(question.strip())
            st.rerun()

    with st.expander("Medji notifications and settings"):
        st.write("Medji can pop up a notification on this device when a dose is due. It works while this page stays open in your browser.")
        embed_html(notify_html([]), 70)
        st.selectbox("Country (for emergency numbers)", list(sv.EMERGENCY_NUMBERS), key="country")
        s1, s2, s3, s4 = st.columns([2, 1.3, 1.3, 1.6])
        s1.slider("Minutes before a dose counts as missed", 10, 120, step=10, key="grace")
        s2.checkbox("Play a beep when a dose is due", key="sound")
        s3.checkbox("High-contrast mode", key="contrast")
        s4.checkbox("Calm mode (less movement)", key="calm", help="Turns off animations, balloons and the typing effect.")
        b1, b2 = st.columns(2)
        b1.button("Load sample week", on_click=load_demo, help="Fills the app with example medicines and history for testing.")
        if b2.button("Clear everything"):
            ss.meds, ss.next_id = [], 1
            st.rerun()

    # --- Input area at the top: medicine name, dose and time (as in the wireframe) ---
    st.subheader("Add a medicine")
    with st.form("add_form", clear_on_submit=True):
        f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
        name = f1.text_input("Medicine name", placeholder="e.g. Metformin")
        dose = f2.text_input("Dose (optional)", placeholder="e.g. 500 mg")
        when = f3.time_input("Time to take it", value=dtime(8, 0), step=300)
        f4.markdown("<div style='height:2.1rem'></div>", unsafe_allow_html=True)
        submitted = f4.form_submit_button("Add medicine", **STRETCH)
    if submitted:
        if not name.strip():
            st.error("Please type the medicine name, then press Add medicine.")
        elif any(m["name"].lower() == name.strip().lower() and m["time"] == when for m in ss.meds):
            st.warning(f"{name.strip()} is already on your list at {when.strftime('%I:%M %p')}.")
        else:
            add_medicine(name, dose, when)
            st.success(f"Added {name.strip()} at {when.strftime('%I:%M %p')}.")
            st.rerun()

    all_done = bool(meds) and all(s == "taken" for s in statuses.values())
    if all_done and ss.celebrated != now.date().isoformat():
        ss.celebrated = now.date().isoformat()
        st.toast("All doses taken today. Well done!", icon="🎉")
        if not ss.calm:
            st.balloons()

    # Checklist on the left; weekly score, Turtle drawing, badges and tip on the right (the side)
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Today's checklist")
        if not meds:
            st.info("Your list is empty. Add your first medicine above, or load the sample week in the settings.")
        else:
            taken_n = sum(s == "taken" for s in statuses.values())
            st.progress(taken_n / len(meds), text=f"{taken_n} of {len(meds)} doses taken today")
        due_css = "".join(f".st-key-t{m['id']} button {{ animation:pulse 1.6s infinite; }}" for m in meds if statuses[m["id"]] == "due")
        if due_css and not ss.calm:
            st.markdown(f"<style>{due_css}</style>", unsafe_allow_html=True)
        for m in meds:  # one colour-coded card per medicine
            status = statuses[m["id"]]
            dose_txt = f" ({html.escape(m['dose'])})" if m["dose"] else ""
            a, b = st.columns([4, 1.4])
            a.markdown(
                f"<div class='med {'taken' if status == 'taken' else ''}' style='border-left:14px solid {COLORS[status]}'>"
                f"<div class='med-name'>{html.escape(m['name'])}{dose_txt}</div>"
                f"<div class='med-time'>{m['time'].strftime('%I:%M %p')}"
                f"<span class='pill {status}' style='background:{COLORS[status]};color:{PILL_TEXT[status]}'>{LABELS[status]}</span></div></div>",
                unsafe_allow_html=True)
            b.button("Undo" if status == "taken" else "Mark taken", key=f"t{m['id']}", on_click=toggle_taken,
                     args=(m["id"],), **STRETCH, type="secondary" if status == "taken" else "primary")
            with st.expander("Edit or delete"):
                e1, e2 = st.columns(2)
                new_name = e1.text_input("Name", m["name"], key=f"n{m['id']}")
                new_time = e2.time_input("Time", m["time"], key=f"tm{m['id']}", step=300)
                s1, s2 = st.columns(2)
                if s1.button("Save changes", key=f"s{m['id']}"):
                    if new_name.strip():
                        m["name"], m["time"] = new_name.strip(), new_time
                        st.rerun()
                    else:
                        st.error("The name cannot be empty.")
                if s2.button("Delete medicine", key=f"d{m['id']}"):
                    delete_medicine(m["id"])
                    st.rerun()
        if st.button("Refresh times"):
            st.rerun()

    with right:
        st.subheader("Your week")
        embed_html(ring_html(score, not ss.calm), 195)
        st.write(score_message(score))
        # The Turtle drawing depends on the weekly score (trophy / smiley / seedling); a pill shows when the list is empty
        kind = art_for(score) or "pill"
        if kind != ss.last_art:  # the picture changed: celebrate and replay the animation
            if kind == "trophy" and not ss.calm:
                st.balloons()
            ss.last_art = kind
        st.image(static_art(kind) if ss.calm else build_art(kind, ss.replay), width=320)
        if not ss.calm and st.button("Replay drawing"):
            ss.replay += 1
            st.rerun()
        flame = "<span class='flame'>🔥</span> " if streak > 0 else ""
        st.markdown(f"{flame}<b>Streak:</b> {streak} perfect day{'s' if streak != 1 else ''} in a row", unsafe_allow_html=True)
        badges = earned_badges(meds, now, grace, score, streak)
        st.markdown("".join(f"<span class='badge'>{b}</span>" for b in badges)
                    or "Take a dose today to earn your first badge.", unsafe_allow_html=True)
        st.subheader("Tip for today")
        st.info(TIPS[ss.tip % len(TIPS)])
        if st.button("Show another tip"):
            ss.tip += 1
            st.rerun()

    st.divider()
    st.subheader("Last 7 days")
    chart = pd.DataFrame({"Day": [d.strftime("%a %d") for d, _ in daily],
                          "Adherence %": [p or 0 for _, p in daily]}).set_index("Day")
    st.bar_chart(chart, color=SEA, height=260)
    st.caption("See more charts on the Insights page.")
    st.download_button("Download weekly report (CSV)", build_report(meds, now, grace, score, streak),
                       file_name=f"medtimer_report_{now.date()}.csv", mime="text/csv", disabled=not meds)
    with st.expander("About MedTimer and your privacy"):
        st.write("MedTimer is a reminder and tracking tool. It is not medical advice and never tells you to change a dose. "
                 "Your list lives only in this browser session and nothing is stored on a server, so download your report to keep it. "
                 "If you use Medji or the pharmacy finder, only what you type (and your medicine list, if you allow it) is sent to those services.")


def page_insights():
    page_title("Insights")
    if not meds:
        st.info("Add medicines on the Dashboard (or load the sample week) to see your charts.")
        return
    score, daily = weekly_summary(meds, now, grace)
    k1, k2, k3 = st.columns(3)
    k1.metric("Weekly adherence", "--" if score is None else f"{score}%")
    k2.metric("Current streak", f"{current_streak(meds, now, grace)} days")
    k3.metric("Medicines tracked", len(meds))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Today")
        counts = today_counts(meds, now, grace)
        if sum(counts.values()):
            df = pd.DataFrame({"Status": list(counts), "Doses": list(counts.values())})
            donut = alt.Chart(df).mark_arc(innerRadius=70, cornerRadius=6).encode(
                theta="Doses:Q",
                color=alt.Color("Status:N", scale=alt.Scale(domain=["Taken", "Pending", "Missed"],
                                                            range=["#2E9E6B", "#F2C230", "#D64545"]),
                                legend=alt.Legend(orient="bottom")),
                tooltip=["Status", "Doses"]).properties(height=280)
            show_chart(donut)
    with c2:
        st.subheader("Adherence trend")
        trend = pd.DataFrame({"Day": [d.strftime("%a %d") for d, _ in daily], "Adherence %": [p or 0 for _, p in daily]})
        area = alt.Chart(trend).mark_area(line={"color": SEA}, color=alt.Gradient(
            gradient="linear", stops=[alt.GradientStop(color="#2E9E6B", offset=0), alt.GradientStop(color="#EAF4F7", offset=1)],
            x1=1, x2=1, y1=1, y2=0)).encode(x=alt.X("Day:N", sort=None), y=alt.Y("Adherence %:Q", scale=alt.Scale(domain=[0, 100])),
                                           tooltip=["Day", "Adherence %"]).properties(height=280)
        show_chart(area)

    st.subheader("Each medicine, last 7 days")
    st.bar_chart(pd.DataFrame(per_med_stats(meds, now, grace)), x="Medicine", y="Adherence %", horizontal=True, color=SEA)

    st.subheader("Week at a glance")
    hm = pd.DataFrame(heatmap_rows(meds, now, grace))
    days = list(dict.fromkeys(hm["Day"]))
    heat = alt.Chart(hm).mark_rect(cornerRadius=6, stroke="white", strokeWidth=3).encode(
        x=alt.X("Day:N", sort=days, title=None), y=alt.Y("Medicine:N", title=None),
        color=alt.Color("State:N", scale=alt.Scale(domain=["Taken", "Missed", "Pending", "Not scheduled"],
                                                   range=["#2E9E6B", "#D64545", "#F2C230", "#D5DEE0"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Medicine", "Day", "State"]).properties(height=max(120, 56 * len(meds) + 50))
    show_chart(heat)

    st.subheader("When you take your medicines")
    tod = time_of_day_counts(meds)
    st.bar_chart(pd.DataFrame({"Time of day": list(tod), "Medicines": list(tod.values())}), x="Time of day", y="Medicines", color="#4F8FD9")


def medji_key():
    """The NVIDIA key comes only from the app's secrets or environment. It is never shown or typed on screen."""
    return sv.get_api_key()[0]


def medicine_summary():
    return "; ".join(f"{m['name']} {m['dose']} at {m['time'].strftime('%I:%M %p')}".replace("  ", " ") for m in meds)


def page_medji():
    page_title("Medji, your medicine helper")
    st.info("Medji shares general information about **generic medicines** only. It is not a doctor and cannot diagnose you or change "
            f"your treatment. If something feels serious, please call or visit a doctor. In an emergency, call {numbers[0]} "
            f"(ambulance: {numbers[1]}) straight away.")
    api_key = medji_key()
    if not ss.chat:
        st.caption("Try one of these:")
        ideas = ["What is paracetamol used for?", "Which common medicines can affect memory?",
                 "What does anticholinergic mean?", "How can I remember to take my medicines?"]
        cols = st.columns(len(ideas))
        for col, idea in zip(cols, ideas):
            col.button(idea, key=f"idea_{idea}", on_click=ask_medji, args=(idea,), **STRETCH)
    for msg in ss.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    typed = st.chat_input("Ask Medji about a generic medicine, e.g. 'What is paracetamol used for?'")
    question, ss.pending = ss.pending or typed, ""
    if question:
        ss.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            if sv.looks_like_emergency(question):
                reply = sv.emergency_reply(ss.country)
                st.markdown(reply)
            elif not api_key:
                reply = "Medji is not connected yet, so I cannot answer right now. Please try again later."
                st.markdown(reply)
            else:
                dots = thinking("Medji is thinking")
                ok, reply = sv.ask_medji(api_key, sv.get_model(), ss.chat[-10:])
                dots.empty()
                if ok:
                    reply += "\n\n*General information only. Please check with a doctor or pharmacist before changing anything.*"
                    say(reply)
                else:
                    st.markdown(reply)
        ss.chat.append({"role": "assistant", "content": reply})
    if ss.chat and st.button("Clear chat"):
        ss.chat = []
        st.rerun()


def acb_message(result):
    level, text = acb.describe(result)
    getattr(st, level)(text)


def page_acb():
    page_title("Anticholinergic check")
    st.write("Anticholinergic medicines block acetylcholine, a chemical messenger the brain uses for memory and attention. "
             "The **anticholinergic burden (ACB)** is the combined effect of all such medicines you take. "
             "Each medicine on the scale scores **1** (possible effect), **2** (definite, moderate) or **3** (definite, severe). "
             "Medicines that are not on the scale score **0**. Your total is the sum.")
    query = st.text_input("Type any medicine name (generic or brand)", placeholder="e.g. paracetamol, Benadryl, amitriptyline")
    result = acb.check(query)
    if result:
        acb_message(result)
        if result["status"] != "unknown":
            subject = result["name"].title()
            st.button(f"Ask Medji about {subject}", on_click=ask_medji, key="ask_acb", type="primary",
                      args=(f"What is {result['name']} generally used for, and can it affect memory or cause confusion in older adults? "
                            "Explain in simple words.",))
    st.subheader("Your medicine list")
    if meds:
        rows, total = [], 0
        for m in meds:
            r = acb.check(m["name"])
            total += r["score"]
            note = {"scored": "On the ACB scale", "reviewed": "Reviewed, not scored", "none": "Not on the scale (0)",
                    "other": "Caution: see pharmacist", "suggest": "Check spelling", "unknown": "Not recognised"}[r["status"]]
            rows.append({"Medicine": m["name"], "ACB score": r["score"], "Note": note})
        df = pd.DataFrame(rows)
        t1, t2 = st.columns([3, 2])
        t1.dataframe(df, hide_index=True, **STRETCH)
        t2.metric("Total burden", total)
        level, text = acb.acb_total_message(total)
        getattr(st, level)(text)
        st.bar_chart(df, x="Medicine", y="ACB score", color="#D64545")
    else:
        st.caption("Add medicines on the Dashboard and your total burden will appear here.")
    with st.expander(f"Browse the whole ACB scale ({len(acb.ACB)} medicines)"):
        st.dataframe(acb.scale_table(), hide_index=True, **STRETCH)
    st.caption("Source: Anticholinergic Cognitive Burden Scale, 2012 update (Aging Brain Care, Indiana University Center for Aging Research / "
               "Regenstrief Institute, copyright 2008, 2012). Used here for learning. Contact acb@agingbraincare.org for permission before any "
               "public or commercial use. This is not medical advice.")


def page_compare():
    page_title("Compare two medicines")
    st.caption("Type any two medicine names. You do not need to have them on your list.")
    c1, c2 = st.columns(2)
    a = c1.text_input("First medicine", key="cmp_a", placeholder="e.g. cetirizine")
    b = c2.text_input("Second medicine", key="cmp_b", placeholder="e.g. diphenhydramine")
    ra, rb = acb.check(a), acb.check(b)
    if ra and rb:
        st.subheader("Anticholinergic burden side by side")
        m1, m2 = st.columns(2)
        m1.metric("First", f"{ra['name'].title()}: {ra['score']}")
        m2.metric("Second", f"{rb['name'].title()}: {rb['score']}")
        acb_message(ra)
        acb_message(rb)
        st.bar_chart(pd.DataFrame({"Medicine": [ra["name"].title(), rb["name"].title()], "ACB score": [ra["score"], rb["score"]]}),
                     x="Medicine", y="ACB score", color="#D64545")
        st.write(f"Taking both together would add up to **{ra['score'] + rb['score']}**. A total of 3 or more is considered clinically relevant.")
        st.subheader("Ask Medji to compare them")
        api_key = medji_key()
        if st.button("Compare with Medji", type="primary"):
            if not api_key:
                st.warning("Medji is not connected yet, so it cannot compare right now.")
            else:
                prompt = (f"Compare the generic medicines '{ra['name']}' and '{rb['name']}' for a general reader. Use short sections: "
                          "What each is generally used for; Common side effects; Important cautions (including memory, confusion "
                          "or falls in older adults); Main differences. No doses. Under 250 words.")
                dots = thinking("Medji is comparing")
                ok, reply = sv.ask_medji(api_key, sv.get_model(), [{"role": "user", "content": prompt}])
                dots.empty()
                if ok:
                    say(reply)
                else:
                    st.error(reply)
                if ok:
                    st.caption("General information only. Please check with a doctor or pharmacist before changing anything.")
    else:
        st.info("Enter two medicine names to compare them.")


def page_pharmacy():
    page_title("Find a nearby pharmacy")
    place = st.text_input("Your area and city", placeholder="e.g. Navrangpura, Ahmedabad (or a pin code, or latitude, longitude)")
    radius = st.selectbox("How far to look", [1000, 2000, 5000], index=1, format_func=lambda m: f"{m // 1000} km")
    if st.button("Search pharmacies", type="primary"):
        if not place.strip():
            st.error("Please type your area and city first.")
        else:
            dots = thinking("Searching nearby")
            region = "India" if ss.country == "India" else ""
            ss.pharm = (place.strip(), *sv.find_pharmacies(place.strip(), radius, region))
            dots.empty()
    if place.strip():
        b1, b2 = st.columns(2)
        b1.link_button("Open in Google Maps", sv.maps_search_url(place.strip()), **STRETCH)
        b2.link_button("Open in OpenStreetMap", sv.osm_search_url(place.strip()), **STRETCH)
    if ss.pharm:
        searched, ok, result = ss.pharm
        if ok and result["rows"]:
            df = pd.DataFrame(result["rows"])
            if result["matched"] and result["matched"].lower() != searched.lower():
                st.warning(f"I could not find '{searched}' exactly, so I searched around '{result['matched']}'.")
            st.success(f"Found {len(df)} pharmacies and chemists near {result['matched'] or searched}.")
            st.map(df.rename(columns={"lon": "longitude", "lat": "latitude"}), zoom=14)
            st.dataframe(df[["name", "km", "hours", "phone"]].rename(columns={"name": "Pharmacy", "km": "Distance (km)",
                         "hours": "Opening hours", "phone": "Phone"}), hide_index=True, **STRETCH)
            st.caption("Data comes from OpenStreetMap volunteers and may be incomplete. Call ahead to check a pharmacy is open.")
        else:
            st.error(result if not ok else "No pharmacies were listed in that range. Try a wider distance.")
            st.write("Here is a Google Maps view instead. If it does not load, use the buttons above.")
            embed_url(sv.maps_embed_url(searched), 450)


def page_sos():
    page_title("SOS: get help now")
    st.error("MedTimer cannot send an ambulance by itself. The buttons below dial the emergency services from your phone. "
             "On a computer, use your phone to call.")
    st.selectbox("Country", list(sv.EMERGENCY_NUMBERS), key="country")
    numbers_now = sv.EMERGENCY_NUMBERS[ss.country]
    st.markdown(f"<a class='sos' href='tel:{numbers_now[1]}'>Call ambulance: {numbers_now[1]}</a>"
                f"<a class='sos alt' href='tel:{numbers_now[0]}'>Call emergency services: {numbers_now[0]}</a>",
                unsafe_allow_html=True)
    st.subheader("Tell someone you trust")
    c1, c2 = st.columns(2)
    c1.text_input("Emergency contact name", key="contact_name")
    c2.text_input("Their phone number with country code", key="contact_phone", placeholder="+91XXXXXXXXXX")
    where = st.text_input("Where are you? (address or landmark)")
    include = st.checkbox("Include my medicine list in the message", value=True)
    msg = f"EMERGENCY: I need help. I am at: {where or 'unknown location'}."
    if include and meds:
        msg += f" My medicines: {medicine_summary()}."
    digits = "".join(ch for ch in ss.contact_phone if ch.isdigit())
    if digits:
        d1, d2 = st.columns(2)
        d1.link_button("Send WhatsApp message", f"https://wa.me/{digits}?text={quote(msg)}", **STRETCH)
        d2.markdown(f"<a href='sms:+{digits}?body={quote(msg)}'>Send a text message instead</a>", unsafe_allow_html=True)
    else:
        st.caption("Add your contact's phone number to get one-tap message buttons.")
    st.subheader("What to tell the operator")
    st.markdown("- Where you are, and any landmark nearby\n- What happened and how many people need help\n"
                "- Whether the person is awake and breathing\n- The medicines they take (shown below)\n- Stay on the line until they say you can hang up")
    st.subheader("Medical card")
    if meds:
        st.dataframe(pd.DataFrame([{"Medicine": m["name"], "Dose": m["dose"], "Time": m["time"].strftime("%I:%M %p")} for m in meds]),
                     hide_index=True, **STRETCH)
    else:
        st.caption("Your medicine list will show here for the paramedics.")


def page_learn():
    page_title("Learn")
    t1, t2, t3 = st.tabs(["Why track?", "Side effects", "Healthy habits"])
    with t1:
        st.subheader("Why does a person need a tracker?")
        st.write("A medicine only works when the right dose is taken at the right time. Missed doses can let a condition flare up, "
                 "and doubled doses can cause harm. A tracker gives you one clear place to see what is done and what is next.")
        st.subheader("Why do so many people forget?")
        st.markdown("- **Busy, changing days.** Routines shift, and a dose slips by unnoticed.\n- **No reminder.** Nothing in the day tells you it is time.\n"
                    "- **Many medicines at different times.** The more tablets, the easier it is to lose track.\n"
                    "- **Feeling better.** People stop or skip once the symptoms ease.\n"
                    "- **Memory difficulties.** Some medicines can themselves affect memory and attention, which makes forgetting more likely.")
        st.subheader("How MedTimer helps")
        st.markdown("- A colour-coded checklist: green is taken, yellow is coming up, red is missed.\n- Medji reminders on your device.\n"
                    "- A weekly score and streak, so progress is visible.\n- A report you can share with family or a doctor.")
    with t2:
        st.subheader("What can anticholinergic medicines do?")
        st.write("When acetylcholine is blocked, signals between brain cells slow down. Memory, attention and clear thinking are the first to feel it. "
                 "Older adults are more affected because the body clears medicines more slowly and the brain is more sensitive, "
                 "but younger people can have effects too.")
        c1, c2 = st.columns(2)
        c1.markdown("**In the brain**\n- Confusion or delirium\n- Poor memory and attention\n- Slower thinking\n- Dizziness and falls\n- Long-term, a higher risk of cognitive decline")
        c2.markdown("**In the body**\n- Dry mouth (which can lead to tooth decay)\n- Constipation\n- Blurred vision\n- Difficulty passing urine")
        st.subheader("What can you do?")
        st.write("Never stop a medicine suddenly. Take your medicine list to your doctor or pharmacist and ask: "
                 "*Is there an alternative with a lower anticholinergic burden?* Review the list regularly, especially if you see several doctors.")
    with t3:
        st.subheader("Habits that support a healthy brain")
        st.write("These habits support brain health. They do not cancel out a medicine's side effects, but they help your mind and body cope better.")
        st.markdown("- **Sleep well.** Keep a regular bedtime. Most adults need 7 to 9 hours. Sleep is when the brain sorts and stores memories.\n"
                    "- **Keep your mind busy.** Read, do puzzles, learn something new or play word games.\n"
                    "- **Move your body.** A daily walk helps blood flow to the brain and improves balance, which lowers the risk of falls.\n"
                    "- **Talk with people.** Conversation with family and friends exercises memory and attention, and lifts mood.")


{"Dashboard": page_dashboard, "Insights": page_insights, "Medji": page_medji, "Anticholinergic check": page_acb,
 "Compare medicines": page_compare, "Find a pharmacy": page_pharmacy, "SOS": page_sos, "Learn": page_learn}[ss.page]()
