#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_gate53_margini.py — i due margini della predizione SGC dichiarata in SGC_PRED.

LA PREDIZIONE
    `SGC_PRED = {"spectral_fraction_range": [0.70, 0.82], "min_z_residual": 3.0}`,
    dichiarata prima del run in src/paper2_gate53.py ed emessa dallo stesso file. Il
    censimento della voce 6.9 (record 65) l'ha trovata SENZA record nel ledger: l'item 5.3
    ne ha molti, ma nessuno contiene l'intervallo di SGC_PRED.

    Solo SGC. Il ramo NGC dello stesso file stampa «cancello contro i valori congelati:
    SUPERATO / FALLITO» contro TARGETS_NGC: e' un cancello di riproduzione, non una
    predizione, e non ha un margine. Questo strumento rifiuta --region NGC.

I DUE MARGINI, E PERCHE' SONO DIVERSI IN NATURA

  |z| > 3
    `z_residual = residual / gain_mock_sd`, e `gain_mock_sd` E' la dispersione
    mock-to-mock. Quindi z e' GIA' un margine sul denominatore che decide, e la soglia e'
    una soglia SUL margine. Non si ricalcola niente: il margine e' |z| - 3, in unita'
    proprie. Nel codice questo si esprime passando sd = 1.0 a margine(), e sd = 1.0 qui
    e' una costruzione, non un'assunzione: la quantita' testata e' un rapporto a una
    dispersione.

  frazione spettrale in [0.70, 0.82]
    `spectral_fraction = (<N_phi> - <DESI_phi>) / (<N> - DESI)` e' un RAPPORTO FRA MEDIE
    D'INSIEME. Una frazione spettrale per singolo mock NON ESISTE, quindi la dispersione
    non si ottiene per mock: si ottiene con un BOOTSTRAP SULLE COPPIE APPAIATE,
    ricampionando con reimmissione gli indici e tenendo insieme N e N_phi dello stesso
    indice — l'appaiamento e' il motivo per cui load_pairs legge la coppia dalla stessa
    riga.

    Due varianti, dichiarate entrambe perche' non misurano la stessa cosa:
      (a) PRIMARIA — si ricampionano solo i mock; DESI e le sue estrazioni restano fissi.
          E' il denominatore COERENTE con z_residual, che e' mock-to-mock e nient'altro.
      (b) ACCANTO — si ricampionano anche le estrazioni DESI randomizzate. Piu' larga.

    Due margini etichettati per ciascuna variante, distanza da 0.70 e da 0.82: un
    intervallo non ha un lato privilegiato. Se il valore cade dentro, il margine riportato
    e' il MINORE dei due, e il record dice che e' il minore.

CIO' CHE NESSUN BOOTSTRAP CHIUDE
    Al denominatore c'e' `desi_orig`, il campo osservato, che e' N = 1. Ricampionare i
    mock non tocca quella componente, e la variante (b) ricampiona le estrazioni della
    randomizzazione di fase, non il campo. Sta scritto nel record fra i limiti dichiarati:
    e' la stessa regola del denominatore che ha chiuso una classe di errori fra M26,
    Paper 1 e Paper 2.

CANCELLI DI RIPRODUZIONE, PRIMA DI QUALUNQUE MARGINE
    1. dal record stesso: residual / gain_mock_sd == z_residual a rel <= 1e-12;
    2. dai file appaiati congelati: compute(load_pairs(...), desi) riproduce OGNI campo
       numerico del record a rel <= 1e-12.
    Se il secondo non passa, non sto leggendo il file che ha prodotto quei numeri, e un
    margine calcolato su un altro file non e' il margine di quella predizione.

    load_pairs e compute si importano da paper2_gate53, non si riscrivono; margine() si
    importa da paper2_d6_incertezze.

USO
    python src\\paper2_gate53_margini.py selftest
    python src\\paper2_gate53_margini.py margini --registro results\\paper2\\gate53.jsonl ^
        --appaiati results\\paper2\\fasi_mock_pr_v1_SGC.jsonl --region SGC ^
        --out results\\paper2\\gate53_margini.jsonl

Sola lettura su registro e file appaiati. Uscita JSONL append-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

REV = "paper2_gate53_margini rev.1"
REL_MAX = 1e-12
BOOT_DEFAULT = 20000
SEED_DEFAULT = 20260914
SCHEMA_REG = "paper2_gate53_v1"

# campi del record che compute() deve riprodurre. 'rank' e' una stringa e si confronta
# per uguaglianza; gli altri per rel.
CAMPI_NUMERICI = [
    "n_mock", "n_desi_draws", "desi", "desi_phi_mean", "mock_mean", "mock_phi_mean",
    "gain_mock_mean", "gain_mock_sd", "gain_desi", "residual", "z_residual",
    "corr_N_Nphi", "spectral_fraction", "sem_procedural", "sd_draw_exact",
    "sd_deconvolved_exact", "z_deconvolved_exact", "sd_draw_published",
    "sd_deconvolved", "z_deconvolved",
]


def _importa():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from paper2_gate53 import load_pairs, compute, SGC_PRED
    except Exception as e:
        raise SystemExit("ERRORE: non riesco a importare da paper2_gate53.py: %s: %s"
                         % (type(e).__name__, e))
    try:
        from paper2_d6_incertezze import margine
    except Exception as e:
        raise SystemExit("ERRORE: non riesco a importare margine() da "
                         "paper2_d6_incertezze.py: %s: %s" % (type(e).__name__, e))
    return load_pairs, compute, SGC_PRED, margine


def _sha256(percorso):
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _rel(a, b):
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return 0.0
    d = max(abs(a), abs(b))
    return 0.0 if d == 0 else abs(a - b) / d


def _carica_registro(path, region):
    if not os.path.isfile(path):
        raise SystemExit("ERRORE: registro assente: %s" % path)
    trovati = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, linea in enumerate(fh, 1):
            s = linea.strip()
            if not s:
                continue
            try:
                r = json.loads(s)
            except json.JSONDecodeError as e:
                raise SystemExit("ERRORE: riga %d di %s malformata: %s" % (i, path, e))
            if r.get("region") == region:
                trovati.append((i, r))
    if not trovati:
        raise SystemExit("ERRORE: nessun record con region=%s in %s" % (region, path))
    riga, rec = trovati[-1]
    if rec.get("schema") != SCHEMA_REG:
        raise SystemExit("ERRORE: schema inatteso: %s, atteso %s"
                         % (rec.get("schema"), SCHEMA_REG))
    return riga, rec, len(trovati)


def _cancello_interno(rec):
    """Dal record e da nient'altro: z_residual == residual / gain_mock_sd."""
    for k in ("residual", "gain_mock_sd", "z_residual"):
        if k not in rec:
            return [(False, k, "assente dal record")]
    z = float(rec["residual"]) / float(rec["gain_mock_sd"])
    r = _rel(z, float(rec["z_residual"]))
    return [(r <= REL_MAX, "z_residual da residual/gain_mock_sd",
             "ricalcolato %.12f, rel = %.3e" % (z, r))]


def _cancello_appaiati(rec, ricalcolato):
    """compute() sui file congelati riproduce ogni campo del record."""
    esiti = []
    for k in CAMPI_NUMERICI:
        if k not in rec or k not in ricalcolato:
            esiti.append((False, k, "assente (record=%s, ricalcolo=%s)"
                          % (k in rec, k in ricalcolato)))
            continue
        r = _rel(float(rec[k]), float(ricalcolato[k]))
        esiti.append((r <= REL_MAX, k, "rel = %.3e" % r))
    if "rank" in rec and "rank" in ricalcolato:
        esiti.append((rec["rank"] == ricalcolato["rank"], "rank",
                      "%s contro %s" % (rec["rank"], ricalcolato["rank"])))
    return esiti


def _bootstrap(N, N_phi, desi_pr, desi_orig, n_boot, seed, ricampiona_desi):
    """Dispersione della frazione spettrale. Le coppie si ricampionano INSIEME."""
    rng = np.random.default_rng(seed)
    n = N.size
    nd = desi_pr.size
    desi_phi_fisso = float(desi_pr.mean())
    fuori = np.empty(n_boot, float)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)             # coppie appaiate, stesso indice
        num_mock = float(N_phi[idx].mean())
        den_mock = float(N[idx].mean())
        if ricampiona_desi:
            jdx = rng.integers(0, nd, size=nd)
            desi_phi = float(desi_pr[jdx].mean())
        else:
            desi_phi = desi_phi_fisso
        den = den_mock - desi_orig
        fuori[b] = (num_mock - desi_phi) / den if den != 0 else float("nan")
    validi = fuori[np.isfinite(fuori)]
    return {
        "n_boot": int(n_boot),
        "n_validi": int(validi.size),
        "sd": float(validi.std(ddof=1)),
        "media": float(validi.mean()),
        "p2.5": float(np.percentile(validi, 2.5)),
        "p97.5": float(np.percentile(validi, 97.5)),
    }


def _margini_intervallo(valore, sd, lo, hi, margine):
    """Due margini etichettati. Dentro l'intervallo si riporta il minore, dichiarandolo."""
    m_lo = margine(valore, sd, lo, ">")
    m_hi = margine(valore, sd, hi, "<")
    dentro = lo <= valore <= hi
    quale = None
    if dentro:
        quale = "estremo_inferiore" if m_lo["margine_in_sigma"] <= m_hi["margine_in_sigma"] \
            else "estremo_superiore"
    return {
        "valore": valore, "sd": sd, "intervallo": [lo, hi], "dentro": bool(dentro),
        "dall_estremo_inferiore": m_lo,
        "dall_estremo_superiore": m_hi,
        "margine_riportato": (min(m_lo["margine_in_sigma"], m_hi["margine_in_sigma"])
                              if dentro else None),
        "margine_riportato_e": ("il MINORE dei due, dall'%s" % quale) if dentro else
                               "nessuno: il valore cade fuori dall'intervallo",
        "esito": "confermata" if dentro else "SMENTITA",
    }


def cmd_margini(a):
    load_pairs, compute, SGC_PRED, margine = _importa()

    if a.region != "SGC":
        raise SystemExit(
            "ERRORE: la predizione dichiarata in SGC_PRED riguarda solo SGC. Il ramo NGC di "
            "paper2_gate53.py confronta contro TARGETS_NGC e stampa 'SUPERATO / FALLITO': "
            "e' un cancello di riproduzione, non una predizione, e non ha un margine. "
            "E' la distinzione che il censimento della voce 6.9 ha stabilito.")

    riga, rec, quanti = _carica_registro(a.registro, a.region)
    if not os.path.isfile(a.appaiati):
        raise SystemExit("ERRORE: file appaiati assente: %s" % a.appaiati)

    lo, hi = SGC_PRED["spectral_fraction_range"]
    min_z = float(SGC_PRED["min_z_residual"])

    print("=== %s ===" % REV)
    print("  registro   : %s   (riga %d; %d record per %s, si usa l'ULTIMO)"
          % (a.registro, riga, quanti, a.region))
    print("  misurato   : %s   sorgente dichiarata: %s" % (rec.get("utc"), rec.get("source")))
    print("  appaiati   : %s   sha256 %s" % (a.appaiati, _sha256(a.appaiati)[:16] + "..."))
    print("  predizione : frazione spettrale in [%.2f, %.2f]  e  |z| > %.1f" % (lo, hi, min_z))
    print("  numerosita': %s mock, %s estrazioni DESI"
          % (rec.get("n_mock"), rec.get("n_desi_draws")))

    print("")
    print("  cancello 1 — dal record (rel <= %.0e):" % REL_MAX)
    e1 = _cancello_interno(rec)
    for ok, nome, det in e1:
        print("    [%s] %-34s %s" % ("ok" if ok else "FALLITO", nome, det))

    N, N_phi, desi_pr = load_pairs(a.appaiati)
    ric = compute(N, N_phi, desi_pr, float(rec["desi"]))
    print("")
    print("  cancello 2 — compute() sui file congelati riproduce il record:")
    e2 = _cancello_appaiati(rec, ric)
    falliti = [(n, d) for ok, n, d in e2 if not ok]
    print("    %d campi confrontati, %d falliti" % (len(e2), len(falliti)))
    for n, d in falliti:
        print("    [FALLITO] %-26s %s" % (n, d))
    if not falliti:
        print("    [ok] tutti i campi tornano, rank compreso")

    if falliti or not all(ok for ok, _n, _d in e1):
        print("")
        print("ESITO: CANCELLO FALLITO — nessun margine calcolato.")
        print("  Un margine calcolato su un file che non riproduce il record non e' il")
        print("  margine di quella predizione.")
        return 1

    # --- margine 1: |z| > 3, nessun ricalcolo
    z = abs(float(rec["z_residual"]))
    m_z = margine(z, 1.0, min_z, ">")
    m_z["denominatore"] = ("nessuno da scegliere: z e' GIA' residual/gain_mock_sd, cioe' un "
                           "rapporto alla dispersione mock-to-mock. sd = 1.0 per "
                           "costruzione, non per assunzione.")
    print("")
    print("  margine 1 — |z| > %.1f" % min_z)
    print("    |z| = %.4f   ->  %s a %.2f sigma dalla soglia   [%s]"
          % (z, m_z["esito"], m_z["margine_in_sigma"],
             "decidibile" if m_z["decidibile"] else "NON decidibile"))
    print("    (nessun ricalcolo: la soglia e' una soglia SUL margine)")

    # --- margine 2: bootstrap sulle coppie
    sf = float(rec["spectral_fraction"])
    print("")
    print("  margine 2 — frazione spettrale %.6f in [%.2f, %.2f]" % (sf, lo, hi))
    print("    bootstrap sulle coppie appaiate, %d estrazioni, seed %d"
          % (a.boot, a.seed))
    varianti = {}
    for etichetta, ric_desi, nota in (
            ("a_solo_mock", False,
             "PRIMARIA — coerente con z_residual, che e' mock-to-mock e nient'altro"),
            ("b_mock_e_estrazioni_desi", True,
             "ACCANTO — include il rumore delle estrazioni della randomizzazione di fase")):
        bs = _bootstrap(N, N_phi, desi_pr, float(rec["desi"]), a.boot, a.seed, ric_desi)
        mi = _margini_intervallo(sf, bs["sd"], lo, hi, margine)
        mi["bootstrap"] = bs
        mi["nota"] = nota
        varianti[etichetta] = mi
        print("      %-26s sd %.6f   [%.4f, %.4f] al 95%%"
              % (etichetta, bs["sd"], bs["p2.5"], bs["p97.5"]))
        print("        da %.2f: %.2f sigma      da %.2f: %.2f sigma      -> %s%s"
              % (lo, mi["dall_estremo_inferiore"]["margine_in_sigma"],
                 hi, mi["dall_estremo_superiore"]["margine_in_sigma"],
                 mi["esito"],
                 (", margine riportato %.2f sigma (il minore)" % mi["margine_riportato"])
                 if mi["dentro"] else ""))

    uscita = {
        "schema": "paper2_gate53_margini_v1",
        "rev": REV,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "region": a.region,
        "predizione": "SGC_PRED di src/paper2_gate53.py",
        "dichiarata_in": ("SGC_PRED, dichiarata prima del run in src/paper2_gate53.py ed "
                          "emessa dallo stesso file (rami SGC dei verdetti)"),
        "senza_record_nel_ledger": ("l'item 5.3 ha molti record; nessuno contiene "
                                    "l'intervallo di SGC_PRED. Verificato per contenuto, "
                                    "non per nome di file. Censimento: record 65."),
        "soglie": {"spectral_fraction_range": [lo, hi], "min_z_residual": min_z},
        "registro_letto": {"path": a.registro.replace("\\", "/"), "riga": riga,
                           "record_per_regione": quanti, "utc_misura": rec.get("utc"),
                           "sha256": _sha256(a.registro)},
        "appaiati_letti": {"path": a.appaiati.replace("\\", "/"),
                           "sha256": _sha256(a.appaiati),
                           "n_mock": int(N.size), "n_desi_draws": int(desi_pr.size)},
        "cancelli": {"rel_max": REL_MAX,
                     "dal_record": [n for _o, n, _d in e1],
                     "campi_riprodotti": len(e2),
                     "superati": True},
        "margine_1_z": {"quantita": "|z_residual|", "valore": z, "soglia": min_z,
                        "verso": ">", **m_z},
        "margine_2_frazione_spettrale": varianti,
        "limiti_dichiarati": [
            "Al denominatore della frazione spettrale c'e' desi_orig, il campo osservato, "
            "che e' N = 1. Ricampionare i mock non tocca quella componente, e la variante "
            "(b) ricampiona le estrazioni della randomizzazione di fase, non il campo. "
            "Nessun bootstrap qui chiude quella parte dell'incertezza.",
            "Con %d mock la sd del bootstrap ha essa stessa un'incertezza relativa "
            "dell'ordine di 1/sqrt(2*(n-1)) = %.1f%%: i margini si leggono a una cifra "
            "significativa." % (int(N.size), 100.0 / math.sqrt(2 * (int(N.size) - 1))),
            "Il rango del record e' confrontabile con l'1/101 di NGC solo a parita' di "
            "numerosita': qui %d mock e %d estrazioni." % (int(N.size), int(desi_pr.size)),
            "La frazione spettrale non ha una versione per singolo mock: e' un rapporto "
            "fra medie d'insieme, e la sua dispersione si ottiene solo per "
            "ricampionamento delle coppie.",
        ],
    }

    if a.out:
        cartella = os.path.dirname(os.path.abspath(a.out))
        if cartella and not os.path.isdir(cartella):
            os.makedirs(cartella, exist_ok=True)
        tmp = a.out + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(uscita, ensure_ascii=False) + "\n")
        with open(a.out, "ab") as dst, open(tmp, "rb") as src:
            dst.write(src.read())
        os.remove(tmp)
        print("")
        print("  record appeso a %s" % a.out)

    print("")
    print("ESITO: CLEAN")
    return 0


# --------------------------------------------------------------------------------------


def _finti_appaiati(path, n_mock=100, n_draws=50, seed=7):
    """Un file appaiato con la forma che load_pairs legge: la coppia sulla stessa riga."""
    rng = np.random.default_rng(seed)
    N = rng.normal(9000.0, 300.0, n_mock)
    N_phi = N + rng.normal(250.0, 180.0, n_mock)
    desi = rng.normal(8200.0, 157.0, n_draws)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for i in range(n_mock):
            fh.write(json.dumps({"tipo": "mock_pr", "idx": i,
                                 "N_H1_orig": float(N[i]), "N_H1": float(N_phi[i])}) + "\n")
        for v in desi:
            fh.write(json.dumps({"tipo": "desi_pr", "N_H1": float(v)}) + "\n")
    return N, N_phi, desi


def cmd_selftest(a=None):
    import subprocess
    import tempfile
    import shutil

    load_pairs, compute, SGC_PRED, margine = _importa()
    esiti = []

    def check(cond, testo):
        esiti.append((bool(cond), testo))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", testo))

    base = tempfile.mkdtemp(prefix="g53m_")
    io_ = os.path.abspath(__file__)
    try:
        app = os.path.join(base, "fasi_mock_pr_v1_SGC.jsonl")
        N, N_phi, desi = _finti_appaiati(app)
        desi_orig = 7900.0
        got = compute(*load_pairs(app), desi_orig)
        got.update({"schema": "paper2_gate53_v1", "region": "SGC", "desi": desi_orig,
                    "source": app, "utc": "2026-08-31T14:50:06Z", "pass": True, "fails": []})
        reg = os.path.join(base, "gate53.jsonl")
        with open(reg, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"schema": "paper2_gate53_v1", "region": "NGC"}) + "\n")
            fh.write(json.dumps(got, sort_keys=True, default=float) + "\n")

        out = os.path.join(base, "margini.jsonl")
        cmd = [sys.executable, io_, "margini", "--registro", reg, "--appaiati", app,
               "--region", "SGC", "--boot", "800", "--out", out]
        p = subprocess.run(cmd, capture_output=True, text=True)
        check(p.returncode == 0, "01 la CLI esce con 0 su registro e appaiati coerenti")
        check("ESITO: CLEAN" in p.stdout, "02 l'esito e' stampato")
        check("cancello 1" in p.stdout and "cancello 2" in p.stdout,
              "03 i due cancelli girano prima dei margini")
        check("tutti i campi tornano, rank compreso" in p.stdout,
              "04 compute() sui file congelati riproduce ogni campo del record")

        with open(out, encoding="utf-8") as fh:
            u = json.loads(fh.read().strip())
        check(u["schema"] == "paper2_gate53_margini_v1", "05 lo schema d'uscita e' dichiarato")
        check(u["soglie"]["spectral_fraction_range"] == [0.7, 0.82]
              and u["soglie"]["min_z_residual"] == 3.0,
              "06 le soglie vengono da SGC_PRED importato, non riscritte")

        m1 = u["margine_1_z"]
        atteso = margine(abs(float(got["z_residual"])), 1.0, 3.0, ">")
        check(_rel(m1["margine_in_sigma"], atteso["margine_in_sigma"]) == 0.0,
              "07 il margine di |z| e' |z| - 3, da margine() importata")
        check(m1["sd"] == 1.0 and "costruzione" in m1["denominatore"],
              "08 sd = 1 e' dichiarato come costruzione, non come assunzione")

        v = u["margine_2_frazione_spettrale"]
        check(set(v) == {"a_solo_mock", "b_mock_e_estrazioni_desi"},
              "09 entrambe le varianti del bootstrap sono riportate")
        check("PRIMARIA" in v["a_solo_mock"]["nota"]
              and "ACCANTO" in v["b_mock_e_estrazioni_desi"]["nota"],
              "10 quale sia la primaria e' scritto nel record")
        check(v["b_mock_e_estrazioni_desi"]["sd"] >= v["a_solo_mock"]["sd"],
              "11 ricampionare anche le estrazioni DESI non restringe la dispersione")
        for et in v:
            check("dall_estremo_inferiore" in v[et] and "dall_estremo_superiore" in v[et],
                  "12-%s due margini etichettati, uno per estremo" % et[0])
        dentro = v["a_solo_mock"]["dentro"]
        if dentro:
            check(v["a_solo_mock"]["margine_riportato"] ==
                  min(v["a_solo_mock"]["dall_estremo_inferiore"]["margine_in_sigma"],
                      v["a_solo_mock"]["dall_estremo_superiore"]["margine_in_sigma"]),
                  "13 dentro l'intervallo si riporta il minore dei due")
            check("MINORE" in v["a_solo_mock"]["margine_riportato_e"],
                  "14 e il record dichiara che e' il minore")
        else:
            check(v["a_solo_mock"]["margine_riportato"] is None,
                  "13 fuori dall'intervallo non si riporta un margine unico")
            check("fuori" in v["a_solo_mock"]["margine_riportato_e"],
                  "14 e il record dice perche'")

        check(any("N = 1" in x for x in u["limiti_dichiarati"]),
              "15 il limite del campo osservato N=1 e' dichiarato")
        check(any("per singolo mock" in x for x in u["limiti_dichiarati"]),
              "16 e' dichiarato che la frazione per mock non esiste")
        check(any("1/sqrt" in x for x in u["limiti_dichiarati"]),
              "17 l'incertezza della sd del bootstrap e' dichiarata")
        check(u["appaiati_letti"]["sha256"] == _sha256(app)
              and u["registro_letto"]["sha256"] == _sha256(reg),
              "18 gli sha dei due file letti sono nel record")

        # riproducibilita' del bootstrap
        out2 = os.path.join(base, "m2.jsonl")
        subprocess.run(cmd[:-1] + [out2], capture_output=True, text=True)
        with open(out2, encoding="utf-8") as fh:
            u2 = json.loads(fh.read().strip())
        check(u2["margine_2_frazione_spettrale"]["a_solo_mock"]["sd"]
              == v["a_solo_mock"]["sd"],
              "19 stesso seed, stessa sd: il bootstrap e' riproducibile")
        out3 = os.path.join(base, "m3.jsonl")
        p3 = subprocess.run(cmd[:-1] + [out3, "--seed", "12345"],
                            capture_output=True, text=True)
        with open(out3, encoding="utf-8") as fh:
            u3 = json.loads(fh.read().strip())
        check(u3["margine_2_frazione_spettrale"]["a_solo_mock"]["sd"]
              != v["a_solo_mock"]["sd"],
              "20 seed diverso, sd diversa: il seed conta e sta nel record")

        # NGC rifiutato
        p = subprocess.run([sys.executable, io_, "margini", "--registro", reg,
                            "--appaiati", app, "--region", "NGC"],
                           capture_output=True, text=True)
        check(p.returncode != 0 and "non una predizione" in (p.stdout + p.stderr),
              "21 --region NGC e' rifiutato: la' c'e' un cancello, non una predizione")

        # cancello 1: z_residual manomesso nel record
        reg_ko = os.path.join(base, "gate53_ko1.jsonl")
        g = dict(got)
        g["z_residual"] = float(got["z_residual"]) * (1 + 1e-9)
        with open(reg_ko, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(g, default=float) + "\n")
        p = subprocess.run([sys.executable, io_, "margini", "--registro", reg_ko,
                            "--appaiati", app, "--region", "SGC", "--boot", "50"],
                           capture_output=True, text=True)
        check(p.returncode != 0 and "CANCELLO FALLITO" in p.stdout,
              "22 z_residual spostato di 1e-9 ferma il cancello 1")

        # cancello 2: file appaiati diversi da quelli che hanno prodotto il record
        app_ko = os.path.join(base, "appaiati_altri.jsonl")
        _finti_appaiati(app_ko, seed=99)
        p = subprocess.run([sys.executable, io_, "margini", "--registro", reg,
                            "--appaiati", app_ko, "--region", "SGC", "--boot", "50"],
                           capture_output=True, text=True)
        check(p.returncode != 0 and "CANCELLO FALLITO" in p.stdout,
              "23 file appaiati che non riproducono il record fermano il cancello 2")
        check("nessun margine calcolato" in p.stdout,
              "24 e nessun margine viene calcolato comunque")

        # schema, regione, file assenti
        reg_s = os.path.join(base, "gate53_schema.jsonl")
        g = dict(got)
        g["schema"] = "altro_v2"
        with open(reg_s, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(g, default=float) + "\n")
        p = subprocess.run([sys.executable, io_, "margini", "--registro", reg_s,
                            "--appaiati", app, "--region", "SGC"],
                           capture_output=True, text=True)
        check(p.returncode != 0 and "schema inatteso" in (p.stdout + p.stderr),
              "25 uno schema diverso e' rifiutato, non interpretato")
        p = subprocess.run([sys.executable, io_, "margini", "--registro", reg,
                            "--appaiati", os.path.join(base, "niente.jsonl"),
                            "--region", "SGC"], capture_output=True, text=True)
        check(p.returncode != 0, "26 file appaiati assente fa fallire")

        # sola lettura e append-only
        sha_reg, sha_app = _sha256(reg), _sha256(app)
        subprocess.run(cmd, capture_output=True, text=True)
        check(_sha256(reg) == sha_reg and _sha256(app) == sha_app,
              "27 registro e appaiati non vengono toccati")
        with open(out, encoding="utf-8") as fh:
            n = len([x for x in fh if x.strip()])
        check(n == 2, "28 l'uscita e' append-only: due passate, due righe")
        check(not os.path.exists(out + ".tmp"), "29 nessun temporaneo lasciato indietro")

        # le coppie restano appaiate: rompere l'appaiamento cambia la sd
        rng = np.random.default_rng(3)
        Np = np.array(N_phi)
        rng.shuffle(Np)
        sd_app = _bootstrap(np.array(N), np.array(N_phi), np.array(desi), desi_orig,
                            800, SEED_DEFAULT, False)["sd"]
        sd_rotto = _bootstrap(np.array(N), Np, np.array(desi), desi_orig,
                              800, SEED_DEFAULT, False)["sd"]
        check(sd_app != sd_rotto,
              "30 l'appaiamento conta: mescolare N_phi cambia la dispersione")

    finally:
        shutil.rmtree(base, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="paper2_gate53_margini.py",
        description="I due margini della predizione SGC di gate53, dai registri congelati.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("margini")
    q.add_argument("--registro", required=True, help="results\\paper2\\gate53.jsonl")
    q.add_argument("--appaiati", required=True,
                   help="results\\paper2\\fasi_mock_pr_v1_SGC.jsonl — il file di coppie "
                        "che ha prodotto il record")
    q.add_argument("--region", required=True, choices=["NGC", "SGC"])
    q.add_argument("--boot", type=int, default=BOOT_DEFAULT)
    q.add_argument("--seed", type=int, default=SEED_DEFAULT)
    q.add_argument("--out", default=None)
    q.set_defaults(func=cmd_margini)

    q = sub.add_parser("selftest")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
