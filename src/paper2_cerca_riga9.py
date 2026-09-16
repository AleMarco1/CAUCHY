# -*- coding: utf-8 -*-
"""
paper2_cerca_riga9.py -- cerca il codice e i risultati del test su maschere sintetiche del
Paper 1 §8.2, da cui escono il "-3.4 +/- 2.8 per cent" e le 58 configurazioni (riga 9 del
budget di 5.1).

SOLA LETTURA: non modifica nessun file cercato. Scrive un solo report JSONL nuovo (rifiuta di
sovrascriverne uno esistente), di default in results/paper2, che il freeze esenta.

Cosa cerca, dal testo del Paper 1 §8.2:
  - le cinque topologie di maschera: slab, shell, tube, wedge, slab-with-holes;
  - il campo: campi gaussiani, pendenze spettrali -1.5 e -2.3, rumore bianco condiviso;
  - il criterio: w-bar, peso del kernel in maschera, test differenziale, contrasto;
  - impronte numeriche: 36.9 e 33.5 (contrasto vero e misurato), 0.019 e 0.158 (escursioni di
    forma), 19.5 (bias assoluto), 3.4 e 2.8 (bias differenziale), 240 e 58 (configurazioni).

Le impronte numeriche sono indizi DEBOLI: un file con migliaia di numeri ne contiene alcune per
caso. Il report dice quanti numeri ha letto per ogni file, e la classifica mette prima le parole
chiave e poi i numeri. Lo script NON emette un verdetto: ordina candidati da aprire a mano.

Uso:
  python src\\paper2_cerca_riga9.py selftest
  python src\\paper2_cerca_riga9.py cerca --root D:\\projects\\cauchy
  python src\\paper2_cerca_riga9.py cerca --root D:\\projects\\cauchy --root D:\\projects\\cauchy_2.0 --git

Opzioni di cerca:
  --root DIR      una o piu' radici (ripetibile)
  --out FILE      report JSONL; default results/paper2/ricerca_riga9_<UTC>.jsonl
  --git           cerca anche nella storia git (pickaxe) i file che hanno aggiunto o tolto
                  "wedge" e "slab": trova codice cancellato o mai salvato nel ramo attuale
  --max-mb N      salta file di testo piu' grandi di N MB (default 50)
  --top N         candidati stampati per categoria (default 15)
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

VERSIONE = "1.0"

# ---------------------------------------------------------------------------
# Cosa cercare
# ---------------------------------------------------------------------------

# Topologie: confine di LETTERA, non di parola, perche' nei nomi di funzione il separatore e'
# spesso "_" (make_wedge, wedge_mask), che per \b e' un carattere di parola. Cosi' "PowerShell" e
# "youtube" restano esclusi (lettera prima), "make_wedge" e "slab2" sono inclusi.
# "shell" non conta se seguito da "=" (shell=True di subprocess).
_L0, _L1 = r"(?<![A-Za-z])", r"(?![A-Za-z])"
TOPOLOGIE = {
    "slab": re.compile(_L0 + r"slabs?" + _L1, re.I),
    "shell": re.compile(_L0 + r"shells?" + _L1 + r"(?!\s*=)", re.I),
    "tube": re.compile(_L0 + r"tubes?" + _L1, re.I),
    "wedge": re.compile(_L0 + r"wedges?" + _L1, re.I),
    "holes": re.compile(_L0 + r"holes?" + _L1 + r"|slab[_\-\s]*with[_\-\s]*holes|slab_?holes", re.I),
}
CAMPO = {
    "gaussian_random_field": re.compile(r"gaussian[_\s\-]*random[_\s\-]*field|\bgrf\b", re.I),
    "white_noise": re.compile(r"white[_\s\-]*noise", re.I),
    "spectral_slope": re.compile(r"spectral[_\s\-]*slope|power[_\s\-]*law|pendenz[ae][_\s]*spettral", re.I),
    "slope_-1.5_e_-2.3": re.compile(r"-\s*1\.5\b[\s\S]{0,200}?-\s*2\.3\b|-\s*2\.3\b[\s\S]{0,200}?-\s*1\.5\b"),
}
CRITERIO = {
    "wbar": re.compile(r"\bw[_\-]?bar\b|\bwbar\b|w̄", re.I),
    "kernel_weight": re.compile(r"kernel[_\s\-]*weight|in[_\-\s]*mask[_\s\-]*weight", re.I),
    "differential": re.compile(r"differenzial|differential", re.I),
    "synthetic": re.compile(r"synthetic|sintetic", re.I),
    "contrast": re.compile(r"\bcontrast|contrasto", re.I),
    "retention": re.compile(r"retention|ritenzione", re.I),
}

# Impronte numeriche: (etichetta, forte?, lista di (valore, decimali di confronto))
IMPRONTE = [
    ("contrasto_vero_36.9", True, [(36.9, 1), (0.369, 3)]),
    ("contrasto_misurato_33.5", True, [(33.5, 1), (0.335, 3)]),
    ("escursione_differenziale_0.019", True, [(0.019, 3)]),
    ("escursione_assoluta_0.158", True, [(0.158, 3)]),
    ("bias_assoluto_19.5", False, [(19.5, 1), (0.195, 3)]),
    ("bias_differenziale_3.4", False, [(3.4, 1), (0.034, 3)]),
    ("errore_2.8", False, [(2.8, 1), (0.028, 3)]),
    ("configurazioni_240", False, [(240.0, 0)]),
    ("configurazioni_58", False, [(58.0, 0)]),
]
NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")

EST_CODICE = {".py", ".ipynb", ".pyw"}
EST_DATI = {".json", ".jsonl", ".csv", ".tsv", ".txt", ".log", ".yaml", ".yml", ".toml", ".cfg", ".ini"}
EST_DOC = {".md", ".tex", ".rst", ".bib"}
DIR_SALTATE = {".git", "__pycache__", "node_modules", ".ipynb_checkpoints", ".venv", "venv",
               "env", ".mypy_cache", ".pytest_cache"}


class Errore(Exception):
    pass


# ---------------------------------------------------------------------------
# Lettura
# ---------------------------------------------------------------------------

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def leggi_testo(p, est):
    """Restituisce il testo, oppure None se il file e' binario. Non solleva su encoding."""
    with open(p, "rb") as f:
        raw = f.read()
    if b"\x00" in raw[:8192]:
        return None
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        txt = raw.decode("latin-1")
    if est == ".ipynb":
        try:
            nb = json.loads(txt)
            celle = nb.get("cells", [])
            parti = []
            for c in celle:
                src = c.get("source", "")
                parti.append("".join(src) if isinstance(src, list) else str(src))
                for o in c.get("outputs", []) or []:
                    t = o.get("text")
                    if t:
                        parti.append("".join(t) if isinstance(t, list) else str(t))
            txt = "\n".join(parti)
        except (ValueError, AttributeError):
            pass  # notebook malformato: si cerca sul testo grezzo
    return txt


def categoria(est):
    if est in EST_CODICE:
        return "codice"
    if est in EST_DATI:
        return "dati"
    if est in EST_DOC:
        return "documenti"
    return None


# ---------------------------------------------------------------------------
# Analisi di un testo
# ---------------------------------------------------------------------------

def trova_gruppo(txt, gruppo):
    return sorted(k for k, rx in gruppo.items() if rx.search(txt))


def trova_impronte(txt):
    numeri = NUM.findall(txt)
    valori = []
    for s in numeri:
        try:
            valori.append(float(s))
        except ValueError:
            pass
    trovate = []
    for etichetta, forte, forme in IMPRONTE:
        hit = False
        for v, dec in forme:
            for x in valori:
                if round(abs(x), dec) == v:
                    hit = True
                    break
            if hit:
                break
        if hit:
            trovate.append((etichetta, forte))
    return trovate, len(valori)


def estratti(txt, max_n=6):
    """Righe con topologie o parole del campo, con numero di riga."""
    out = []
    rxs = list(TOPOLOGIE.values()) + list(CAMPO.values())[:3]
    for i, riga in enumerate(txt.splitlines(), 1):
        if any(rx.search(riga) for rx in rxs):
            out.append([i, riga.strip()[:200]])
            if len(out) >= max_n:
                break
    return out


def punteggio(top, camp, crit, impr):
    forti = sum(1 for _, f in impr if f)
    deboli = len(impr) - forti
    return 3 * len(top) + 2 * len(camp) + len(crit) + 2 * forti + deboli


def candidato_forte(top, camp):
    return len(top) >= 3 or (len(top) >= 2 and len(camp) >= 1)


def analizza(p, root, max_bytes):
    est = os.path.splitext(p)[1].lower()
    cat = categoria(est)
    if cat is None:
        return None, "estensione"
    try:
        size = os.path.getsize(p)
    except OSError:
        return None, "illeggibile"
    if size > max_bytes:
        return None, "troppo_grande"
    try:
        txt = leggi_testo(p, est)
    except OSError:
        return None, "illeggibile"
    if txt is None:
        return None, "binario"
    top = trova_gruppo(txt, TOPOLOGIE)
    camp = trova_gruppo(txt, CAMPO)
    crit = trova_gruppo(txt, CRITERIO)
    impr, n_num = trova_impronte(txt)
    sc = punteggio(top, camp, crit, impr)
    if sc == 0:
        return None, "nessun_indizio"
    st = os.stat(p)
    rec = {
        "tipo": "candidato",
        "categoria": cat,
        "percorso": os.path.relpath(p, root),
        "radice": root,
        "punteggio": sc,
        "forte": candidato_forte(top, camp),
        "topologie": top,
        "campo": camp,
        "criterio": crit,
        "impronte": [e for e, _ in impr],
        "impronte_forti": [e for e, f in impr if f],
        "numeri_letti": n_num,
        "byte": size,
        "mtime_utc": _dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha256_file(p),
        "estratti": estratti(txt),
    }
    return rec, "candidato"


def cammina(root, max_bytes, out_abs):
    cand, saltati = [], {}
    if not os.path.isdir(root):
        raise Errore(f"radice non trovata: {root}")
    for d, sub, files in os.walk(root, onerror=lambda e: saltati.__setitem__("dir_illeggibile",
                                                                              saltati.get("dir_illeggibile", 0) + 1)):
        sub[:] = sorted(s for s in sub if s not in DIR_SALTATE)
        for f in sorted(files):
            p = os.path.join(d, f)
            if os.path.abspath(p) == out_abs:
                continue
            rec, motivo = analizza(p, root, max_bytes)
            if rec is not None:
                cand.append(rec)
            else:
                saltati[motivo] = saltati.get(motivo, 0) + 1
    return cand, saltati


def ordina(cand):
    return sorted(cand, key=lambda r: (not r["forte"], -r["punteggio"], -len(r["topologie"]),
                                       r["numeri_letti"], r["percorso"]))


# ---------------------------------------------------------------------------
# Git pickaxe
# ---------------------------------------------------------------------------

def git_pickaxe(root, termini=("wedge", "slab")):
    if shutil.which("git") is None:
        raise Errore("--git richiesto ma 'git' non è nel PATH")
    r = subprocess.run(["git", "-C", root, "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return [{"tipo": "git", "radice": root, "esito": "non_repository"}]
    out = []
    for t in termini:
        r = subprocess.run(["git", "-C", root, "log", "--all", "--name-status", "--date=iso",
                            "--format=@@%H|%ad|%s", "-S", t],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise Errore(f"git log -S {t} fallito in {root}: {r.stderr.strip()[:200]}")
        commit = None
        for riga in r.stdout.splitlines():
            if riga.startswith("@@"):
                h, data, msg = (riga[2:].split("|", 2) + ["", ""])[:3]
                commit = {"tipo": "git", "radice": root, "termine": t, "commit": h, "data": data,
                          "messaggio": msg, "file": []}
                out.append(commit)
            elif riga.strip() and commit is not None:
                commit["file"].append(riga.strip())
    return out


# ---------------------------------------------------------------------------
# Comando cerca
# ---------------------------------------------------------------------------

def scrivi_report(out, righe):
    d = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(d):
        raise Errore(f"cartella del report inesistente: {d}")
    with open(out, "x", encoding="utf-8") as f:  # 'x': rifiuta se esiste
        for r in righe:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def cerca(roots, out, usa_git, max_mb, top_n, stampa=True):
    if out is None:
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = os.path.join("results", "paper2", f"ricerca_riga9_{stamp}.jsonl")
    if os.path.exists(out):
        raise Errore(f"report già esistente, non lo sovrascrivo: {out}")
    out_abs = os.path.abspath(out)
    max_bytes = int(max_mb * 1024 * 1024)
    tutti, saltati_tot, git_rec = [], {}, []
    for root in roots:
        c, s = cammina(root, max_bytes, out_abs)
        tutti += c
        for k, v in s.items():
            saltati_tot[k] = saltati_tot.get(k, 0) + v
        if usa_git:
            git_rec += git_pickaxe(root)
    tutti = ordina(tutti)
    testa = {"tipo": "intestazione", "strumento": "paper2_cerca_riga9", "versione": VERSIONE,
             "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
             "radici": roots, "git": usa_git, "max_mb": max_mb,
             "topologie": list(TOPOLOGIE), "campo": list(CAMPO), "criterio": list(CRITERIO),
             "impronte": [e for e, _, _ in IMPRONTE]}
    forti = [r for r in tutti if r["forte"]]
    coda = {"tipo": "riepilogo", "candidati": len(tutti), "candidati_forti": len(forti),
            "per_categoria": {c: sum(1 for r in tutti if r["categoria"] == c)
                              for c in ("codice", "dati", "documenti")},
            "saltati": saltati_tot, "commit_git": sum(1 for g in git_rec if "commit" in g)}
    scrivi_report(out, [testa] + tutti + git_rec + [coda])
    if stampa:
        for cat in ("codice", "dati", "documenti"):
            sel = [r for r in tutti if r["categoria"] == cat][:top_n]
            print(f"\n=== {cat}: {coda['per_categoria'][cat]} candidati, primi {len(sel)} ===")
            for r in sel:
                flag = "FORTE" if r["forte"] else "     "
                print(f"  [{flag}] {r['punteggio']:3d}  {r['percorso']}")
                print(f"          topologie={r['topologie']} campo={r['campo']} "
                      f"impronte_forti={r['impronte_forti']} numeri_letti={r['numeri_letti']}")
        if usa_git:
            print(f"\n=== git: {coda['commit_git']} commit toccano 'wedge' o 'slab' ===")
            for g in git_rec[:top_n]:
                if "commit" in g:
                    print(f"  {g['termine']:6s} {g['commit'][:10]} {g['data'][:10]}  {g['messaggio'][:60]}")
                    for fl in g["file"][:5]:
                        print(f"           {fl}")
                else:
                    print(f"  {g['radice']}: {g['esito']}")
        print(f"\nsaltati: {saltati_tot}")
        print(f"candidati forti: {len(forti)} (>= 3 topologie, oppure 2 topologie + un indizio di campo)")
        print(f"report: {out}")
    return out, tutti, coda


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

POSITIVO_PY = '''import numpy as np
# synthetic masks: slab, shell, tube, wedge, slab-with-holes
TOPOLOGIES = ["slab", "shell", "tube", "wedge", "slab_holes"]
def gaussian_random_field(n, slope): pass   # spectral slope -1.5 and -2.3, shared white noise
def wbar(mask, sigma): pass                  # in-mask kernel weight
# differential test: true contrast 36.9, measured 33.5
'''
DATI_JSON = {"test": "differential", "topologies": ["slab", "wedge", "tube"],
             "true_contrast": 0.369, "measured_contrast": 0.335, "diff_bias": -0.034,
             "diff_err": 0.028, "shape_exc": [0.019, 0.158], "n_configs": 58}
ESCA_PY = 'import subprocess\nsubprocess.run("dir", shell=True)\n# PowerShell wrapper, youtube link\n'
NOTEBOOK = {"cells": [{"cell_type": "code", "source": ["mask = make_wedge()\n", "t = 'tube'; s='slab'\n"],
                       "outputs": []}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}


def _albero(tmp):
    os.makedirs(os.path.join(tmp, "src"))
    os.makedirs(os.path.join(tmp, "results", "revision"))
    os.makedirs(os.path.join(tmp, "results", "paper2"))
    os.makedirs(os.path.join(tmp, ".git"))
    os.makedirs(os.path.join(tmp, "data"))
    open(os.path.join(tmp, "src", "synth_masks.py"), "w", encoding="utf-8").write(POSITIVO_PY)
    json.dump(DATI_JSON, open(os.path.join(tmp, "results", "revision", "synth.json"), "w", encoding="utf-8"))
    open(os.path.join(tmp, "src", "esca.py"), "w", encoding="utf-8").write(ESCA_PY)
    json.dump(NOTEBOOK, open(os.path.join(tmp, "src", "nb.ipynb"), "w", encoding="utf-8"))
    open(os.path.join(tmp, ".git", "leak.py"), "w", encoding="utf-8").write(POSITIVO_PY)
    open(os.path.join(tmp, "data", "bin.json"), "wb").write(b"\x00\x01slab shell tube wedge holes")
    open(os.path.join(tmp, "src", "latin.py"), "wb").write("# campo sintetico: pendenza \xe8 wedge slab\n".encode("latin-1"))
    open(os.path.join(tmp, "src", "grande.txt"), "w", encoding="utf-8").write("slab shell tube wedge " * 60000)
    open(os.path.join(tmp, "src", "neutro.py"), "w", encoding="utf-8").write("x = 1\n")
    open(os.path.join(tmp, "img.npy"), "wb").write(b"slab shell tube wedge")


def selftest():
    checks = []

    def chk(c, m):
        checks.append((bool(c), m))

    # unità: espressioni regolari
    chk(TOPOLOGIE["shell"].search("subprocess.run(x, shell=True)") is None, "shell=True non conta come topologia")
    chk(TOPOLOGIE["shell"].search("PowerShell") is None, "PowerShell non conta come topologia")
    chk(TOPOLOGIE["tube"].search("youtube") is None, "youtube non conta come topologia")
    chk(TOPOLOGIE["holes"].search("slab-with-holes") is not None, "slab-with-holes riconosciuto")
    chk(TOPOLOGIE["wedge"].search("m = make_wedge(n)") is not None, "make_wedge riconosciuto (separatore _)")
    chk(TOPOLOGIE["slab"].search("slab2 = ...") is not None, "slab2 riconosciuto (cifra dopo)")
    chk(CAMPO["slope_-1.5_e_-2.3"].search("slopes -1.5 and -2.3") is not None, "coppia di pendenze riconosciuta")
    imp, n = trova_impronte("a 0.36912 b 33.49 c 7")
    etich = {e for e, _ in imp}
    chk({"contrasto_vero_36.9", "contrasto_misurato_33.5"} <= etich and n == 3,
        "impronte a precisione piena: 0.36912 -> 36.9, 33.49 -> 33.5")
    imp2, _ = trova_impronte("0.3695")  # round(0.3695,3) = 0.369 o 0.37: controllo esplicito
    chk(("contrasto_vero_36.9" in {e for e, _ in imp2}) == (round(0.3695, 3) == 0.369),
        "arrotondamento coerente con round() di Python")

    tmp = tempfile.mkdtemp(prefix="cerca_riga9_selftest_")
    _so = sys.stdout
    try:
        _albero(tmp)
        out = os.path.join(tmp, "results", "paper2", "r.jsonl")
        mb = 0.5  # grande.txt supera 0.5 MB, gli altri no
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            _, cand, coda = cerca([tmp], out, False, mb, 5)
        finally:
            sys.stdout.close()
            sys.stdout = _so
        per = {c["percorso"].replace("\\", "/"): c for c in cand}
        chk(cand and cand[0]["percorso"].replace("\\", "/") == "src/synth_masks.py",
            "il codice positivo è primo in classifica")
        chk(per.get("src/synth_masks.py", {}).get("topologie") == sorted(TOPOLOGIE),
            "tutte e cinque le topologie trovate nel positivo")
        chk(per.get("src/synth_masks.py", {}).get("forte") is True, "positivo marcato FORTE")
        dj = per.get("results/revision/synth.json")
        attese_forti = sorted(e for e, f, _ in IMPRONTE if f)
        chk(dj is not None and sorted(dj["impronte_forti"]) == attese_forti,
            "JSON dei risultati: tutte le impronte forti trovate")
        chk(dj is not None and dj["categoria"] == "dati" and dj["forte"], "JSON: categoria dati, FORTE")
        nb = per.get("src/nb.ipynb")
        chk(nb is not None and set(nb["topologie"]) == {"slab", "tube", "wedge"},
            "notebook letto dalle celle")
        esca = per.get("src/esca.py")
        chk(esca is None or not esca["topologie"], "esca (shell=True, PowerShell, youtube): nessuna topologia")
        chk(not any(k.startswith(".git") for k in per), "cartella .git saltata")
        chk("data/bin.json" not in per and coda["saltati"].get("binario", 0) == 1, "file binario saltato e contato")
        chk("src/grande.txt" not in per and coda["saltati"].get("troppo_grande", 0) == 1,
            "file oltre --max-mb saltato e contato")
        chk("img.npy" not in per and coda["saltati"].get("estensione", 0) >= 1, "estensione non testuale saltata")
        la = per.get("src/latin.py")
        chk(la is not None and set(la["topologie"]) == {"slab", "wedge"}, "file latin-1 letto senza errori")
        chk("src/neutro.py" not in per, "file senza indizi non è un candidato")
        # report
        righe = [json.loads(x) for x in open(out, encoding="utf-8")]
        chk(righe[0]["tipo"] == "intestazione" and righe[-1]["tipo"] == "riepilogo", "report: intestazione e riepilogo")
        chk(sum(1 for r in righe if r["tipo"] == "candidato") == len(cand), "report: un record per candidato")
        chk(all(len(r["sha256"]) == 64 for r in righe if r["tipo"] == "candidato"), "report: sha256 per ogni candidato")
        # rifiuto di sovrascrittura
        prima = open(out, "rb").read()
        try:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                cerca([tmp], out, False, mb, 5)
            finally:
                sys.stdout.close()
                sys.stdout = _so
            chk(False, "report esistente: rifiuto")
        except Errore:
            chk(open(out, "rb").read() == prima, "report esistente: rifiuto, file intatto")
        # sola lettura: i file cercati non cambiano
        chk(open(os.path.join(tmp, "src", "synth_masks.py"), encoding="utf-8").read() == POSITIVO_PY,
            "sola lettura: il sorgente cercato è intatto")
        # radice inesistente
        try:
            cerca([os.path.join(tmp, "non_esiste")], os.path.join(tmp, "r2.jsonl"), False, mb, 5, stampa=False)
            chk(False, "radice inesistente: errore esplicito")
        except Errore:
            chk(not os.path.exists(os.path.join(tmp, "r2.jsonl")), "radice inesistente: errore esplicito, nessun report")
    finally:
        sys.stdout = _so
        shutil.rmtree(tmp, ignore_errors=True)

    n_ok = sum(ok for ok, _ in checks)
    for ok, m in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {m}")
    print(f"SELFTEST: {n_ok}/{len(checks)}")
    return 0 if n_ok == len(checks) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    c = sub.add_parser("cerca")
    c.add_argument("--root", action="append", required=True)
    c.add_argument("--out", default=None)
    c.add_argument("--git", action="store_true")
    c.add_argument("--max-mb", type=float, default=50.0)
    c.add_argument("--top", type=int, default=15)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    try:
        if a.cmd == "selftest":
            return selftest()
        cerca(a.root, a.out, a.git, a.max_mb, a.top)
        return 0
    except Errore as e:
        print(f"RIFIUTO: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
