#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_ladder_sigma.py — rev.2 di paper2_giunzione_ladder.

Ricompone la scala di erosione PER REALIZZAZIONE dal registro di fase 3 e ne misura sigma(P).

Cosa e' cambiato rispetto alla rev.1, e perche':
  - i quattro livelli del punto FID stanno TUTTI in fase3_mock.jsonl, quindi non serve una
    giunzione fra registri: serve l'UNIONE dentro un registro solo (record 49);
  - quel file contiene ENTRAMBI gli emisferi nel campo `region`: senza filtro l'indice 5 di
    NGC e l'indice 5 di SGC finirebbero nella stessa realizzazione. I filtri sono quindi
    obbligatori quando un campo discriminante esiste;
  - il lato dati non si digita: si legge da fase3.jsonl (`ladder.k.N_H1`), selezionando UN
    solo record per filtri. Se i filtri ne selezionano zero o piu' di uno, lo strumento si ferma.

P e sigma(P) sono importati da paper2_prominenza_v1: unica implementazione della grandezza.

Uso:
    python paper2_ladder_sigma.py selftest
    python paper2_ladder_sigma.py misura ^
        --mock-file results\\paper2\\fase3_mock.jsonl --filtro region=NGC ^
        --k0 points.FID.N_H1_k0 --k1 points.FID.N_H1_k1 --k2 points.FID.N_H1_k2 ^
        --desi-file results\\paper2\\fase3.jsonl --desi-filtro region=NGC --desi-filtro point=FID ^
        --desi-k0 ladder.0.N_H1 --desi-k1 ladder.1.N_H1 --desi-k2 ladder.2.N_H1 ^
        --gate-indice 0 --gate-k0 35318 --etichetta NGC --out logs\\ladder_sigma.jsonl
"""

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_prominenza_v1 import prominenza  # noqa: E402  unica implementazione

CANDIDATI_INDICE = ("index", "idx", "mock", "mock_id", "mock_index", "realisation",
                    "realization", "seed", "i")


class Rifiuto(Exception):
    pass


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(flatten(v, key))
            elif not isinstance(v, list):
                out[key] = v
    return out


def carica(path, filtri, senza=()):
    """Legge il registro, applica i filtri, restituisce i record piatti.
    `senza` tiene solo i record in cui la chiave e' ASSENTE: serve per le prove di fumo,
    che stanno nello stesso registro della produzione e si distinguono solo per una chiave
    in piu'."""
    if not os.path.isfile(path):
        raise Rifiuto(f"file inesistente: {path}")
    piatti, n_tot = [], 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                raise Rifiuto(f"{os.path.basename(path)} riga {i}: JSON malformato")
            n_tot += 1
            p = flatten(rec)
            if all(k in p and str(p[k]) == v for k, v in filtri) \
                    and all(k not in p for k in senza):
                piatti.append(p)
    return piatti, n_tot


SOSPETTI = ("region", "point", "gauge", "gauge_version", "schema", "tag", "block",
            "pass", "gate", "smoke", "pad_mode")


def campi_discriminanti(piatti, esclusi=()):
    """Campi che partizionano il registro: se non sono filtrati l'unione fonde cose diverse.

    L'ASSENZA di una chiave conta come valore. Senza questa regola una prova di fumo marcata
    da una sola chiave booleana presente su pochi record passa inosservata, perche' i valori
    distinti sono uno solo."""
    fuori = []
    for k in SOSPETTI:
        if k in esclusi:
            continue
        valori = {str(p[k]) if k in p else "<assente>" for p in piatti}
        if len(valori) > 1:
            n_pres = sum(1 for p in piatti if k in p)
            fuori.append((k, sorted(valori)[:6], n_pres, len(piatti) - n_pres))
    return fuori


def trova_indice(piatti, dichiarata=None):
    if not piatti:
        raise Rifiuto("nessun record dopo i filtri")
    if dichiarata:
        mancanti = sum(1 for p in piatti if dichiarata not in p)
        if mancanti:
            raise Rifiuto(f"la chiave indice '{dichiarata}' manca in {mancanti} record su {len(piatti)}")
        return dichiarata
    cand = [c for c in CANDIDATI_INDICE
            if all(c in p and isinstance(p[c], int) and not isinstance(p[c], bool) for p in piatti)]
    if len(cand) == 0:
        raise Rifiuto(f"nessuna chiave indice riconosciuta fra {CANDIDATI_INDICE}; usa --indice")
    if len(cand) > 1:
        raise Rifiuto(f"chiave indice ambigua fra {cand}; usa --indice")
    return cand[0]


def unione(piatti, chiavi, chiave_indice):
    """Unione, mai last-wins. Valori diversi per la stessa (realizzazione, chiave) = conflitto."""
    per_idx, conflitti = {}, []
    for p in piatti:
        idx = p[chiave_indice]
        slot = per_idx.setdefault(idx, {})
        for k in chiavi:
            v = p.get(k)
            if v is None:
                continue
            v = float(v)
            if k in slot and slot[k] != v:
                conflitti.append((idx, k, slot[k], v))
            else:
                slot[k] = v
    if conflitti:
        idx, k, a, b = conflitti[0]
        raise Rifiuto(f"{len(conflitti)} conflitti nell'unione; primo: idx {idx}, chiave {k}, "
                      f"{a} contro {b}. Un campo discriminante non e' filtrato, oppure due run "
                      f"hanno scritto valori diversi per la stessa realizzazione.")
    return per_idx


def valore_unico(path, filtri, chiavi):
    piatti, n_tot = carica(path, filtri)
    if len(piatti) != 1:
        raise Rifiuto(f"{os.path.basename(path)}: i filtri selezionano {len(piatti)} record su "
                      f"{n_tot}, ne serve esattamente 1")
    p = piatti[0]
    fuori = [k for k in chiavi if k not in p or p[k] is None]
    if fuori:
        raise Rifiuto(f"{os.path.basename(path)}: il record selezionato non ha {fuori}")
    return [float(p[k]) for k in chiavi], n_tot


def cmd_misura(args):
    try:
        filtri = [tuple(f.split("=", 1)) for f in (args.filtro or [])]
        if any(len(f) != 2 for f in filtri):
            raise Rifiuto("i filtri si scrivono chiave=valore")
        senza = tuple(args.senza or [])
        piatti, n_tot = carica(args.mock_file, filtri, senza)
        print(f"mock     : {os.path.basename(args.mock_file)}  righe {n_tot}  "
              f"dopo i filtri {len(piatti)}  filtri {filtri or 'nessuno'}"
              f"{'  senza ' + str(list(senza)) if senza else ''}")
        if not piatti:
            raise Rifiuto("i filtri non selezionano nessun record")

        fuori = campi_discriminanti(piatti, esclusi=[k for k, _ in filtri] + list(senza))
        if fuori and not args.ignora_discriminanti:
            desc = "; ".join(f"{k} = {v} (presente su {np}, assente su {na})"
                             for k, v, np, na in fuori)
            raise Rifiuto(f"campi discriminanti non filtrati: {desc}. Senza filtro l'unione "
                          f"fonderebbe realizzazioni diverse. Aggiungi --filtro, oppure "
                          f"--ignora-discriminanti se sai perche'.")

        ki = trova_indice(piatti, args.indice)
        chiavi = [args.k0, args.k1, args.k2]
        per_idx = unione(piatti, chiavi, ki)
        copertura = {k: sum(1 for v in per_idx.values() if k in v) for k in chiavi}
        print(f"indice   : '{ki}'  realizzazioni {len(per_idx)}")
        for k in chiavi:
            print(f"           {copertura[k]:5d}  {k}")

        completi = sorted(i for i, v in per_idx.items() if all(k in v for k in chiavi))
        if len(completi) < 3:
            raise Rifiuto(f"solo {len(completi)} realizzazioni hanno tutti e tre i livelli")
        print(f"completi : {len(completi)}")

        if args.gate_indice is not None:
            v = per_idx.get(args.gate_indice, {}).get(args.k0)
            if v is None:
                raise Rifiuto(f"cancello di riproduzione: l'indice {args.gate_indice} non ha {args.k0}")
            if v != args.gate_k0:
                raise Rifiuto(f"cancello di riproduzione FALLITO: indice {args.gate_indice} "
                              f"da' {v:.0f}, atteso {args.gate_k0:.0f}")
            print(f"cancello : indice {args.gate_indice} riproduce {args.gate_k0:.0f}  OK")

        desi_filtri = [tuple(f.split("=", 1)) for f in (args.desi_filtro or [])]
        (d0, d1, d2), n_desi = valore_unico(args.desi_file, desi_filtri,
                                            [args.desi_k0, args.desi_k1, args.desi_k2])
        print(f"dati     : {os.path.basename(args.desi_file)}  {n_desi} record, 1 selezionato  "
              f"N_H1 DESI k0 {d0:.0f}  k1 {d1:.0f}  k2 {d2:.0f}")

        N0 = [per_idx[i][args.k0] for i in completi]
        N1 = [per_idx[i][args.k1] for i in completi]
        N2 = [per_idx[i][args.k2] for i in completi]
        r = prominenza(N0, N1, N2, d0, d1, d2)

        if args.bersaglio_k0_pp is not None:
            scarto = abs(r["D_k0_pp"] - args.bersaglio_k0_pp)
            if scarto > args.bersaglio_tolleranza_pp:
                raise Rifiuto(f"bersaglio k=0: ricalcolato {r['D_k0_pp']:.4f} pp contro "
                              f"{args.bersaglio_k0_pp} pp, scarto {scarto:.4f}")
            print(f"bersaglio: D(k=0) {r['D_k0_pp']:.4f} pp  OK")
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    print()
    print(f"{args.etichetta}  n = {r['n']}")
    print(f"  deficit  k0 {r['D_k0_pp']:7.3f} pp   k1 {r['D_k1_pp']:7.3f} pp   k2 {r['D_k2_pp']:7.3f} pp")
    print(f"  P        {r['P_pp']:+.4f} pp = lato mock {r['P_corretta_pp']:+.4f} + "
          f"residuo a mock lineare {r['P_curvatura_pp']:+.4f}")
    print(f"  scarti   mock(k1) - lineare {r['mock_dev_k1']:+.1f} gen   "
          f"DESI(k1) - lineare {r['desi_dev_k1']:+.1f} gen")
    print(f"  sigma    appaiata {r['sem_appaiata_pp']:.4f}   jackknife {r['sem_jackknife_pp']:.4f}"
          f"   non appaiata {r['sem_non_appaiata_pp']:.4f}  (x{r['guadagno_appaiamento']:.1f})")
    print(f"  correlaz k0-k1 {r['r_k0_k1']:.4f}   k1-k2 {r['r_k1_k2']:.4f}")
    print(f"  sigma    lato mock, appaiata {r['sem_corretta_pp']:.4f}")
    print(f"  SOGLIE su P lato mock: successo < {r['soglia_successo_corretta_pp']:.4f} pp   "
          f"fallimento > {r['soglia_fallimento_corretta_pp']:.4f} pp")
    print(f"  le due zone distano {r['separazione_zone_corretta_sigma']:.1f} sigma", end="  ")
    print("[REGOLA VALIDA]" if r["separazione_zone_corretta_sigma"] >= 3.0
          else "[REGOLA NON DECIDE]")
    print(f"  (su P totale sarebbero {r['soglia_successo_pp']:.4f} e "
          f"{r['soglia_fallimento_pp']:.4f} pp, ma includono il lato dati che v2 non tocca)")
    scarto = abs(r["sem_appaiata_pp"] - r["sem_jackknife_pp"]) / max(r["sem_appaiata_pp"], 1e-12)
    print(f"  appaiata vs jackknife: scarto {scarto:.3%}",
          "[concordi]" if scarto < 0.05 else "[DISCORDI]")

    if args.out:
        rec = dict(r)
        rec.update({"etichetta": args.etichetta, "n_completi": len(completi),
                    "mock_file": os.path.abspath(args.mock_file), "filtri": filtri,
                    "indice": ki, "chiavi": chiavi,
                    "desi_file": os.path.abspath(args.desi_file), "desi_filtri": desi_filtri,
                    "desi": [d0, d1, d2],
                    "gate_indice": args.gate_indice, "gate_k0": args.gate_k0})
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  registro: {os.path.abspath(args.out)}")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="ladder_sigma_")

    def scrivi(nome, records):
        p = os.path.join(base, nome)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")
        return p

    # Due emisferi nello stesso file, quattro livelli spezzati su due run.
    basi = {"NGC": [35000 + 137 * i - 3 * i * i for i in range(30)],
            "SGC": [18000 + 91 * i - 2 * i * i for i in range(30)]}
    off = {"k0": 0.0, "k1": 900.0, "k2": 200.0}
    mock = []
    for reg, bs in basi.items():
        for i, b in enumerate(bs):
            mock.append({"index": i, "region": reg, "points": {"FID": {
                "N_H1_k0": b + off["k0"], "N_H1_k1": b + off["k1"]}}})
        for i, b in enumerate(bs):
            mock.append({"index": i, "region": reg, "points": {"FID": {
                "N_H1_k2": b + off["k2"]}}})
    f_mock = scrivi("fase3_mock.jsonl", mock)

    desi = [{"region": r, "point": p,
             "ladder": {"0": {"N_H1": 28000.0 if r == "NGC" else 15000.0},
                        "1": {"N_H1": 28900.0 if r == "NGC" else 15900.0},
                        "2": {"N_H1": 28200.0 if r == "NGC" else 15200.0}}}
            for r in ("NGC", "SGC") for p in ("FID", "B1")]
    f_desi = scrivi("fase3.jsonl", desi)

    class A:
        pass

    def a_misura(**kw):
        a = A()
        a.mock_file = f_mock; a.filtro = ["region=NGC"]; a.indice = None
        a.k0, a.k1, a.k2 = "points.FID.N_H1_k0", "points.FID.N_H1_k1", "points.FID.N_H1_k2"
        a.desi_file = f_desi; a.desi_filtro = ["region=NGC", "point=FID"]
        a.desi_k0, a.desi_k1, a.desi_k2 = "ladder.0.N_H1", "ladder.1.N_H1", "ladder.2.N_H1"
        a.gate_indice = None; a.gate_k0 = None; a.senza = None
        a.bersaglio_k0_pp = None; a.bersaglio_tolleranza_pp = 0.05
        a.ignora_discriminanti = False
        a.etichetta = "TEST"; a.out = None
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    ok("1 misura con filtro di emisfero: esito 0", cmd_misura(a_misura()) == 0)

    # Prove di fumo nello stesso registro, marcate da una sola chiave presente su pochi record.
    fumo = [{"index": i, "region": "NGC", "smoke": True,
             "points": {"FID": {"N_H1_k0": basi["NGC"][i] + 220,
                                "N_H1_k1": basi["NGC"][i] + 1120}}} for i in range(3)]
    f_fumo = scrivi("con_fumo.jsonl", mock + fumo)
    ok("1b lo smoke e' rilevato come discriminante malgrado un solo valore distinto",
       cmd_misura(a_misura(mock_file=f_fumo)) == 2)
    ok("1c con --senza smoke la misura passa",
       cmd_misura(a_misura(mock_file=f_fumo, senza=["smoke"])) == 0)
    ok("1d senza il filtro negativo si arriva al conflitto",
       cmd_misura(a_misura(mock_file=f_fumo, ignora_discriminanti=True)) == 2)

    # Senza filtro di regione i due emisferi collidono sull'indice: DEVE fermarsi.
    ok("2 senza filtro region: rifiuto sul campo discriminante",
       cmd_misura(a_misura(filtro=[])) == 2)
    ok("3 forzando --ignora-discriminanti si arriva al conflitto dell'unione",
       cmd_misura(a_misura(filtro=[], ignora_discriminanti=True)) == 2)

    # Il filtro cambia il risultato: NGC e SGC devono dare numeri diversi.
    out = os.path.join(base, "logs", "ls.jsonl")
    cmd_misura(a_misura(out=out))
    cmd_misura(a_misura(filtro=["region=SGC"], desi_filtro=["region=SGC", "point=FID"],
                        etichetta="SGC", out=out))
    with open(out, encoding="utf-8") as fh:
        righe = [json.loads(l) for l in fh if l.strip()]
    ok("4 due righe nel registro", len(righe) == 2)
    ok("5 i due emisferi danno P diverse", abs(righe[0]["P_pp"] - righe[1]["P_pp"]) > 0.01)
    ok("6 trenta realizzazioni per emisfero", all(r["n_completi"] == 30 for r in righe))

    # Unione: 60 righe per emisfero -> 30 realizzazioni con tre livelli
    piatti, _ = carica(f_mock, [("region", "NGC")])
    per_idx = unione(piatti, ["points.FID.N_H1_k0", "points.FID.N_H1_k1",
                              "points.FID.N_H1_k2"], "index")
    ok("7 unione: 60 righe -> 30 realizzazioni complete", len(piatti) == 60
       and len(per_idx) == 30 and all(len(v) == 3 for v in per_idx.values()))

    # Lato dati: i filtri devono selezionare esattamente un record
    try:
        valore_unico(f_desi, [("region", "NGC")], ["ladder.0.N_H1"])
        ok("8 lato dati ambiguo: rifiuto", False)
    except Rifiuto as e:
        ok("8 lato dati ambiguo: rifiuto", "selezionano 2 record" in str(e))
    try:
        valore_unico(f_desi, [("region", "XXX")], ["ladder.0.N_H1"])
        ok("9 lato dati vuoto: rifiuto", False)
    except Rifiuto as e:
        ok("9 lato dati vuoto: rifiuto", "selezionano 0 record" in str(e))

    # Cancello di riproduzione
    ok("10 cancello giusto: passa",
       cmd_misura(a_misura(gate_indice=0, gate_k0=float(basi["NGC"][0]))) == 0)
    ok("11 cancello sbagliato: rifiuto",
       cmd_misura(a_misura(gate_indice=0, gate_k0=float(basi["NGC"][0]) + 1)) == 2)

    # Bersaglio
    ok("12 bersaglio sbagliato: rifiuto", cmd_misura(a_misura(bersaglio_k0_pp=99.0)) == 2)

    # Conflitto vero: due run che scrivono valori diversi per la stessa realizzazione
    f_conf = scrivi("conflitto.jsonl", mock + [{"index": 3, "region": "NGC",
                                                "points": {"FID": {"N_H1_k1": 1.0}}}])
    ok("13 conflitto nell'unione: rifiuto", cmd_misura(a_misura(mock_file=f_conf)) == 2)

    # P e sigma vengono dal modulo importato, e rispondono agli ingressi
    import paper2_prominenza_v1 as mod
    ok("14 P importata da paper2_prominenza_v1", "paper2_prominenza_v1" in mod.__file__)
    ok("15 registro senza CRLF", b"\r\n" not in open(out, "rb").read())

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print(f"selftest: {passati}/{len(controlli)}")
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_m = sub.add_parser("misura")
    p_m.add_argument("--mock-file", required=True)
    p_m.add_argument("--filtro", action="append", default=None, help="chiave=valore, ripetibile")
    p_m.add_argument("--senza", action="append", default=None,
                     help="tieni solo i record SENZA questa chiave, ripetibile")
    p_m.add_argument("--indice", default=None)
    p_m.add_argument("--k0", required=True)
    p_m.add_argument("--k1", required=True)
    p_m.add_argument("--k2", required=True)
    p_m.add_argument("--desi-file", required=True)
    p_m.add_argument("--desi-filtro", action="append", default=None)
    p_m.add_argument("--desi-k0", required=True)
    p_m.add_argument("--desi-k1", required=True)
    p_m.add_argument("--desi-k2", required=True)
    p_m.add_argument("--gate-indice", type=int, default=None)
    p_m.add_argument("--gate-k0", type=float, default=None)
    p_m.add_argument("--bersaglio-k0-pp", type=float, default=None)
    p_m.add_argument("--bersaglio-tolleranza-pp", type=float, default=0.05)
    p_m.add_argument("--ignora-discriminanti", action="store_true")
    p_m.add_argument("--etichetta", default="")
    p_m.add_argument("--out", default=None)
    p_m.set_defaults(func=cmd_misura)

    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
