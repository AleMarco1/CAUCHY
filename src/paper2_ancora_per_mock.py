#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_ancora_per_mock.py

Il cancello del runner di 4.2a si e' fermato su SGC idx 24: ramo unitario 18684
contro 18592 congelato, scarto 92. Ventiquattro realizzazioni prima avevano
scarto ZERO.

Una differenza di implementazione fallirebbe ovunque. Uno scarto di 92 su 18600
e' mezza sd dell'ensemble: un valore plausibile ma diverso, non un errore di
aritmetica. La forma e' quella di due record per la stessa chiave, o di una
mappatura chiave -> indice che scivola.

IL SOSPETTO, DA VERIFICARE
--------------------------
`carica_ancore` legge il registro con `int(str(key).split("_")[-1])` e scrive in
un dizionario: LAST-WINS. Il record 49 impone di leggere fase3_mock per UNIONE, e
il record 50 §vii dice lo stesso di per_mock_*_erosion_restrict. Se anche
per_mock_<REG>_R5.jsonl ha piu' record per chiave, il runner confronta il proprio
risultato con UNO dei due.

E per_mock_SGC_R5.jsonl non e' mai stato usato come ancora prima: n6 gira solo su
NGC e solo da 200 in su.

COSA FA
-------
Sola lettura. Conta i record e le chiavi distinte, elenca TUTTI i record di una
chiave, e cerca un valore nell'intero registro per vedere sotto quale chiave
compare. Quest'ultima e' la prova decisiva: se 18684 sta sotto un'altra chiave,
la mappatura scivola; se non c'e' affatto, i due numeri vengono da trattamenti
diversi.

USO
    python src\\paper2_ancora_per_mock.py selftest
    python src\\paper2_ancora_per_mock.py esamina --region SGC --idx 24 --valore 18684
    python src\\paper2_ancora_per_mock.py esamina --region NGC --idx 24

Uscita: 0 sempre che il file esista. Il verdetto sta nel testo.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

NH1 = "base.N_H1"
ROOT_DEFAULT = "."


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def indice_da_chiave(chiave, fallback):
    """La stessa mappatura di carica_ancore e di n6, riprodotta qui."""
    try:
        return int(str(chiave).split("_")[-1])
    except (TypeError, ValueError):
        return fallback


def leggi(path):
    righe = []
    with Path(path).open("r", encoding="utf-8", errors="replace") as fh:
        for i, l in enumerate(fh, 1):
            l = l.strip()
            if not l:
                continue
            try:
                righe.append((i, json.loads(l)))
            except Exception:
                righe.append((i, None))
    return righe


def esamina(root, region, idx, valore=None):
    p = Path(root) / "results" / "paper1" / ("per_mock_%s_R5.jsonl" % region)
    if not p.is_file():
        raise SystemExit("RIFIUTO: file inesistente: %s" % p)
    righe = leggi(p)
    buone = [(n, r) for n, r in righe if isinstance(r, dict)]

    print("=" * 78)
    print("ANCORA per_mock  |  %s  |  %s" % (region, p.name))
    print("=" * 78)
    print("  righe: %d   leggibili: %d   malformate: %d"
          % (len(righe), len(buone), len(righe) - len(buone)))

    per_indice = defaultdict(list)
    chiavi = Counter()
    for j, (n, r) in enumerate(buone):
        fl = flatten(r)
        ch = fl.get("key", j)
        chiavi[str(ch)] += 1
        per_indice[indice_da_chiave(ch, j)].append((n, ch, fl))

    dup_chiavi = {k: v for k, v in chiavi.items() if v > 1}
    dup_indici = {k: len(v) for k, v in per_indice.items() if len(v) > 1}
    print("  chiavi distinte: %d   chiavi ripetute: %d"
          % (len(chiavi), len(dup_chiavi)))
    print("  indici distinti: %d   indici con piu' record: %d"
          % (len(per_indice), len(dup_indici)))
    if dup_indici:
        primi = sorted(dup_indici.items())[:10]
        print("    primi indici con piu' record: %s" % primi)
        print("    *** LAST-WINS sta scegliendo, e la scelta non e' dichiarata ***")
    mancanti = [i for i in range(2000) if i not in per_indice]
    print("  indici 0..1999 assenti: %d%s"
          % (len(mancanti), (" (primi: %s)" % mancanti[:10]) if mancanti else ""))

    print("\n--- tutti i record dell'indice %d ---" % idx)
    for n, ch, fl in per_indice.get(idx, []):
        v = fl.get(NH1)
        altre = {k: fl[k] for k in sorted(fl) if k.endswith("N_H1") or "N_H1_" in k}
        print("  riga %-6d chiave %-16s %s = %s" % (n, ch, NH1, v))
        if len(altre) > 1:
            print("      altre celle N_H1: %s" % altre)
        extra = {k: fl[k] for k in sorted(fl)
                 if k not in ("key", NH1) and not str(k).startswith("base.")}
        if extra:
            print("      altri campi: %s" % {k: extra[k] for k in list(extra)[:8]})
    if idx not in per_indice:
        print("  NESSUN record per questo indice")

    if valore is not None:
        print("\n--- dove compare il valore %g nell'intero registro ---" % valore)
        trovati = []
        for i, (n, ch, fl) in enumerate(
                [(n, ch, fl) for lst in per_indice.values() for (n, ch, fl) in lst]):
            for k, v in fl.items():
                try:
                    if abs(float(v) - float(valore)) < 0.5:
                        trovati.append((n, ch, k, v))
                except (TypeError, ValueError):
                    continue
        if not trovati:
            print("  NON compare da nessuna parte.")
            print("  -> i due numeri vengono da trattamenti diversi, non da uno")
            print("     scivolamento di indice. Va capito quale sia il trattamento")
            print("     del registro PRIMA di usarlo come ancora.")
        for n, ch, k, v in trovati[:12]:
            print("  riga %-6d chiave %-16s campo %-24s = %s" % (n, ch, k, v))
        if trovati:
            chiavi_t = {ch for _, ch, _, _ in trovati}
            atteso = "delta_%04d" % idx
            if chiavi_t == {atteso}:
                print("  -> sta SOLO sotto la chiave attesa: nessuno scivolamento")
            else:
                print("  -> compare sotto %s, non solo sotto %s"
                      % (sorted(chiavi_t), atteso))
                print("     *** la mappatura chiave -> indice non e' quella giusta ***")
    return 0


# ---------------------------------------------------------------------------

def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_ancora_per_mock")

    chk("la mappatura e' quella di carica_ancore e di n6",
        indice_da_chiave("delta_0024", -1) == 24)
    chk("una chiave senza suffisso numerico cade sul fallback",
        indice_da_chiave("pippo", 7) == 7)
    chk("e una chiave assente pure", indice_da_chiave(None, 3) == 3)
    chk("attenzione: chiavi diverse possono dare lo STESSO indice",
        indice_da_chiave("R5_0024", -1) == indice_da_chiave("delta_0024", -1) == 24)

    chk("flatten usa il punto", flatten({"base": {"N_H1": 5}}) == {"base.N_H1": 5})

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "results" / "paper1"
        d.mkdir(parents=True)
        f = d / "per_mock_SGC_R5.jsonl"
        # due record per la stessa chiave, con valori diversi: e' il sospetto
        f.write_text("\n".join([
            json.dumps({"key": "delta_0023", "base": {"N_H1": 18500}}),
            json.dumps({"key": "delta_0024", "base": {"N_H1": 18592}}),
            json.dumps({"key": "delta_0024", "base": {"N_H1": 18684}}),
        ]) + "\n", encoding="utf-8")
        righe = leggi(f)
        chk("leggi tiene il numero di riga", [n for n, _ in righe] == [1, 2, 3])
        per = {}
        for j, (n, r) in enumerate(righe):
            per.setdefault(indice_da_chiave(flatten(r).get("key", j), j), []).append(n)
        chk("due record sullo stesso indice vengono visti entrambi",
            per[24] == [2, 3], per)
        chk("e last-wins ne perderebbe uno", len(per[24]) == 2)
        chk("esamina gira senza sollevare", esamina(td, "SGC", 24, 18684) == 0)
        try:
            esamina(td, "NGC", 24)
            chk("regione assente: rifiuto", False, "non ha rifiutato")
        except SystemExit as e:
            chk("regione assente: rifiuto", "inesistente" in str(e))

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("esamina")
    e.add_argument("--root", default=ROOT_DEFAULT)
    e.add_argument("--region", choices=["NGC", "SGC"], required=True)
    e.add_argument("--idx", type=int, required=True)
    e.add_argument("--valore", type=float, default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "esamina":
        return esamina(a.root, a.region, a.idx, a.valore)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
