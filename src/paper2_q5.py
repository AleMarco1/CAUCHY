#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_q5.py — il margine di Q5, letto dal registro che tiene i numeri.

PERCHE' ESISTE
    Il docstring di `paper2_compD_nonlinear.py` dichiara CINQUE predizioni per D6:

        Q5  R^2_cv(P(k)) resta SOTTO il tetto 0.832 dei predittori misurati.
            Se lo superasse, P(k) starebbe catturando anche il termine HOD, il che
            significherebbe che il cache non e' quello che credo.

    ed e' emessa dalla riga 290 dello stesso file. Ma il dizionario `SOGLIE` di
    `paper2_d6_incertezze.py` (riga 70) ne contiene QUATTRO: Q1, Q2, Q3, Q4. Per questo
    il margine di Q5 non e' mai stato calcolato, il record 63 non la nomina, la checklist
    alla riga 602 dice «D6 con P1 e Q1-Q4» e la sezione 3-bis di `paper2_5_5_smentite.md`
    ne porta quattro. In tutto il ledger Q5 compare UNA volta, nel record 1, come
    predizione che sara' ripetuta su v2. Il suo esito non e' mai stato raccolto.

CHE COSA FA
    Legge `results/paper2/d6_incertezze.jsonl` — il registro che tiene i numeri — e
    applica la MEDESIMA funzione `margine()` di `paper2_d6_incertezze.py`, importata e
    non riscritta. Non rifa' nessuna regressione: se un numero non e' nel registro, lo
    dichiara mancante invece di ricavarlo.

CANCELLO DI RIPRODUZIONE
    Prima di calcolare Q5 ricalcola i margini di Q1-Q4 dalle quantita' del record e li
    confronta con `rec["soglie"]` a rel <= 1e-12. Se uno solo non torna, si ferma: vuol
    dire che il percorso di lettura non e' quello che ha prodotto il record 63, e un Q5
    calcolato su quel percorso non sarebbe confrontabile con gli altri quattro.

LE DUE FORME, ENTRAMBE RIPORTATE
    Q3 e' dichiarata sulla forma `ln_di_log10P_come_nel_codice` — il doppio logaritmo
    accidentale — perche' quella e' la procedura su cui il run di agosto ha girato. Q5 e'
    dichiarata nello stesso docstring e sullo stesso predittore, quindi il suo esito di
    riferimento sta sulla stessa forma. La forma dichiarata `log10P_come_nel_cache` si
    riporta accanto, etichettata, mai al posto dell'altra.

DUE PROCEDURE, DUE QUANTITA' DIVERSE — e non si mescolano
    Q5 parla di «R^2_cv(P(k))», e di R^2_cv(P(k)) ne esistono due:

      (a) la procedura su cui Q5 E' STATA DICHIARATA: regressione LINEARE su 12 componenti
          principali di P(k), registro `d6_incertezze.jsonl`, chiave
          B/<forma>/migliore/r2cv_media. Questa procedura ha SOLO la dispersione fra
          partizioni: un bootstrap sulle realizzazioni per il modello lineare non esiste.
      (b) lo STESSO STIMATORE AI DUE LATI: kernel ridge su 110 bin, registro
          `d6bis.jsonl`, chiave stime/K. Questa ha entrambe le dispersioni, e la
          `sd_ensemble` e' quella che decide un attraversamento di soglia.

    Le due si riportano accanto, mai una al posto dell'altra: e' la stessa disciplina che
    il record 63 ha imposto a Q3, che «tiene per la procedura su cui era dichiarata».

    LA `sd_ensemble` DEL KERNEL APPARTIENE A K, NON AL VALORE LINEARE. In rev.1 c'era
    un'opzione `--sd-bootstrap` che prendeva un numero dalla riga di comando: permetteva
    di attaccare la dispersione d'insieme del kernel al valore della procedura (a), che
    e' un'altra quantita'. E' stata TOLTA e sostituita da `--registro-kernel`, cosi' il
    valore e la sua dispersione arrivano sempre dalla stessa riga dello stesso registro.

USO
    python src\\paper2_q5.py margine --registro results\\paper2\\d6_incertezze.jsonl --region NGC
    python src\\paper2_q5.py margine --registro results\\paper2\\d6_incertezze.jsonl --registro-kernel results\\paper2\\d6bis.jsonl --region NGC --out results\\paper2\\q5_margine.jsonl
    python src\\paper2_q5.py selftest

Sola lettura sul registro. Uscita JSONL append-only e atomica.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

REV = "paper2_q5 rev.2"
REL_MAX = 1e-12

# La forma su cui Q3 e' dichiarata, e quindi Q5.
FORMA_RIF = "ln_di_log10P_come_nel_codice"
FORMA_DICHIARATA = "log10P_come_nel_cache"

# Q1-Q4 come stanno in paper2_d6_incertezze.SOGLIE, col percorso della quantita' e della
# sua dispersione dentro il record. Serve al cancello: si ricalcolano e si confrontano.
QUATTRO = {
    "Q1_quadrati": (["A", "gain_quad", "media"], ["A", "gain_quad", "sd_appaiata"], 0.05, "<"),
    "Q2_interazioni": (["A", "gain_int", "media"], ["A", "gain_int", "sd_appaiata"], 0.03, "<"),
    "Q3_B_sopra_mezzo": (["B", FORMA_RIF, "migliore", "r2cv_media"],
                         ["B", FORMA_RIF, "migliore", "r2cv_sd"], 0.50, ">"),
    "Q4_meta_divario": (["C", "base_divario_parametri", "frazione_chiusa"],
                        ["C", "base_divario_parametri", "sd"], 0.50, ">"),
}

# schema e chiavi del registro del kernel, letti da src/paper2_d6bis_kernel.py
SCHEMA_KERNEL = "paper2_d6bis_kernel_v1"
INGRESSO_KERNEL = "K"          # log10 P(k), 110 bin -> tetto 0.832
RAPPORTO_DICHIARATO = (2.8, 3.8)   # sd_ensemble / sd_partizione, consegna del 13 set

TESTO_Q5 = ("R^2_cv(P(k)) resta SOTTO il tetto dei predittori misurati. Se lo superasse, "
            "P(k) starebbe catturando anche il termine HOD, il che significherebbe che il "
            "cache non e' quello che credo.")


def _importa():
    """margine() e CEIL_MEASURED si importano, non si riscrivono. Fallisce esplicitamente."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from paper2_d6_incertezze import margine  # noqa: E402
    except Exception as e:
        raise SystemExit("ERRORE: non riesco a importare margine() da "
                         "paper2_d6_incertezze.py: %s: %s" % (type(e).__name__, e))
    try:
        from paper2_compD_nonlinear import CEIL_MEASURED  # noqa: E402
    except Exception as e:
        raise SystemExit("ERRORE: non riesco a importare CEIL_MEASURED da "
                         "paper2_compD_nonlinear.py: %s: %s" % (type(e).__name__, e))
    return margine, float(CEIL_MEASURED)


def _dig(rec, percorso):
    cur = rec
    for k in percorso:
        if not isinstance(cur, dict) or k not in cur:
            raise KeyError("/".join(percorso))
        cur = cur[k]
    return cur


def _rel(a, b):
    d = max(abs(a), abs(b))
    return 0.0 if d == 0 else abs(a - b) / d


def _carica_registro(path, region):
    """Ultimo record della regione chiesta. La scelta e' dichiarata, non implicita."""
    if not os.path.isfile(path):
        raise SystemExit("ERRORE: registro assente: %s" % path)
    trovati = []
    with open(path, "r", encoding="utf-8") as f:
        for i, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                r = json.loads(linea)
            except json.JSONDecodeError as e:
                raise SystemExit("ERRORE: riga %d del registro malformata: %s" % (i, e))
            if r.get("region") == region:
                trovati.append((i, r))
    if not trovati:
        raise SystemExit("ERRORE: nessun record con region=%s in %s" % (region, path))
    return trovati[-1][0], trovati[-1][1], len(trovati)


def _cancello(rec, margine):
    """Ricalcola Q1-Q4 dal record e li confronta con rec['soglie'] a rel <= 1e-12."""
    esiti = []
    soglie = rec.get("soglie")
    if not isinstance(soglie, dict):
        raise SystemExit("ERRORE: il record non porta la sezione 'soglie': "
                         "non e' un record di paper2_d6_incertezze")
    for nome, (p_val, p_sd, soglia, verso) in QUATTRO.items():
        if nome not in soglie:
            esiti.append((False, nome, "assente da rec['soglie']"))
            continue
        try:
            v = float(_dig(rec, p_val))
            sd = float(_dig(rec, p_sd))
        except KeyError as e:
            esiti.append((False, nome, "quantita' assente dal record: %s" % e))
            continue
        mio = margine(v, sd, soglia, verso)
        suo = soglie[nome]
        for campo in ("valore", "sd", "soglia", "margine_in_sigma"):
            if campo not in suo:
                esiti.append((False, nome, "campo '%s' assente" % campo))
                break
            r = _rel(float(mio[campo]), float(suo[campo]))
            if r > REL_MAX:
                esiti.append((False, nome, "%s: rel = %.3e > %.0e" % (campo, r, REL_MAX)))
                break
        else:
            if mio["esito"] != suo.get("esito"):
                esiti.append((False, nome, "esito: '%s' contro '%s'"
                              % (mio["esito"], suo.get("esito"))))
            else:
                esiti.append((True, nome, "rel = 0.0 su valore, sd, soglia, margine, esito"))
    return esiti


def _cancello_kernel(k, ceil_atteso, n_atteso):
    """Coerenza interna del record del kernel. Tutto letto dal record, niente ricalcolato."""
    esiti = []

    def voce(ok, nome, det):
        esiti.append((ok, nome, det))

    if k.get("schema") != SCHEMA_KERNEL:
        voce(False, "schema", "atteso %s, trovato %s" % (SCHEMA_KERNEL, k.get("schema")))
        return esiti
    voce(True, "schema", k["schema"])

    if "stime" not in k or INGRESSO_KERNEL not in k["stime"]:
        voce(False, "stime/%s" % INGRESSO_KERNEL, "assente dal record")
        return esiti
    st = k["stime"][INGRESSO_KERNEL]

    for campo in ("r2cv_media", "sd_partizione", "sd_ensemble", "tetto", "quota_del_tetto",
                  "rapporto_sd"):
        if campo not in st:
            voce(False, campo, "assente da stime/%s" % INGRESSO_KERNEL)
            return esiti

    r = _rel(float(st["tetto"]), ceil_atteso)
    voce(r <= REL_MAX, "tetto di K",
         "registro kernel %.16f contro %.16f, rel = %.3e" % (float(st["tetto"]),
                                                             ceil_atteso, r))

    q = float(st["r2cv_media"]) / float(st["tetto"])
    r = _rel(q, float(st["quota_del_tetto"]))
    voce(r <= REL_MAX, "quota_del_tetto", "ricalcolata, rel = %.3e" % r)

    rr = float(st["sd_ensemble"]) / float(st["sd_partizione"])
    r = _rel(rr, float(st["rapporto_sd"]))
    voce(r <= REL_MAX, "rapporto_sd", "ricalcolato %.6f, rel = %.3e" % (rr, r))

    if n_atteso is not None:
        voce(int(k.get("n", -1)) == int(n_atteso),
             "stessa coorte", "n = %s contro %s del registro lineare"
             % (k.get("n"), n_atteso))
    return esiti


def cmd_margine(a):
    margine, ceil_importato = _importa()

    riga, rec, quanti = _carica_registro(a.registro, a.region)

    print("=== %s ===" % REV)
    print("  registro   : %s" % a.registro)
    print("  region     : %s   (record alla riga %d; %d record per questa regione, "
          "si usa l'ULTIMO)" % (a.region, riga, quanti))
    print("  schema     : %s" % rec.get("schema"))
    print("  misurato   : %s   n = %s, k = %s, ripetizioni = %s"
          % (rec.get("utc"), rec.get("n"), rec.get("k_fold"), rec.get("ripetizioni")))

    # il tetto si legge dal record, e si confronta con la costante del codice
    ceil_rec = rec.get("ceil_measured")
    if ceil_rec is None:
        raise SystemExit("ERRORE: il record non porta 'ceil_measured'.")
    ceil_rec = float(ceil_rec)
    r = _rel(ceil_rec, ceil_importato)
    print("  tetto      : registro %.16f   codice %.16f   rel = %.3e"
          % (ceil_rec, ceil_importato, r))
    if r > REL_MAX:
        raise SystemExit("FALLIMENTO: il tetto del registro e quello del codice differiscono "
                         "di rel = %.3e. Q5 e' dichiarata su UN tetto: non si scelgono "
                         "due valori." % r)

    print("")
    print("  cancello di riproduzione su Q1-Q4 (rel <= %.0e):" % REL_MAX)
    esiti = _cancello(rec, margine)
    for ok, nome, det in esiti:
        print("    [%s] %-18s %s" % ("ok" if ok else "FALLITO", nome, det))
    if not all(ok for ok, _n, _d in esiti):
        print("")
        print("ESITO: CANCELLO FALLITO — Q5 non viene calcolata.")
        print("  Il percorso di lettura non riproduce i margini del record 63, quindi un Q5")
        print("  calcolato qui non sarebbe confrontabile con gli altri quattro.")
        return 1

    # --- Q5, sulle due forme
    print("")
    print("  Q5 — soglia %.16f, verso '<'  (il docstring la cita come 0.832)" % ceil_rec)
    print("")
    print("  (a) procedura su cui Q5 e' stata DICHIARATA — lineare su componenti di P(k)")
    forme = {}
    for nome_forma in (FORMA_RIF, FORMA_DICHIARATA):
        try:
            mg = _dig(rec, ["B", nome_forma, "migliore"])
        except KeyError:
            print("    [manca] forma '%s' assente dal record" % nome_forma)
            continue
        v, sd = float(mg["r2cv_media"]), float(mg["r2cv_sd"])
        m = margine(v, sd, ceil_rec, "<")
        m["ncomp"] = mg.get("ncomp")
        m["denominatore"] = "partizioni della CV ripetuta (r2cv_sd)"
        forme[nome_forma] = m
        etichetta = "di riferimento" if nome_forma == FORMA_RIF else "dichiarata"
        print("    %-30s (%s, ncomp %s)" % (nome_forma, etichetta, mg.get("ncomp")))
        print("      valore %.6f   sd %.6f   ->  %s a %.1f sigma dalla soglia   [%s]"
              % (v, sd, m["esito"], m["margine_in_sigma"],
                 "decidibile" if m["decidibile"] else "NON decidibile"))

    if FORMA_RIF not in forme:
        raise SystemExit("ERRORE: la forma di riferimento '%s' non e' nel record: "
                         "Q5 non e' calcolabile." % FORMA_RIF)

    print("")
    print("    Denominatore: partizioni della CV ripetuta. Per questa procedura un")
    print("    bootstrap sulle realizzazioni NON esiste, quindi qui il denominatore che")
    print("    decide resta assente — e non si prende in prestito da un'altra procedura.")

    # --- (b) lo stesso stimatore ai due lati: il registro del kernel
    kernel = None
    if a.registro_kernel:
        riga_k, k_rec, quanti_k = _carica_registro(a.registro_kernel, a.region)
        print("")
        print("  (b) stesso stimatore ai due lati — %s" % a.registro_kernel)
        print("      record alla riga %d; %d per questa regione, si usa l'ULTIMO; "
              "misurato %s" % (riga_k, quanti_k, k_rec.get("utc")))
        esiti_k = _cancello_kernel(k_rec, ceil_rec, rec.get("n"))
        for ok, nome, det in esiti_k:
            print("      [%s] %-16s %s" % ("ok" if ok else "FALLITO", nome, det))
        if not all(ok for ok, _n, _d in esiti_k):
            print("")
            print("ESITO: CANCELLO FALLITO sul registro del kernel — Q5 esce solo su (a).")
            return 1
        st = k_rec["stime"][INGRESSO_KERNEL]
        v_k = float(st["r2cv_media"])
        m_part = margine(v_k, float(st["sd_partizione"]), ceil_rec, "<")
        m_ens = margine(v_k, float(st["sd_ensemble"]), ceil_rec, "<")
        rapp = float(st["rapporto_sd"])
        dentro = RAPPORTO_DICHIARATO[0] <= rapp <= RAPPORTO_DICHIARATO[1]
        print("      ingresso %s (%s), valore %.6f" % (INGRESSO_KERNEL, "kernel ridge", v_k))
        print("        sd_partizione %.6f  ->  %s a %.1f sigma"
              % (float(st["sd_partizione"]), m_part["esito"], m_part["margine_in_sigma"]))
        print("        sd_ensemble   %.6f  ->  %s a %.1f sigma   <- DECIDE"
              % (float(st["sd_ensemble"]), m_ens["esito"], m_ens["margine_in_sigma"]))
        print("        rapporto fra le due dispersioni: %.3f  (la consegna del 13 set "
              "dichiara 2.8-3.8: %s)" % (rapp, "dentro" if dentro else "FUORI, da spiegare"))
        kernel = {
            "registro": a.registro_kernel.replace("\\", "/"), "riga": riga_k,
            "record_per_regione": quanti_k, "utc_misura": k_rec.get("utc"),
            "ingresso": INGRESSO_KERNEL, "n": k_rec.get("n"),
            "valore": v_k, "iperparametri": st.get("iperparametri"),
            "sul_denominatore_partizioni": dict(m_part, denominatore="partizioni della CV"),
            "sul_denominatore_che_decide": dict(
                m_ens, denominatore="bootstrap sulle realizzazioni, fold per realizzazione "
                                    "di origine"),
            "rapporto_sd": rapp,
            "rapporto_dichiarato": list(RAPPORTO_DICHIARATO),
            "rapporto_dentro_il_dichiarato": bool(dentro),
        }
    else:
        print("")
        print("  (b) stesso stimatore ai due lati: NON LETTO.")
        print("      Passare --registro-kernel results\\paper2\\d6bis.jsonl per il")
        print("      denominatore che decide. Q5 esce solo sulla procedura dichiarata.")

    uscita = {
        "schema": "paper2_q5_v1",
        "rev": REV,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "region": a.region,
        "predizione": "Q5",
        "testo_dichiarato": TESTO_Q5,
        "dichiarata_in": ("docstring PREDICTIONS di src/paper2_compD_nonlinear.py; "
                          "emessa alla riga 290 dello stesso file; ledger record 1 "
                          "(«P1-P5 e Q1-Q5 invariate»)"),
        "assente_da": ("SOGLIE di src/paper2_d6_incertezze.py; ledger record 63; "
                       "checklist riga 602 («D6 con P1 e Q1-Q4»); sezione 3-bis di "
                       "papers/paper2/paper2_5_5_smentite.md"),
        "registro_letto": {"path": a.registro.replace("\\", "/"), "riga": riga,
                           "record_per_regione": quanti, "utc_misura": rec.get("utc"),
                           "schema": rec.get("schema")},
        "soglia": ceil_rec,
        "verso": "<",
        "cancello_riproduzione": {
            "rel_max": REL_MAX,
            "voci": [n for _ok, n, _d in esiti],
            "superato": True,
        },
        "a_procedura_dichiarata": {
            "descrizione": "regressione lineare su componenti principali di P(k)",
            "registro": a.registro.replace("\\", "/"),
            "forme": forme,
            "denominatore_che_decide": "assente per questa procedura: il bootstrap sulle "
                                       "realizzazioni non esiste per il modello lineare",
        },
        "b_stesso_stimatore_ai_due_lati": kernel,
        "denominatore_che_decide": ("bootstrap sulle realizzazioni (registro del kernel)"
                                    if kernel else "assente"),
        "limiti_dichiarati": [
            "Q5 e' dichiarata sulla procedura di agosto: lineare sulle componenti "
            "principali di ln(log10 P), la forma col doppio logaritmo. L'esito sulla "
            "forma dichiarata log10 P e' riportato accanto, non al posto.",
            "K e' il P(k) della materia oscura nel box a z = 0, non il due punti del "
            "campo di cui si misura la topologia.",
            "47 dei 110 bin stanno sopra Nyquist.",
        ],
    }

    if a.out:
        cartella = os.path.dirname(os.path.abspath(a.out))
        if cartella and not os.path.isdir(cartella):
            os.makedirs(cartella, exist_ok=True)
        tmp = a.out + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(uscita, ensure_ascii=False) + "\n")
        with open(a.out, "ab") as dst, open(tmp, "rb") as src:
            dst.write(src.read())
        os.remove(tmp)
        print("")
        print("  record appeso a %s" % a.out)

    print("")
    print("ESITO: CLEAN")
    return 0


# --------------------------------------------------------------------------------------


def _registro_finto(ceil):
    """Un record con la stessa forma di paper2_d6_incertezze, numeri del record 63."""
    from paper2_d6_incertezze import margine
    rec = {
        "schema": "paper2_d6_incertezze_v1", "region": "NGC", "n": 2000,
        "utc": "2026-09-13T10:00:00Z", "k_fold": 5, "ripetizioni": 20,
        "ceil_params": 0.6979988567812268, "ceil_measured": ceil,
        "A": {"gain_quad": {"media": 0.0505, "sd_appaiata": 0.0172},
              "gain_int": {"media": 0.0546, "sd_appaiata": 0.0091},
              "order1": {"r2cv_media": 0.2554, "r2cv_sd": 0.0120}},
        # valori del LINEARE (registro d6_incertezze), diversi da quelli del kernel:
        # se la fixture usasse gli stessi, il controllo 20 non potrebbe fallire.
        "B": {"ln_di_log10P_come_nel_codice":
              {"migliore": {"ncomp": 12, "r2cv_media": 0.317658, "r2cv_sd": 0.007325}},
              "log10P_come_nel_cache":
              {"migliore": {"ncomp": 12, "r2cv_media": 0.308368, "r2cv_sd": 0.007648}}},
        "C": {"base_divario_parametri": {"frazione_chiusa": 0.216, "sd": 0.031}},
    }
    rec["soglie"] = {
        "Q1_quadrati": margine(0.0505, 0.0172, 0.05, "<"),
        "Q2_interazioni": margine(0.0546, 0.0091, 0.03, "<"),
        "Q3_B_sopra_mezzo": margine(0.317658, 0.007325, 0.50, ">"),
        "Q4_meta_divario": margine(0.216, 0.031, 0.50, ">"),
    }
    return rec


def _kernel_finto(ceil, n=2000, region="NGC", r2=0.3808, sdp=0.0152, sde=0.0467):
    st = {"r2cv_media": r2, "sd_partizione": sdp, "sd_ensemble": sde,
          "quota_del_tetto": r2 / ceil, "tetto": ceil,
          "rapporto_sd": sde / sdp, "bootstrap_media": r2,
          "iperparametri": {"lunghezza": 4.0, "alpha": 1e-3}}
    return {"schema": SCHEMA_KERNEL, "region": region, "n": n,
            "utc": "2026-09-13T12:00:00Z", "stime": {"K": st, "P": dict(st), "PK": dict(st)}}


def cmd_selftest(a):
    import subprocess
    import tempfile
    import shutil

    margine, ceil = _importa()
    esiti = []

    def check(cond, testo):
        esiti.append((bool(cond), testo))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", testo))

    base = tempfile.mkdtemp(prefix="q5_")
    try:
        reg = os.path.join(base, "d6.jsonl")
        rec = _registro_finto(ceil)
        with open(reg, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"schema": "altro", "region": "SGC"}, ensure_ascii=False) + "\n")
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        io_ = os.path.abspath(__file__)
        out = os.path.join(base, "q5.jsonl")
        cmd = [sys.executable, io_, "margine", "--registro", reg, "--region", "NGC",
               "--out", out]
        p = subprocess.run(cmd, capture_output=True, text=True)
        check(p.returncode == 0, "01 la CLI esce con 0 su un registro buono")
        check("ESITO: CLEAN" in p.stdout, "02 l'esito e' stampato")
        check("cancello di riproduzione su Q1-Q4" in p.stdout,
              "03 il cancello gira prima di Q5")
        check(p.stdout.count("[ok] Q") == 4, "04 tutte e quattro le voci del cancello passano")

        with open(out, encoding="utf-8") as f:
            u = json.loads(f.read().strip())
        check(u["predizione"] == "Q5", "05 il record d'uscita e' su Q5")
        check(abs(u["soglia"] - ceil) == 0.0, "06 la soglia e' il tetto del registro, non 0.832 a mano")
        check(u["verso"] == "<", "07 il verso di Q5 e' '<'")
        m = u["a_procedura_dichiarata"]["forme"]["ln_di_log10P_come_nel_codice"]
        atteso = margine(0.317658, 0.007325, ceil, "<")
        check(_rel(m["margine_in_sigma"], atteso["margine_in_sigma"]) == 0.0,
              "08 il margine coincide con margine() importata, non riscritta")
        check(m["esito"] == "confermata",
              "09 Q5 regge: il valore sta sotto il tetto")
        check("log10P_come_nel_cache" in u["a_procedura_dichiarata"]["forme"],
              "10 anche la forma dichiarata e' riportata")
        check(u["denominatore_che_decide"] == "assente",
              "11 senza il registro del kernel il denominatore che decide e' assente")
        check(u["b_stesso_stimatore_ai_due_lati"] is None,
              "12 e non viene sostituito in silenzio con quello delle partizioni")
        check("Q1-Q4" in u["assente_da"] or "Q1-Q4" in str(u["assente_da"]),
              "13 il record dice da dove Q5 era assente")
        check(len(u["limiti_dichiarati"]) >= 3, "14 i limiti sono nel record")
        check(u["registro_letto"]["riga"] == 2 and u["registro_letto"]["record_per_regione"] == 1,
              "15 il record letto e' identificato per riga")

        # --- il registro del kernel
        kreg = os.path.join(base, "d6bis.jsonl")
        with open(kreg, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(_kernel_finto(ceil), ensure_ascii=False) + "\n")
        out2 = os.path.join(base, "q5b.jsonl")
        p = subprocess.run([sys.executable, io_, "margine", "--registro", reg,
                            "--registro-kernel", kreg, "--region", "NGC", "--out", out2],
                           capture_output=True, text=True)
        check(p.returncode == 0, "16 col registro del kernel la CLI passa")
        with open(out2, encoding="utf-8") as f:
            u2 = json.loads(f.read().strip())
        k = u2["b_stesso_stimatore_ai_due_lati"]
        check(u2["denominatore_che_decide"].startswith("bootstrap"),
              "17 il denominatore che decide e' dichiarato")
        att = margine(0.3808, 0.0467, ceil, "<")
        check(_rel(k["sul_denominatore_che_decide"]["margine_in_sigma"],
                   att["margine_in_sigma"]) == 0.0,
              "18 il margine d'insieme usa la sd_ensemble del kernel")
        check(_rel(k["valore"], 0.3808) == 0.0,
              "19 e il VALORE e' quello del kernel, non quello lineare: dispersione e "
              "valore vengono dalla stessa riga")
        lin = u2["a_procedura_dichiarata"]["forme"]["ln_di_log10P_come_nel_codice"]["valore"]
        check(lin != k["valore"],
              "20 le due procedure restano due quantita' distinte nel record")
        check(u2["a_procedura_dichiarata"]["denominatore_che_decide"].startswith("assente"),
              "21 per la procedura dichiarata il denominatore che decide resta assente")
        check(k["sul_denominatore_partizioni"]["denominatore"].startswith("partizioni"),
              "21b il margine sulle partizioni resta etichettato come tale")
        check(k["rapporto_dentro_il_dichiarato"] is True and
              abs(k["rapporto_sd"] - 0.0467 / 0.0152) < 1e-12,
              "21c il rapporto fra le dispersioni e' confrontato col 2.8-3.8 dichiarato")

        # cancelli sul kernel: tetto discordante, coorte diversa, coerenza interna
        for nome_f, guasto, atteso in (
                ("tetto", lambda r: r["stime"]["K"].__setitem__("tetto", 0.832), "tetto di K"),
                ("quota", lambda r: r["stime"]["K"].__setitem__("quota_del_tetto", 0.5),
                 "quota_del_tetto"),
                ("rapporto", lambda r: r["stime"]["K"].__setitem__("rapporto_sd", 9.9),
                 "rapporto_sd"),
                ("coorte", lambda r: r.__setitem__("n", 1999), "stessa coorte")):
            kko = os.path.join(base, "d6bis_%s.jsonl" % nome_f)
            rr = _kernel_finto(ceil)
            guasto(rr)
            with open(kko, "w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(rr, ensure_ascii=False) + "\n")
            pp = subprocess.run([sys.executable, io_, "margine", "--registro", reg,
                                 "--registro-kernel", kko, "--region", "NGC"],
                                capture_output=True, text=True)
            check(pp.returncode != 0 and "FALLITO" in pp.stdout and atteso in pp.stdout,
                  "22-%s il cancello del kernel prende '%s'" % (nome_f, atteso))

        kko = os.path.join(base, "d6bis_schema.jsonl")
        rr = _kernel_finto(ceil)
        rr["schema"] = "altro_v9"
        with open(kko, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rr, ensure_ascii=False) + "\n")
        pp = subprocess.run([sys.executable, io_, "margine", "--registro", reg,
                             "--registro-kernel", kko, "--region", "NGC"],
                            capture_output=True, text=True)
        check(pp.returncode != 0 and "schema" in pp.stdout,
              "22-schema uno schema diverso e' rifiutato, non interpretato")

        pp = subprocess.run([sys.executable, io_, "margine", "--registro", reg,
                             "--region", "NGC", "--sd-bootstrap", "0.0467"],
                            capture_output=True, text=True)
        check(pp.returncode != 0,
              "22-tolta l'opzione --sd-bootstrap di rev.1 non esiste piu'")

        # il cancello deve fermarsi se un margine del record e' stato manomesso
        reg_ko = os.path.join(base, "d6_ko.jsonl")
        rec_ko = json.loads(json.dumps(rec))
        rec_ko["soglie"]["Q2_interazioni"]["margine_in_sigma"] += 1e-6
        with open(reg_ko, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec_ko, ensure_ascii=False) + "\n")
        p = subprocess.run([sys.executable, io_, "margine", "--registro", reg_ko,
                            "--region", "NGC"], capture_output=True, text=True)
        check(p.returncode != 0 and "CANCELLO FALLITO" in p.stdout,
              "22 un margine manomesso di 1e-6 ferma il cancello")
        check("Q5 non viene calcolata" in p.stdout,
              "23 e Q5 non viene calcolata comunque")

        # un esito manomesso, non un numero
        reg_ko2 = os.path.join(base, "d6_ko2.jsonl")
        rec_ko2 = json.loads(json.dumps(rec))
        rec_ko2["soglie"]["Q3_B_sopra_mezzo"]["esito"] = "confermata"
        with open(reg_ko2, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec_ko2, ensure_ascii=False) + "\n")
        p = subprocess.run([sys.executable, io_, "margine", "--registro", reg_ko2,
                            "--region", "NGC"], capture_output=True, text=True)
        check(p.returncode != 0 and "esito:" in p.stdout,
              "24 anche un esito discordante ferma il cancello")

        # tetto discordante fra registro e codice
        reg_ko3 = os.path.join(base, "d6_ko3.jsonl")
        rec_ko3 = json.loads(json.dumps(rec))
        rec_ko3["ceil_measured"] = 0.832
        with open(reg_ko3, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec_ko3, ensure_ascii=False) + "\n")
        p = subprocess.run([sys.executable, io_, "margine", "--registro", reg_ko3,
                            "--region", "NGC"], capture_output=True, text=True)
        check(p.returncode != 0 and "non si scelgono" in p.stdout + p.stderr,
              "25 il tetto arrotondato a 0.832 non passa: la soglia e' una sola")

        # registro senza la sezione soglie
        reg_ko4 = os.path.join(base, "d6_ko4.jsonl")
        with open(reg_ko4, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"schema": "x", "region": "NGC",
                                "ceil_measured": ceil}, ensure_ascii=False) + "\n")
        p = subprocess.run([sys.executable, io_, "margine", "--registro", reg_ko4,
                            "--region", "NGC"], capture_output=True, text=True)
        check(p.returncode != 0 and "soglie" in p.stdout + p.stderr,
              "26 un record senza 'soglie' e' rifiutato, non interpretato")

        p = subprocess.run([sys.executable, io_, "margine", "--registro", reg,
                            "--region", "SGC"], capture_output=True, text=True)
        check(p.returncode != 0, "27 una regione senza record di misura fa fallire")
        p = subprocess.run([sys.executable, io_, "margine",
                            "--registro", os.path.join(base, "niente.jsonl"),
                            "--region", "NGC"], capture_output=True, text=True)
        check(p.returncode != 0 and "assente" in p.stdout + p.stderr,
              "28 un registro inesistente fa fallire")

        # append-only e sola lettura
        sha_prima = open(reg, "rb").read()
        subprocess.run(cmd, capture_output=True, text=True)
        check(open(reg, "rb").read() == sha_prima, "29 il registro non viene toccato")
        with open(out, encoding="utf-8") as f:
            n = len([x for x in f if x.strip()])
        check(n == 2, "30 l'uscita e' append-only: due passate, due righe")
        check(not os.path.exists(out + ".tmp"), "31 nessun temporaneo lasciato indietro")

        # l'ultimo record vince, e lo dichiara
        with open(reg, "a", encoding="utf-8", newline="\n") as f:
            rec2 = json.loads(json.dumps(rec))
            rec2["B"][FORMA_RIF]["migliore"]["r2cv_media"] = 0.3900
            rec2["soglie"]["Q3_B_sopra_mezzo"] = margine(0.3900, 0.007325, 0.50, ">")
            f.write(json.dumps(rec2, ensure_ascii=False) + "\n")
        out3 = os.path.join(base, "q5c.jsonl")
        p = subprocess.run([sys.executable, io_, "margine", "--registro", reg,
                            "--region", "NGC", "--out", out3], capture_output=True, text=True)
        check(p.returncode == 0 and "si usa l'ULTIMO" in p.stdout,
              "32 con piu' record per regione si usa l'ultimo, e lo dice")
        with open(out3, encoding="utf-8") as f:
            u3 = json.loads(f.read().strip())
        check(u3["a_procedura_dichiarata"]["forme"][FORMA_RIF]["valore"] == 0.3900,
              "33 e il valore e' quello dell'ultimo record")
        check(u3["registro_letto"]["record_per_regione"] == 2,
              "34 quanti record esistevano e' scritto nell'uscita")

    finally:
        shutil.rmtree(base, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="paper2_q5.py",
        description="Il margine di Q5, letto dal registro di misura di D6. "
                    "Nessuna regressione rifatta, nessun numero riscritto.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("margine", help="calcola il margine di Q5 dal registro")
    q.add_argument("--registro", required=True,
                   help="results\\paper2\\d6_incertezze.jsonl")
    q.add_argument("--region", required=True, choices=["NGC", "SGC"])
    q.add_argument("--registro-kernel", default=None,
                   help="results\\paper2\\d6bis.jsonl — il registro di "
                        "paper2_d6bis_kernel.py, che porta la dispersione d'insieme "
                        "insieme al valore a cui appartiene. In rev.1 c'era un'opzione "
                        "per passare la sola dispersione a mano: e' stata tolta perche' "
                        "consentiva di attaccarla a una quantita' diversa.")
    q.add_argument("--out", default=None, help="JSONL append-only di uscita")
    q.set_defaults(func=cmd_margine)

    q = sub.add_parser("selftest", help="controlli, attraversando la riga di comando")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
