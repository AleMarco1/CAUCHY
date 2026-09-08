#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_contratto_4_2a.py — il contratto di uscita di 4.2a, verificabile.

Il record 50 elenca in prosa i campi per mock che l'ensemble v2 deve emettere. Qui quell'elenco
diventa una tabella e una verifica: dato un registro, lo strumento dice quali campi ci sono,
su quante realizzazioni, e quali mancano — con il nome della regola che resta inapplicabile.

Due usi, in quest'ordine:
  1. su v1, per sapere cosa manca DAVVERO invece di fidarsi dell'elenco;
  2. su una prova di fumo di v2 a poche realizzazioni, PRIMA delle ~16 ore di TDA.

Non calcola nessuna delle grandezze: verificare e produrre sono mestieri diversi, e questo
strumento non deve poter diventare una seconda implementazione di quantita' che la pipeline
gia' definisce.

Uso:
    python paper2_contratto_4_2a.py contratto
    python paper2_contratto_4_2a.py verifica --file results\\paper1\\n1_spectra_NGC.jsonl ^
        --etichetta "v1 NGC delta" --attese 2000
    python paper2_contratto_4_2a.py verifica --file results\\paper2\\v2_onepoint.jsonl ^
        --filtro region=NGC --senza smoke --attese 2000 --riproduzione 0 --tolleranza-relativa 1e-6
"""

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_ladder_sigma import carica, unione, trova_indice, Rifiuto  # noqa: E402

# campo (chiave piatta, o alternative separate da |), lato, regola che lo richiede
CONTRATTO = [
    ("sigma_in_mask|delta.sigma_in_mask", "delta", "4.2b-1 varianza di delta"),
    ("kurt_in_mask|delta.kurt_in_mask", "delta", "diagnostica di delta (non e' una regola)"),
    ("nu_sigma_in_mask|nu.sigma_in_mask|sigma_in_mask", "nu", "4.2b-3 denominatore di nu99-nu1"),
    ("nu_kurt_in_mask|nu.kurt_in_mask|kurt_in_mask", "nu", "4.2b-2 curtosi in eccesso di nu"),
    ("max_delta|delta.max", "delta", "4.2b-4 massimo di delta"),
    ("nu_p1|nu.p1", "nu", "4.2b-3 nu99-nu1"),
    ("nu_p99|nu.p99", "nu", "4.2b-3 nu99-nu1"),
    ("n_patologici|n_pathological", "delta", "4.2c voxel patologici"),
    ("N_H1_k0|ladder.0.N_H1|points.FID.N_H1_k0", "topologia", "4.3a-b scala di erosione"),
    ("N_H1_k1|ladder.1.N_H1|points.FID.N_H1_k1", "topologia", "4.3a-b scala di erosione"),
    ("N_H1_k2|ladder.2.N_H1|points.FID.N_H1_k2", "topologia", "4.3a-b scala di erosione"),
    ("N_H1_k3|ladder.3.N_H1|points.FID.N_H1_k3", "topologia", "4.3a scala di erosione"),
]

# Valori congelati di v1: chi produce questi campi deve riprodurli prima di riportarne di nuovi.
RIPRODUZIONE = {
    ("NGC", 0, "sigma_in_mask"): 56.953956604003906,
    ("NGC", 0, "kurt_in_mask"): 1048.5986328125,
    ("NGC", 0, "N_H1_k0"): 35318.0,
    ("NGC", 200, "nu_sigma_in_mask"): 2.101883888244629,
    ("NGC", 200, "nu_kurt_in_mask"): 2.710988998413086,
}


# Nomi piatti che compaiono in v1 con DUE significati diversi: in n1_spectra_*.jsonl
# valgono su delta, in n1b_spectra_*.jsonl su nu. Il nome non identifica la grandezza,
# quindi da soli non soddisfano nessun campo: va dichiarato di quale lato sono.
AMBIGUI = {"sigma_in_mask", "kurt_in_mask"}


def risolvi(alternative, presenti, lato=None, lato_piatto=None):
    """Un campo del contratto e' soddisfatto da una qualunque delle sue alternative.
    Le alternative ambigue contano solo se il lato e' stato DICHIARATO e coincide."""
    for nome in alternative.split("|"):
        if nome in AMBIGUI and lato_piatto != lato:
            continue
        if nome in presenti:
            return nome
    return None


def cmd_contratto(args):
    print("CONTRATTO DI USCITA DI 4.2a — per mock, per emisfero, su tutti i 2000\n")
    print(f"{'campo (alternative accettate)':52s} {'lato':10s} regola che lo richiede")
    for alt, lato, regola in CONTRATTO:
        print(f"{alt:52s} {lato:10s} {regola}")
    print("\nnu99 - nu1 in unita' di sigma e' un DERIVATO di nu_p99, nu_p1 e nu_sigma_in_mask:")
    print("non va depositato come campo autonomo, o diventerebbe una seconda implementazione.")
    print("\nValori congelati che chi produce i campi deve riprodurre:")
    for (reg, idx, campo), v in sorted(RIPRODUZIONE.items()):
        print(f"  {reg}  indice {idx:4d}  {campo:22s} {v!r}")
    return 0


def cmd_verifica(args):
    try:
        filtri = [tuple(f.split("=", 1)) for f in (args.filtro or [])]
        if any(len(f) != 2 for f in filtri):
            raise Rifiuto("i filtri si scrivono chiave=valore")
        senza = tuple(args.senza or [])
        piatti, n_tot = carica(args.file, filtri, senza)
        if not piatti:
            raise Rifiuto("nessun record dopo i filtri")
        ki = trova_indice(piatti, args.indice)
        presenti = set()
        for p in piatti:
            presenti.update(p.keys())
        chiavi = [c for c in (risolvi(alt, presenti, lato, args.lato_piatto)
                              for alt, lato, _ in CONTRATTO) if c]
        per_idx = unione(piatti, chiavi, ki)
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    n_real = len(per_idx)
    print(f"file      : {os.path.abspath(args.file)}")
    print(f"etichetta : {args.etichetta}")
    print(f"righe     : {n_tot}  dopo i filtri {len(piatti)}  indice '{ki}'  realizzazioni {n_real}")
    print()

    ambigui_presenti = sorted(AMBIGUI & presenti)
    if ambigui_presenti and args.lato_piatto is None:
        print(f"  NOTA: il file usa nomi piatti ambigui {ambigui_presenti}, che in v1 valgono")
        print(f"        su delta in n1_spectra e su nu in n1b_spectra. Senza --lato-piatto non")
        print(f"        soddisfano nessun campo: dichiaralo, oppure usa nomi con prefisso.")
        print()

    mancanti, parziali, completi = [], [], []
    for alt, lato, regola in CONTRATTO:
        nome = risolvi(alt, presenti, lato, args.lato_piatto)
        if nome is None:
            mancanti.append((alt, lato, regola))
            print(f"  ASSENTE   {alt.split('|')[0]:24s} {lato:10s} -> {regola}")
            continue
        n_cop = sum(1 for v in per_idx.values() if nome in v)
        stato = "ok" if n_cop == n_real else "PARZIALE"
        (completi if n_cop == n_real else parziali).append((nome, n_cop))
        print(f"  {stato:9s} {nome:24s} {lato:10s} {n_cop}/{n_real}")

    print()
    esito = 0
    if args.attese is not None and n_real != args.attese:
        print(f"  realizzazioni {n_real}, attese {args.attese}")
        esito = 2
    if mancanti:
        regole = sorted({r for _, _, r in mancanti})
        print(f"  {len(mancanti)} campi assenti; regole non applicabili:")
        for r in regole:
            print(f"    - {r}")
        esito = 2
    if parziali:
        print(f"  {len(parziali)} campi coperti solo in parte: "
              f"{[n for n, _ in parziali]}")
        esito = 2

    if args.riproduzione is not None:
        idx = args.riproduzione
        attesi = {c: v for (reg, i, c), v in RIPRODUZIONE.items()
                  if i == idx and (args.regione is None or reg == args.regione)}
        if not attesi:
            print(f"  nessun valore congelato per indice {idx}"
                  f"{' in ' + args.regione if args.regione else ''}")
            esito = 2
        for campo, atteso in sorted(attesi.items()):
            voce = next((a, l) for a, l, _ in CONTRATTO if campo in a.split("|"))
            nome = risolvi(voce[0], presenti, voce[1], args.lato_piatto)
            avuto = per_idx.get(idx, {}).get(nome) if nome else None
            if avuto is None:
                print(f"  RIPRODUZIONE  {campo:22s} ASSENTE, atteso {atteso!r}")
                esito = 2
                continue
            if args.tolleranza_relativa:
                ok_v = abs(avuto - atteso) <= args.tolleranza_relativa * max(abs(atteso), 1e-30)
            else:
                ok_v = avuto == atteso
            print(f"  RIPRODUZIONE  {campo:22s} {avuto!r} contro {atteso!r}  "
                  f"{'OK' if ok_v else 'FALLITA'}")
            if not ok_v:
                esito = 2

    print()
    print("CONTRATTO SODDISFATTO" if esito == 0 else "CONTRATTO NON SODDISFATTO")
    return esito


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="contratto_")

    def scrivi(nome, records):
        p = os.path.join(base, nome)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        return p

    completo = []
    for i in range(5):
        completo.append({"index": i, "region": "NGC",
                         "sigma_in_mask": 56.953956604003906 if i == 0 else 50.0 + i,
                         "kurt_in_mask": 1048.5986328125 if i == 0 else 400.0 + i,
                         "nu": {"sigma_in_mask": 2.1 + i, "kurt_in_mask": 2.7 + i,
                                "p1": -5.0 - i, "p99": 3.5 + i},
                         "max_delta": 3000.0 + i, "n_patologici": 4000 - i,
                         "N_H1_k0": 35318.0 if i == 0 else 35000.0 + i,
                         "N_H1_k1": 36000.0 + i, "N_H1_k2": 34000.0 + i,
                         "N_H1_k3": 33000.0 + i})
    f_ok = scrivi("completo.jsonl", completo)

    class A:
        pass

    def a(**kw):
        x = A(); x.file = f_ok; x.filtro = ["region=NGC"]; x.senza = None; x.indice = None
        x.etichetta = "test"; x.attese = 5; x.riproduzione = None; x.regione = "NGC"
        x.tolleranza_relativa = None; x.lato_piatto = "delta"
        for k, v in kw.items():
            setattr(x, k, v)
        return x

    ok("1 registro completo: contratto soddisfatto", cmd_verifica(a()) == 0)
    ok("2 numero di realizzazioni sbagliato: non soddisfatto", cmd_verifica(a(attese=2000)) == 2)

    # Registro tipo v1: solo i due campi di delta, come n1_spectra
    v1 = [{"index": i, "region": "NGC", "sigma_in_mask": 50.0 + i, "kurt_in_mask": 400.0 + i}
          for i in range(5)]
    f_v1 = scrivi("v1_stile.jsonl", v1)
    ok("3 registro tipo v1: non soddisfatto per campi assenti",
       cmd_verifica(a(file=f_v1)) == 2)

    # Copertura parziale: un campo presente solo su alcune realizzazioni
    parziale = [dict(r) for r in completo]
    del parziale[3]["max_delta"]
    f_par = scrivi("parziale.jsonl", parziale)
    ok("4 copertura parziale rilevata", cmd_verifica(a(file=f_par)) == 2)

    # Riproduzione
    ok("5 riproduzione esatta: passa", cmd_verifica(a(riproduzione=0)) == 0)
    rotto = [dict(r) for r in completo]
    rotto[0] = dict(rotto[0]); rotto[0]["kurt_in_mask"] = 1048.6
    f_rotto = scrivi("rotto.jsonl", rotto)
    ok("6 riproduzione fallita: non soddisfatto",
       cmd_verifica(a(file=f_rotto, riproduzione=0)) == 2)
    # 1048.6 contro 1048.5986328125: scarto relativo 1.3e-6. La tolleranza va scelta
    # sapendo questo, non a occhio.
    ok("7 tolleranza 1e-5: la riproduzione passa",
       cmd_verifica(a(file=f_rotto, riproduzione=0, tolleranza_relativa=1e-5)) == 0)
    ok("7b tolleranza 1e-6: appena troppo stretta, fallisce",
       cmd_verifica(a(file=f_rotto, riproduzione=0, tolleranza_relativa=1e-6)) == 2)
    ok("8 tolleranza troppo stretta: torna a fallire",
       cmd_verifica(a(file=f_rotto, riproduzione=0, tolleranza_relativa=1e-12)) == 2)
    ok("9 indice senza valori congelati: non soddisfatto",
       cmd_verifica(a(riproduzione=3)) == 2)

    # Le alternative del contratto: nomi annidati diversi soddisfano lo stesso campo
    annidato = [{"index": i, "region": "NGC",
                 "delta": {"sigma_in_mask": 50.0 + i, "kurt_in_mask": 400.0 + i, "max": 3000.0 + i},
                 "nu": {"sigma_in_mask": 2.1, "kurt_in_mask": 2.7, "p1": -5.0, "p99": 3.5},
                 "n_pathological": 4000,
                 "ladder": {"0": {"N_H1": 35000.0}, "1": {"N_H1": 36000.0},
                            "2": {"N_H1": 34000.0}, "3": {"N_H1": 33000.0}}}
                for i in range(5)]
    f_ann = scrivi("annidato.jsonl", annidato)
    ok("10 nomi annidati alternativi soddisfano il contratto",
       cmd_verifica(a(file=f_ann)) == 0)

    # I due registri diversi danno esiti diversi: la verifica non e' costante
    ok("11 registri diversi, esiti diversi",
       cmd_verifica(a()) == 0 and cmd_verifica(a(file=f_v1)) == 2)

    # Le funzioni di lettura sono quelle di paper2_ladder_sigma
    import paper2_ladder_sigma as mod
    ok("12 lettura e unione importate da paper2_ladder_sigma",
       mod.unione is unione and mod.carica is carica)

    # Lo smoke va escluso anche qui
    con_fumo = completo + [{"index": 0, "region": "NGC", "smoke": True,
                            "sigma_in_mask": 1.0, "kurt_in_mask": 2.0,
                            "nu": {"sigma_in_mask": 1.0, "kurt_in_mask": 1.0,
                                   "p1": -1.0, "p99": 1.0},
                            "max_delta": 1.0, "n_patologici": 1,
                            "N_H1_k0": 1.0, "N_H1_k1": 1.0, "N_H1_k2": 1.0, "N_H1_k3": 1.0}]
    f_fumo = scrivi("con_fumo.jsonl", con_fumo)
    ok("13 lo smoke crea conflitto se non escluso", cmd_verifica(a(file=f_fumo)) == 2)
    ok("14 con --senza smoke il contratto e' soddisfatto",
       cmd_verifica(a(file=f_fumo, senza=["smoke"])) == 0)

    # I nomi piatti ambigui: un file di nu non deve poter soddisfare i campi di delta.
    file_nu = scrivi("stile_n1b.jsonl", [{"idx": i, "sigma_in_mask": 2.1 + i,
                                          "kurt_in_mask": 2.7 + i} for i in range(5)])
    ok("15 nomi piatti senza dichiarazione: nessun campo soddisfatto",
       cmd_verifica(a(file=file_nu, filtro=[], attese=5, lato_piatto=None)) == 2)
    ok("16 dichiarando il lato sbagliato i campi di nu restano assenti",
       cmd_verifica(a(file=file_nu, filtro=[], attese=5, lato_piatto="nu")) == 2)

    # ...e con la dichiarazione giusta soddisfano il lato giusto, che e' un esito DIVERSO.
    def campi_ok(lato_piatto):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_verifica(a(file=file_nu, filtro=[], attese=5, lato_piatto=lato_piatto))
        return buf.getvalue().count("  ok ")
    ok("17 la dichiarazione cambia quali campi risultano soddisfatti",
       campi_ok("delta") == 2 and campi_ok("nu") == 2 and campi_ok(None) == 0)

    ok("18 il contratto elenca dodici campi", len(CONTRATTO) == 12)

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

    p_c = sub.add_parser("contratto")
    p_c.set_defaults(func=cmd_contratto)

    p_v = sub.add_parser("verifica")
    p_v.add_argument("--file", required=True)
    p_v.add_argument("--filtro", action="append", default=None)
    p_v.add_argument("--senza", action="append", default=None)
    p_v.add_argument("--indice", default=None)
    p_v.add_argument("--etichetta", default="")
    p_v.add_argument("--attese", type=int, default=None)
    p_v.add_argument("--riproduzione", type=int, default=None)
    p_v.add_argument("--regione", default=None)
    p_v.add_argument("--tolleranza-relativa", type=float, default=None)
    p_v.add_argument("--lato-piatto", choices=("delta", "nu"), default=None,
                     help="dichiara a quale lato si riferiscono i nomi piatti "
                          "sigma_in_mask e kurt_in_mask in QUESTO file")
    p_v.set_defaults(func=cmd_verifica)

    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
