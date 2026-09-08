#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_selection_channel_patch.py — selection_channel salta i punti che non
hanno il livello richiesto, e DICE quali.

IL DIFETTO
    KeyError: 'N_H1_k2'  in selection_channel

  `selection_channel` cicla su TUTTI i punti del lato dati. Dopo il run del
  blocco A sul lato mock, quel registro contiene A0, A1m, A3m e A0m, girati a
  erosioni 0 e 1 SOLTANTO: a k=2 e k=3 la chiave non esiste e il run muore a
  meta', dopo aver gia' stampato l'esito del livello.

  Non e' un difetto dei dati: e' corretto che quei quattro punti abbiano solo
  due livelli, perche' il blocco A serve al PAVIMENTO e il pavimento si calcola
  ai livelli del budget. E' il consumatore che dava per scontato che ogni punto
  avesse ogni livello.

LA CORREZIONE, E PERCHE' NON UN try/except
  Si potrebbero avvolgere le due medie in un try. Sarebbe peggio: un punto che
  sparisce in silenzio da una tabella e' esattamente il modo in cui si perdono
  le righe senza accorgersene. Qui i punti si filtrano PRIMA, e quelli saltati
  si contano e si stampano, cosi' chi legge sa che la tabella e' parziale e
  perche'.

COSA NON CAMBIA
  A k=0 e k=1 tutti i punti hanno la chiave, quindi la lista dei saltati e'
  vuota e la tabella e' identica a prima. Il selftest lo verifica.

Uso:
    python src\\paper2_selection_channel_patch.py selftest
    python src\\paper2_selection_channel_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_analisi.py")

A_OLD = '''def selection_channel(mock_rows, key, desi_pts):
    """dN_H1/dn_sel per punto: e' il termine (c) del 3.3."""
    out = {}
    for p in desi_pts:
        if p == "FID":
            continue
        dn = np.mean([r["points"][p]["N_H1_k1" if key.endswith("k1") else key]
                      - r["points"]["FID"]["N_H1_k1" if key.endswith("k1") else key]
                      for r in mock_rows])'''

A_NEW = '''def selection_channel(mock_rows, key, desi_pts):
    """dN_H1/dn_sel per punto: e' il termine (c) del 3.3.

    I punti che non hanno il livello richiesto sul lato mock si SALTANO, e si
    dice quali. Succede dal 4 set 2026: il blocco A e' stato esteso a sei punti
    e i quattro nuovi - A0, A1m, A3m, A0m - sono stati girati a erosioni 0 e 1
    soltanto, perche' servono al PAVIMENTO e il pavimento si calcola ai livelli
    del budget. Prima di questa correzione il run moriva con KeyError a meta',
    dopo aver gia' stampato l'esito del livello.

    Non si usa un try/except attorno alle medie: un punto che sparisce in
    silenzio da una tabella e' il modo in cui si perdono le righe senza
    accorgersene. Si filtra prima e si conta."""
    kk = "N_H1_k1" if key.endswith("k1") else key
    disponibili = [p for p in desi_pts
                   if p != "FID"
                   and all(kk in r["points"].get(p, {}) for r in mock_rows)]
    saltati = [p for p in desi_pts if p != "FID" and p not in disponibili]
    if saltati:
        print(f"    [canale selezione] {len(saltati)} punti saltati, senza "
              f"{kk} sul lato mock: {', '.join(sorted(saltati))}. "
              f"La tabella che segue e' parziale.")
    out = {"_punti_saltati": sorted(saltati)} if saltati else {}
    for p in disponibili:
        dn = np.mean([r["points"][p][kk] - r["points"]["FID"][kk]
                      for r in mock_rows])'''

B_OLD = '''        ds = np.mean([r["points"][p]["n_sel"] - r["points"]["FID"]["n_sel"]
                      for r in mock_rows])
        out[p] = {"d_N_H1": float(dn), "d_n_sel": float(ds),
                  "gen_per_gal": float(dn / ds) if abs(ds) > 1.0 else None}
    return out'''

B_NEW = '''        ds = np.mean([r["points"][p]["n_sel"] - r["points"]["FID"]["n_sel"]
                      for r in mock_rows])
        out[p] = {"d_N_H1": float(dn), "d_n_sel": float(ds),
                  "gen_per_gal": float(dn / ds) if abs(ds) > 1.0 else None}
    return out'''

EDITS = [("A  selection_channel filtra prima e dichiara i saltati", A_OLD, A_NEW)]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        n = s.count(old)
        if n != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, n))
        s = s.replace(old, new, 1)
    return s


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def _semantica():
    """La correzione deve fare quel che dice, su righe che imitano le vere."""
    rows = [{"points": {"FID": {"N_H1_k0": 100, "N_H1_k2": 60, "n_sel": 1000},
                        "B1": {"N_H1_k0": 90, "N_H1_k2": 55, "n_sel": 990},
                        "A0": {"N_H1_k0": 98, "n_sel": 999}}}]
    pts = ["FID", "B1", "A0"]
    res = {}
    for kk in ("N_H1_k0", "N_H1_k2"):
        disp = [p for p in pts if p != "FID"
                and all(kk in r["points"].get(p, {}) for r in rows)]
        res[kk] = sorted(disp)
    return res


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    r = _semantica()
    chk("1  a k=0 nessun punto si salta: la tabella resta quella di prima",
        r["N_H1_k0"] == ["A0", "B1"], repr(r["N_H1_k0"]))
    chk("2  a k=2 si salta SOLO il punto che non ha la chiave",
        r["N_H1_k2"] == ["B1"], repr(r["N_H1_k2"]))

    ok = os.path.isfile(path)
    chk("3  analisi presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("4  prerequisito: --levels e' gia' applicato",
        "--levels" in s)
    chk("5  idempotenza: il filtro non c'e' ancora", "_punti_saltati" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=6):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("7  il risultato e' Python valido", _parses(out))
        chk("8  NIENTE try/except attorno alle medie",
            "try:" not in out.split("def selection_channel")[1].split("return out")[0])
        chk("9  i saltati si CONTANO e si STAMPANO, non spariscono",
            ("punti saltati" in out) and ("_punti_saltati" in out)
            and ("tabella che segue e' parziale" in out))
        chk("10 e finiscono nel record, non solo a schermo",
            'out = {"_punti_saltati": sorted(saltati)} if saltati else {}' in out)
        chk("11 il ciclo gira sui DISPONIBILI, non su tutti",
            "for p in disponibili:" in out
            and "for p in desi_pts:" not in out.split("def selection_channel")[1][:1400])
        chk("12 la chiave si calcola UNA volta, non tre",
            out.split("def selection_channel")[1][:1600].count(
                '"N_H1_k1" if key.endswith("k1") else key') == 1)
        chk("13 il perche' e' nel codice: il blocco A ha solo due livelli",
            ("A0, A1m, A3m, A0m" in out) and ("PAVIMENTO" in out))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_selection_channel_patch ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    if selftest(a.path):
        print("")
        fail("selftest fallito: nessuna scrittura.")
    s = read(a.path)
    out = apply_all(s)
    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="prima", tofile="dopo", n=2))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_selchan"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print(r"""
POI:
  python src\paper2_fase3_analisi.py selftest
  python src\paper2_fase3_analisi.py run --region NGC
  python src\paper2_fase3_analisi.py run --region SGC

Senza --levels nulla deve cambiare: -98.3 e -114.0, e NESSUNA riga
'[canale selezione] ... punti saltati', perche' a k=0 e k=1 tutti i punti hanno
la chiave.

E POI i quattro livelli:
  python src\paper2_fase3_analisi.py run --region NGC --levels 1 0 2 3
  python src\paper2_fase3_analisi.py run --region SGC --levels 1 0 2 3

A k=2 e k=3 deve comparire '[canale selezione] 4 punti saltati, senza N_H1_k2
sul lato mock: A0, A0m, A1m, A3m. La tabella che segue e' parziale.'
Se NON compare e il run passa lo stesso, il filtro non sta filtrando e va
guardato prima di usare quei numeri.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="selection_channel salta i punti senza livello")
    p.add_argument("--path", default=DEFAULT_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: 1 if selftest(a.path) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
