#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_pareggi.py — dove stanno i voxel in pareggio, e cosa ne segue per P1-7.

LA DOMANDA
----------
La Tabella 12 del Paper 1 riporta, sotto le etichette «multiply-occupied voxel
fraction» e «maximum voxel multiplicity», due numeri che vengono in realta' dalla
sezione D di paper1_rev_par_bundle.py — «PAREGGI PRODOTTI DAL CLIP A -1+1e-3» —
e contano voxel che condividono lo STESSO VALORE del campo lisciato nu, non
galassie che condividono una cella:

    u, cnt = np.unique(nu[mask], return_counts=True)
    dup = (cnt[cnt > 1].sum() - (cnt > 1).sum()) / nu[mask].size    # 1.654%
    top = int(cnt.max())                                            # 52

Il §9 ci costruisce sopra un'affermazione fisica: «the data contain
concentrations — rich clusters, dense fingers of God — that an HOD with
uniformly distributed satellites does not produce».

QUESTO STRUMENTO NON CONFRONTA DUE NUMERI RIASSUNTIVI: GUARDA DOVE STANNO
-------------------------------------------------------------------------
Confrontare la frazione di pareggi con una frazione di occupazione sarebbe un
confronto fra due medie. La domanda ha una risposta molto piu' netta a livello
di VOXEL: i voxel in pareggio, dove sono?

  in regioni DENSE   -> la lettura del §9 e' confermata, e P1-7 diventa una
                        conferma invece di un'attenuazione;
  in regioni VUOTE   -> e' smentita. E c'e' un candidato ovvio: il pavimento
                        del clip. Dove non c'e' nessuna galassia delta vale -1,
                        il clip lo porta a -1+1e-3, e log(1e-3) e' lo stesso
                        numero in ogni voxel vuoto. Se il pareggio a
                        molteplicita' 52 sta li', conta il VUOTO, non gli
                        ammassi — e l'affermazione va rovesciata, non attenuata.

Il campo e' lisciato, quindi il pavimento esatto sopravvive solo dove
l'intorno e' anch'esso vuoto: e' una previsione verificabile, non una
supposizione.

COSA MISURA
-----------
Per ogni classe di voxel — in pareggio contro non in pareggio — riporta la
distribuzione di delta, di field_r (che e' la copertura dei random, cioe' il
volume effettivo) e di nu. E per il pareggio piu' grande dice a QUALE valore
sta, se e' il minimo del campo, e quanti dei suoi voxel hanno delta al
pavimento del clip.

Lo stesso su un mock, per il contrasto 52 contro 3.

USO
    python src\\paper2_pareggi.py selftest
    python src\\paper2_pareggi.py esamina --region NGC
    python src\\paper2_pareggi.py esamina --region NGC --mock 1999

Uscita: 0 sempre che i file esistano. Il verdetto sta nel testo e nel JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

CLIP = -1.0 + 1e-3          # il pavimento, da paper1_remap e da rev1_r14_monotone
N_VOXEL = {"NGC": 307805, "SGC": 172225}
MASCHERA = {"NGC": "bgs_ngc_mask_128.npy", "SGC": "bgs_sgc_mask_128.npy"}
# I valori della Tabella 12, da riscontrare
TAB12 = {"NGC": {"frazione": 0.01654, "molteplicita": 52}}
ROOT_DEFAULT = "."


def percorsi(root, region):
    d = Path(root)
    return {"nu_congelata": d / "results" / "paper1" / ("n1_desi_nu_%s.npy" % region),
            "nu_nuova": d / "results" / "paper2" / ("n1_desi_nu_%s.npy" % region),
            "cubi": d / "results" / "phase8_test2_fields",
            "maschera": d / "data" / "processed" / "phase6_fields" / MASCHERA[region],
            "out": d / "results" / "paper2" / ("pareggi_%s.json" % region)}


def statistiche_pareggi(v):
    """Da un vettore di valori: frazione di duplicati e molteplicita' massima,
    con la STESSA formula di paper1_rev_par_bundle.py sezione D."""
    u, cnt = np.unique(v, return_counts=True)
    dup = float((cnt[cnt > 1].sum() - (cnt > 1).sum()) / v.size)
    return {"n_voxel": int(v.size), "n_distinti": int(u.size),
            "frazione_duplicati": dup, "molteplicita_max": int(cnt.max())}, u, cnt


def maschera_pareggi(v, u, cnt):
    """Booleano: quali elementi di v stanno in un gruppo di molteplicita' > 1."""
    ripetuti = u[cnt > 1]
    return np.isin(v, ripetuti)


def riassunto(x, nome):
    x = np.asarray(x, float)
    if x.size == 0:
        return {"nome": nome, "n": 0}
    q = np.percentile(x, [1, 25, 50, 75, 99])
    return {"nome": nome, "n": int(x.size), "media": float(x.mean()),
            "sd": float(x.std(ddof=1)) if x.size > 1 else 0.0,
            "min": float(x.min()), "p1": float(q[0]), "p25": float(q[1]),
            "mediana": float(q[2]), "p75": float(q[3]), "p99": float(q[4]),
            "max": float(x.max())}


def esamina(root, region, mock=None, out_path=None):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402

    P = percorsi(root, region)
    mask = np.load(P["maschera"]).astype(bool)
    if int(mask.sum()) != N_VOXEL[region]:
        raise SystemExit("RIFIUTO: %d voxel, attesi %d"
                         % (int(mask.sum()), N_VOXEL[region]))

    print("=" * 78)
    print("DOVE STANNO I VOXEL IN PAREGGIO  |  %s  |  %s"
          % (region, "mock %s" % mock if mock is not None else "DESI"))
    print("=" * 78)

    G = P1.setup_region(M, region, root / "data" / "raw" / "desi_dr1",
                        root / "data" / "processed" / "phase6_fields")
    field_r = np.asarray(G["field_r"], float)

    if mock is None:
        cache = (P["nu_congelata"] if P["nu_congelata"].is_file() else P["nu_nuova"])
        if not cache.is_file():
            raise SystemExit("RIFIUTO: campo nu di DESI assente: %s" % cache)
        nu = np.load(cache)
        alpha = G["sum_wd"] / G["sum_wr"]
        delta = np.asarray(P1.compute_delta(G["field_d"], field_r, alpha,
                                            mask, M.NGRID), dtype=np.float64)
        etichetta = "DESI"
    else:
        fp = P["cubi"] / ("test2_%04d.npz" % int(mock))
        if not fp.is_file():
            raise SystemExit("RIFIUTO: cubo inesistente: %s" % fp)
        with np.load(fp) as Z:
            nu = np.asarray(Z["delta"])
        delta = None
        etichetta = fp.name

    vi = nu[mask]
    st, u, cnt = statistiche_pareggi(vi)
    print("  %s: %d voxel, %d valori distinti" % (etichetta, st["n_voxel"],
                                                  st["n_distinti"]))
    print("  duplicati %.3f%%   molteplicita' massima %d"
          % (100 * st["frazione_duplicati"], st["molteplicita_max"]))
    if mock is None and region in TAB12:
        t = TAB12[region]
        print("  Tabella 12 riporta %.2f%% e %d -> %s"
              % (100 * t["frazione"], t["molteplicita"],
                 "COMBACIA" if (abs(st["frazione_duplicati"] - t["frazione"]) < 5e-5
                                and st["molteplicita_max"] == t["molteplicita"])
                 else "NON combacia"))

    # --- dove stanno --------------------------------------------------------
    pari = maschera_pareggi(vi, u, cnt)
    print("\n--- i voxel in pareggio, contro gli altri ---")
    campi = [("nu", vi)]
    campi.append(("field_r", field_r[mask]))
    if delta is not None:
        campi.append(("delta", delta[mask]))
    conf = {}
    for nome, x in campi:
        a, b = riassunto(x[pari], "in pareggio"), riassunto(x[~pari], "non in pareggio")
        conf[nome] = {"in_pareggio": a, "non_in_pareggio": b}
        print("  %-8s  in pareggio: mediana %12.5g  [p1 %11.4g, p99 %11.4g]"
              % (nome, a["mediana"], a["p1"], a["p99"]))
        print("  %-8s  gli altri  : mediana %12.5g  [p1 %11.4g, p99 %11.4g]"
              % ("", b["mediana"], b["p1"], b["p99"]))

    # --- il gruppo piu' grande ---------------------------------------------
    top_i = int(np.argmax(cnt))
    val = float(u[top_i])
    sel = vi == val
    print("\n--- il gruppo piu' grande: %d voxel allo stesso valore ---" % cnt[top_i])
    print("  valore di nu   : %.12g" % val)
    print("  e' il MINIMO del campo in maschera: %s   (min %.12g)"
          % (val == float(vi.min()), float(vi.min())))
    print("  rango del valore fra i distinti: %d su %d (dal basso)"
          % (int((u < val).sum()) + 1, u.size))
    gruppo = {"molteplicita": int(cnt[top_i]), "valore_nu": val,
              "e_il_minimo": bool(val == float(vi.min()))}
    if delta is not None:
        dsel = delta[mask][sel]
        al_pavimento = int((dsel <= CLIP + 1e-9).sum())
        gruppo.update({"delta_mediano": float(np.median(dsel)),
                       "delta_min": float(dsel.min()),
                       "delta_max": float(dsel.max()),
                       "n_al_pavimento_del_clip": al_pavimento,
                       "frazione_al_pavimento": al_pavimento / dsel.size})
        print("  delta nei suoi voxel: mediana %.6g, da %.6g a %.6g"
              % (np.median(dsel), dsel.min(), dsel.max()))
        print("  al PAVIMENTO del clip (delta <= %.6g): %d su %d (%.1f%%)"
              % (CLIP, al_pavimento, dsel.size, 100 * al_pavimento / dsel.size))
        fr = field_r[mask][sel]
        gruppo["field_r_mediano"] = float(np.median(fr))
        print("  field_r nei suoi voxel: mediana %.4g, contro %.4g del campo"
              % (np.median(fr), np.median(field_r[mask])))

    # --- il verdetto sul meccanismo ----------------------------------------
    verdetto = None
    if delta is not None:
        fr_pari = float(np.median(field_r[mask][pari]))
        fr_altri = float(np.median(field_r[mask][~pari]))
        d_pari = float(np.median(delta[mask][pari]))
        d_altri = float(np.median(delta[mask][~pari]))
        vuoti = gruppo.get("frazione_al_pavimento", 0.0)
        print("\n--- il meccanismo ---")
        if vuoti > 0.5:
            verdetto = "VUOTO"
            print("  Il gruppo piu' grande sta al PAVIMENTO DEL CLIP: sono voxel")
            print("  senza galassie, non concentrazioni. La lettura del §9 va")
            print("  ROVESCIATA, non attenuata: il numero misura il vuoto.")
        elif d_pari > d_altri and fr_pari < fr_altri:
            verdetto = "DENSO"
            print("  I voxel in pareggio hanno delta piu' alto e copertura piu'")
            print("  bassa: e' compatibile con la lettura del §9, che diventa una")
            print("  CONFERMA. Resta da misurare l'occupazione vera in galassie.")
        else:
            verdetto = "MISTO"
            print("  delta in pareggio %.4g contro %.4g, field_r %.4g contro %.4g:"
                  % (d_pari, d_altri, fr_pari, fr_altri))
            print("  ne' il vuoto ne' la densita' spiegano il pareggio da soli.")
            print("  Serve l'occupazione vera in galassie per decidere.")

    rec = {"schema": "paper2_pareggi_v1", "region": region,
           "campo": etichetta, "mock": mock,
           "utc": datetime.now(timezone.utc).isoformat(),
           "statistiche": st, "per_classe": conf, "gruppo_massimo": gruppo,
           "clip": CLIP, "verdetto_meccanismo": verdetto}
    dest = Path(out_path) if out_path else P["out"]
    if mock is not None:
        dest = dest.with_name(dest.stem + "_mock%04d" % int(mock) + dest.suffix)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rec, indent=2, ensure_ascii=True), encoding="utf-8")
    print("\n  scritto: %s" % dest)
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

    print("selftest paper2_pareggi")

    chk("il pavimento del clip e' quello di paper1_remap", CLIP == -1.0 + 1e-3)
    chk("i valori della Tabella 12 sono quelli letti dalla bozza",
        TAB12["NGC"] == {"frazione": 0.01654, "molteplicita": 52})

    # la formula dei pareggi: la STESSA di rev_par_bundle sezione D
    v = np.array([1.0, 1.0, 1.0, 2.0, 2.0, 3.0, 4.0])
    st, u, cnt = statistiche_pareggi(v)
    chk("valori distinti contati", st["n_distinti"] == 4)
    chk("molteplicita' massima", st["molteplicita_max"] == 3)
    # dup = (somma dei conteggi>1 meno il numero di gruppi) / n = (3+2-2)/7
    chk("la frazione e' (somma dei ripetuti meno i gruppi) su n",
        abs(st["frazione_duplicati"] - 3.0 / 7) < 1e-12, st["frazione_duplicati"])
    chk("senza duplicati la frazione e' zero",
        statistiche_pareggi(np.array([1.0, 2.0, 3.0]))[0]["frazione_duplicati"] == 0.0)
    chk("con tutti uguali la molteplicita' e' n",
        statistiche_pareggi(np.full(9, 7.0))[0]["molteplicita_max"] == 9)

    m = maschera_pareggi(v, u, cnt)
    chk("la maschera prende i tre 1.0 e i due 2.0, non il 3 e il 4",
        list(m) == [True, True, True, True, True, False, False], list(m))
    chk("e ne conta cinque", int(m.sum()) == 5)

    # il caso che decide: il pavimento del clip
    nu_finto = np.array([-6.9077553, -6.9077553, -6.9077553, 0.5, 1.2, -0.3])
    st2, u2, c2 = statistiche_pareggi(nu_finto)
    top = int(np.argmax(c2))
    chk("il gruppo piu' grande e' il pavimento, ed e' il MINIMO del campo",
        c2[top] == 3 and float(u2[top]) == float(nu_finto.min()))
    d_finto = np.array([CLIP, CLIP, CLIP, 2.0, 5.0, 0.1])
    sel = nu_finto == u2[top]
    frac = float((d_finto[sel] <= CLIP + 1e-9).sum()) / int(sel.sum())
    chk("e i suoi voxel hanno delta al pavimento: frazione 1.0", frac == 1.0)
    chk("con frazione oltre 0.5 il verdetto e' VUOTO", frac > 0.5)

    # il caso opposto: pareggi in voxel densi
    d_denso = np.array([30.0, 30.0, 30.0, 2.0, 5.0, 0.1])
    frac2 = float((d_denso[sel] <= CLIP + 1e-9).sum()) / int(sel.sum())
    chk("con delta alti la frazione al pavimento e' zero", frac2 == 0.0)
    chk("e allora il verdetto NON puo' essere VUOTO", not frac2 > 0.5)

    r = riassunto(np.arange(101, dtype=float), "x")
    chk("il riassunto porta i percentili estremi", r["p1"] == 1.0 and r["p99"] == 99.0)
    chk("e la mediana", r["mediana"] == 50.0)
    chk("un insieme vuoto non solleva", riassunto(np.array([]), "y")["n"] == 0)

    P = percorsi("/b", "SGC")
    chk("la cache nu si cerca prima fra le congelate",
        P["nu_congelata"].parent.name == "paper1"
        and P["nu_nuova"].parent.name == "paper2")
    chk("l'uscita sta in results/paper2", P["out"].parent.name == "paper2")

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("esamina")
    e.add_argument("--root", default=ROOT_DEFAULT)
    e.add_argument("--region", choices=["NGC", "SGC"], required=True)
    e.add_argument("--mock", type=int, default=None,
                   help="indice di un cubo test2_ per il contrasto; senza, DESI")
    e.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "esamina":
        return esamina(a.root, a.region, a.mock, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
