# -*- coding: utf-8 -*-
"""
paper2_cerca_5_4_5_5.py -- due ricerche in SOLA LETTURA per chiudere le voci 5.4 e 5.5.

  --profilo clip        practice 6: che cosa fa il codice con le posizioni fuori dal cubo di
                        embedding, e se da qualche parte ne stampa o ne registra il CONTEGGIO.
  --profilo predizioni  voce 5.5: tutte le predizioni dichiarate prima di un run e il loro
                        riscontro, per verificare che siano sette e non di piu'.

Scrive un solo report JSONL nuovo (rifiuta di sovrascriverne uno esistente), di default in
results/paper2. Non modifica nessun file cercato.

COME LEGGERE L'ESITO. Lo script non emette un verdetto: ordina candidati da aprire a mano.
"FORTE" significa: almeno un indizio del gruppo A e almeno uno del gruppo B, cioe' il costrutto
giusto nel contesto giusto. Il gruppo C e' quello che serve davvero al profilo clip (il
conteggio); un file con A e B ma senza C dice come il codice tratta le posizioni fuori, non
quante ce ne sono.

Uso:
  python src\\paper2_cerca_5_4_5_5.py selftest
  python src\\paper2_cerca_5_4_5_5.py cerca --profilo clip --root D:\\projects\\cauchy
  python src\\paper2_cerca_5_4_5_5.py cerca --profilo predizioni --root D:\\projects\\cauchy

Opzioni: --out FILE, --max-mb N (default 50), --top N (default 15).
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

VERSIONE = "1.0"

# ---------------------------------------------------------------------------
# I due profili. A = costrutto, B = contesto, C = cio' che cerchiamo davvero.
# ---------------------------------------------------------------------------

CLIP_A = {  # come si gestisce una posizione o un indice fuori intervallo
    "np_clip": re.compile(r"\bnp\.clip\b|\.clip\s*\(", re.I),
    "minimum_maximum": re.compile(r"np\.(minimum|maximum)\s*\(", re.I),
    "mode_clip_wrap": re.compile(r"mode\s*=\s*['\"](clip|wrap|raise)['\"]", re.I),
    "modulo_griglia": re.compile(r"%\s*n(grid|_grid|side)?\b|np\.mod\s*\(", re.I),
    "filtro_indici": re.compile(r"(idx|ix|iy|iz|i[xyz]?)\s*(>=|<|>)\s*(n|ngrid|nside)\b", re.I),
    "clamp_esplicito": re.compile(r"\bclamp\b|\bclip_to\b|\bsatur", re.I),
}
CLIP_B = {  # contesto: voxelizzazione, embedding, costruzione della griglia
    "box_min_size": re.compile(r"box_min|box_size|boxsize", re.I),
    "cell_grid": re.compile(r"\bcell\b|\bngrid\b|\bnside\b|grid_size", re.I),
    "ravel_digitize": re.compile(r"ravel_multi_index|np\.digitize|histogramdd", re.I),
    "cic_voxel": re.compile(r"\bCIC\b|voxeli[sz]|\bvoxel\b", re.I),
    "embedding": re.compile(r"embedding|embed_cube|cubo di embedding", re.I),
    "floor_pos": re.compile(r"np\.floor\s*\(\s*\(?\s*(pos|xyz|coords)", re.I),
}
CLIP_C = {  # il conteggio: e' questo che manca alla practice 6
    "nome_contatore": re.compile(r"n_out\b|n_fuori\b|n_outside\b|n_clip|n_dropped|n_scartat", re.I),
    "somma_maschera": re.compile(r"\.sum\s*\(\s*\)\s*(#.*)?$|np\.count_nonzero", re.I | re.M),
    "parola_fuori": re.compile(r"\bfuori dal (cubo|box)\b|\boutside the (cube|box)\b|out[_\-\s]of[_\-\s]bounds", re.I),
    "stampa_conteggio": re.compile(r"(print|log|append_jsonl|report)\s*\([^)]{0,120}(fuori|outside|clip|dropped)", re.I),
}

PRED_A = {  # la predizione dichiarata
    "predizione": re.compile(r"predizion[ei]|predic[eo]|prevediamo|prediction|predicted", re.I),
    "atteso_dichiarato": re.compile(r"atteso prima|attesa dichiarata|dichiarat[ao] prima del run|"
                                    r"declared before|pre[_\-\s]?registrat", re.I),
    "soglia_dichiarata": re.compile(r"soglia dichiarata|soglie dichiarate|clausola di (successo|fallimento)", re.I),
}
PRED_B = {  # il riscontro
    "smentita": re.compile(r"smentit[ao]|falsificat[ao]|FALSIFICAT|SMENTIT", re.I),
    "confermata": re.compile(r"confermat[ao]|CONFERMAT|verificat[ao]", re.I),
    "ritirata": re.compile(r"ritirat[ao]|RITIRAT|caratterizzazione ritirata", re.I),
    "esito": re.compile(r"\besito\b|verdetto|VERDETTO", re.I),
}
PRED_C = {  # ancoraggio a un record, che rende la predizione citabile
    "record": re.compile(r"record\s+\d+", re.I),
    "regola": re.compile(r"\bregola\b|\bcancello\b|\bgate\b", re.I),
}

PROFILI = {
    "clip": {"A": CLIP_A, "B": CLIP_B, "C": CLIP_C,
             "forte": "almeno un costrutto (A) e un indizio di voxelizzazione (B)",
             "cercato": "C = il conteggio delle posizioni fuori dal cubo"},
    "predizioni": {"A": PRED_A, "B": PRED_B, "C": PRED_C,
                   "forte": "una predizione dichiarata (A) con il suo riscontro (B)",
                   "cercato": "C = l'ancoraggio a un record"},
}

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


def estratti(txt, prof, max_n=8):
    """Righe che contengono un indizio di A o di C, con numero di riga."""
    out = []
    rxs = list(prof["A"].values()) + list(prof["C"].values())
    for i, riga in enumerate(txt.splitlines(), 1):
        if any(rx.search(riga) for rx in rxs):
            out.append([i, riga.strip()[:200]])
            if len(out) >= max_n:
                break
    return out


def punteggio(a, b, c):
    return 3 * len(a) + 2 * len(b) + 2 * len(c)


def candidato_forte(a, b):
    return len(a) >= 1 and len(b) >= 1


def analizza(p, root, max_bytes, prof):
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
    a = trova_gruppo(txt, prof["A"])
    b = trova_gruppo(txt, prof["B"])
    c = trova_gruppo(txt, prof["C"])
    sc = punteggio(a, b, c)
    if sc == 0:
        return None, "nessun_indizio"
    st = os.stat(p)
    rec = {
        "tipo": "candidato",
        "categoria": cat,
        "percorso": os.path.relpath(p, root),
        "radice": root,
        "punteggio": sc,
        "forte": candidato_forte(a, b),
        "A": a, "B": b, "C": c,
        "ha_cercato": bool(c),
        "numeri_letti": len(NUM.findall(txt)),
        "byte": size,
        "mtime_utc": _dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha256_file(p),
        "estratti": estratti(txt, prof),
    }
    return rec, "candidato"


def cammina(root, max_bytes, out_abs, prof):
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
            rec, motivo = analizza(p, root, max_bytes, prof)
            if rec is not None:
                cand.append(rec)
            else:
                saltati[motivo] = saltati.get(motivo, 0) + 1
    return cand, saltati


def ordina(cand):
    """Prima i FORTI che contengono anche cio' che cerchiamo (C), poi gli altri forti."""
    return sorted(cand, key=lambda r: (not (r["forte"] and r["ha_cercato"]), not r["forte"],
                                       -r["punteggio"], -len(r["A"]), r["numeri_letti"], r["percorso"]))


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


def cerca(profilo, roots, out, max_mb, top_n, stampa=True):
    if profilo not in PROFILI:
        raise Errore(f"profilo sconosciuto: {profilo}")
    prof = PROFILI[profilo]
    if out is None:
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = os.path.join("results", "paper2", f"ricerca_{profilo}_{stamp}.jsonl")
    if os.path.exists(out):
        raise Errore(f"report gia' esistente, non lo sovrascrivo: {out}")
    out_abs = os.path.abspath(out)
    max_bytes = int(max_mb * 1024 * 1024)
    tutti, saltati_tot = [], {}
    for root in roots:
        c, sal = cammina(root, max_bytes, out_abs, prof)
        tutti += c
        for k, v in sal.items():
            saltati_tot[k] = saltati_tot.get(k, 0) + v
    tutti = ordina(tutti)
    forti = [r for r in tutti if r["forte"]]
    con_c = [r for r in forti if r["ha_cercato"]]
    testa = {"tipo": "intestazione", "strumento": "paper2_cerca_5_4_5_5", "versione": VERSIONE,
             "profilo": profilo, "forte": prof["forte"], "cercato": prof["cercato"],
             "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
             "radici": roots, "max_mb": max_mb,
             "A": list(prof["A"]), "B": list(prof["B"]), "C": list(prof["C"])}
    coda = {"tipo": "riepilogo", "candidati": len(tutti), "forti": len(forti),
            "forti_con_C": len(con_c),
            "per_categoria": {cat: sum(1 for r in tutti if r["categoria"] == cat)
                              for cat in ("codice", "dati", "documenti")},
            "saltati": saltati_tot}
    scrivi_report(out, [testa] + tutti + [coda])
    if stampa:
        print(f"profilo: {profilo}   FORTE = {prof['forte']}")
        print(f"cercato: {prof['cercato']}")
        for cat in ("codice", "dati", "documenti"):
            sel = [r for r in tutti if r["categoria"] == cat][:top_n]
            print(f"\n=== {cat}: {coda['per_categoria'][cat]} candidati, primi {len(sel)} ===")
            for r in sel:
                flag = "FORTE+C" if (r["forte"] and r["ha_cercato"]) else ("FORTE  " if r["forte"] else "       ")
                print(f"  [{flag}] {r['punteggio']:3d}  {r['percorso']}")
                print(f"          A={r['A']}")
                print(f"          B={r['B']}  C={r['C']}")
                for e in r["estratti"][:3]:
                    print(f"            {e[0]}: {e[1][:120]}")
        print(f"\nsaltati: {saltati_tot}")
        print(f"forti: {len(forti)}, di cui {len(con_c)} contengono anche C")
        print(f"report: {out}")
    return out, tutti, coda


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

CLIP_POS = '''import numpy as np
def voxelize(pos, box_min, box_size, ngrid):
    idx = np.floor((pos - box_min) / cell).astype(int)
    n_out = int(((idx < 0) | (idx >= ngrid)).any(axis=1).sum())
    print(f"posizioni fuori dal cubo: {n_out}")
    idx = np.clip(idx, 0, ngrid - 1)       # impilate sulle facce
    return np.ravel_multi_index(idx.T, (ngrid,) * 3, mode="clip"), n_out
'''
CLIP_SENZA_C = '''import numpy as np
def voxelize(pos, box_min, cell, ngrid):
    idx = np.clip(np.floor((pos - box_min) / cell).astype(int), 0, ngrid - 1)
    return np.ravel_multi_index(idx.T, (ngrid,) * 3)
'''
CLIP_ESCA = '''import matplotlib.pyplot as plt
rgb = np.clip(rgb, 0.0, 1.0)   # colori, nessuna griglia qui
plt.imshow(rgb)
'''
PRED_POS = '''# Record 30: predizione dichiarata prima del run.
# La potenza estrapolata prediceva |pari| = 32.4 / 75.4 / 15.1 alla terza ampiezza.
# VERDETTO: misurato 18.5 / 23.5 / 3.5 - predizione FALSIFICATA, non riparata.
'''
PRED_SENZA_C = '''Ci aspettiamo che la predizione regga; l'esito e' confermato dal run.
'''
PRED_ESCA = '''Il modello di previsione meteo non c'entra nulla con questo progetto.
'''


def _albero(tmp, profilo):
    os.makedirs(os.path.join(tmp, "src"))
    os.makedirs(os.path.join(tmp, "results", "paper2"))
    os.makedirs(os.path.join(tmp, ".git"))
    if profilo == "clip":
        open(os.path.join(tmp, "src", "pos.py"), "w", encoding="utf-8").write(CLIP_POS)
        open(os.path.join(tmp, "src", "senza_c.py"), "w", encoding="utf-8").write(CLIP_SENZA_C)
        open(os.path.join(tmp, "src", "esca.py"), "w", encoding="utf-8").write(CLIP_ESCA)
        open(os.path.join(tmp, ".git", "leak.py"), "w", encoding="utf-8").write(CLIP_POS)
    else:
        open(os.path.join(tmp, "src", "pos.md"), "w", encoding="utf-8").write(PRED_POS)
        open(os.path.join(tmp, "src", "senza_c.md"), "w", encoding="utf-8").write(PRED_SENZA_C)
        open(os.path.join(tmp, "src", "esca.md"), "w", encoding="utf-8").write(PRED_ESCA)
        open(os.path.join(tmp, ".git", "leak.md"), "w", encoding="utf-8").write(PRED_POS)
    open(os.path.join(tmp, "bin.json"), "wb").write(b"\x00\x01 np.clip predizione smentita")


def selftest():
    checks = []

    def chk(c, m):
        checks.append((bool(c), m))

    # unita': le esche non devono passare per FORTI
    chk(not trova_gruppo(CLIP_ESCA, CLIP_B), "clip: np.clip sui colori non ha contesto di voxelizzazione")
    chk(trova_gruppo(CLIP_POS, CLIP_C), "clip: il conteggio e' riconosciuto")
    chk(not trova_gruppo(CLIP_SENZA_C, CLIP_C), "clip: senza contatore, gruppo C vuoto")
    chk(not trova_gruppo(PRED_ESCA, PRED_A), "predizioni: 'previsione meteo' non e' una predizione dichiarata")
    chk("smentita" in trova_gruppo(PRED_POS, PRED_B), "predizioni: il riscontro e' riconosciuto")

    _so = sys.stdout
    for profilo in ("clip", "predizioni"):
        tmp = tempfile.mkdtemp(prefix=f"cerca_{profilo}_selftest_")
        try:
            _albero(tmp, profilo)
            out = os.path.join(tmp, "results", "paper2", "r.jsonl")
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                _, cand, coda = cerca(profilo, [tmp], out, 50.0, 5)
            finally:
                sys.stdout.close()
                sys.stdout = _so
            per = {c["percorso"].replace("\\", "/"): c for c in cand}
            primo = cand[0]["percorso"].replace("\\", "/") if cand else ""
            chk(primo.startswith("src/pos."), f"{profilo}: il positivo completo e' primo in classifica")
            chk(cand and cand[0]["forte"] and cand[0]["ha_cercato"], f"{profilo}: positivo FORTE+C")
            sc = [v for k, v in per.items() if "senza_c" in k]
            chk(sc and sc[0]["forte"] and not sc[0]["ha_cercato"],
                f"{profilo}: il file senza C e' FORTE ma senza cio' che cerchiamo")
            esca = [v for k, v in per.items() if "esca" in k]
            chk(not esca or not esca[0]["forte"], f"{profilo}: l'esca non e' FORTE")
            chk(not any(k.startswith(".git") for k in per), f"{profilo}: cartella .git saltata")
            chk(coda["saltati"].get("binario", 0) == 1, f"{profilo}: file binario saltato e contato")
            chk(cand[0]["estratti"] and all(len(e) == 2 for e in cand[0]["estratti"]),
                f"{profilo}: estratti con numero di riga")
            righe = [json.loads(x) for x in open(out, encoding="utf-8")]
            chk(righe[0]["tipo"] == "intestazione" and righe[0]["profilo"] == profilo,
                f"{profilo}: report con intestazione del profilo")
            chk(righe[-1]["tipo"] == "riepilogo" and righe[-1]["forti_con_C"] >= 1,
                f"{profilo}: riepilogo con il conteggio dei forti con C")
            chk(all(len(r["sha256"]) == 64 for r in righe if r["tipo"] == "candidato"),
                f"{profilo}: sha256 per ogni candidato")
            prima = open(out, "rb").read()
            try:
                cerca(profilo, [tmp], out, 50.0, 5, stampa=False)
                chk(False, f"{profilo}: report esistente -> rifiuto")
            except Errore:
                chk(open(out, "rb").read() == prima, f"{profilo}: report esistente -> rifiuto, file intatto")
            src_intatto = os.path.join(tmp, "src", "pos.py" if profilo == "clip" else "pos.md")
            atteso = CLIP_POS if profilo == "clip" else PRED_POS
            chk(open(src_intatto, encoding="utf-8").read() == atteso, f"{profilo}: sola lettura")
        finally:
            sys.stdout = _so
            shutil.rmtree(tmp, ignore_errors=True)

    try:
        cerca("inesistente", ["."], None, 50.0, 5, stampa=False)
        chk(False, "profilo sconosciuto -> errore")
    except Errore:
        chk(True, "profilo sconosciuto -> errore")

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
    c.add_argument("--profilo", required=True, choices=sorted(PROFILI))
    c.add_argument("--root", action="append", required=True)
    c.add_argument("--out", default=None)
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
        cerca(a.profilo, a.root, a.out, a.max_mb, a.top)
        return 0
    except Errore as e:
        print(f"RIFIUTO: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
