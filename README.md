# MedTimer: Your Daily Medicine Companion


**Author:** TODO: vishvam himanshu patel 
**Course:** Year 1 Python Programming, Summative Assessment, Scenario 2 (Design MedTimer Daily Medicine Companion using Python)

---

## Project overview

MedTimer is a calm, large-print web app that helps older adults and people with chronic conditions take their medicines
on time. It turns medicine routines from stress and forgetfulness into clarity and peace of mind.

**The problem.** People forget doses because routines change, nothing reminds them, they take several medicines at
different times, or they stop once they feel better. Some medicines can also affect memory themselves.

**The solution.** Users type a medicine and a time, and MedTimer shows a colour-coded checklist that updates through the day:
**green = taken, yellow = upcoming, red = missed.** It calculates a weekly adherence score, celebrates streaks, draws a
**Turtle smiley or trophy** when the score is high, and offers a downloadable report for family or doctors.

**Design goals.** Large fonts, soft blue and green colours, simple buttons, kind language, and nothing that makes the user feel judged.
The planning notes and layout wireframe are in [`docs/PLANNING.md`](docs/PLANNING.md).

![Dashboard wireframe](docs/wireframe_dashboard.png)

## Key features

**Core features (from the brief)**
- Add, edit and delete daily medicines (name, optional dose, time of day)
- Live checklist of scheduled, taken and missed doses, colour-coded green, yellow and red
- Weekly adherence score with a 7-day chart
- Turtle drawing on good adherence: a trophy (95% or more), a smiley (75% or more), otherwise a growing seedling
- Tips and motivational quotes (14 of them, with a "show another" button)
- Optional features: audio beep and user-defined reminders (each medicine has its own time, with pop-up notifications)

**Extras**
- Streaks and badges (First step, Perfect day, 3+ day streak, Week warrior)
- Insights page: donut, trend, per-medicine and heat-map charts
- Anticholinergic check: scores any medicine against the ACB scale and totals your list
- Compare two medicines, and a Medji AI helper for general questions about generic medicines
- Nearby pharmacy finder with a map, and an SOS page with one-tap call buttons
- Time zone setting, high-contrast mode and a calm mode that switches animations off
- Pixel-art turtle theme with animations (can be turned off)

## Screenshots

<img width="1920" height="1080" alt="Screenshot (118)" src="https://github.com/user-attachments/assets/3f1bcb43-2ec3-4cae-9315-edf5832c1329" />
<img width="1920" height="1080" alt="Screenshot (117)" src="https://github.com/user-attachments/assets/16679ca7-8c45-42c8-9fa1-87432a74b04e" />
<img width="1920" height="1080" alt="Screenshot (116)" src="https://github.com/user-attachments/assets/ca3316ac-487e-478a-9629-e5122323592e" />
<img width="1920" height="1080" alt="Screenshot (115)" src="https://github.com/user-attachments/assets/6af5fc3c-a27b-49c7-9e69-fb981797a495" />
<img width="1920" height="1080" alt="Screenshot (114)" src="https://github.com/user-attachments/assets/cf41da5e-2a55-4f52-8403-5c8ded3340bc" />
<img width="1920" height="1080" alt="Screenshot (113)" src="https://github.com/user-attachments/assets/5ffe7d5c-247c-4d0d-952d-9696f1de948d" />
<img width="1920" height="1080" alt="Screenshot (112)" src="https://github.com/user-attachments/assets/6563aeae-6021-4440-9700-ec796974fa2f" />


Add more screenshots (for example the checklist with sample data, the Turtle smiley or trophy, the Insights charts and the live app) to the `screenshots` folder, then run `py update_screenshots.py` to add them here.

## How it works

**Data.** Every medicine is a Python dictionary, and the list of medicines is kept in `st.session_state`:
`{"id", "name", "dose", "time", "start", "log"}`. `log` is a set of the dates on which the dose was taken, so one structure
gives the checklist, the weekly score, the streak and the report.

| Part | Rule (in `core.py`) |
|---|---|
| Status colour | `dose_status()` compares the current time with the dose time: before it = **upcoming** (yellow), within the grace period (default 30 minutes) = **due**, later = **missed** (red), ticked = **taken** (green) |
| Weekly score | `weekly_summary()`: doses taken divided by doses scheduled over the last 7 days. Doses still to come today are not counted against the user |
| Streak | `current_streak()`: consecutive days with every dose taken |
| Badges | `earned_badges()`: first dose today, all doses today, 3+ day streak, 90%+ week |
| Turtle drawing | `art_for(score)` picks trophy, smiley or seedling; the drawings are made with turtle commands in `core.py` |

**Turtle graphics.** Python's built-in `turtle` module needs a desktop window, which Streamlit Cloud does not have.
The web app therefore runs the drawing functions on `MiniTurtle`, a small class with the same commands (`forward`, `left`,
`circle`, `begin_fill` and so on) that draws to an image and plays it back as an animated GIF. The drawing functions only
use real turtle commands, so `py turtle_demo.py smiley` draws the same picture with Python's real `turtle` module on any
computer with a screen.

## Integration details

| Integration | Used for | Where |
|---|---|---|
| Streamlit | Web interface, one function per page | `app.py` |
| pandas and Altair | Tables, charts and the CSV report | `app.py`, `core.py` |
| Pillow | Turtle drawings, pixel-art background, GIF animation | `core.py` |
| NVIDIA API (`nvidia/nemotron-3.5-super-vl-120b-a12b`) | Medji AI helper and medicine comparison | `services.py` |
| OpenStreetMap (Nominatim, Overpass), Photon, Open-Meteo | Place search and nearby pharmacies | `services.py` |
| Anticholinergic Cognitive Burden scale | Medicine scores (99 scored medicines, about 300 common ones recognised, brand names and spelling help) | `acb.py` |
| Browser Notification API | Pop-up at dose time while the page is open | `app.py` |

## Deployment instructions

### Run on your computer
```
pip install -r requirements.txt
streamlit run app.py
```
On Windows you can also use `py -m streamlit run app.py`.

### Add the NVIDIA key (kept private)
The key is never shown or typed in the app. Medji reads it from private settings only.
- **Locally:** copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and put your key in it. That file is listed in `.gitignore`.
- **On Streamlit Cloud:** add `NVIDIA_API_KEY = "nvapi-..."` under **Advanced settings, Secrets** (or **Manage app, Settings, Secrets** later).
- Never commit a real key. Before pushing, run `git ls-files .streamlit` and check that `secrets.toml` is not listed.

### Deploy on Streamlit Community Cloud
1. Upload the project to a GitHub repository (see the structure below).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub and choose **Create app**.
3. Select the repository, branch `main` and main file `app.py`.
4. Open **Advanced settings** and paste your secret, then click **Deploy**.
5. Copy the app's link into the **Live app** line at the top of this README.

## Repository structure
```
app.py                  main file: sidebar menu and every page
core.py                 logic, chart data and Turtle-style drawings
acb.py                  anticholinergic (ACB) scale and lookup
services.py             Medji (NVIDIA API), emergency detection, pharmacy search
turtle_demo.py          draws the same pictures with Python's real turtle module
test_medtimer.py        automated tests of the logic
requirements.txt        packages for Streamlit Cloud
.streamlit/             config.toml (light theme) and secrets.toml.example
docs/                   PLANNING.md and wireframe_dashboard.png
screenshots/            screenshots of the running app
update_screenshots.py   rebuilds the screenshot list above from the files in screenshots/
```

## Testing

**Automated.** `py test_medtimer.py` runs 9 tests of the status colours, score, streak, badges, Turtle choice, report and ACB lookup.








## Accessibility and design choices
- Large, readable text (Atkinson Hyperlegible) and strong contrast; status is shown in words as well as colour
- High-contrast mode, and a calm mode that removes all movement; the app also respects the browser's "reduce motion" setting
- Light theme forced in `.streamlit/config.toml` so a computer in dark mode does not change the colours
- Palette: soft blue `#EAF4F7`, deep teal `#12343B`, sea green `#2E9E6B`, warm yellow `#F2C230`, coral red `#D64545`

## Ethics, privacy and limits
- MedTimer is a reminder and learning tool, **not medical advice**. It never tells anyone to change a dose.
- **SOS cannot dispatch an ambulance.** The buttons open the phone's dialler for 108 or 112; on a computer, use a phone.
- Medji gives general information about generic medicines and can be wrong. It is told not to diagnose or give doses, and urgent wording shows the emergency numbers instead.
- The medicine list stays in the browser session and is never sent to NVIDIA. Medji only sees the questions typed.
- Pharmacy data comes from OpenStreetMap volunteers and may be incomplete. Pop-up notifications work only while the page is open.
- A medicine that is not on the ACB scale scores 0. The list of common medicines is a convenience, not a safety guarantee.

## Sources and acknowledgements
- Anticholinergic Cognitive Burden Scale, 2012 update. Aging Brain Care, Indiana University Center for Aging Research / Regenstrief Institute, copyright 2008, 2012. Used here for learning; contact acb@agingbraincare.org before any public or commercial use.
- Streamlit documentation; Python `turtle` documentation; NVIDIA API documentation; OpenStreetMap contributors.
- Fonts: Atkinson Hyperlegible and Silkscreen (Google Fonts).
- Built with AI assistance (Claude) for code and documentation, then reviewed and tested by the author.
- streamlit link:**[https://idai101-265279---vishvampatel-tg64wlw9sxtnxut2puxqbn.streamlit.app/](https://idai101-265279---vishvampatel-tg64wlw9sxtnxut2puxqbn.streamlit.app/)**
  
