"""
Anticholinergic Cognitive Burden (ACB) data and lookup for MedTimer.

The scores below follow the Anticholinergic Cognitive Burden Scale, 2012 update
(Aging Brain Care, Indiana University Center for Aging Research / Regenstrief Institute,
copyright 2008, 2012). Score 1 = possible anticholinergic, 2 = definite (moderate),
3 = definite (may cause delirium). Anything not on the scale counts as 0.
Use of the scale is subject to its Terms of Use: cite it, and request permission
(acb@agingbraincare.org) before any public or commercial use.
"""
import difflib
import re

import pandas as pd

# score|generic name|brand names (taken from the official scale)
_SCALE = """
1|Alimemazine|Theralen
1|Alverine|Spasmonal
1|Alprazolam|Xanax
1|Aripiprazole|Abilify
1|Asenapine|Saphris
1|Atenolol|Tenormin
1|Bupropion|Wellbutrin, Zyban
1|Captopril|Capoten
1|Cetirizine|Zyrtec
1|Chlorthalidone|Diuril, Hygroton
1|Cimetidine|Tagamet
1|Clidinium|Librax
1|Clorazepate|Tranxene
1|Codeine|
1|Colchicine|Colcrys
1|Desloratadine|Clarinex
1|Diazepam|Valium
1|Digoxin|Lanoxin
1|Dipyridamole|Persantine
1|Disopyramide|Norpace
1|Fentanyl|Duragesic, Actiq
1|Furosemide|Lasix
1|Fluvoxamine|Luvox
1|Haloperidol|Haldol
1|Hydralazine|Apresoline
1|Hydrocortisone|Cortef, Cortaid
1|Iloperidone|Fanapt
1|Isosorbide|Isordil, Ismo
1|Levocetirizine|Xyzal
1|Loperamide|Imodium
1|Loratadine|Claritin
1|Metoprolol|Lopressor, Toprol
1|Morphine|MS Contin, Avinza
1|Nifedipine|Procardia, Adalat
1|Paliperidone|Invega
1|Prednisone|Deltasone, Sterapred
1|Quinidine|Quinaglute
1|Ranitidine|Zantac
1|Risperidone|Risperdal
1|Theophylline|Theodur, Uniphyl
1|Trazodone|Desyrel
1|Triamterene|Dyrenium
1|Venlafaxine|Effexor
1|Warfarin|Coumadin
2|Amantadine|Symmetrel
2|Belladonna|
2|Carbamazepine|Tegretol
2|Cyclobenzaprine|Flexeril
2|Cyproheptadine|Periactin
2|Loxapine|Loxitane
2|Meperidine|Demerol
2|Methotrimeprazine|Levoprome
2|Molindone|Moban
2|Nefopam|Nefogesic
2|Oxcarbazepine|Trileptal
2|Pimozide|Orap
3|Amitriptyline|Elavil
3|Amoxapine|Asendin
3|Atropine|Sal-Tropine
3|Benztropine|Cogentin
3|Brompheniramine|Dimetapp
3|Carbinoxamine|Histex, Carbihist
3|Chlorpheniramine|Chlor-Trimeton
3|Chlorpromazine|Thorazine
3|Clemastine|Tavist
3|Clomipramine|Anafranil
3|Clozapine|Clozaril
3|Darifenacin|Enablex
3|Desipramine|Norpramin
3|Dicyclomine|Bentyl
3|Dimenhydrinate|Dramamine
3|Diphenhydramine|Benadryl
3|Doxepin|Sinequan
3|Doxylamine|Unisom
3|Fesoterodine|Toviaz
3|Flavoxate|Urispas
3|Hydroxyzine|Atarax, Vistaril
3|Hyoscyamine|Anaspaz, Levsin
3|Imipramine|Tofranil
3|Meclizine|Antivert
3|Methocarbamol|Robaxin
3|Nortriptyline|Pamelor
3|Olanzapine|Zyprexa
3|Orphenadrine|Norflex
3|Oxybutynin|Ditropan
3|Paroxetine|Paxil
3|Perphenazine|Trilafon
3|Promethazine|Phenergan
3|Propantheline|Pro-Banthine
3|Propiverine|Detrunorm
3|Quetiapine|Seroquel
3|Scopolamine|Transderm Scop
3|Solifenacin|Vesicare
3|Thioridazine|Mellaril
3|Tolterodine|Detrol
3|Trifluoperazine|Stelazine
3|Trihexyphenidyl|Artane
3|Trimipramine|Surmontil
3|Trospium|Sanctura
"""
ACB = {}  # generic name -> (score, [brand names])
for _line in _SCALE.strip().splitlines():
    _score, _name, _brands = _line.split("|")
    ACB[_name.lower()] = (int(_score), [b.strip() for b in _brands.split(",") if b.strip()])

# Reviewed for the 2012 update but NOT added to the scale (score 0)
REVIEWED_ZERO = {"fexofenadine": "Allegra", "gabapentin": "Neurontin", "topiramate": "Topamax",
                 "levetiracetam": "Keppra", "tamoxifen": "Nolvadex", "nizatidine": "Axid", "duloxetine": "Cymbalta"}

# Known to have anticholinergic activity, but NOT scored on the ACB scale: shown as a caution
OTHER_ANTICHOLINERGIC = {"ipratropium", "tiotropium", "umeclidinium", "aclidinium", "glycopyrronium", "glycopyrrolate",
                         "pheniramine", "triprolidine", "hyoscine", "buscopan", "butylscopolamine"}

# Common medicines that are not on the ACB scale (score 0)
_COMMON = """
paracetamol acetaminophen ibuprofen naproxen diclofenac aspirin ketorolac tramadol etoricoxib celecoxib mefenamic aceclofenac
nimesulide piroxicam indomethacin meloxicam amoxicillin azithromycin ciprofloxacin doxycycline cefixime cefuroxime ceftriaxone
cephalexin levofloxacin ofloxacin metronidazole clarithromycin erythromycin clindamycin nitrofurantoin trimethoprim
sulfamethoxazole penicillin ampicillin linezolid gentamicin norfloxacin tinidazole rifampicin isoniazid ethambutol pyrazinamide
fluconazole itraconazole terbinafine clotrimazole acyclovir valacyclovir oseltamivir ivermectin albendazole hydroxychloroquine
chloroquine primaquine metformin glimepiride gliclazide glibenclamide glipizide pioglitazone sitagliptin vildagliptin linagliptin
empagliflozin dapagliflozin canagliflozin insulin teneligliptin voglibose acarbose liraglutide semaglutide amlodipine
atorvastatin rosuvastatin simvastatin pravastatin losartan telmisartan olmesartan valsartan candesartan irbesartan ramipril
enalapril lisinopril perindopril bisoprolol carvedilol propranolol nebivolol labetalol clopidogrel prasugrel ticagrelor
rivaroxaban apixaban dabigatran hydrochlorothiazide indapamide spironolactone torsemide torasemide diltiazem verapamil
nitroglycerin ivabradine ranolazine amiodarone ezetimibe fenofibrate clonidine methyldopa prazosin doxazosin omeprazole
pantoprazole esomeprazole rabeprazole lansoprazole famotidine domperidone ondansetron metoclopramide lactulose bisacodyl
mesalazine sucralfate simethicone drotaverine salbutamol albuterol levosalbutamol montelukast budesonide formoterol
salmeterol fluticasone acebrophylline ambroxol bromhexine dextromethorphan guaifenesin pseudoephedrine phenylephrine
xylometazoline sertraline escitalopram citalopram fluoxetine mirtazapine lorazepam clonazepam zolpidem melatonin pregabalin
lamotrigine valproate phenytoin levodopa carbidopa pramipexole ropinirole donepezil memantine rivastigmine lithium sumatriptan
rizatriptan flunarizine betahistine levothyroxine thyroxine carbimazole prednisolone methylprednisolone dexamethasone estradiol
progesterone norethisterone letrozole anastrozole finasteride tamsulosin alfuzosin sildenafil tadalafil alendronate calcium
cholecalciferol folic cyanocobalamin ferrous zinc magnesium multivitamin omega allopurinol febuxostat methotrexate azathioprine
cyclosporine tacrolimus mycophenolate hydroxyurea potassium vitamin vitamins
"""
COMMON = set(_COMMON.split())

# Brand or alternative names -> generic name (Indian and international)
_EXTRA_ALIASES = {
    "crocin": "paracetamol", "dolo": "paracetamol", "calpol": "paracetamol", "tylenol": "paracetamol",
    "brufen": "ibuprofen", "advil": "ibuprofen", "motrin": "ibuprofen", "glycomet": "metformin", "glucophage": "metformin",
    "lipitor": "atorvastatin", "norvasc": "amlodipine", "ecosprin": "aspirin", "disprin": "aspirin",
    "singulair": "montelukast", "augmentin": "amoxicillin", "zithromax": "azithromycin", "azithral": "azithromycin",
    "voveran": "diclofenac", "voltaren": "diclofenac", "prilosec": "omeprazole", "nexium": "esomeprazole",
    "protonix": "pantoprazole", "zoloft": "sertraline", "lexapro": "escitalopram", "prozac": "fluoxetine",
    "plavix": "clopidogrel", "synthroid": "levothyroxine", "eltroxin": "levothyroxine", "thyronorm": "levothyroxine",
    "cetzine": "cetirizine", "avil": "pheniramine", "chlorphenamine": "chlorpheniramine", "dicycloverine": "dicyclomine",
    "paracetomol": "paracetamol", "imodium": "loperamide", "allegra": "fexofenadine", "neurontin": "gabapentin",
    "topamax": "topiramate", "keppra": "levetiracetam", "cymbalta": "duloxetine",
}


def _norm(text):
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


KNOWN = set(ACB) | set(REVIEWED_ZERO) | OTHER_ANTICHOLINERGIC | COMMON
ALIASES = {name: name for name in KNOWN}
for _g, (_s, _brands) in ACB.items():
    for _b in _brands:
        ALIASES[_norm(_b).strip()] = _g
for _g, _b in REVIEWED_ZERO.items():
    ALIASES[_b.lower()] = _g
for _a, _g in _EXTRA_ALIASES.items():
    ALIASES[_a] = _g
_ALIAS_ORDER = sorted(ALIASES, key=len, reverse=True)
_FUZZY = [n for n in set(ALIASES) | KNOWN if len(n) >= 5 and " " not in n]


def _result(generic, matched):
    if generic in ACB:
        return {"status": "scored", "name": generic, "score": ACB[generic][0], "matched": matched}
    if generic in REVIEWED_ZERO:
        return {"status": "reviewed", "name": generic, "score": 0, "matched": matched}
    if generic in OTHER_ANTICHOLINERGIC:
        return {"status": "other", "name": generic, "score": 0, "matched": matched}
    return {"status": "none", "name": generic, "score": 0, "matched": matched}


def check(text):
    """Look a medicine up. Returns a dict with status: scored, none, reviewed, other, suggest or unknown."""
    if not text or not text.strip():
        return None
    t = _norm(text)
    best = None
    for alias in _ALIAS_ORDER:
        if f" {alias} " in t:
            r = _result(ALIASES[alias], alias)
            if best is None or r["score"] > best["score"]:
                best = r
    if best:
        return best
    for token in t.split():
        if len(token) >= 5:
            close = difflib.get_close_matches(token, _FUZZY, n=1, cutoff=0.8)
            if close:
                return {"status": "suggest", "name": ALIASES.get(close[0], close[0]), "score": 0, "matched": close[0]}
    return {"status": "unknown", "name": text.strip(), "score": 0, "matched": ""}


def describe(r):
    """Plain-language sentence for a lookup result: returns (level, text)."""
    n = r["name"].title()
    if r["status"] == "scored":
        meaning = {1: "a possible anticholinergic effect", 2: "a definite anticholinergic effect (moderate)",
                   3: "a definite anticholinergic effect that may cause confusion or delirium"}[r["score"]]
        return ("warning" if r["score"] >= 2 else "info"), f"**{n}** has an ACB score of **{r['score']}**: {meaning}."
    if r["status"] == "reviewed":
        return "success", f"**{n}** was reviewed for the ACB scale and not added, so its score is **0**."
    if r["status"] == "other":
        return "warning", (f"**{n}** is not scored on the ACB scale, but it is known to have anticholinergic activity. "
                           "Ask your pharmacist about it.")
    if r["status"] == "none":
        return "success", (f"**{n}** is not on the ACB scale, so its score is **0**. "
                           "That means no significant anticholinergic effect is recorded for it.")
    if r["status"] == "suggest":
        return "info", f"I did not recognise that spelling. Did you mean **{r['name'].title()}**? Type it again to check."
    return "info", ("I do not recognise that name. Check the spelling, try the generic name, or ask Medji. "
                    "Anything that is not on the ACB scale counts as 0.")


def acb_total_message(total):
    """Total burden = sum of each medicine's score. A total of 3 or more is treated as clinically relevant."""
    if total == 0:
        return "success", "Your total is 0. None of your listed medicines are on the ACB scale."
    if total < 3:
        return "info", f"Your total is {total}. That is low, but mention it at your next check-up."
    return "warning", (f"Your total is {total}. A total of 3 or more is considered clinically relevant. Please talk to your "
                       "doctor or pharmacist about it. Do not stop or change any medicine on your own.")


def scale_table():
    rows = [{"Medicine": g.title(), "ACB score": s, "Brand names": ", ".join(b) or "-"} for g, (s, b) in ACB.items()]
    return pd.DataFrame(rows).sort_values(["ACB score", "Medicine"], ascending=[False, True]).reset_index(drop=True)
