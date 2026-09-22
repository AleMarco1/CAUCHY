#!/usr/bin/env python3
"""
paper2_patch_budget_doppione.py  —  voce 6.2-iv: chiude il doppione del §4 del budget

Il §4, punto 4, di papers/paper2/paper2_budget_5_1.md chiede alla voce 5.1 della
checklist di togliere «denominatori conservativi ovunque» e di portare la banda a
17.3–31.2 %. La voce 5.1 lo porta già (checklist rev. 3.31, 6.2-iv «GIÀ SODDISFATTA»).
Il punto non si cancella: si CHIUDE, come i punti 2 e 3, e la numerazione resta stabile
perché consegna e checklist citano «§4 punto 4».

Garanzie:
  - ancora: sha256 e byte del file prima di toccarlo
  - le due righe del punto 4 si cercano per POSIZIONE (due righe consecutive),
    devono esistere esattamente una volta; il confronto normalizza solo spazi
    non separabili e trattini, la sostituzione riscrive le righe originali
  - fine riga preservata: il file si legge e si scrive in BYTE; EOL misto = rifiuto
  - nessun altro byte cambia: verificato prima della scrittura

Uso:
  python src\\paper2_patch_budget_doppione.py selftest
  python src\\paper2_patch_budget_doppione.py dry-run
  python src\\paper2_patch_budget_doppione.py apply
  python src\\paper2_patch_budget_doppione.py verify
"""

import argparse, hashlib, sys, tempfile
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
TARGET = ROOT / "papers" / "paper2" / "paper2_budget_5_1.md"

SHA_ATTESO  = "47503c980ef532d8915689809acd074cd53fd3166b2f2060f1fe3e46adc4a88b"
BYTE_ATTESI = 19108

OLD = [
    "4. **Voce 5.1 della checklist** (rev. 3.21): togliere «denominatori conservativi ovunque» e",
    "   rimandare a questo documento. Aggiornare anche la banda, da «17–29 %» a 17.3–31.2 %.",
]
NEW = [
    "4. **Voce 5.1 della checklist — già soddisfatta, chiuso il 18 settembre (voce 6.2-iv).** La",
    "   richiesta di togliere «denominatori conservativi ovunque» e di portare la banda a 17.3–31.2 %",
    "   era un doppione: la voce 5.1 la porta già, come registra la checklist rev. 3.31 alla 6.2-iv.",
]

# ── normalizzazione per il SOLO confronto ─────────────────────────────────
_TR = str.maketrans({"\u00a0": " ", "\u202f": " ", "\u2009": " ",
                     "\u2013": "-", "\u2014": "-", "\u2212": "-"})
def norm(s: str) -> str:
    return s.translate(_TR).rstrip()

# ── lettura/scrittura in byte con EOL preservato ──────────────────────────
def leggi(raw: bytes):
    testo = raw.decode("utf-8")
    n_crlf, n_lf = testo.count("\r\n"), testo.count("\n")
    if n_crlf == n_lf and n_crlf > 0:
        eol = "\r\n"
    elif n_crlf == 0 and "\r" not in testo:
        eol = "\n"
    else:
        raise SystemExit(f"STOP: fine riga miste (CRLF {n_crlf}, LF {n_lf}); nessuna modifica")
    return testo.split(eol), eol

def trova(righe):
    """Indici i tali che righe[i], righe[i+1] coincidono (normalizzate) con OLD."""
    a, b = norm(OLD[0]), norm(OLD[1])
    return [i for i in range(len(righe) - 1) if norm(righe[i]) == a and norm(righe[i + 1]) == b]

def trova_new(righe):
    n = [norm(x) for x in NEW]
    return [i for i in range(len(righe) - 2) if [norm(x) for x in righe[i:i + 3]] == n]

def trasforma(raw: bytes):
    righe, eol = leggi(raw)
    hit = trova(righe)
    if len(hit) != 1:
        raise SystemExit(f"STOP: il punto 4 compare {len(hit)} volte (attesa 1); nessuna modifica")
    i = hit[0]
    nuove = righe[:i] + NEW + righe[i + 2:]
    # nessun'altra riga cambia
    assert nuove[:i] == righe[:i] and nuove[i + 3:] == righe[i + 2:], "righe fuori finestra alterate"
    out = eol.join(nuove).encode("utf-8")
    return out, i, eol

# ── selftest ──────────────────────────────────────────────────────────────
def selftest():
    ok = 0
    base = ["# titolo", "", "1. punto uno", "2. punto due", "3. punto tre"] + OLD + ["5. punto cinque", ""]
    # 1-2: CRLF e LF preservati, sostituzione esatta
    for eol in ("\r\n", "\n"):
        raw = eol.join(base).encode("utf-8")
        out, i, e = trasforma(raw)
        assert e == eol and i == 5
        exp = eol.join(base[:5] + NEW + base[7:]).encode("utf-8")
        assert out == exp, f"uscita diversa con EOL {eol!r}"
        ok += 1
    # 3: spazio non separabile prima di % e trattino ASCII: trovato lo stesso
    var = [OLD[0], OLD[1].replace(" %", "\u00a0%").replace("–", "-")]
    raw = "\r\n".join(base[:5] + var + base[7:]).encode("utf-8")
    out, i, _ = trasforma(raw); assert i == 5; ok += 1
    # 4: EOL misto rifiutato
    raw = ("\r\n".join(base[:4]) + "\n" + "\r\n".join(base[4:])).encode("utf-8")
    try: trasforma(raw); raise AssertionError("EOL misto accettato")
    except SystemExit: ok += 1
    # 5: zero occorrenze rifiutate
    raw = "\n".join(base[:5] + base[7:]).encode("utf-8")
    try: trasforma(raw); raise AssertionError("zero occorrenze accettate")
    except SystemExit: ok += 1
    # 6: due occorrenze rifiutate
    raw = "\n".join(base + OLD).encode("utf-8")
    try: trasforma(raw); raise AssertionError("due occorrenze accettate")
    except SystemExit: ok += 1
    # 7: idempotenza negata — sul file già patchato il punto 4 vecchio non si trova
    out, _, _ = trasforma("\n".join(base).encode("utf-8"))
    try: trasforma(out); raise AssertionError("seconda applicazione accettata")
    except SystemExit: ok += 1
    # 8: il verify riconosce il blocco nuovo una volta e nessun residuo del vecchio
    righe, _ = leggi(out)
    assert len(trova_new(righe)) == 1 and len(trova(righe)) == 0; ok += 1
    # 9: la banda vecchia non compare nel testo nuovo (proprietà di posizione, non conteggio)
    assert all("17–29" not in x and "17-29" not in x for x in NEW); ok += 1
    print(f"selftest: {ok}/9 OK")

# ── comandi ───────────────────────────────────────────────────────────────
def ancora():
    raw = TARGET.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SHA_ATTESO or len(raw) != BYTE_ATTESI:
        raise SystemExit(f"STOP: ancora attesa {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, "
                         f"trovata {sha[:12]}… {len(raw)} byte; nessuna modifica")
    return raw

def dry_run():
    raw = ancora()
    out, i, eol = trasforma(raw)
    print(f"dry-run OK: ancora {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'}")
    print(f"  punto 4 alle righe {i+1}-{i+2}; diventa righe {i+1}-{i+3}")
    print(f"  byte dopo: {len(out)} (Δ {len(out)-len(raw):+d}); nessuna modifica scritta")

def apply():
    raw = ancora()
    out, i, _ = trasforma(raw)
    TARGET.write_bytes(out)
    print(f"[apply] scritto: sha {hashlib.sha256(out).hexdigest()}  {len(out)} byte")

def verify():
    raw = TARGET.read_bytes()
    righe, eol = leggi(raw)
    n_new, n_old = len(trova_new(righe)), len(trova(righe))
    sha = hashlib.sha256(raw).hexdigest()
    esito = "OK" if (n_new == 1 and n_old == 0) else "ANOMALIA"
    print(f"verify {esito}: blocco nuovo {n_new}x, punto 4 vecchio {n_old}x, "
          f"EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'} uniforme")
    print(f"  sha {sha}  {len(raw)} byte")
    if esito != "OK":
        sys.exit(1)

CMDS = {"selftest": selftest, "dry-run": dry_run, "apply": apply, "verify": verify}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=list(CMDS))
    CMDS[ap.parse_args().cmd]()
