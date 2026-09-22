#!/usr/bin/env python3
"""
paper2_patch_budget_riga5.py  —  la riga 5 del budget ha un registro (record 76, voce 6.2-vi)

Tre interventi su papers/paper2/paper2_budget_5_1.md, posizionali:
  C1  riga 5, colonna «fonte»: il registro accanto al manoscritto (celle contate)
  N   nota 5/6: un paragrafo di correzione IN CODA, che cita la frase falsa per
      dichiararla tale; il testo del 17 settembre resta com'era
  P3  §4, punto 3: la riga 5 riaperta e chiusa con esito positivo

Stesse garanzie dei patcher del budget: ancora sha+byte; byte ed EOL preservati;
ancore uniche; seconda applicazione rifiutata; verify per posizione.

Uso:
  python src\\paper2_patch_budget_riga5.py selftest | dry-run | apply | verify
"""
import argparse, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "papers" / "paper2" / "paper2_budget_5_1.md"
SHA_ATTESO = "dd4fffd51bc7863b0d8f238b8b103a62f446c9c2a9199a551531089e8592c537"
BYTE_ATTESI = 26662

R5_PREFISSO = "| 5 | profilo dei satelliti NFW |"
R5_OLD = "Paper 1 §7.1"
R5_NEW = "`results/paper1/n7_nfw_NGC.jsonl`, 40 coppie; Paper 1 §7.1 (nota 5/6)"

ULTIMA_5_6 = "resta quella giusta, e queste due righe non avranno un percorso accanto."
FRASE_FALSA = "**Riga 5: nessun candidato, ASSENTE su entrambi i metri.**"
CORREZIONE = [
"",
"**Correzione del 18 settembre (voce 6.2-vi, record 76): la riga 5 ha un registro.** È",
"`results/paper1/n7_nfw_NGC.jsonl` (`efe9ee50fd7a…`): 40 record, `idx` 200–239, tutti `gate_ok`, una",
"coppia per record con `uniform`, `nfw` e la loro differenza. Δ medio **−56.475**, SEM appaiata",
"**23.531**, *z* **−2.40**: il −56.5 ± 23.5 a 2.4σ di questa tabella e del §7.1. La frase «Riga 5:",
"nessun candidato, ASSENTE su entrambi i metri» qui sopra è falsa, e resta scritta perché questa",
"correzione la cita. La ricerca cercava i tre valori della riga **sullo stesso record**, e un",
"registro per realizzazione non contiene mai l'aggregato: il metodo era cieco per costruzione a",
"questa specie di fonte. La riga 6 resta senza registro, e va riesaminata con lo stesso occhio. E il",
"«47 % della varianza» ripreso qui dal §7.1 si riproduce, 46.7 %, ma come 1 − σ_Δ/σ_uniform, cioè",
"sulla deviazione standard: sulla varianza l'appaiamento ne toglie il 71.5 % rispetto a un braccio.",
]
P3_OLD = ["3. **Righe 5 e 6 — chiuse con esito negativo**: il run non è registrato, misurato su due",
          "   metri il 17 settembre (nota 5/6). La riga 4 è chiusa: nota 4b."]
P3_NEW = ["3. **Righe 5 e 6 — chiuse con esito negativo il 17 settembre; la 5 riaperta e chiusa con",
          "   esito positivo il 18** (nota 5/6, record 76): il registro della 5 è `n7_nfw_NGC.jsonl`; per",
          "   la 6 il run resta non registrato. La riga 4 è chiusa: nota 4b."]

def leggi(raw: bytes):
    t = raw.decode("utf-8"); n_crlf, n_lf = t.count("\r\n"), t.count("\n")
    if n_crlf == n_lf and n_crlf > 0: eol = "\r\n"
    elif n_crlf == 0 and "\r" not in t: eol = "\n"
    else: raise SystemExit(f"STOP: fine riga miste (CRLF {n_crlf}, LF {n_lf}); nessuna modifica")
    return t.split(eol), eol

def unico(righe, pred, nome):
    hit = [i for i, r in enumerate(righe) if pred(r)]
    if len(hit) != 1: raise SystemExit(f"STOP: {nome} trovata {len(hit)} volte (attesa 1); nessuna modifica")
    return hit[0]

def trasforma(raw: bytes):
    righe, eol = leggi(raw)
    if any(r.startswith("**Correzione del 18 settembre (voce 6.2-vi") for r in righe):
        raise SystemExit("STOP: la correzione esiste già; nessuna modifica")
    i = unico(righe, lambda r: r.startswith(R5_PREFISSO), "riga 5")
    c = righe[i].split("|")
    if len(c) - 2 != 8 or c[4].strip() != R5_OLD:
        raise SystemExit(f"STOP: riga 5 inattesa ({len(c)-2} celle, fonte {c[4].strip()!r})")
    c[4] = " " + R5_NEW + " "; righe[i] = "|".join(c)
    j = unico(righe, lambda r: r == ULTIMA_5_6, "fine della nota 5/6")
    f = unico(righe, lambda r: FRASE_FALSA in r, "frase falsa della riga 5")
    if not f < j or not righe[j + 1] == "" or not righe[j + 2].startswith("**Nota S"):
        raise SystemExit("STOP: la nota 5/6 non ha la forma attesa; nessuna modifica")
    righe[j + 1:j + 1] = CORREZIONE
    k = unico(righe, lambda r: r == P3_OLD[0], "punto 3 del §4")
    if righe[k + 1] != P3_OLD[1]: raise SystemExit("STOP: seconda riga del punto 3 inattesa")
    righe[k:k + 2] = P3_NEW
    return eol.join(righe).encode("utf-8"), eol

def controlla(righe):
    err = []
    r5 = [r for r in righe if r.startswith(R5_PREFISSO)]
    if len(r5) != 1 or r5[0].split("|")[4].strip() != R5_NEW or len(r5[0].split("|")) - 2 != 8: err.append("riga 5 non aggiornata")
    corr = [i for i, r in enumerate(righe) if r.startswith("**Correzione del 18 settembre (voce 6.2-vi")]
    falsa = [i for i, r in enumerate(righe) if FRASE_FALSA in r]
    nota_s = [i for i, r in enumerate(righe) if r.startswith("**Nota S")]
    if len(corr) != 1: err.append(f"correzione presente {len(corr)} volte")
    elif not (falsa and nota_s and falsa[0] < corr[0] < nota_s[0]): err.append("correzione fuori posizione")
    if sum(1 for r in righe if r == P3_NEW[0]) != 1 or any(r == P3_OLD[0] for r in righe): err.append("punto 3 non aggiornato")
    return err

def selftest():
    ok = 0
    fx = ["# t", "", "| # | a | b | c | d | e | f | g |",
          f"{R5_PREFISSO} v | {R5_OLD} | x | y | z | w |", "",
          "**Nota 5/6 — t.** testo", FRASE_FALSA + " altro", ULTIMA_5_6, "", "**Nota S — s.**", "",
          "## 4.", "", P3_OLD[0], P3_OLD[1], "4. **Voce**", ""]
    for eol in ("\n", "\r\n"):
        out, e = trasforma(eol.join(fx).encode("utf-8")); rr, e2 = leggi(out)
        assert e == e2 == eol and not controlla(rr), controlla(rr); ok += 1
    out, _ = trasforma("\n".join(fx).encode("utf-8"))
    try: trasforma(out); raise AssertionError("seconda applicazione accettata")
    except SystemExit: ok += 1
    f2 = list(fx); f2[3] = f2[3].replace(R5_OLD, "Paper 1 §7.2")
    try: trasforma("\n".join(f2).encode("utf-8")); raise AssertionError("fonte diversa accettata")
    except SystemExit: ok += 1
    f3 = list(fx); f3[8] = "testo in mezzo"
    try: trasforma("\n".join(f3).encode("utf-8")); raise AssertionError("nota 5/6 di forma diversa accettata")
    except SystemExit: ok += 1
    assert all("|" not in x for x in CORREZIONE + P3_NEW) and "|" not in R5_NEW; ok += 1
    print(f"selftest: {ok}/6 OK")

def ancora(p):
    raw = p.read_bytes(); s = hashlib.sha256(raw).hexdigest()
    if s != SHA_ATTESO or len(raw) != BYTE_ATTESI:
        raise SystemExit(f"STOP: ancora attesa {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, trovata {s[:12]}… {len(raw)} byte")
    return raw

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--file", type=Path, default=TARGET); a = ap.parse_args()
    if a.cmd == "selftest": selftest()
    elif a.cmd == "verify":
        raw = a.file.read_bytes(); rr, eol = leggi(raw); err = controlla(rr)
        print(f"verify {'OK' if not err else 'ANOMALIA'}: sha {hashlib.sha256(raw).hexdigest()}  {len(raw)} byte, EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'} uniforme")
        for e in err: print("  -", e)
        sys.exit(1 if err else 0)
    else:
        raw = ancora(a.file); out, eol = trasforma(raw)
        if a.cmd == "dry-run":
            print(f"dry-run OK: ancora {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, EOL {'CRLF' if eol == chr(13)+chr(10) else 'LF'}")
            print(f"  dopo: {len(out)} byte (Δ {len(out)-len(raw):+d}), sha {hashlib.sha256(out).hexdigest()[:12]}…; nessuna modifica scritta")
        else:
            a.file.write_bytes(out); print(f"[apply] scritto: sha {hashlib.sha256(out).hexdigest()}  {len(out)} byte")
