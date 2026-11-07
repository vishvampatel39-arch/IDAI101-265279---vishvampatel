"""Run with:  py check_setup.py   It checks that MedTimer can start and tells you what is wrong."""
import importlib
import os
import sys

print("Python:", sys.version.split()[0])
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
missing = [f for f in ("app.py", "core.py", "acb.py", "services.py", "requirements.txt") if not os.path.exists(os.path.join(here, f))]
print("Missing files:", ", ".join(missing) if missing else "none")
for pkg in ("streamlit", "pandas", "PIL", "altair", "requests", "tzdata"):
    try:
        m = importlib.import_module(pkg)
        print(f"  {pkg}: OK {getattr(m, '__version__', '')}")
    except Exception as e:
        print(f"  {pkg}: PROBLEM ({type(e).__name__}). Fix with:  py -m pip install -r requirements.txt")
for mod in ("core", "acb", "services"):
    try:
        importlib.import_module(mod)
        print(f"  {mod}.py: OK")
    except Exception as e:
        print(f"  {mod}.py: PROBLEM -> {type(e).__name__}: {e}")
print("\nIf everything says OK, start the app with:  py -m streamlit run app.py")
