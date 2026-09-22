#!/usr/bin/env python3
"""
paper2_patch_budget_notaF.py  —  voce 6.2-vi (a): la colonna «fonte» del budget, riletta

Su papers/paper2/paper2_budget_5_1.md:
  C1-C8  otto celle, righe 1, 2, 3, 7, B0, 8: cartelle complete, n, rimandi alla nota F;
         riga 3 dallo stadio a due punti al blocco A a sei punti (decisione A, 18 set:
         cornice del record 40, pavimento misurato in entrambi gli emisferi)
  N      nota F inserita dopo la nota 10/11, prima del separatore e di «## 2. Colonna B»
  P7     §4, punto 7 accodato al punto 6, che deve chiudere il file

Garanzie come i patcher precedenti: ancora sha+byte; byte ed EOL preservati (EOL misto
= rifiuto); ogni riga trovata per prefisso esattamente una volta; ogni cella confrontata
col testo atteso prima della sostituzione; celle contate prima e dopo; righe delle
tabelle nuove contate prima di scriverle; seconda applicazione rifiutata.

Uso:
  python src\\paper2_patch_budget_notaF.py selftest | dry-run | apply | verify
"""

import argparse, hashlib, sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
TARGET = ROOT / "papers" / "paper2" / "paper2_budget_5_1.md"
SHA_ATTESO  = "df6f36e03c19c64f8a9d8bac7582a7738d316d2b5c733bfd8aa1f41afb4c2a60"
BYTE_ATTESI = 22287

# (prefisso della riga, celle attese, indice della cella, testo vecchio, testo nuovo)
CELLE = [
 ("| 1 | **AP**", 8, 4, "`results/paper2/fase3_analisi.jsonl` (3.4)",
  "`results/paper2/fase3_analisi.jsonl` (3.4), *n* = 200; nota F"),
 ("| 2 | sistematico", 8, 4, "`results/paper2/fase3_budget.jsonl` (3.3)",
  "`results/paper2/fase3_budget.jsonl` (3.3); nota F"),
 ("| 3 | (e) conteggio voxel", 8, 3, "pendenze su *D*: +0.0492 (NGC *k*=1), +0.0939 (SGC); (f) ±25",
  "pendenze su *D*: +0.0492 (NGC *k*=1), +0.0939 (SGC); (f) ±25 **a due punti** (3.1)"),
 ("| 3 | (e) conteggio voxel", 8, 4, "`fase3_budget.jsonl` (3.3)",
  "`results/paper2/fase3_budget.jsonl` (3.3); nota F"),
 ("| 3 | (e) conteggio voxel", 8, 6, "**sottrazione per punto**; pavimento SGC *k*=0 come intervallo, 11–32",
  "**sottrazione per punto**; pavimento **misurato** sul blocco A a sei punti (record 40): NGC 51.13 / 32.96, SGC 34.61 / 27.51 a *k*=0 / *k*=1"),
 ("| 7 | tiling sulla media", 8, 4, "`results/revision/rev1_r11_pilot.json`",
  "`results/revision/rev1_r11_pilot.json`; SEM ricavata dai due array del file (nota F)"),
 ("| B0 | dispersione di riferimento", 6, 4, "bersagli del cancello",
  "`results/paper1/paper1_remap_{NGC,SGC}_R5.json`, campo `mock_baseline_std`; i bersagli del cancello ne sono copie (nota F)"),
 ("| 8 | tiling sulla dispersione", 6, 4, "M26 §5.6; `rev1_r11_pilot.json`",
  "M26 §5.6; `results/revision/rev1_r11_pilot.json` (nota F)"),
]

ANCORA_1011 = "cammino del caricatore di DESI, cioè una seconda implementazione: si valuta in Fase 7."
DOPO_1011   = ["", "---", "", "## 2. Colonna B — la dispersione per realizzazione"]
NOTA = [
"**Nota F — la colonna «fonte», riletta (voce 6.2-vi, 18 settembre 2026).** Le righe che le note",
"4b, 5/6 e 10/11 non avevano toccato, rilette dai loro registri. I due JSONL sono append-only, con 9",
"e 20 record: i campi citati sono **identici in ogni record**, quindi la lettura per unione e",
"l'ultimo record danno lo stesso numero, e non c'è ambiguità da dichiarare.",
"",
"| riga | registro e campo | riprodotto | *n* |",
"|---|---|---|---:|",
"| 1 | `results/paper2/fase3_analisi.jsonl` (`c307fb30bda6…`), `levels.k1.DD_max_B5_B1` | −98.30 ± 11.249 / −91.13 ± 8.708 | 200 |",
"| 2 | `results/paper2/fase3_budget.jsonl` (`f5aec09b051c…`), `total_systematic_on_b` e `term_c` | 41.94 · 60.28 · 53.67 · 42.02 (NGC *k*=1, *k*=0; SGC *k*=1, *k*=0); carving 7.73 · 7.69 · 6.29 · 6.78 | — |",
"| 3 | stesso file: `levels.k1.slope_all`; `prop2_floor` e `blockA` | 0.049183 / 0.093865; pavimento: vedi sotto | — |",
"| 7 | `results/revision/rev1_r11_pilot.json` (`4d2f69c120d9…`), `mean_shift`; la SEM non è nel file | −12.790; SEM appaiata **20.143**, dai due array `beta1_max` sugli stessi 100 indici | 100 |",
"| 8 | M26 §5.6 (1.44, 70 %, 114.6 → 137.3, 313.0 → 322.0, −22.9 → −22.3) e lo stesso file, `sigma_ratio`, `sigma_ratio_ci95` | 0.9726, [0.8487, 1.1183] | 100 |",
"| B0 | `results/paper1/paper1_remap_{NGC,SGC}_R5.json`, `mock_baseline_std` | 312.98917 / 197.78738 | 2000 |",
"",
"**Riga 3: il budget citava lo stadio a due punti.** Il «(f) ±25» è il massimo dei quattro residui",
"della 3.1 e il «pavimento SGC 11–32» viene dalla 3.3, entrambi scritti con il blocco A a due punti:",
"il 32 è il `prop2_floor` SGC del record del 31 agosto (32.47), l'11 il calcolo con la pendenza del",
"blocco A che la 3.3 stessa dichiara circolare, e che non è mai stato in un registro. Dal 4",
"settembre il registro porta il blocco A a sei punti (record 40, checklist 3.6): pavimento **51.13 /",
"32.96** in NGC e **34.61 / 27.51** in SGC, a *k*=0 / *k*=1. Nella cornice del record 40 il",
"pavimento è ciò che resta sul blocco A, dove il segnale è nullo per teorema: è quindi misurato in",
"entrambi gli emisferi, e l'intervallo esce (decisione del 18 settembre). Il ±25 resta nella cella",
"con il suo stadio, perché è una misura a due punti e non una frase falsa; il registro a sei punti",
"porta (f) come spostamento previsto in voxel (`prop2_predicted_voxel`, 0.006–0.014), non in",
"generatori.",
"",
"**Un'osservazione che la prova di segno della 3.3 impone di scrivere.** La 3.3 chiamava",
"«misurato» il pavimento di NGC perché la pendenza di controllo del blocco A concordava in segno con",
"quella globale, e intervallo quello di SGC perché no. Nel registro a sei punti",
"(`slope_blockA_sign_check`) anche NGC ha segno opposto: −0.0434 contro +0.0545 a *k*=0, −0.0078",
"contro +0.0492 a *k*=1, dove a due punti erano +0.0335 e +0.0349; SGC resta opposto, −0.1955 e",
"−0.0925. Il campo non porta un errore, e a *k*=1 il valore di NGC è prossimo a zero. Nella cornice",
"del record 40 questo non cambia lo statuto del pavimento, ma dice che cosa può contenere: un termine",
"(e) che non si trasferisce al blocco A, ora in entrambi gli emisferi. Nel ledger non se ne parla:",
"`sign_check`, «pendenza di controllo», *slope* accanto a *block A* danno zero occorrenze, e le nove",
"di *opposite sign* stanno nei record 22, 37, 38 e 63, dove la ricerca non trova *slope* accanto a",
"*block A*.",
"",
"**Righe 7 e B0.** La SEM della riga 7 non è scritta nel file: si ricava dai due array, e vale",
"quella del budget. La B0 citava un ruolo, «bersagli del cancello»: il produttore è il run v1 a R5,",
"e il cancello ne tiene una copia. Righe 3 e 8 citavano il file senza cartella; il nome è unico sul",
"disco, quindi la citazione non era ambigua, ma ora porta il percorso.",
"",
]

ULTIMO_P6 = "   metri."
PUNTO_7 = [
"7. **Colonna «fonte» — riletta il 18 settembre (voce 6.2-vi, nota F).** Righe 1, 2, 3, 7, 8 e B0",
"   riprodotte dai loro registri; la riga 3 portava lo stadio a due punti ed è riscritta a sei",
"   (decisione A, cornice del record 40); la prova di segno della 3.3, rifatta a sei punti, è",
"   registrata come osservazione.",
]

# ── byte ed EOL ────────────────────────────────────────────────────────────
def leggi(raw: bytes):
    t = raw.decode("utf-8")
    n_crlf, n_lf = t.count("\r\n"), t.count("\n")
    if n_crlf == n_lf and n_crlf > 0: eol = "\r\n"
    elif n_crlf == 0 and "\r" not in t: eol = "\n"
    else: raise SystemExit(f"STOP: fine riga miste (CRLF {n_crlf}, LF {n_lf}); nessuna modifica")
    return t.split(eol), eol

def unico(righe, pred, nome):
    hit = [i for i, r in enumerate(righe) if pred(r)]
    if len(hit) != 1:
        raise SystemExit(f"STOP: {nome} trovata {len(hit)} volte (attesa 1); nessuna modifica")
    return hit[0]

def trasforma(raw: bytes):
    righe, eol = leggi(raw)
    for pref, n_celle, idx, old, new in CELLE:
        i = unico(righe, lambda r, p=pref: r.startswith(p), f"riga «{pref}»")
        c = righe[i].split("|")
        if len(c) - 2 != n_celle:
            raise SystemExit(f"STOP: «{pref}» ha {len(c)-2} celle (attese {n_celle})")
        if c[idx].strip() != old:
            raise SystemExit(f"STOP: «{pref}», cella {idx} diversa dall'attesa: {c[idx].strip()!r}")
        c[idx] = " " + new + " "
        righe[i] = "|".join(c)
        assert len(righe[i].split("|")) == len(c)
    if any(r.startswith("**Nota F —") for r in righe):
        raise SystemExit("STOP: la nota F esiste già; nessuna modifica")
    j = unico(righe, lambda r: r == ANCORA_1011, "fine della nota 10/11")
    if righe[j + 1:j + 1 + len(DOPO_1011)] != DOPO_1011:
        raise SystemExit("STOP: dopo la nota 10/11 non ci sono separatore e sezione 2")
    righe[j + 2:j + 2] = NOTA
    k = unico(righe, lambda r: r == ULTIMO_P6, "ultima riga del punto 6")
    if any(r.strip() for r in righe[k + 1:]):
        raise SystemExit("STOP: dopo il punto 6 c'è altro testo; nessuna modifica")
    righe[k + 1:k + 1] = PUNTO_7
    return eol.join(righe).encode("utf-8"), eol

def controlla(righe):
    err = []
    for pref, n_celle, idx, old, new in CELLE:
        rr = [r for r in righe if r.startswith(pref)]
        if len(rr) != 1: err.append(f"«{pref}» presente {len(rr)} volte"); continue
        c = rr[0].split("|")
        if len(c) - 2 != n_celle: err.append(f"«{pref}»: {len(c)-2} celle")
        if c[idx].strip() != new: err.append(f"«{pref}»: cella {idx} non aggiornata")
    f   = [i for i, r in enumerate(righe) if r.startswith("**Nota F —")]
    n11 = [i for i, r in enumerate(righe) if r.startswith("**Nota 10/11")]
    s2  = [i for i, r in enumerate(righe) if r.startswith("## 2. Colonna B")]
    if len(f) != 1: err.append(f"nota F presente {len(f)} volte")
    elif not (n11 and s2 and n11[0] < f[0] < s2[0]): err.append("nota F fuori posizione")
    p6 = [i for i, r in enumerate(righe) if r.startswith("6. **Righe 10 e 11")]
    p7 = [i for i, r in enumerate(righe) if r.startswith("7. **Colonna «fonte»")]
    if len(p7) != 1: err.append(f"punto 7 presente {len(p7)} volte")
    elif not (p6 and p6[0] < p7[0]): err.append("punto 7 non segue il punto 6")
    if any("11–32" in r for r in righe if r.startswith("| 3 |")):
        err.append("la riga 3 porta ancora l'intervallo 11–32")
    return err

# ── selftest ───────────────────────────────────────────────────────────────
def riga(pref, n, celle_extra):
    # costruisce una riga col prefisso e n celle totali
    base = [x.strip() for x in pref.strip("| ").split(" | ")]
    cs = (base + celle_extra + ["—"] * n)[:n]
    return "| " + " | ".join(cs) + " |"

def fixture():
    out = ["# titolo", ""]
    for pref, n, idx, old, new in CELLE:
        if any(r.startswith(pref) for r in out): continue
        celle = {i: "x" for i in range(1, n + 1)}
        for p2, n2, i2, o2, _ in CELLE:
            if p2 == pref: celle[i2] = o2
        base = [x.strip() for x in pref.strip("| ").split(" | ")]
        cs = [base[0], base[1] if len(base) > 1 else "t"] + [celle[i] for i in range(3, n + 1)]
        out.append("| " + " | ".join(cs) + " |")
    out += ["", "**Nota 10/11 — x.**", ANCORA_1011] + DOPO_1011 + ["", "## 4. Da fare", "",
            "6. **Righe 10 e 11 — y.**", ULTIMO_P6, ""]
    return out

def selftest():
    ok = 0
    for eol in ("\n", "\r\n"):
        out, e = trasforma(eol.join(fixture()).encode("utf-8"))
        righe, e2 = leggi(out)
        assert e == e2 == eol and not controlla(righe), controlla(righe)
        ok += 1
    tab = [r for r in NOTA if r.startswith("|")]
    assert tab and all(len(r.split("|")) - 2 == 4 for r in tab), [len(r.split("|")) - 2 for r in tab]; ok += 1
    out, _ = trasforma("\n".join(fixture()).encode("utf-8"))
    try: trasforma(out); raise AssertionError("seconda applicazione accettata")
    except SystemExit: ok += 1
    f = fixture(); f = [r.replace("11–32", "11-32") for r in f]
    try: trasforma("\n".join(f).encode("utf-8")); raise AssertionError("cella diversa accettata")
    except SystemExit: ok += 1
    f = fixture(); f.insert(3, f[2])
    try: trasforma("\n".join(f).encode("utf-8")); raise AssertionError("riga duplicata accettata")
    except SystemExit: ok += 1
    f = fixture(); f.insert(-1, "8. altro")
    try: trasforma("\n".join(f).encode("utf-8")); raise AssertionError("coda inattesa accettata")
    except SystemExit: ok += 1
    assert all("|" not in new for *_, new in CELLE); ok += 1
    assert not any("11–32" in new for *_, new in CELLE); ok += 1
    print(f"selftest: {ok}/9 OK")

def ancora(p):
    raw = p.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
    if sha != SHA_ATTESO or len(raw) != BYTE_ATTESI:
        raise SystemExit(f"STOP: ancora attesa {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, "
                         f"trovata {sha[:12]}… {len(raw)} byte; nessuna modifica")
    return raw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--file", type=Path, default=TARGET)
    a = ap.parse_args()
    if a.cmd == "selftest": return selftest()
    if a.cmd == "verify":
        raw = a.file.read_bytes(); righe, eol = leggi(raw); err = controlla(righe)
        print(f"verify {'OK' if not err else 'ANOMALIA'}: sha {hashlib.sha256(raw).hexdigest()}  {len(raw)} byte, EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'} uniforme")
        for e in err: print("  -", e)
        return sys.exit(1 if err else 0)
    raw = ancora(a.file); out, eol = trasforma(raw)
    if a.cmd == "dry-run":
        print(f"dry-run OK: ancora {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'}")
        print(f"  dopo: {len(out)} byte (Δ {len(out)-len(raw):+d}), sha {hashlib.sha256(out).hexdigest()[:12]}…; nessuna modifica scritta")
    else:
        a.file.write_bytes(out)
        print(f"[apply] scritto: sha {hashlib.sha256(out).hexdigest()}  {len(out)} byte")

if __name__ == "__main__":
    main()
