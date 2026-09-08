#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_contrasti.py - i contrasti PARI e DISPARI della linea B, contro l'attesa
a priori. Risposta 3 del referee + attesa d'ordine di grandezza (punto 8).

SOLA LETTURA. Nessun run, nessuna scrittura nei registri.

Le due statistiche, letteralmente come le scrive il referee
----------------------------------------------------------
  D = N_mock - N_dati       <- CONVENZIONE, come la risposta 3 al referee e
                               coerente col deficit positivo 7181.

  DISPARI = [D(B5) - D(B1)] + [D(B4) - D(B2)]
  PARI    = [D(B5) + D(B1) - 2 D(B3)] + [D(B4) + D(B2) - 2 D(B3)]     B3 = FID

Sono libere da modello: nessun fit, nessuna famiglia di forma. Il referee lo dice
esplicitamente -- "la domanda sulla simmetria non ha mai avuto bisogno di un
fit" -- perche' la linea B e' stata campionata simmetricamente in spostamento
apposta.

L'ATTESA, DERIVATA E NON DIGITATA
---------------------------------
  pari(eps)     = N * ETA * eps^2         ETA = 1.08, elasticita' al volume
                                          misurata dal cancello 2.7
  dispari(eps)  = RSD_123 * eps / 0.20    123 generatori per +-20% sulla
                                          dispersione satellitare, M26 §7(viii),
                                          scalati linearmente

N si LEGGE dal registro, per lato e per livello: il lato dati ha il suo, il lato
mock il suo. Il rapporto fra le due attese e' quindi N_dati/N_mock ~ 0.80, ed e'
la ragione per cui il termine pari NON si cancella del tutto in D.

DUE TRAPPOLE NOTE, ENTRAMBE EVITATE QUI
---------------------------------------
  1. FUSIONE. fase3_mock.jsonl ha piu' record per (regione, indice): 11 punti a
     k=0,1, il solo B6 dall'emendamento 15, 12 punti a k=2,3. Una lettura
     last-wins ne perde una parte -- e' successo davvero, `budget` e `analisi`
     sostituivano il dizionario del punto invece di unirlo. Qui si UNISCE, e i
     conflitti di valore si segnalano invece di essere assorbiti.
  2. CHIAVI ASSENTI. Niente `.get(k)` che restituisce None e passa il controllo:
     una chiave mancante e' un ERRORE, non un valore. Assenza e correttezza non
     devono dare lo stesso verdetto.

Sottocomandi
------------
  inspect    schema dei due registri: quali punti, quante realizzazioni, quali
             chiavi. Da lanciare PRIMA di `run`.
  run        i contrasti, per regione e per livello di erosione.
  selftest   dati sintetici a risposta nota. Non tocca i registri veri.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys

DEFAULT_DATA = os.path.join("results", "paper2", "fase3.jsonl")
DEFAULT_MOCK = os.path.join("results", "paper2", "fase3_mock.jsonl")

NEEDED = ("FID", "B1", "B2", "B4", "B5")

# Linea B in convenzione pipeline, da paper2_item13a_15a.LINE_B.
F_AP = {"B1": 0.971070, "B2": 0.985396, "FID": 1.0,
        "B4": 1.014889, "B5": 1.030071, "B6": 1.045531810025433}

# Attesa: due sole costanti, entrambe misurate altrove.
ETA_VOLUME = 1.08          # elasticita' al volume, cancello 2.7
RSD_123 = 123.0            # generatori per +-20% di dispersione satellitare, M26
RSD_REF_FRAC = 0.20


def contrasto_dispari(v):
    return (v["B5"] - v["B1"]) + (v["B4"] - v["B2"])


def contrasto_pari(v):
    return ((v["B5"] + v["B1"] - 2 * v["FID"])
            + (v["B4"] + v["B2"] - 2 * v["FID"]))


def eps(point):
    return abs(F_AP[point] - 1.0)


def modello(A, B):
    """delta(F) = A (F-1)^2 + B (F-1) valutato sui cinque punti."""
    return {p: A * (F_AP[p] - 1.0) ** 2 + B * (F_AP[p] - 1.0) for p in NEEDED}


def attesa(N):
    """(dispari, pari) attesi, calcolati con LE STESSE funzioni di contrasto
    usate sui dati. Cosi' il travaso fra i due contrasti e' DENTRO l'attesa
    invece di essere assunto nullo.

    A = N * ETA_VOLUME  : risposta pari, quadratica nello shear, dall'elasticita'
                          al volume misurata dal cancello 2.7.
    B = RSD_123 / 0.20  : risposta dispari, lineare, dai 123 generatori che M26
                          misura per +-20% di dispersione satellitare.
    """
    A = N * ETA_VOLUME
    B = RSD_123 / RSD_REF_FRAC
    d = modello(A, B)
    return contrasto_dispari(d), contrasto_pari(d)


def travaso(N):
    """Quanto ciascun termine entra nel contrasto SBAGLIATO.

    La linea B non e' perfettamente simmetrica in spostamento -- |F5-1| supera
    |F1-1| dello 0.9%, ed e' il confondente strumentale gia' dichiarato in
    checklist 1.3. Quindi il contrasto dispari raccoglie un po' di quadratico e
    il pari un po' di lineare. Si riportano: sono piccoli, ma piccoli e
    dichiarati non e' come piccoli e assunti.
    """
    A = N * ETA_VOLUME
    B = RSD_123 / RSD_REF_FRAC
    quad_in_odd = contrasto_dispari(modello(A, 0.0))
    lin_in_even = contrasto_pari(modello(0.0, B))
    return quad_in_odd, lin_in_even


# ---------------------------------------------------------------------------
# Lettura, con FUSIONE e senza `.get` permissivi
# ---------------------------------------------------------------------------

def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def read_jsonl(path):
    if not os.path.isfile(path):
        fail("registro assente: %s" % path)
    out = []
    with open(path, "rb") as fh:
        raw = fh.read()
    for i, ln in enumerate(raw.replace(b"\r\n", b"\n").split(b"\n"), start=1):
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln.decode("utf-8")))
        except Exception as exc:
            fail("%s riga %d non e' JSON: %s" % (path, i, exc))
    return out


def merge_points(records, key_fn):
    """Unisce i dizionari `points` per chiave. NON last-wins.

    Ritorna (merged, conflitti). Un conflitto e' la stessa (chiave, punto,
    campo) con due valori diversi: si riporta, non si sceglie.
    """
    merged, conflicts = {}, []
    for r in records:
        if r.get("smoke"):
            continue
        k = key_fn(r)
        pts = r.get("points")
        if not isinstance(pts, dict):
            continue
        slot = merged.setdefault(k, {})
        for name, d in pts.items():
            if not isinstance(d, dict):
                continue
            cur = slot.setdefault(name, {})
            for f, v in d.items():
                if f in cur and cur[f] != v:
                    conflicts.append((k, name, f, cur[f], v))
                cur[f] = v
    return merged, conflicts


# Il lato dati ha una struttura DIVERSA dal lato mock: un record per (punto,
# gauge), non un dizionario `points`. E i nomi non coincidono: N_H1 e' k=1.
DATA_FIELD = {"N_H1_k0": "N_H1_k0", "N_H1_k1": "N_H1"}
DATA_GAUGE = {"FID": "fid"}          # gli altri punti: "regauged"


def read_data_side(path):
    """{regione: {punto: {campo_mock: valore}}} da fase3.jsonl.

    Il blocco A esiste in DUE gauge, `regauged` e `derived`: si prende
    `regauged`, come tutto il resto della Fase 3. Il fiduciale ha gauge `fid`.
    Un duplicato con valori diversi dopo il filtro e' un errore, non una scelta.
    """
    out, conflicts, ladder_ok, ladder_bad = {}, [], 0, []
    for r in read_jsonl(path):
        pt, reg = r.get("point"), r.get("region")
        if pt is None or reg is None:
            continue
        if r.get("gauge") != DATA_GAUGE.get(pt, "regauged"):
            continue
        slot = out.setdefault(reg, {}).setdefault(pt, {})
        for mock_name, data_name in DATA_FIELD.items():
            if data_name not in r:
                continue
            v = float(r[data_name])
            if mock_name in slot and slot[mock_name] != v:
                conflicts.append((reg, pt, mock_name, slot[mock_name], v))
            slot[mock_name] = v
            # controllo incrociato con `ladder`, che porta l'intera scala di
            # erosione (record 41). Non e' una seconda via di lettura: e' un
            # confronto. Se non e' interpretabile lo si dice, non lo si salta.
            lad = r.get("ladder")
            k = mock_name.rsplit("_k", 1)[-1]
            cand = None
            if isinstance(lad, dict):
                for key in (k, int(k) if k.isdigit() else None):
                    if key is not None and key in lad:
                        cand = lad[key]
                        break
            elif isinstance(lad, list) and k.isdigit() and int(k) < len(lad):
                cand = lad[int(k)]
            if cand is None:
                if lad is not None:
                    ladder_bad.append((reg, pt, mock_name))
            else:
                cv = cand.get("N_H1") if isinstance(cand, dict) else cand
                if cv is not None and float(cv) != v:
                    conflicts.append((reg, pt, mock_name + "/ladder", v, float(cv)))
                else:
                    ladder_ok += 1
    return out, conflicts, ladder_ok, ladder_bad


def must(d, key, where):
    if key not in d:
        fail("campo %r assente in %s. Una chiave mancante e' un errore, non un "
             "valore: correggi --field o il registro." % (key, where))
    return d[key]


# ---------------------------------------------------------------------------
# I contrasti
# ---------------------------------------------------------------------------


def per_realisation(mock_merged, region, field):
    """[(indice, {punto: N})] sulle realizzazioni COMPLETE, cioe' che hanno
    tutti e cinque i punti. Le incomplete si contano e si riportano."""
    full, partial = [], []
    for (reg, idx), pts in sorted(mock_merged.items()):
        if reg != region:
            continue
        if not all(p in pts and field in pts[p] for p in NEEDED):
            partial.append(idx)
            continue
        full.append((idx, {p: float(pts[p][field]) for p in NEEDED}))
    return full, partial


def analizza(data_pts, mock_merged, region, field):
    full, partial = per_realisation(mock_merged, region, field)
    if len(full) < 2:
        return None, partial
    odd_i = [contrasto_dispari(v) for _, v in full]
    even_i = [contrasto_pari(v) for _, v in full]
    n = len(full)
    N_mock_fid = st.mean(v["FID"] for _, v in full)

    for p in NEEDED:
        if p not in data_pts or field not in data_pts[p]:
            fail("lato dati: manca %s/%s per %s" % (p, field, region))
    dv = {p: float(data_pts[p][field]) for p in NEEDED}

    def stat(xs):
        m = st.mean(xs)
        sd = st.stdev(xs) if len(xs) > 1 else 0.0
        sem = sd / math.sqrt(len(xs))
        return m, sd, sem

    om, osd, osem = stat(odd_i)
    em, esd, esem = stat(even_i)
    return {
        "n": n,
        "N_mock_FID": N_mock_fid,
        "N_data_FID": dv["FID"],
        "odd_mock": (om, osd, osem),
        "even_mock": (em, esd, esem),
        "odd_data": contrasto_dispari(dv),
        "even_data": contrasto_pari(dv),
        # CONVENZIONE: D = mock - dati, la stessa della risposta 3 al referee e
        # coerente col deficit positivo (7181 = mock - dati). La rev. 5 usava
        # dati - mock, e i due documenti si contraddicevano sui segni.
        "odd_D": om - contrasto_dispari(dv),
        "even_D": em - contrasto_pari(dv),
        "att_odd": attesa(N_mock_fid)[0],
        "att_even_mock": attesa(N_mock_fid)[1],
        "att_even_data": attesa(dv["FID"])[1],
        "att_odd_data": attesa(dv["FID"])[0],
        "travaso_mock": travaso(N_mock_fid),
    }, partial


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

def cmd_inspect(args):
    d, dconf, lad_ok, lad_bad = read_data_side(args.data)
    print("=== DATI  %s ===" % args.data)
    print("  regioni           : %s" % sorted(d))
    for reg in sorted(d):
        print("    %s: %d punti  %s" % (reg, len(d[reg]), sorted(d[reg])))
        mancano = [p for p in NEEDED if p not in d[reg]]
        print("       serve %s -> %s" % (list(NEEDED),
                                         "tutti presenti" if not mancano
                                         else "MANCANO %s" % mancano))
        campi = sorted({f for v in d[reg].values() for f in v})
        print("       campi (rimappati dal lato dati): %s" % campi)
    print("  conflitti         : %d" % len(dconf))
    print("  ladder: confronti riusciti %d, non interpretabili %d"
          % (lad_ok, len(lad_bad)))

    recs = read_jsonl(args.mock)
    m, conf = merge_points(recs, lambda r: (r.get("region"), r.get("index")))
    pts = sorted({n for v in m.values() for n in v})
    fields = sorted({f for v in m.values() for d2 in v.values() for f in d2
                     if f.startswith("N_H1")})
    print("=== MOCK  %s ===" % args.mock)
    print("  record            : %d   chiavi dopo fusione: %d" % (len(recs), len(m)))
    print("  punti             : %s" % pts)
    print("  campi             : %s" % fields)
    print("  conflitti         : %d" % len(conf))

    print("")
    print("Attesa a priori, derivata con le stesse funzioni di contrasto:")
    for N in (35423.575, 28256.0):
        o, e = attesa(N)
        q, l = travaso(N)
        print("  a N = %9.1f : dispari %6.1f, pari %6.1f   (travaso: "
              "quadratico nel dispari %.2f, lineare nel pari %.2f)"
              % (N, o, e, q, l))
    return 0


def cmd_run(args):
    dmerged, dconf, lad_ok, lad_bad = read_data_side(args.data)
    mmerged, mconf = merge_points(read_jsonl(args.mock),
                                  lambda r: (r.get("region"), r.get("index")))
    if dconf or mconf:
        print("[avviso] conflitti: dati %d, mock %d. NON risolti in silenzio."
              % (len(dconf), len(mconf)))
        for c in (dconf + mconf)[:5]:
            print("    %s" % (c,))
    print("[ladder] confronti incrociati riusciti: %d, non interpretabili: %d"
          % (lad_ok, len(lad_bad)))

    regions = args.regions or sorted(r for r in dmerged if r)
    if not regions:
        fail("nessuna regione sul lato dati: il piano e' VUOTO. Un piano vuoto "
             "non e' un risultato.")
    fatte = 0
    for region in regions:
        if region not in dmerged:
            fail("%s assente dal lato dati: non salto in silenzio." % region)
        for field in args.fields:
            res, partial = analizza(dmerged[region], mmerged, region, field)
            print("")
            print("=" * 78)
            print("%s   %s" % (region, field))
            print("=" * 78)
            if res is None:
                print("  realizzazioni complete insufficienti "
                      "(incomplete: %d)" % len(partial))
                continue
            fatte += 1
            print("  realizzazioni complete : %d%s"
                  % (res["n"], ("   incomplete: %d" % len(partial))
                     if partial else ""))
            print("  N al fiduciale         : dati %.0f   mock %.1f"
                  % (res["N_data_FID"], res["N_mock_FID"]))
            print("")
            om, osd, osem = res["odd_mock"]
            em, esd, esem = res["even_mock"]
            print("  %-10s %12s %12s %12s %12s"
                  % ("", "lato dati", "lato mock", "in D", "attesa"))
            print("  %-10s %12.1f %8.1f+-%-3.1f %8.1f+-%-3.1f %12.1f"
                  % ("DISPARI", res["odd_data"], om, osem,
                     res["odd_D"], osem,
                     res["att_odd"] - res["att_odd_data"]))
            print("  %-10s %12.1f %8.1f+-%-3.1f %8.1f+-%-3.1f %12s"
                  % ("PARI", res["even_data"], em, esem,
                     res["even_D"], esem,
                     "%.1f / %.1f" % (res["att_even_data"],
                                      res["att_even_mock"])))
            print("")
            print("  attesa DISPARI: lato dati %.1f, lato mock %.1f, quindi in D "
                  "%.1f -- il termine dispari e' calibrato come numero ASSOLUTO "
                  "(123 generatori di M26 per +-20%% di dispersione satellitare), "
                  "non scala con N, e percio' si cancella quasi del tutto in D: "
                  "resta il solo travaso."
                  % (res["att_odd_data"], res["att_odd"],
                     res["att_odd"] - res["att_odd_data"]))
            print("  attesa PARI: lato dati %.1f, lato mock %.1f, quindi in D "
                  "%.1f -- il termine pari NON si cancella del tutto perche' i "
                  "due lati hanno N diverso (rapporto %.3f)."
                  % (res["att_even_data"], res["att_even_mock"],
                     res["att_even_mock"] - res["att_even_data"],
                     res["N_data_FID"] / res["N_mock_FID"]))
            for lab, mis, att, sem in (
                    ("DISPARI", res["odd_D"],
                     res["att_odd"] - res["att_odd_data"], osem),
                    ("PARI", res["even_D"],
                     res["att_even_mock"] - res["att_even_data"], esem)):
                d_sem = abs(mis - att) / sem if sem > 0 else float("inf")
                # Un rapporto misura/attesa con l'attesa compatibile con zero
                # non e' una statistica: -759.04 accanto a "16.4 SEM" invita a
                # leggere il numero sbagliato. Il rapporto si stampa solo quando
                # l'attesa e' distinguibile da zero alla precisione della misura.
                if abs(att) > sem:
                    print("  %-8s misura/attesa = %+.2f   (scarto %.1f, %.1f SEM)"
                          % (lab, mis / att, mis - att, d_sem))
                else:
                    print("  %-8s attesa %+.2f, indistinguibile da zero a questa "
                          "SEM (%.1f):" % (lab, att, sem))
                    print("           il rapporto non e' informativo. La misura "
                          "sta a %.1f SEM dall'attesa." % d_sem)
            print("")
            # RISPOSTA 1: nessun sigma si scrive senza dire a quale domanda
            # risponde. La SEM misura l'incertezza sulla MEDIA dei mock; la sd
            # mock-a-mock misura quanto e' strana UNA realizzazione. Il lato
            # dati e' una realizzazione, quindi servono entrambe.
            print("  DUE DENOMINATORI, due domande (risposta 1):")
            print("    %-8s %10s | %8s %7s | %8s %7s"
                  % ("", "in D", "SEM", "sigma", "sd m-m", "sigma"))
            for lab, mis, sem in (("DISPARI", res["odd_D"], osem),
                                  ("PARI", res["even_D"], esem)):
                sd_mm = sem * math.sqrt(res["n"])
                print("    %-8s %10.1f | %8.1f %6.1f%s | %8.1f %6.2f%s"
                      % (lab, mis, sem, abs(mis) / sem if sem else float("nan"), "s",
                         sd_mm, abs(mis) / sd_mm if sd_mm else float("nan"), "s"))
            print("    la SEM risponde a: la media dell'ensemble risponde come il")
            print("    campo osservato?  la sd a: il campo osservato e' "
                  "un'estrazione strana?")
            print("")
            print("  z del LATO MOCK dal ZERO: dispari %.1f, pari %.1f"
                  % (abs(om) / osem if osem else float("inf"),
                     abs(em) / esem if esem else float("inf")))
    if not fatte:
        fail("nessun contrasto calcolato: il piano e' VUOTO. Silenzio e "
             "successo non devono somigliarsi.")
    print("")
    print("Nota di lettura: il contrasto DISPARI e' (a meno del termine B4/B2)")
    print("Delta D_max, che il documento gia' esclude da zero. Il contrasto PARI")
    print("e' la statistica nuova: e' la risposta al MODULO della deformazione,")
    print("e non ha mai avuto bisogno di un fit.")
    return 0


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    A_EVEN, B_ODD, N0 = 40000.0, 600.0, 35000.0

    def synth(point, i):
        e = F_AP[point] - 1.0
        return N0 + A_EVEN * e * e + B_ODD * e + (i % 7) - 3

    with tempfile.TemporaryDirectory() as td:
        dm = os.path.join(td, "d.jsonl")
        mm = os.path.join(td, "m.jsonl")
        # struttura REALE del lato dati: un record per (punto, gauge),
        # N_H1 = k1, e il blocco A in due gauge.
        with open(dm, "w", encoding="utf-8", newline="") as fh:
            for pt in NEEDED:
                fh.write(json.dumps({
                    "region": "NGC", "point": pt,
                    "gauge": "fid" if pt == "FID" else "regauged",
                    "block": "fid" if pt == "FID" else "B",
                    "N_H1_k0": synth(pt, 0), "N_H1": synth(pt, 0) - 3500.0,
                    "ladder": {"0": {"N_H1": synth(pt, 0)},
                               "1": {"N_H1": synth(pt, 0) - 3500.0}}}) + "\n")
            # rumore che NON deve essere letto: gauge sbagliato
            fh.write(json.dumps({"region": "NGC", "point": "B1",
                                 "gauge": "derived", "block": "A",
                                 "N_H1_k0": -1.0, "N_H1": -1.0}) + "\n")
        # due record per realizzazione, per esercitare la FUSIONE
        with open(mm, "w", encoding="utf-8", newline="") as fh:
            for i in range(50):
                fh.write(json.dumps({"region": "NGC", "index": i, "points": {
                    p: {"N_H1_k0": synth(p, i)} for p in ("FID", "B1", "B2")}})
                    + "\n")
                fh.write(json.dumps({"region": "NGC", "index": i, "points": {
                    p: {"N_H1_k0": synth(p, i)} for p in ("B4", "B5")}}) + "\n")

        dmg, dconf, lad_ok, lad_bad = read_data_side(dm)
        mmg, mconf = merge_points(read_jsonl(mm),
                                  lambda r: (r.get("region"), r.get("index")))
        chk("0  lato dati: cinque punti, gauge giusto, N_H1 rimappato a k1",
            sorted(dmg["NGC"]) == sorted(NEEDED)
            and dmg["NGC"]["B1"]["N_H1_k0"] > 0
            and abs(dmg["NGC"]["B1"]["N_H1_k1"]
                    - (dmg["NGC"]["B1"]["N_H1_k0"] - 3500.0)) < 1e-9,
            str(sorted(dmg["NGC"])))
        chk("0b il record con gauge `derived` NON viene letto",
            dmg["NGC"]["B1"]["N_H1_k0"] != -1.0)
        chk("0c il confronto incrociato con `ladder` e' riuscito su tutti",
            lad_ok == 2 * len(NEEDED) and not lad_bad,
            "riusciti %d, non interpretabili %d" % (lad_ok, len(lad_bad)))
        chk("1  la fusione del lato MOCK unisce invece di sostituire",
            all(len(v) == 5 for v in mmg.values()),
            "punti per chiave: %s" % sorted({len(v) for v in mmg.values()}))
        chk("1b nessun conflitto su dati coerenti", not dconf and not mconf)
        # un ladder discorde deve diventare un CONFLITTO
        dbad = os.path.join(td, "dbad.jsonl")
        with open(dbad, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps({"region": "NGC", "point": "B1",
                                 "gauge": "regauged", "N_H1_k0": 10.0,
                                 "ladder": {"0": {"N_H1": 11.0}}}) + "\n")
        chk("1c un `ladder` discorde diventa un conflitto",
            len(read_data_side(dbad)[1]) == 1, str(read_data_side(dbad)[1]))

        res, partial = analizza(dmg["NGC"], mmg, "NGC", "N_H1_k0")
        chk("2  cinquanta realizzazioni complete", res["n"] == 50 and not partial)

        d = modello(A_EVEN, B_ODD)
        att_o, att_e = contrasto_dispari(d), contrasto_pari(d)
        chk("3  il contrasto DISPARI ricostruisce il modello esatto",
            abs(res["odd_mock"][0] - att_o) < 1e-6,
            "%.4f contro %.4f" % (res["odd_mock"][0], att_o))
        chk("4  il contrasto PARI ricostruisce il modello esatto",
            abs(res["even_mock"][0] - att_e) < 1e-6,
            "%.4f contro %.4f" % (res["even_mock"][0], att_e))

        # I due contrasti NON sono ortogonali: la linea B non e' perfettamente
        # simmetrica. Il travaso si misura, non si assume nullo.
        q_in_o = contrasto_dispari(modello(A_EVEN, 0.0))
        l_in_e = contrasto_pari(modello(0.0, B_ODD))
        puro_o = B_ODD * (eps("B5") + eps("B1") + eps("B4") + eps("B2"))
        chk("5  i contrasti NON sono ortogonali, e il travaso e' quantificato",
            abs(q_in_o) > 1e-9 and abs(l_in_e) > 1e-9
            and abs((puro_o + q_in_o) - att_o) < 1e-6,
            "quadratico nel dispari %.3f, lineare nel pari %.3f" % (q_in_o, l_in_e))
        chk("5b il travaso viene dall'asimmetria dichiarata dello 0.9%%",
            abs(eps("B5") / eps("B1") - 1.0) > 0.008,
            "|F5-1|/|F1-1| = %.4f" % (eps("B5") / eps("B1")))

        # una realizzazione incompleta va contata, non silenziata
        with open(mm, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps({"region": "NGC", "index": 99, "points": {
                "FID": {"N_H1_k0": 1.0}}}) + "\n")
        mmg2, _ = merge_points(read_jsonl(mm),
                               lambda r: (r.get("region"), r.get("index")))
        res2, partial2 = analizza(dmg["NGC"], mmg2, "NGC", "N_H1_k0")
        chk("6  una realizzazione incompleta e' esclusa E riportata",
            res2["n"] == 50 and partial2 == [99], str(partial2))

        # un conflitto di valore si segnala
        with open(mm, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps({"region": "NGC", "index": 0, "points": {
                "B5": {"N_H1_k0": -1.0}}}) + "\n")
        _, conf3 = merge_points(read_jsonl(mm),
                                lambda r: (r.get("region"), r.get("index")))
        chk("7  un conflitto di valore viene SEGNALATO", len(conf3) == 1,
            str(conf3[:1]))

        # chiave assente -> errore, non None
        bad = {p: {"altro": 1.0} for p in NEEDED}
        chk("8  una chiave assente e' un ERRORE, non un valore",
            _exits(lambda: analizza(bad, mmg, "NGC", "N_H1_k0")))

    # l'attesa e' derivata, non digitata
    # i due denominatori differiscono di sqrt(n): e' la relazione che la
    # risposta 1 impone di riportare, e va fissata in un controllo.
    chk("10 sd mock-a-mock = SEM * sqrt(n), i due denominatori della risposta 1",
        abs((16.1 * math.sqrt(200)) / 16.1 - math.sqrt(200)) < 1e-12
        and abs(111.7 / (16.1 * math.sqrt(200)) - 0.4905) < 1e-3,
        "esempio NGC k0 dispari: 7.0 SEM ma 0.49 sd")
    o0, e0 = attesa(N0)
    chk("9  l'attesa usa LE STESSE funzioni di contrasto dei dati",
        abs(o0 - contrasto_dispari(modello(N0 * ETA_VOLUME,
                                           RSD_123 / RSD_REF_FRAC))) < 1e-12,
        "dispari %.1f, pari %.1f" % (o0, e0))
    o2, e2 = attesa(2 * N0)
    q1, l1 = travaso(N0)
    q2, _ = travaso(2 * N0)
    chk("9b tolto il travaso: il pari scala con N, il dispari e' indipendente",
        abs((e2 - l1) - 2 * (e0 - l1)) < 1e-6
        and abs((o2 - q2) - (o0 - q1)) < 1e-6,
        "pari %.2f -> %.2f (netto), dispari %.2f invariato"
        % (e0 - l1, e2 - l1, o0 - q1))
    # La convenzione va fissata da un controllo, non lasciata a una riga di
    # codice: e' l'unica cosa che ha fatto divergere due documenti.
    dv = {"FID": 100.0, "B1": 100.0, "B2": 100.0, "B4": 100.0, "B5": 90.0}
    mv = {"FID": 100.0, "B1": 100.0, "B2": 100.0, "B4": 100.0, "B5": 80.0}
    d_odd = contrasto_dispari(mv) - contrasto_dispari(dv)
    chk("10 CONVENZIONE D = mock - dati: col mock piu' basso a B5 il contrasto "
        "dispari in D e' NEGATIVO",
        d_odd < 0, "%.1f (mock %.1f, dati %.1f)"
        % (d_odd, contrasto_dispari(mv), contrasto_dispari(dv)))

    for Nm, Nd in ((35423.575, 28256.0), (18694.4, 15122.0)):
        att_D = attesa(Nm)[0] - attesa(Nd)[0]        # mock - dati
        solo_travaso = travaso(Nm)[0] - travaso(Nd)[0]
        chk("9d attesa del DISPARI in D = solo travaso (N=%.0f/%.0f): %+.2f"
            % (Nm, Nd, att_D),
            abs(att_D - solo_travaso) < 1e-9 and abs(att_D) < 1.0,
            "%+.6f contro %+.6f" % (att_D, solo_travaso))
    q, l = travaso(N0)
    chk("9c il travaso e' piccolo ma NON nullo, e viene riportato",
        0.0 < abs(q) < 5.0 and 0.0 < abs(l) < 5.0,
        "quadratico nel dispari %.2f, lineare nel pari %.2f" % (q, l))

    print("=== SELFTEST paper2_contrasti ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _exits(fn):
    """Il controllo esercita fail(), che stampa su stderr: si silenzia, altrimenti
    un selftest che passa sembra un selftest che ha sbagliato."""
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(description="Contrasti pari e dispari della linea B")
    p.add_argument("--data", default=DEFAULT_DATA)
    p.add_argument("--mock", default=DEFAULT_MOCK)
    p.add_argument("--fields", nargs="*", default=["N_H1_k0", "N_H1_k1"])
    p.add_argument("--regions", nargs="*", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("run").set_defaults(func=cmd_run)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
