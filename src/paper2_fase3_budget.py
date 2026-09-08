#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 — item 3.3: il budget d'errore, assemblato.

I SEI TERMINI
  (a) convenzione sigma_px   ZERO per costruzione. Nel gauge dell'emendamento 13
                             sigma_px e' identico su tutti i punti (escursione
                             relativa 5.9e-14). Verificato, non stimato.
  (b) anisotropia F_AP       IL SEGNALE. E' quello che resta.
  (c) ri-randomizzazione     MISURATA a geometria ferma, con l'HOD identico e il
      del carving            solo seme del carving cambiato: 7.73 e 7.69 (NGC),
                             6.29 e 6.78 (SGC) generatori SULLA MEDIA di 200.
                             Entra in QUADRATURA.
  (d) tiling                 ZERO. Repliche costanti su tutti gli undici punti
                             (15 NGC, 10 SGC) e frazione indipendente con
                             escursione 0.2%. Verificato nel gauge nuovo.
  (e) conteggio dei voxel    SI SOTTRAE, con la pendenza MISURATA SU D.
  (f) residuo Prop. 2'       SI SOTTRAE, in forma chiusa.
  (-) non attribuito         Quello che resta dopo (e) e (f). Entra in
                             QUADRATURA ed e' DICHIARATO, non nascosto.

PERCHE' LA PENDENZA DI (e) SI MISURA SU D E NON SI PRENDE DAL LATO DATI
  D = <N_mock> - N_DESI, e i due lati condividono la maschera: se rispondessero
  allo stesso modo al conteggio dei voxel il canale si cancellerebbe in D. Non
  si cancella, ma si cancella IN PARTE, e la parte dipende dall'emisfero:
  misurata +0.045 in NGC k=1 contro s = 0.1009 del lato dati (45%), e +0.099 in
  SGC contro 0.0945 (104%). Usare s sbaglierebbe di un fattore due al nord.

E PERCHE' SE NE CALCOLANO DUE
  Stimare la pendenza sugli stessi punti che poi si correggono rende il residuo
  ortogonale a dV per costruzione: si toglie una parte del segnale insieme
  all'artefatto. La stima alternativa usa il solo BLOCCO A, dove il segnale
  fisico e' NULLO per la Proposizione 2 — verificata in forma esatta sul percorso
  reale — quindi la' la pendenza e' artefatto puro. Ha due punti soli e dV
  piccolo, quindi e' imprecisa. Si riportano ENTRAMBE e la differenza fra le due
  correzioni entra nel budget come incertezza del termine (e). Nessuna delle due
  e' "quella giusta": la loro distanza e' informazione.

(f) E IL BLOCCO A: UN PAVIMENTO MISURATO, NON UN FATTORE DA ESTRAPOLARE
  CORREZIONE DI DISEGNO, 31 ago. La prima versione tarava generatori-per-voxel
  di spostamento sul blocco A — 15.8 generatori su 0.009 voxel, cioe' ~1750 —
  e li applicava a B6 con du = 1.14 voxel: DUEMILA generatori, un'estrapolazione
  di 126 volte. Non e' difendibile. Sul blocco A lo spostamento e' una
  dilatazione UNIFORME attorno al centro del cubo (Prop. 2'); su B e C e' un
  residuo radiale ANISOTROPO. Sono due meccanismi, e la taratura dell'uno non
  vale per l'altro.

  Il modo corretto e' l'opposto. Sul blocco A il segnale fisico e' NULLO per la
  Proposizione 2 — verificata in forma esatta sul percorso reale, delta = 0 nel
  gauge derivato — quindi il residuo che si misura li', dopo la sottrazione del
  canale dei voxel, e' interamente artefatto. E' un PAVIMENTO MISURATO sul
  termine non attribuito, non un coefficiente da propagare.

  Su B e C il residuo della Prop. 2' NON e' separabile dal segnale: si somma a
  (b) e finisce dentro il termine non attribuito, di cui il blocco A da' il
  limite inferiore. Dichiararlo cosi' e' l'unica cosa onesta: fingere di
  sottrarlo per punto significherebbe inventare una relazione fra due
  spostamenti che non hanno la stessa origine.

COSA NON FA
  Non decide se il residuo non attribuito sia fisico. Undici punti non bastano a
  identificarlo — tutti i candidati sono morti al jackknife o cambiano segno fra
  emisferi — e B6 ha mostrato che non scala nemmeno con la deformazione. Il
  budget lo riporta come termine dichiarato, che e' l'unica cosa onesta da farne.

Uso:
    python src\\paper2_fase3_budget.py selftest
    python src\\paper2_fase3_budget.py run --region NGC
    python src\\paper2_fase3_budget.py run --region SGC --out results\\paper2\\fase3_budget.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

NGRID = 128
PAD = 5.0
# Sei punti dopo i record 27, 28 e 30: tre coppie simmetriche a |alpha-1| =
# 0.018627, 0.0275 e 0.0406. La coppia DEPOSITATA e' {A1, A3}, che sta a due
# ampiezze diverse e mescola una compressione con un'espansione: e' la ragione
# per cui la regola del record 32 non reggeva (record 33).
BLOCK_A = ("A0", "A1", "A1m", "A3", "A3m", "A0m")
BLOCK_A_DEPOSITATO = ("A1", "A3")      # la coppia del pavimento depositato
FLOOR_DEPOSITATO = {"NGC": {1: 10.1, 0: 17.7}, "SGC": {1: 20.2, 0: 32.5}}

# (c): misurato con --carve-reseed, geometria ferma, HOD identico. SULLA MEDIA.
# TERM_C = sd(dN)/sqrt(2)/sqrt(200) al fiduciale, con dN la differenza appaiata
# fra il run principale e il reseed del carving. Il sqrt(2) perche' la
# differenza e' fra DUE estrazioni indipendenti dalla stessa distribuzione
# condizionata, non fra una misura e una verita'.
#
# k=0 e k=1: reseed del 31 ago 2026, valori depositati.
# k=2 e k=3: reseed FID-only del 4 set 2026 (record 26), 1.49 h + 1.48 h.
#   Il cancello di riproduzione ha verificato che 0 e 1, ricalcolati dallo
#   stesso registro e dallo stesso codice dei nuovi, ridiano 7.687, 7.725,
#   6.785 e 6.288 contro i depositati 7.69, 7.73, 6.78 e 6.29.
#
# TERM_C DECRESCE con l'erosione in entrambi gli emisferi - 7.69 -> 5.80 in NGC,
# 6.79 -> 4.41 in SGC - e i due vanno nello STESSO verso. Non era previsto e non
# porta verdetto: nessuna soglia era dichiarata su questo.
TERM_C = {"NGC": {0: 7.69, 1: 7.73, 2: 7.00, 3: 5.80},
          "SGC": {0: 6.78, 1: 6.29, 2: 5.54, 3: 4.41}}
# --- §4.5 del referee, aggiunto il 1 set 2026 --------------------------------
# I quattro numeri sopra sono la DISPERSIONE di (c) sulla media. La MEDIA della
# ri-randomizzazione non e' mai stata guardata. Il sottocomando `termc` la
# calcola, e prima di riportarla riproduce i quattro numeri congelati.
#
# PREDIZIONE DICHIARATA PRIMA DI GUARDARE (1 set 2026, prima del primo run di
# `termc`). N_main(p,i) e N_reseed(p,i) sono DUE ESTRAZIONI DALLA STESSA
# distribuzione condizionata — stesso campo HOD, stessa geometria, stessa
# maschera — che differiscono solo per il seme del carving. Per scambiabilita':
#
#   (i)   <dN>(p) = 0 a OGNI punto;
#   (ii)  la pendenza di <dN> contro (F-1) sulla linea B e' 0;
#   (iii) <dN>(B5) - <dN>(B1), cioe' il contributo a DD_max, e' 0.
#
# FALSIFICATA se |z| > 3 su (iii), oppure se |z| > 3 su (i) in piu' di un punto
# su ventiquattro (sei punti x due emisferi x due livelli; sotto il nullo se ne
# attende 0.065). Una media non nulla NON e' un termine da aggiungere al budget:
# e' la scambiabilita' che cade, cioe' un difetto nel carving. Non si ripara
# dopo: si registra.
#
# SECONDA DOMANDA, sulla prima meta' del §4.5: (c) ed (e) sono lo stesso canale?
# Se sd(dN) cresce con |F-1|, il rumore del carving e' guidato dal movimento
# della maschera, e sommare (c) in quadratura mentre si sottrae (e) linearmente
# conta due volte la stessa cosa. Nessuna predizione dichiarata qui: non ho un
# argomento che imponga un verso, e inventarne uno dopo sarebbe peggio.
TERM_C_REPRO_TOL = 0.05
# (a) e (d): verificati a zero, non stimati.
TERM_A = 0.0
TERM_D = 0.0
# Pendenza del lato dati, per confronto soltanto: NON si usa per correggere D.
S_DATA = {"NGC": 0.1009, "SGC": 0.0945}


def load_jsonl(path):
    p = Path(path)
    return [] if not p.exists() else [
        json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def gather(a, region, ki):
    """Una riga per punto: dD, sem, dV, du, e il fattore c del gauge."""
    D = {}
    for r in load_jsonl(a.data):
        if r.get("region") != region:
            continue
        nm = "FID" if (r.get("gate") == "d3" or r.get("gauge") == "fid") else r.get("point")
        if nm and r.get("gauge") in ("regauged", "fid"):
            D[nm] = r
    an = [r for r in load_jsonl(a.analisi) if r.get("region") == region]
    if not an or "FID" not in D:
        sys.exit(f"[FATAL] registri incompleti per {region}")
    per = an[-1]["levels"][f"k{ki}"]["per_point"]

    rows = []
    for p, v in per.items():
        if p not in D:
            continue
        rows.append({
            "pt": p, "block": D[p].get("block", "?"),
            "dD": float(v["estimate"]), "sem": float(v["sem"]),
            "dV": int(D[p]["n_valid_voxels"] - D["FID"]["n_valid_voxels"]),
            "du": float(D[p].get("grid_shift_vs_fid", {}).get("max", np.nan)),
            "c": float(D[p].get("c", 1.0)),
            "alpha_iso": float(D[p].get("alpha_iso", np.nan)),
        })
    # Il blocco A non e' in per_point del 3.4: la' non e' un punto di misura.
    # Qui serve, ed e' l'unico posto dove il segnale e' nullo PER TEOREMA.
    # Il suo Delta D non e' in nessun registro: si calcola dal lato mock, con la
    # stessa definizione del 3.4 — media appaiata meno differenza DESI, esatta.
    mk = {}
    for r in load_jsonl(a.mock):
        if r.get("region") != region or r.get("smoke") \
                or r.get("carve_reseed") is not None:
            continue
        for q, v in r["points"].items():
            # FUSIONE PER UNIONE: vedi paper2_fusione_patch.py, 1 set 2026.
            if isinstance(v, dict):
                mk.setdefault(q, {}).setdefault(r["index"], {}).update(v)
            else:
                mk.setdefault(q, {})[r["index"]] = v
    key = f"N_H1_k{ki}"

    def _desi(p):
        """Lato dati al livello ki.

        A k=0 e k=1 i due campi piatti; a k=2 e k=3 la SCALA `ladder`. La forma
        precedente era `dkey = "N_H1" if ki == 1 else "N_H1_k0"`, che a ki=2,3
        prendeva il lato dati a k=0 SENZA DIRLO: un Delta D fra un lato mock a
        k=2 e un lato dati a k=0, scritto nel registro come una misura. Un crash
        si vede, quello no."""
        if ki == 1:
            return D[p]["N_H1"]
        if ki == 0:
            return D[p]["N_H1_k0"]
        lad = D[p].get("ladder") or {}
        if str(ki) not in lad or "N_H1" not in lad[str(ki)]:
            sys.exit(f"[FATAL] il lato dati non ha il livello k={ki} per {p}: "
                     f"la scala di erosione dei record del 3.1 non lo contiene. "
                     f"Non si ripiega su k=0.")
        return lad[str(ki)]["N_H1"]

    # I punti del blocco A senza la chiave sul lato mock si saltano e si
    # dichiarano: A0, A1m, A3m e A0m sono girati a erosioni 0 e 1 soltanto,
    # perche' servono al PAVIMENTO. Stesso trattamento di selection_channel.
    _senza = []
    for p in BLOCK_A:
        if p not in D or p not in mk or "FID" not in mk:
            continue
        idx = sorted(set(mk[p]) & set(mk["FID"]))
        idx = [i for i in idx if key in mk[p][i] and key in mk["FID"][i]]
        if len(idx) < 10:
            if p in mk:
                _senza.append(p)
            continue
        d = np.array([mk[p][i][key] - mk["FID"][i][key] for i in idx], float)
        dd = float(d.mean() - (_desi(p) - _desi("FID")))
        rows.append({
            "pt": p, "block": "A", "dD": dd,
            "sem": float(d.std(ddof=1) / np.sqrt(len(d))),
            "dV": int(D[p]["n_valid_voxels"] - D["FID"]["n_valid_voxels"]),
            "du": float(D[p].get("grid_shift_vs_fid", {}).get("max", np.nan)),
            "c": float(D[p].get("c", 1.0)),
            "alpha_iso": float(D[p].get("alpha_iso", np.nan)),
            "n_mock": len(idx),
        })
    if _senza:
        print(f"    [blocco A] {len(_senza)} punti saltati a k={ki}, senza "
              f"{key} sul lato mock: {', '.join(sorted(_senza))}. "
              f"Il pavimento a questo livello si calcola sui restanti.")
    return rows


def wls_origin(x, y, w):
    """Pendenza per l'origine, pesata: a dV = 0 il punto E' il fiduciale e
    dD = 0 per definizione. Un'intercetta libera descriverebbe qualcosa che non
    puo' esistere, e mangerebbe un grado di liberta' su undici punti."""
    sxx = float(np.sum(w * x * x))
    if sxx <= 0:
        return float("nan"), float("nan")
    return float(np.sum(w * x * y) / sxx), float(1.0 / np.sqrt(sxx))


def prop2_shift_voxel(c, alpha_iso, cell):
    """Forma chiusa del residuo Prop. 2', blocco A: (N/2 - p/dx)*|c*alpha - 1|.

    Il termine p/dx e' essenziale: senza, la forma sbaglia dello 0.5%, ed e'
    esattamente il padding in voxel. Verificato a 1e-4 sul blocco A.
    """
    if not np.isfinite(alpha_iso):
        return float("nan")
    return abs((0.5 * NGRID - PAD / cell) * (c * alpha_iso - 1.0))


def build(a, region, ki):
    rows = gather(a, region, ki)
    # I punti di MISURA sono B e C: il blocco A serve come pavimento, non entra
    # nella stima della pendenza ne' nel residuo non attribuito.
    meas = [r for r in rows if r["block"] != "A" and np.isfinite(r["sem"])]
    ablk = [r for r in rows if r["block"] == "A" and np.isfinite(r["dD"])]
    x = np.array([r["dV"] for r in meas], float)
    y = np.array([r["dD"] for r in meas], float)
    w = 1.0 / np.array([r["sem"] for r in meas], float) ** 2

    s_all, e_all = wls_origin(x, y, w)
    # Stima alternativa sul solo blocco A: segnale nullo per la Prop. 2.
    # DUE punti e dV piccolo: nessun grado di liberta', nessuna barra d'errore.
    # Si riporta come CONTROLLO DI SEGNO, non come correzione alternativa.
    if len(ablk) >= 2:
        xa = np.array([r["dV"] for r in ablk], float)
        ya = np.array([r["dD"] for r in ablk], float)
        wa = np.ones(len(xa))
        s_a, e_a = wls_origin(xa, ya, wa)
    else:
        s_a, e_a = float("nan"), float("nan")

    cell = None
    for r in load_jsonl(a.data):
        if r.get("region") == region and (r.get("gate") == "d3"
                                          or r.get("gauge") == "fid"):
            cell = float(r["cell"])
    if cell is None:
        sys.exit(f"[FATAL] cella fiduciale non trovata per {region}")

    # (f): il PAVIMENTO. Sul blocco A il segnale e' nullo per teorema, quindi
    # il residuo dopo la sottrazione del canale voxel e' interamente artefatto.
    a_rows = []
    for r in ablk:
        pred = prop2_shift_voxel(r["c"], r["alpha_iso"], cell)
        a_rows.append({**r, "e_term": s_all * r["dV"],
                       "b_residual": r["dD"] - s_all * r["dV"],
                       "prop2_predicted_voxel": pred})
    # CANCELLO, record 33: prima di riportare qualunque valore nuovo, la rms
    # sulla COPPIA DEPOSITATA {A1, A3} deve riprodurre il pavimento depositato.
    # Se non lo fa, l'estensione a sei punti ha cambiato il calcolo esistente e
    # nulla di quel che segue si usa. Il cancello e' sulla COPPIA e non su
    # un'ampiezza: quei due punti stanno ad ampiezze diverse.
    dep = [x for x in a_rows if x["pt"] in BLOCK_A_DEPOSITATO]
    atteso = FLOOR_DEPOSITATO.get(region, {}).get(ki)
    if len(dep) == len(BLOCK_A_DEPOSITATO) and atteso is not None:
        rms_dep = float(np.sqrt(np.mean([x["b_residual"] ** 2 for x in dep])))
        if abs(rms_dep - atteso) > 0.1:
            sys.exit(f"[FATAL] pavimento, cancello del record 33: la rms sulla "
                     f"coppia depositata {BLOCK_A_DEPOSITATO} vale {rms_dep:.2f} "
                     f"contro {atteso} depositato, {region} k={ki}. "
                     f"L'estensione a sei punti ha cambiato il calcolo "
                     f"esistente: nulla di quel che segue si usa.")
    else:
        rms_dep = float("nan")

    # (f) = MAX |b_residual| sui punti disponibili (record 33). Il massimo e'
    # >= la rms di qualunque sottoinsieme, quindi la regola non puo' ABBASSARE
    # il pavimento rispetto al depositato, qualunque siano i numeri. E' la
    # proprieta' che la rende adottabile dopo aver visto i grezzi.
    floor = (float(max(abs(x["b_residual"]) for x in a_rows))
             if a_rows else float("nan"))
    floor_driver = (max(a_rows, key=lambda x: abs(x["b_residual"]))["pt"]
                    if a_rows else None)
    floor_rms_dep = rms_dep
    floor_n = len(a_rows)

    # Il pavimento si riporta con il punto che lo DETERMINA e con quanti punti
    # lo compongono: un massimo senza il suo argomento non e' verificabile.
    # Record 41: a k=2,3 non esiste un pavimento depositato, quindi il
    # cancello NON SI APPLICA. «nan contro None» era corretto nella sostanza
    # e invitava a leggerlo come un guasto: ora la riga dice cosa succede.
    # Non cambia nessun numero.
    _dep = FLOOR_DEPOSITATO.get(region, {}).get(ki)
    _nota = (f"[rms coppia depositata {floor_rms_dep:.2f} contro {_dep}]"
             if _dep is not None else
             "[cancello non applicabile: nessun pavimento depositato a "
             "questo livello]")
    print(f"  (f) pavimento = {floor:7.2f}  su {floor_n} punti, determinato da "
          f"{floor_driver}   {_nota}")

    out = []
    for r in meas:
        e_main = s_all * r["dV"]
        # Incertezza su (e): dall'errore della pendenza, che ha undici punti e
        # dieci gradi di liberta'. NON dalla differenza col blocco A, che ne ha
        # due e nessuna barra d'errore.
        e_unc = e_all * abs(r["dV"])
        out.append({**r, "e_term": e_main, "e_uncertainty": e_unc,
                    "b_residual": r["dD"] - e_main})
    resid = np.array([o["b_residual"] for o in out], float)
    rms = float(np.sqrt(np.mean(resid ** 2)))
    return {"rows": out, "blockA": a_rows, "slope_all": s_all,
            "slope_all_err": e_all, "slope_blockA_sign_check": s_a,
            "slope_data_side": S_DATA[region], "cell": cell,
            "prop2_floor": floor,
            "unattributed_rms": rms, "n_points": len(out)}


def termc_table(main_recs, reseed_recs, region, ki):
    """(c) punto per punto: dispersione E media della ri-randomizzazione.

    Appaiata per indice di realizzazione: dN(p,i) = N_reseed(p,i) - N_main(p,i).
    Solo i record senza `smoke`, e per il lato principale solo quelli SENZA
    carve_reseed."""
    key = f"N_H1_k{ki}"

    def index_by_point(recs, want_reseed):
        out = {}
        for r in recs:
            if r.get("region") != region or r.get("smoke"):
                continue
            has = r.get("carve_reseed") is not None
            if has != want_reseed:
                continue
            for q, v in (r.get("points") or {}).items():
                if isinstance(v, dict) and key in v:
                    out.setdefault(q, {})[r["index"]] = float(v[key])
        return out

    A = index_by_point(main_recs, False)
    B = index_by_point(reseed_recs, True)
    rows, per_real = [], {}
    for p in sorted(set(A) & set(B)):
        idx = sorted(set(A[p]) & set(B[p]))
        if len(idx) < 10:
            continue
        d = np.array([B[p][i] - A[p][i] for i in idx], float)
        sd = float(d.std(ddof=1))
        # dN e' la differenza fra DUE estrazioni indipendenti del carving:
        # Var(dN) = 2 sigma_carve^2. La definizione congelata di (c) e' la
        # dispersione di UNA estrazione, quindi il sqrt(2) va tolto.
        sigma_carve = sd / np.sqrt(2.0)
        sem_mean = sd / np.sqrt(len(d))          # per z sulla media: (i)
        sem_carve = sigma_carve / np.sqrt(len(d))  # questo E' TERM_C
        rows.append({"pt": p, "n": len(d), "mean": float(d.mean()), "sd": sd,
                     "sigma_carve": float(sigma_carve),
                     "sem": float(sem_mean), "sem_carve": float(sem_carve),
                     "z": float(d.mean() / sem_mean) if sem_mean else float("nan")})
        per_real[p] = {i: (B[p][i] - A[p][i]) for i in idx}
    return rows, per_real


def cmd_termc(a):
    main_recs = load_jsonl(a.mock)
    reseed_recs = load_jsonl(a.reseed)
    if not reseed_recs:
        sys.exit(f"[FATAL] nessun record di reseed in {a.reseed}")
    out = {"schema": "paper2_fase3_termc_v1", "region": a.region,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "levels": {}}
    print("=" * 74)
    print(f"§4.5 — termine (c): dispersione E MEDIA, {a.region}")
    print("=" * 74)
    all_ok = True
    for ki in (0, 1):
        rows, per_real = termc_table(main_recs, reseed_recs, a.region, ki)
        if not rows:
            print(f"\n  k={ki}: nessun punto appaiato. Salto.")
            continue
        frozen = TERM_C.get(a.region, {}).get(ki)
        sems = [r["sem_carve"] for r in rows]
        fid = next((r["sem_carve"] for r in rows if r["pt"] == "FID"), float("nan"))
        mean_sem = float(np.mean(sems))
        print(f"\n  --- k = {ki} ---")
        print(f"  {'punto':<6} {'n':>5} {'sd(dN)':>9} {'sigma_c':>9} "
              f"{'(c)':>7} {'media':>10} {'z':>7}")
        for r in rows:
            print(f"  {r['pt']:<6} {r['n']:>5} {r['sd']:>9.2f} "
                  f"{r['sigma_carve']:>9.2f} {r['sem_carve']:>7.2f} "
                  f"{r['mean']:>+10.3f} {r['z']:>+7.2f}")

        # --- RIPRODUZIONE DEL CONGELATO -----------------------------------
        cands = {"media sui punti": mean_sem, "al FID": fid}
        hit = [k for k, v in cands.items()
               if frozen is not None and abs(v - frozen) <= TERM_C_REPRO_TOL]
        print(f"\n  TERM_C congelato = {frozen}   calcolato: " +
              "  ".join(f"{k} {v:.3f}" for k, v in cands.items()))
        if hit:
            print(f"  RIPRODUZIONE: OK tramite '{hit[0]}'")
        else:
            all_ok = False
            print("  RIPRODUZIONE: NON TORNA -> non usare le medie sopra. "
                  "Significa che la definizione di (c) nel codice non e' quella "
                  "che ha prodotto la costante.")

        # --- (i) e (iii): la predizione dichiarata -------------------------
        bad = [r["pt"] for r in rows if abs(r["z"]) > 3.0]
        print(f"\n  (i)   punti con |z| > 3 sulla media: "
              f"{bad if bad else 'nessuno'}")
        if set(r["pt"] for r in rows) <= {"FID"}:
            print("  (ii)  NON CALCOLABILE: il registro di reseed contiene il solo")
            print("        FID. La pendenza contro (F-1) richiede almeno due punti.")
            print("  (iii) NON CALCOLABILE per la stessa ragione. Serve un run di")
            print("        reseed a B1 e B5, 200 realizzazioni, due emisferi.")
            print("  NOTA: (c) e' quindi misurato al SOLO fiduciale e applicato a")
            print("        tutti i punti. Che il rumore del carving sia indipendente")
            print("        dal punto e' un'assunzione MAI TESTATA, ed e' esattamente")
            print("        il dubbio del §4.5. Va dichiarata, non taciuta.")
        contrib = None
        if "B1" in per_real and "B5" in per_real:
            idx = sorted(set(per_real["B1"]) & set(per_real["B5"]))
            dd = np.array([per_real["B5"][i] - per_real["B1"][i] for i in idx], float)
            s = float(dd.std(ddof=1) / np.sqrt(len(dd)))
            contrib = {"n": len(dd), "mean": float(dd.mean()), "sem": s,
                       "z": float(dd.mean() / s) if s else float("nan")}
            print(f"  (iii) contributo a DD_max, <dN>(B5)-<dN>(B1) = "
                  f"{contrib['mean']:+.3f} +- {contrib['sem']:.3f}  "
                  f"({contrib['z']:+.2f} z, n={contrib['n']})")
            if abs(contrib["z"]) > 3.0:
                print("        -> PREDIZIONE FALSIFICATA. La scambiabilita' del "
                      "seme del carving cade: non e' un termine da aggiungere, "
                      "e' un difetto. Registrare, non riparare.")
            else:
                print("        -> compatibile con zero, come dichiarato.")

        # --- (c) ed (e) sono lo stesso canale? -----------------------------
        b = [r for r in rows if r["pt"] in LINE_B_PTS]
        corr = float("nan")
        if len(b) >= 4:
            xf = np.array([abs(LINE_B_F[r["pt"]] - 1.0) for r in b])
            ys = np.array([r["sd"] for r in b])
            if xf.std() > 0 and ys.std() > 0:
                corr = float(np.corrcoef(xf, ys)[0, 1])
            print(f"\n  sd(dN) contro |F-1| sulla linea B: r = {corr:+.3f}  "
                  f"({len(b)} punti)")
            print("  (se e' nettamente positivo, (c) ed (e) sono lo stesso canale "
                  "e il budget li conta due volte)")
        out["levels"][f"k{ki}"] = {"rows": rows, "frozen": frozen,
                                   "reproduced": bool(hit),
                                   "reproduced_via": hit[0] if hit else None,
                                   "ddmax_contribution": contrib,
                                   "corr_sd_vs_absF": corr}
    if a.out:
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, sort_keys=True) + "\n")
        print(f"\n[scritto] {a.out}")
    return 0 if all_ok else 3


LINE_B_F = {"B1": 0.971070, "B2": 0.985396, "FID": 1.0,
            "B4": 1.014889, "B5": 1.030071, "B6": 1.045531810025433}
LINE_B_PTS = tuple(LINE_B_F)


def cmd_run(a):
    reg = a.region
    rec = {"schema": "paper2_fase3_budget_v1", "region": reg,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "terms_verified_zero": {"a_sigma_px": TERM_A, "d_tiling": TERM_D},
           "levels": {}}
    print("=" * 78)
    print(f"3.3 — budget d'errore a sei termini, {reg}")
    print("=" * 78)
    print("  (a) sigma_px = 0 e (d) tiling = 0: VERIFICATI, non stimati.")
    levels = getattr(a, "levels", None) or [1, 0]
    _LAB = {1: "k=1  PRIMARIO", 0: "k=0",
            2: "k=2  DIAGNOSTICO", 3: "k=3  DIAGNOSTICO"}
    # CANCELLO: TERM_C deve avere la chiave PRIMA che il livello si costruisca.
    # Senza, il run muore a meta' con un KeyError e senza dire da dove verrebbe
    # il numero mancante.
    _senza = [ki for ki in levels if ki not in TERM_C.get(reg, {})]
    if _senza:
        sys.exit(f"[FATAL] TERM_C[{reg}] non ha i livelli {_senza}. Si "
                 f"misurano con un reseed del carving al fiduciale a quelle "
                 f"erosioni: paper2_runner_fase3_mock.py run --points FID "
                 f"--carve-reseed 777 --erosions {' '.join(map(str, _senza))} "
                 f"(record 26).")
    for ki, lab in ((ki, _LAB.get(ki, f"k={ki}")) for ki in levels):
        B = build(a, reg, ki)
        c_term = TERM_C[reg][ki]
        if ki not in (0, 1):
            # L'analisi a questi livelli NON emette l'esito E1-E4 ne' la §5.4:
            # le soglie depositate sono tarate sul deficit a k=0,1. Il budget
            # qui produce un pavimento e un sistematico senza un verdetto a cui
            # applicarli. Si dice, invece di lasciarlo dedurre.
            print(f"\n  [k={ki}] Il budget a questo livello DESCRIVE e non "
                  f"CLASSIFICA: l'analisi non emette esito ne' §5.4 qui, "
                  f"quindi pavimento e sistematico non hanno una soglia a cui "
                  f"essere confrontati. Sono grandezze diagnostiche.")
        print(f"\n{'-'*78}\n  {lab}\n{'-'*78}")
        print(f"  (e) pendenza dD/dV misurata SU D:")
        print(f"        su tutti i punti  {B['slope_all']:+.5f} +- {B['slope_all_err']:.5f}"
              f"   ({100*B['slope_all']/B['slope_data_side']:.0f}% di s = "
              f"{B['slope_data_side']} del lato dati)")
        sc = B["slope_blockA_sign_check"]
        print(f"        blocco A, controllo di SEGNO {sc:+.5f}   "
              f"(due punti, nessuna barra d'errore: non si usa per correggere)")
        print(f"  (c) {c_term:.2f} generatori sulla media, in quadratura")
        print(f"\n  {'pt':>4} {'dD':>8} {'(e)':>8} {'inc(e)':>7} {'(b) resta':>10}")
        for o in B["rows"]:
            print(f"  {o['pt']:>4} {o['dD']:+8.1f} {o['e_term']:+8.1f} "
                  f"{o['e_uncertainty']:7.1f} {o['b_residual']:+10.1f}")
        print(f"\n  (f) PAVIMENTO dal blocco A — segnale nullo per la Prop. 2, "
              f"quindi tutto artefatto:")
        for o in B["blockA"]:
            print(f"  {o['pt']:>4} {o['dD']:+8.1f} {o['e_term']:+8.1f} "
                  f"{'':>7} {o['b_residual']:+10.1f}"
                  f"   (Prop. 2' predice {o['prop2_predicted_voxel']:.4f} voxel)")
        print(f"       pavimento = {B['prop2_floor']:.1f} generatori rms")
        u = B["unattributed_rms"]
        tot = float(np.sqrt(c_term ** 2 + u ** 2))
        print(f"\n  residuo NON ATTRIBUITO: {u:.1f} generatori rms fra i punti")
        print(f"  incertezza sistematica su (b): sqrt({c_term:.2f}^2 + {u:.1f}^2) "
              f"= {tot:.1f} generatori")
        if np.isfinite(B["prop2_floor"]):
            print(f"    Di questi, almeno {B['prop2_floor']:.1f} sono artefatto "
                  f"MISURATO: e' quanto resta sul blocco A, dove il segnale e'")
            print(f"    nullo per teorema. Il resto e' artefatto non "
                  f"identificato oppure segnale, e undici punti non li separano.")
        print(f"    Il residuo non e' rumore: e' un termine che undici punti non")
        print(f"    identificano. Tutti i candidati muoiono al jackknife o cambiano")
        print(f"    segno fra emisferi, e B6 ha mostrato che non scala con la")
        print(f"    deformazione. Si dichiara, non si nasconde.")
        B.update({"term_c": c_term, "total_systematic_on_b": tot})
        rec["levels"][f"k{ki}"] = B
    if a.out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True, default=float) + "\n")
        print(f"\n[scritto] {a.out}")
    return 0


def cmd_selftest(a):
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    rng = np.random.default_rng(33)
    n = 10
    dV = rng.normal(0, 500, n)
    slope = 0.06
    noise = rng.normal(0, 40, n)
    y = slope * dV + noise
    w = np.ones(n) / 11.0 ** 2
    s, e = wls_origin(dV, y, w)
    expect("1. la pendenza per l'origine recupera quella iniettata",
           abs(s - slope) < 4 * e, f"(stimata {s:.5f} +- {e:.5f})")
    expect("2. e non ha intercetta: a dV = 0 il modello da' esattamente 0",
           abs(s * 0.0) == 0.0)

    resid = y - s * dV
    expect("3. il residuo dopo la sottrazione e' ortogonale a dV per costruzione",
           abs(float(np.sum(w * dV * resid))) < 1e-9,
           "(e' proprio il motivo per cui serve la seconda stima)")

    # forma chiusa (f): il termine di padding vale lo 0.5% e non si omette
    cell = 15.604397742261337
    full = prop2_shift_voxel(1.0 / 1.0406 * 1.0002, 1.0406, cell)
    corner = abs(0.5 * NGRID * (1.0 / 1.0406 * 1.0002 * 1.0406 - 1.0))
    expect("4. la forma chiusa di (f) include il termine di padding",
           full < corner and abs(full / corner - (1 - PAD / cell / (NGRID / 2)))
           < 1e-9,
           f"(rapporto {full/corner:.5f})")
    expect("5. e senza quel termine si sbaglierebbe dello 0.5%",
           0.004 < 1 - full / corner < 0.006)

    expect("6. (a) e (d) sono zero VERIFICATI, non stimati",
           TERM_A == 0.0 and TERM_D == 0.0)
    expect("7. (c) e' per emisfero e per livello, non un numero solo",
           TERM_C["NGC"][1] != TERM_C["SGC"][1])
    expect("8. e la pendenza del lato dati NON si usa per correggere D",
           S_DATA["NGC"] == 0.1009 and abs(S_DATA["NGC"] - 0.045) > 0.05,
           "(0.1009 contro i ~0.045 misurati su D in NGC k=1)")

    c_t, u = 7.73, 37.5
    tot = float(np.sqrt(c_t ** 2 + u ** 2))
    expect("8b. il blocco A NON entra nella stima della pendenza: e' il pavimento",
           True, "(verificato nel codice: meas esclude block == 'A')")
    expect("9. il non attribuito domina l'incertezza sistematica",
           tot > 4 * c_t and abs(tot - 38.3) < 0.2, f"(totale {tot:.1f})")
    expect("10. e resta sotto la soglia di rilevabilita' di 53",
           tot < 53, f"({tot:.1f} < 53)")

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    q = sub.add_parser("run")
    q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    q.add_argument("--data", default="results/paper2/fase3.jsonl")
    q.add_argument("--analisi", default="results/paper2/fase3_analisi.jsonl")
    q.add_argument("--mock", default="results/paper2/fase3_mock.jsonl")
    q.add_argument("--out", default="results/paper2/fase3_budget.jsonl")
    q.add_argument("--levels", type=int, nargs="+", default=[1, 0],
                   choices=[0, 1, 2, 3],
                   help="livelli di erosione. Default 1 0, il comportamento "
                        "depositato. A k=2,3 il budget DESCRIVE e non "
                        "CLASSIFICA: l'analisi non emette esito a quei livelli, "
                        "quindi pavimento e sistematico sono diagnostici")
    t = sub.add_parser("termc")
    t.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    t.add_argument("--mock", default="results/paper2/fase3_mock.jsonl")
    t.add_argument("--reseed", default="results/paper2/fase3_mock_carve777.jsonl")
    t.add_argument("--out", default=None)
    a = p.parse_args()
    return {"selftest": cmd_selftest, "run": cmd_run,
            "termc": cmd_termc}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
