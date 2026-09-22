#!/usr/bin/env python3
"""
paper2_patch_budget_nota10_11.py  —  voce 6.2-v: righe 10 e 11 del budget rilette dalle fonti

Quattro interventi su papers/paper2/paper2_budget_5_1.md, tutti posizionali:
  E1  riga 10, colonna «fonte»: rimando alla nota 10/11 (numero di celle invariato)
  E2  riga 11, colonna «fonte»: reference congelato, run non registrato (celle invariate)
  E3  nota 10/11 inserita dopo la nota 6b, prima del separatore e di «## 2. Colonna B»
  E4  §4, punto 6 accodato al punto 5, che deve essere l'ultimo testo del file

Garanzie: ancora per sha e byte; lettura e scrittura in byte con EOL misurato e
preservato (EOL misto = rifiuto); ogni ancora trovata esattamente una volta; le celle
delle righe 10 e 11 contate prima e dopo; le righe delle tabelle nuove contate prima
di scriverle; seconda applicazione rifiutata.

Uso:
  python src\\paper2_patch_budget_nota10_11.py selftest
  python src\\paper2_patch_budget_nota10_11.py dry-run
  python src\\paper2_patch_budget_nota10_11.py apply
  python src\\paper2_patch_budget_nota10_11.py verify
"""

import argparse, hashlib, sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
TARGET = ROOT / "papers" / "paper2" / "paper2_budget_5_1.md"

SHA_ATTESO  = "a5b98ec22294d97aeb51adeb67c7b9f664afda5ae66cc3f16b9b965356f1c0ca"
BYTE_ATTESI = 19213

# ── E1 / E2: celle «fonte» delle righe 10 e 11 ────────────────────────────
R10_PREFISSO = "| 10 | banda del deficit |"
R10_OLD = "17.3: SGC *k*=3 (4.3a, *n* = 2000); 31.2 ± 0.08: SGC P25 (P1-8, 200 mock)"
R10_NEW = R10_OLD + "; registri nella nota 10/11"
R11_PREFISSO = "| 11 | DESI ricostruito a pesi unitari |"
R11_OLD = "M26 §5.3 e Tab. 1"
R11_NEW = "M26 §5.3 e Tab. 1; reference congelato, run non registrato (nota 10/11)"
CELLA_FONTE = 4          # indice nello split per '|': ['', '#', termine, valore, fonte, ...]
CELLE_RIGA = 8

# ── E3: la nota ───────────────────────────────────────────────────────────
ANCORA_6B = "parametro dichiarato: va letto con quel parametro accanto."
DOPO_6B   = ["", "---", "", "## 2. Colonna B — la dispersione per realizzazione"]
NOTA = [
"**Nota 10/11 — le righe 10 e 11, rilette dalle loro fonti (voce 6.2-v, 18 settembre 2026).** La",
"riga 10 aveva per fonte due *voci*, la 11 un manoscritto. Ora ogni numero ha il suo registro, o",
"la dichiarazione misurata che non ce l'ha.",
"",
"| numero | registro | ancora | *n* | riprodotto |",
"|---|---|---|---:|---|",
"| 17.3 % | `results/paper2/ensemble_v2_SGC.jsonl`, ramo `unit.N_H1_k3`: ⟨*N*⟩ = 8 163.485, SEM 2.767; `results/paper2/desi_ladder_SGC.json`, `N_H1_k3` = 6 751 | `11f2d535ea24…` · `4d28e6212899…` | 2000 | 1 − 6 751 / 8 163.485 = **17.3025 %** ± 0.028 |",
"| 31.2 ± 0.08 % | `results/paper2/copertura_v1_SGC.json`, taglio `field_r > P25`: `deficit` 0.312245, `sem_deficit` 0.00082 | `dcf22ac11977…` | 200 | **31.2245 %** ± 0.082, rango 1/201 |",
"| +309 | `src/paper2_v1_reference.json`, `paired_corrections.unit_weights_on_data` = delta 309, da 28 256 a 28 565, **nessun campo di provenienza** | — | — | solo la partenza: `desi_ladder_NGC.json`, `N_H1_k0` = 28 256 |",
"",
"**Riga 10.** Riscontro prima della lettura: lo stesso ramo dà a *k*=1 ⟨*N*⟩ = 16 494.586, il valore",
"della nota 1b, quindi il campo letto è la linea base e non il ramo FKP del primo livello. E un",
"riscontro fra registri scritti a due giorni di distanza: il *N*_DESI a footprint pieno di",
"`copertura_v1_SGC.json` è 15 122, lo stesso `N_H1_k0` di `desi_ladder_SGC.json`. I due estremi",
"vengono da ensemble e *n* diversi — il ramo unitario di v2 su 2000, v1 su 200 — il che una banda di",
"scelte ammette (R1: nessun denominatore), ma va detto accanto alla banda; i ± sono SEM della media",
"d'ensemble e restano informativi.",
"",
"**Riga 11: la fonte è bibliografica, il run non è registrato.** M26 §5.3 dice che ricostruire il",
"riferimento DESI a pesi unitari sposta *β*₁ di +309 (∼1 %), e la sua Table 1 porta 28 256 → 28 565",
"(letti sul testo accettato il 9 settembre). Il reference congelato li cita con tre numeri e nessuna",
"provenienza. Due metri, entrambi muti: sul disco 28 565 compare in quattro sorgenti `.tex` di M26 e",
"del preprint JCAP e nel reference, in nessun registro; nella storia, `git grep -w` sui cinque commit",
"che il pickaxe segnala e sui loro genitori trova solo il reference — e in `8a2e140` la stringa sta",
"soltanto dentro token più lunghi, un hash e tre decimali. Il **27 947** di",
"`results/paper1/n2_report_NGC.json` vale esattamente 28 256 − 309 ma è un'altra grandezza,",
"`desi.cnt_abs[1]`, il conteggio sopra la seconda soglia di persistenza, e va nel verso opposto:",
"coincidenza di ampiezza, non una fonte. A differenza delle righe 5 e 6 la fonte qui è un articolo",
"accettato, che il Paper 2 può citare come tale. Il ricalcolo a pesi unitari chiederebbe un secondo",
"cammino del caricatore di DESI, cioè una seconda implementazione: si valuta in Fase 7.",
"",
]

# ── E4: §4, punto 6 ───────────────────────────────────────────────────────
ULTIMO_P5 = "   limite come primario, misura accanto (note S e 6b)."
PUNTO_6 = [
"6. **Righe 10 e 11 — chiuse il 18 settembre (voce 6.2-v, nota 10/11).** La 10 è tracciata ai suoi",
"   due registri, con il suo *n*; la 11 alla sua fonte bibliografica, con il run non registrato su due",
"   metri.",
]

# ── lettura/scrittura in byte con EOL preservato ──────────────────────────
def leggi(raw: bytes):
    t = raw.decode("utf-8")
    n_crlf, n_lf = t.count("\r\n"), t.count("\n")
    if n_crlf == n_lf and n_crlf > 0:
        eol = "\r\n"
    elif n_crlf == 0 and "\r" not in t:
        eol = "\n"
    else:
        raise SystemExit(f"STOP: fine riga miste (CRLF {n_crlf}, LF {n_lf}); nessuna modifica")
    return t.split(eol), eol

def unico(righe, pred, nome):
    hit = [i for i, r in enumerate(righe) if pred(r)]
    if len(hit) != 1:
        raise SystemExit(f"STOP: {nome} trovata {len(hit)} volte (attesa 1); nessuna modifica")
    return hit[0]

def celle(riga):
    return riga.split("|")

def sostituisci_fonte(riga, old, new, nome):
    c = celle(riga)
    if len(c) - 2 != CELLE_RIGA:
        raise SystemExit(f"STOP: {nome} ha {len(c)-2} celle (attese {CELLE_RIGA})")
    if c[CELLA_FONTE].strip() != old:
        raise SystemExit(f"STOP: {nome}, cella «fonte» diversa dall'attesa: {c[CELLA_FONTE].strip()!r}")
    c[CELLA_FONTE] = " " + new + " "
    nuova = "|".join(c)
    assert len(celle(nuova)) == len(c), "numero di celle cambiato"
    return nuova

def trasforma(raw: bytes):
    righe, eol = leggi(raw)
    # E1, E2
    i10 = unico(righe, lambda r: r.startswith(R10_PREFISSO), "riga 10")
    i11 = unico(righe, lambda r: r.startswith(R11_PREFISSO), "riga 11")
    righe[i10] = sostituisci_fonte(righe[i10], R10_OLD, R10_NEW, "riga 10")
    righe[i11] = sostituisci_fonte(righe[i11], R11_OLD, R11_NEW, "riga 11")
    # E3: la nota va dopo la 6b, seguita dal separatore e dalla sezione 2
    i6b = unico(righe, lambda r: r == ANCORA_6B, "fine della nota 6b")
    if righe[i6b + 1:i6b + 1 + len(DOPO_6B)] != DOPO_6B:
        raise SystemExit("STOP: dopo la nota 6b non ci sono separatore e sezione 2; nessuna modifica")
    if any(r.startswith("**Nota 10/11") for r in righe):
        raise SystemExit("STOP: la nota 10/11 esiste già; nessuna modifica")
    righe[i6b + 2:i6b + 2] = NOTA
    # E4: il punto 5 deve chiudere il file
    ip5 = unico(righe, lambda r: r == ULTIMO_P5, "ultima riga del punto 5")
    if any(r.strip() for r in righe[ip5 + 1:]):
        raise SystemExit("STOP: dopo il punto 5 c'è altro testo; nessuna modifica")
    righe[ip5 + 1:ip5 + 1] = PUNTO_6
    return eol.join(righe).encode("utf-8"), eol

# ── controlli strutturali, usati da selftest e verify ─────────────────────
def controlla(righe):
    err = []
    n_nota = [i for i, r in enumerate(righe) if r.startswith("**Nota 10/11")]
    n_6b   = [i for i, r in enumerate(righe) if r.startswith("**Nota 6b")]
    n_sez2 = [i for i, r in enumerate(righe) if r.startswith("## 2. Colonna B")]
    if len(n_nota) != 1: err.append(f"nota 10/11 presente {len(n_nota)} volte")
    elif not (n_6b and n_sez2 and n_6b[0] < n_nota[0] < n_sez2[0]):
        err.append("nota 10/11 fuori posizione (deve stare fra la 6b e la sezione 2)")
    for pref, new, nome in ((R10_PREFISSO, R10_NEW, "riga 10"), (R11_PREFISSO, R11_NEW, "riga 11")):
        rr = [r for r in righe if r.startswith(pref)]
        if len(rr) != 1: err.append(f"{nome} presente {len(rr)} volte"); continue
        c = celle(rr[0])
        if len(c) - 2 != CELLE_RIGA: err.append(f"{nome}: {len(c)-2} celle")
        if c[CELLA_FONTE].strip() != new: err.append(f"{nome}: cella «fonte» non aggiornata")
    p6 = [i for i, r in enumerate(righe) if r.startswith("6. **Righe 10 e 11")]
    p5 = [i for i, r in enumerate(righe) if r.startswith("5. **Nota C")]
    if len(p6) != 1: err.append(f"punto 6 presente {len(p6)} volte")
    elif not (p5 and p5[0] < p6[0]): err.append("punto 6 non segue il punto 5")
    return err

# ── selftest ──────────────────────────────────────────────────────────────
def fixture():
    r10 = f"{R10_PREFISSO} **17.3 – 31.2 %** | {R10_OLD} | **nessuno** | **banda** | — | — |"
    r11 = f"{R11_PREFISSO} +309 su *N*_DESI | {R11_OLD} | **nessuno** | **variante** | — | **−4.303** |"
    return ["# titolo", "", "| # | a | b | c | d | e | f | g |", r10, r11, "",
            "**Nota 6b — x.** testo", ANCORA_6B] + DOPO_6B + ["", "testo", "",
            "## 4. Da fare", "", "5. **Nota C — y.** z", ULTIMO_P5, ""]

def selftest():
    ok = 0
    # 1-2: LF e CRLF preservati, struttura corretta
    for eol in ("\n", "\r\n"):
        out, e = trasforma(eol.join(fixture()).encode("utf-8"))
        righe, e2 = leggi(out)
        assert e == e2 == eol and not controlla(righe), controlla(righe)
        ok += 1
    # 3: celle delle tabelle nuove contate prima di scriverle (5 per riga)
    tab = [r for r in NOTA if r.startswith("|")]
    assert tab and all(len(celle(r)) - 2 == 5 for r in tab), [len(celle(r)) - 2 for r in tab]
    ok += 1
    # 4: seconda applicazione rifiutata
    out, _ = trasforma("\n".join(fixture()).encode("utf-8"))
    try: trasforma(out); raise AssertionError("seconda applicazione accettata")
    except SystemExit: ok += 1
    # 5: riga 10 duplicata rifiutata
    f = fixture(); f.insert(4, f[3])
    try: trasforma("\n".join(f).encode("utf-8")); raise AssertionError("riga duplicata accettata")
    except SystemExit: ok += 1
    # 6: cella «fonte» diversa rifiutata
    f = fixture(); f[3] = f[3].replace("200 mock", "2000 mock")
    try: trasforma("\n".join(f).encode("utf-8")); raise AssertionError("cella diversa accettata")
    except SystemExit: ok += 1
    # 7: testo dopo il punto 5 rifiutato
    f = fixture(); f.insert(-1, "6. altro")
    try: trasforma("\n".join(f).encode("utf-8")); raise AssertionError("coda inattesa accettata")
    except SystemExit: ok += 1
    # 8: EOL misto rifiutato
    f = fixture()
    try: trasforma(("\r\n".join(f[:5]) + "\n" + "\r\n".join(f[5:])).encode("utf-8")); raise AssertionError("EOL misto accettato")
    except SystemExit: ok += 1
    # 9: nessun carattere '|' dentro le celle della nota oltre ai separatori
    assert all(r.count("|") == 6 for r in tab); ok += 1
    print(f"selftest: {ok}/9 OK")

# ── comandi ───────────────────────────────────────────────────────────────
def ancora(p):
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SHA_ATTESO or len(raw) != BYTE_ATTESI:
        raise SystemExit(f"STOP: ancora attesa {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, "
                         f"trovata {sha[:12]}… {len(raw)} byte; nessuna modifica")
    return raw

def dry_run(p):
    raw = ancora(p)
    out, eol = trasforma(raw)
    print(f"dry-run OK: ancora {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'}")
    print(f"  dopo: {len(out)} byte (Δ {len(out)-len(raw):+d}), sha {hashlib.sha256(out).hexdigest()[:12]}…; nessuna modifica scritta")

def apply(p):
    raw = ancora(p)
    out, _ = trasforma(raw)
    p.write_bytes(out)
    print(f"[apply] scritto: sha {hashlib.sha256(out).hexdigest()}  {len(out)} byte")

def verify(p):
    raw = p.read_bytes()
    righe, eol = leggi(raw)
    err = controlla(righe)
    print(f"verify {'OK' if not err else 'ANOMALIA'}: sha {hashlib.sha256(raw).hexdigest()}  {len(raw)} byte, "
          f"EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'} uniforme")
    for e in err: print("  -", e)
    if err: sys.exit(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--file", type=Path, default=TARGET)
    a = ap.parse_args()
    if a.cmd == "selftest": selftest()
    else: {"dry-run": dry_run, "apply": apply, "verify": verify}[a.cmd](a.file)
