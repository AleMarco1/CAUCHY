#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_fase5_a_coppie.py — rimette il campo `tipo` che la divisione in due file ha sostituito.

IL PROBLEMA, E PERCHE' NON E' UN ADATTATORE
    `load_pairs` di src/paper2_gate53.py filtra le righe su `r.get("tipo")`. I file di
    Fase 5 non hanno quel campo: il tipo sta nel NOME DEL FILE, perche' la catena di
    Fase 5 ha spezzato in due cio' che paper1_rev_n10_phases.py teneva in uno —
    `fasi_mock_pr_v1_{REG}.jsonl` e `fasi_desi_pr_{REG}.jsonl` — e ha lasciato cadere il
    discriminatore, dato che il percorso lo sostituiva. Da cui `mock_pr=0 desi_pr=0`.

    Le quantita' che servono ci sono, con gli STESSI NOMI, sulla stessa riga:
    `N_H1_orig` e `N_H1` per i mock, `N_H1` per le estrazioni. L'appaiamento e' quindi
    preservato per costruzione, come nell'originale. Non c'e' nessuna quantita' da
    ricalcolare e nessuna conversione di unita': si riscrive il discriminatore e basta.
    Questo strumento NON importa compute() e non calcola nulla di scientifico.

CIO' CHE IL FILE PRODOTTO NON HA
    L'originale porta anche `mean_pers1` e `b1_peak`, che i file di Fase 5 non hanno e che
    `load_pairs` non legge. Il file prodotto NON si chiama `n10_phases_*`: quel nome
    promette lo schema dell'originale. Si chiama `coppie_fase5_{REG}.jsonl`, e porta in
    testa un record che dichiara da dove viene e cosa gli manca. Oggi abbiamo sbagliato
    quattro volte dedicendo il contenuto dal nome; questo file non aggiunge la quinta.

IL CANCELLO CHE DECIDE SE E' LECITO USARLO
    Il record congelato di `gate53.jsonl` per NGC nasce da
    `results/paper1/n10_phases_NGC.jsonl` del 25 luglio. I file di Fase 5 sono del 9
    settembre: due produzioni diverse, a 46 giorni di distanza. Il comando `cancello`
    materializza NGC dai file di Fase 5, fa girare `paper2_gate53.py gate` su quello, e
    confronta OGNI campo col record congelato a rel <= 1e-12.

      SUPERATO -> i due produttori danno gli stessi numeri, e SGC si puo' risolvere.
      FALLITO  -> sono due misure diverse. La predizione di SGC_PRED resta NON RISOLTA
                  finche' results/paper1/n10_phases_SGC.jsonl non viene prodotto con
                  paper1_rev_n10_phases.py.

    Il cancello sta su NGC perche' NGC e' l'unico posto dove la domanda e' decidibile
    senza guardare il dato su cui la predizione non e' ancora stata risolta.

NUMEROSITA'
    100 mock e 50 estrazioni, come NGC. Se i conti non sono quelli il tool rifiuta: il
    rango di gate53 e' confrontabile con l'1/101 di NGC solo a parita' di numerosita', e
    lo dice lo script stesso.

USO
    python src\\paper2_fase5_a_coppie.py selftest
    python src\\paper2_fase5_a_coppie.py cancello --region NGC
    python src\\paper2_fase5_a_coppie.py materializza --region SGC
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time

REV = "paper2_fase5_a_coppie rev.1"
REL_MAX = 1e-12

# LA CORRISPONDENZA FRA I DUE SCHEMI, IN UN POSTO SOLO.
# A sinistra il campo che load_pairs legge, a destra quello dei file di Fase 5.
# `tipo` non compare a destra: e' cio' che manca, e viene dal file di provenienza.
CORRISPONDENZA = {
    "mock_pr": {"idx": "idx", "N_H1_orig": "N_H1_orig", "N_H1": "N_H1"},
    "desi_pr": {"idx": "idx", "N_H1": "N_H1"},
}
ATTESI = {"mock_pr": 100, "desi_pr": 50}

# campi che l'originale ha e il file prodotto non avra'. load_pairs non li legge.
NON_PORTATI = ["mean_pers1", "b1_peak"]

SORGENTI = {
    "mock_pr": os.path.join("results", "paper2", "fasi_mock_pr_v1_%s.jsonl"),
    "desi_pr": os.path.join("results", "paper2", "fasi_desi_pr_%s.jsonl"),
}
USCITA = os.path.join("results", "paper2", "coppie_fase5_%s.jsonl")
CONGELATO = os.path.join("results", "paper2", "gate53.jsonl")

CAMPI_DA_CONFRONTARE = [
    "n_mock", "n_desi_draws", "desi", "desi_phi_mean", "mock_mean", "mock_phi_mean",
    "gain_mock_mean", "gain_mock_sd", "gain_desi", "residual", "z_residual",
    "corr_N_Nphi", "spectral_fraction", "sem_procedural", "sd_draw_exact",
    "sd_deconvolved_exact", "z_deconvolved_exact", "sd_draw_published",
    "sd_deconvolved", "z_deconvolved",
]


class Rifiuto(Exception):
    pass


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _rel(a, b):
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return 0.0
    d = max(abs(a), abs(b))
    return 0.0 if d == 0 else abs(a - b) / d


def _leggi_jsonl(path):
    if not os.path.isfile(path):
        raise Rifiuto("file assente: %s" % path)
    righe = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, linea in enumerate(fh, 1):
            s = linea.strip()
            if not s:
                continue
            try:
                righe.append((i, json.loads(s)))
            except json.JSONDecodeError as e:
                raise Rifiuto("riga %d di %s malformata: %s" % (i, path, e))
    return righe


def _controlla_sorgente(path, tipo, region):
    """Cio' che serve c'e', una volta sola, finito, e sulla regione giusta."""
    righe = _leggi_jsonl(path)
    if len(righe) != ATTESI[tipo]:
        raise Rifiuto("%s: %d righe, attese %d. Il rango di gate53 e' confrontabile con "
                      "l'1/101 di NGC solo a parita' di numerosita'."
                      % (os.path.basename(path), len(righe), ATTESI[tipo]))
    campi = CORRISPONDENZA[tipo]
    visti = set()
    fuori = []
    for n, r in righe:
        for _dest, orig in campi.items():
            if orig not in r:
                raise Rifiuto("%s riga %d: manca il campo '%s'"
                              % (os.path.basename(path), n, orig))
        if "region" in r and r["region"] != region:
            raise Rifiuto("%s riga %d: region='%s', attesa '%s'"
                          % (os.path.basename(path), n, r["region"], region))
        idx = r[campi["idx"]]
        if idx in visti:
            raise Rifiuto("%s riga %d: idx %s duplicato" % (os.path.basename(path), n, idx))
        visti.add(idx)
        nuova = {"tipo": tipo}
        for dest, orig in campi.items():
            v = r[orig]
            if dest != "idx":
                v = float(v)
                if not math.isfinite(v):
                    raise Rifiuto("%s riga %d: %s non finito" % (os.path.basename(path), n,
                                                                 orig))
            nuova[dest] = v
        fuori.append(nuova)
    fuori.sort(key=lambda x: x["idx"])
    return fuori, _sha256(path)


def materializza(region, path_mock, path_desi, path_out):
    mock, sha_mock = _controlla_sorgente(path_mock, "mock_pr", region)
    desi, sha_desi = _controlla_sorgente(path_desi, "desi_pr", region)

    testata = {
        "_questo_file": "coppie per load_pairs di src/paper2_gate53.py",
        "_prodotto_da": REV,
        "_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "_region": region,
        "_sorgenti": [
            {"path": path_mock.replace("\\", "/"), "tipo": "mock_pr",
             "sha256": sha_mock, "righe": len(mock)},
            {"path": path_desi.replace("\\", "/"), "tipo": "desi_pr",
             "sha256": sha_desi, "righe": len(desi)},
        ],
        "_cosa_e_stato_aggiunto": ("il solo campo 'tipo', che i file di Fase 5 non hanno "
                                   "perche' la divisione in due file lo sostituiva. "
                                   "Nessuna quantita' ricalcolata, nessuna conversione."),
        "_corrispondenza_dichiarata": CORRISPONDENZA,
        "_campi_dell_originale_non_portati": NON_PORTATI,
        "_avvertenza": ("NON e' un n10_phases_*.jsonl: quel nome promette lo schema di "
                        "paper1_rev_n10_phases.py, che porta anche %s."
                        % ", ".join(NON_PORTATI)),
        "_nota": "questa riga non ha 'tipo', quindi load_pairs la ignora.",
    }
    cartella = os.path.dirname(os.path.abspath(path_out))
    if cartella and not os.path.isdir(cartella):
        os.makedirs(cartella, exist_ok=True)
    tmp = path_out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(testata, ensure_ascii=False) + "\n")
        for r in mock:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        for r in desi:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path_out)
    return {"mock": len(mock), "desi": len(desi), "sha256": _sha256(path_out),
            "byte": os.path.getsize(path_out), "sorgenti": testata["_sorgenti"]}


def _record_congelato(path, region):
    trovati = [r for _n, r in _leggi_jsonl(path) if r.get("region") == region]
    if not trovati:
        raise Rifiuto("nessun record con region=%s in %s" % (region, path))
    return trovati[-1]


def cmd_materializza(a):
    try:
        info = materializza(a.region, a.mock or SORGENTI["mock_pr"] % a.region,
                            a.desi or SORGENTI["desi_pr"] % a.region,
                            a.out or USCITA % a.region)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2
    out = a.out or USCITA % a.region
    print("=== %s ===" % REV)
    print("  region     : %s" % a.region)
    for s in info["sorgenti"]:
        print("  sorgente   : %-46s %d righe  sha %s"
              % (s["path"], s["righe"], s["sha256"][:16] + "..."))
    print("  prodotto   : %s   %d righe + testata, %d byte"
          % (out, info["mock"] + info["desi"], info["byte"]))
    print("  sha256     : %s" % info["sha256"])
    print("  aggiunto   : il solo campo 'tipo'. Nessuna quantita' ricalcolata.")
    print("  non portati: %s (load_pairs non li legge)" % ", ".join(NON_PORTATI))
    if a.region == "SGC":
        print("")
        print("  ATTENZIONE: usare questo file per risolvere SGC_PRED e' lecito SOLO se")
        print("  'cancello --region NGC' e' SUPERATO. Il cancello non si ricorda: si rifa'.")
    print("")
    print("ESITO: CLEAN")
    return 0


def cmd_cancello(a):
    """Materializza NGC dai file di Fase 5 e confronta col record congelato."""
    if a.region != "NGC":
        print("RIFIUTO: il cancello sta su NGC. E' l'unico posto dove esiste un record "
              "congelato con cui confrontarsi, e l'unico dove la domanda e' decidibile "
              "senza guardare il dato su cui la predizione non e' ancora stata risolta.",
              file=sys.stderr)
        return 2
    base = tempfile.mkdtemp(prefix="g53canc_")
    try:
        coppie = os.path.join(base, "coppie_NGC.jsonl")
        uscita = os.path.join(base, "gate53_prova.jsonl")
        try:
            info = materializza("NGC", a.mock or SORGENTI["mock_pr"] % "NGC",
                                a.desi or SORGENTI["desi_pr"] % "NGC", coppie)
            congelato = _record_congelato(a.congelato or CONGELATO, "NGC")
        except Rifiuto as e:
            print("RIFIUTO: %s" % e, file=sys.stderr)
            return 2

        print("=== %s — cancello su NGC ===" % REV)
        for s in info["sorgenti"]:
            print("  Fase 5     : %-46s sha %s" % (s["path"], s["sha256"][:16] + "..."))
        print("  congelato  : %s, misurato %s, sorgente dichiarata %s"
              % (a.congelato or CONGELATO, congelato.get("utc"), congelato.get("source")))
        print("  desi       : %s (dal record congelato, non dal default del codice)"
              % congelato.get("desi"))

        cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "paper2_gate53.py"),
               "gate", "--region", "NGC", "--phases", coppie,
               "--desi", repr(float(congelato["desi"])), "--out", uscita]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if not os.path.isfile(uscita):
            print("")
            print("  paper2_gate53.py e' uscito con %d senza scrivere un record:"
                  % p.returncode)
            for linea in (p.stdout + p.stderr).splitlines()[-12:]:
                print("    %s" % linea)
            print("")
            print("ESITO: FALLITO — gate53 non ha prodotto un record sui file di Fase 5.")
            return 3

        prova = _record_congelato(uscita, "NGC")

        # Su NGC gate53 applica il proprio cancello contro TARGETS_NGC, che e' un
        # SOTTOINSIEME dei campi, ed esce con codice non nullo se non lo passa. Quel
        # codice non e' fatale qui: il record c'e', e il confronto che decide e' il nostro
        # sui 21 campi. I due esiti si riportano entrambi, separati.
        print("")
        print("  cancello interno di gate53 contro TARGETS_NGC (sottoinsieme dei campi):")
        print("    uscita %d, pass=%s%s"
              % (p.returncode, prova.get("pass"),
                 ("" if not prova.get("fails") else
                  "  fails: " + "; ".join(str(x) for x in prova["fails"])[:200])))
        esiti = []
        for k in CAMPI_DA_CONFRONTARE:
            if k not in congelato or k not in prova:
                esiti.append((False, k, "assente (congelato=%s, prova=%s)"
                              % (k in congelato, k in prova)))
                continue
            r = _rel(float(congelato[k]), float(prova[k]))
            esiti.append((r <= REL_MAX, k, "rel = %.3e" % r))
        if "rank" in congelato and "rank" in prova:
            esiti.append((congelato["rank"] == prova["rank"], "rank",
                          "%s contro %s" % (congelato["rank"], prova["rank"])))

        falliti = [(n, d) for ok, n, d in esiti if not ok]
        print("")
        print("  confronto col record congelato (rel <= %.0e): %d campi, %d falliti"
              % (REL_MAX, len(esiti), len(falliti)))
        for n, d in falliti:
            print("    [FALLITO] %-24s %s" % (n, d))
        if not falliti:
            print("    [ok] tutti i campi tornano, rank compreso")

        print("")
        if falliti:
            print("ESITO: FALLITO — i due produttori NON danno gli stessi numeri.")
            print("  La predizione di SGC_PRED resta NON RISOLTA. Per risolverla va prodotto")
            print("  results/paper1/n10_phases_SGC.jsonl con paper1_rev_n10_phases.py:")
            print("  50 realizzazioni DESI a fasi randomizzate e 100 mock.")
            return 1
        print("ESITO: SUPERATO — i due produttori danno gli stessi numeri su NGC.")
        print("  Usare i file di Fase 5 per risolvere SGC_PRED e' lecito. Prossimo passo:")
        print("    python src\\paper2_fase5_a_coppie.py materializza --region SGC")
        print("    python src\\paper2_gate53.py gate --region SGC --phases "
              "results\\paper2\\coppie_fase5_SGC.jsonl --out results\\paper2\\gate53.jsonl")
        print("  e SOLO dopo aver deciso che il verdetto vale qualunque esca.")
        return 0
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)


# --------------------------------------------------------------------------------------


def _finti(base, region="NGC", n_mock=100, n_desi=50, seed=5, con_tipo=False,
           sotto=None):
    """Ogni chiamata scrive in una SOTTOCARTELLA propria: riusare gli stessi nomi nella
    stessa cartella faceva sovrascrivere le sorgenti di un test precedente."""
    import numpy as np
    cart = os.path.join(base, sotto or ("f_%s_%d_%d_%d" % (region, n_mock, n_desi, seed)))
    os.makedirs(cart, exist_ok=True)
    rng = np.random.default_rng(seed)
    pm = os.path.join(cart, "fasi_mock_pr_v1_%s.jsonl" % region)
    pd = os.path.join(cart, "fasi_desi_pr_%s.jsonl" % region)
    N = rng.normal(9000.0, 300.0, n_mock)
    Np = N + rng.normal(250.0, 180.0, n_mock)
    D = rng.normal(8200.0, 157.0, n_desi)
    with open(pm, "w", encoding="utf-8", newline="\n") as fh:
        for i in range(n_mock):
            r = {"idx": i, "region": region, "versione": "v1", "sorgente": "x",
                 "N_H1_orig": float(N[i]), "N_H1": float(Np[i]),
                 "ancora": 1, "utc": "2026-09-09T00:00:00Z"}
            if con_tipo:
                r["tipo"] = "mock_pr"
            fh.write(json.dumps(r) + "\n")
    with open(pd, "w", encoding="utf-8", newline="\n") as fh:
        for i in range(n_desi):
            r = {"idx": i, "region": region, "N_H1": float(D[i]),
                 "utc": "2026-09-09T00:00:00Z"}
            fh.write(json.dumps(r) + "\n")
    return pm, pd, N, Np, D


def cmd_selftest(a=None):
    import shutil
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from paper2_gate53 import load_pairs, compute

    esiti = []

    def check(cond, testo):
        esiti.append((bool(cond), testo))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", testo))

    base = tempfile.mkdtemp(prefix="f5c_")
    io_ = os.path.abspath(__file__)
    try:
        pm, pd, N, Np, D = _finti(base)
        out = os.path.join(base, "coppie_NGC.jsonl")

        class A(object):
            pass

        x = A()
        x.region, x.mock, x.desi, x.out = "NGC", pm, pd, out
        check(cmd_materializza(x) == 0, "01 materializza esce con 0")

        # load_pairs legge il file prodotto, e ritrova le quantita' giuste
        Nl, Npl, Dl = load_pairs(out)
        check(Nl.size == 100 and Npl.size == 100 and Dl.size == 50,
              "02 load_pairs trova 100 coppie e 50 estrazioni (era 0 e 0)")
        check(np.allclose(np.sort(Nl), np.sort(N), rtol=0, atol=0),
              "03 N_H1_orig arriva intatto, senza conversioni")
        check(np.allclose(np.sort(Npl), np.sort(Np), rtol=0, atol=0),
              "04 N_H1 arriva intatto")
        check(np.allclose(np.sort(Dl), np.sort(D), rtol=0, atol=0),
              "05 le estrazioni DESI arrivano intatte")

        # l'appaiamento e' preservato: la correlazione deve essere quella dei dati veri
        c_vero = float(np.corrcoef(N, Np)[0, 1])
        c_letto = float(np.corrcoef(Nl, Npl)[0, 1])
        check(_rel(c_vero, c_letto) <= REL_MAX,
              "06 l'appaiamento e' preservato: stessa correlazione N/N_phi")

        righe = _leggi_jsonl(out)
        check(righe[0][1].get("tipo") is None,
              "07 la testata non ha 'tipo', quindi load_pairs la ignora")
        check("_corrispondenza_dichiarata" in righe[0][1],
              "08 la corrispondenza fra schemi e' dichiarata nel file")
        check(righe[0][1]["_campi_dell_originale_non_portati"] == NON_PORTATI,
              "09 il file dice quali campi dell'originale non porta")
        check(all(s["sha256"] for s in righe[0][1]["_sorgenti"]),
              "10 la testata porta gli sha delle due sorgenti")
        check("n10_phases" not in os.path.basename(out),
              "11 il nome del file non promette lo schema dell'originale")
        check(sum(1 for _n, r in righe if r.get("tipo") == "mock_pr") == 100
              and sum(1 for _n, r in righe if r.get("tipo") == "desi_pr") == 50,
              "12 i due tipi sono scritti nelle quantita' attese")

        # numerosita' sbagliate
        pm2, pd2, _a, _b, _c = _finti(base, region="SGC", n_mock=99, n_desi=50)
        x2 = A()
        x2.region, x2.mock, x2.desi, x2.out = "SGC", pm2, pd2, os.path.join(base, "b.jsonl")
        check(cmd_materializza(x2) == 2, "13 99 mock invece di 100 -> rifiuto")
        pm3, pd3, _a, _b, _c = _finti(base, region="SGC", n_mock=100, n_desi=49)
        x2.mock, x2.desi = pm3, pd3
        check(cmd_materializza(x2) == 2, "14 49 estrazioni invece di 50 -> rifiuto")

        # regione discordante dentro le righe
        pm4, pd4, _a, _b, _c = _finti(base, region="NGC", seed=11)
        x3 = A()
        x3.region, x3.mock, x3.desi = "SGC", pm4, pd4
        x3.out = os.path.join(base, "c.jsonl")
        check(cmd_materializza(x3) == 2,
              "15 righe con region=NGC chieste come SGC -> rifiuto")

        # campo mancante, idx duplicato, valore non finito
        def guasta(trasforma, nome, atteso=2):
            p = os.path.join(base, "guasto.jsonl")
            righe = [r for _n, r in _leggi_jsonl(pm)]
            trasforma(righe)
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                for r in righe:
                    fh.write(json.dumps(r) + "\n")
            y = A()
            y.region, y.mock, y.desi = "NGC", p, pd
            y.out = os.path.join(base, "g.jsonl")
            check(cmd_materializza(y) == atteso, nome)

        guasta(lambda rr: rr[3].pop("N_H1_orig"), "16 campo mancante -> rifiuto")
        guasta(lambda rr: rr.__setitem__(4, dict(rr[3])), "17 idx duplicato -> rifiuto")
        guasta(lambda rr: rr[7].__setitem__("N_H1", float("nan")),
               "18 valore non finito -> rifiuto")

        # ordine deterministico
        p_mesc = os.path.join(base, "mescolato.jsonl")
        righe_m = [r for _n, r in _leggi_jsonl(pm)]
        righe_m.reverse()
        with open(p_mesc, "w", encoding="utf-8", newline="\n") as fh:
            for r in righe_m:
                fh.write(json.dumps(r) + "\n")
        y = A()
        y.region, y.mock, y.desi = "NGC", p_mesc, pd
        y.out = os.path.join(base, "d.jsonl")
        cmd_materializza(y)
        a1 = [r for _n, r in _leggi_jsonl(out) if r.get("tipo")]
        a2 = [r for _n, r in _leggi_jsonl(y.out) if r.get("tipo")]
        check(a1 == a2, "19 l'ordine delle righe di ingresso non cambia l'uscita")

        # il cancello: lo stesso produttore deve superarlo
        got = compute(*load_pairs(out), 8000.0)
        got.update({"schema": "paper2_gate53_v1", "region": "NGC", "desi": 8000.0,
                    "source": out, "utc": "2026-07-25T19:56:45Z"})
        cong = os.path.join(base, "gate53_congelato.jsonl")
        with open(cong, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(got, default=float) + "\n")
        p = subprocess.run([sys.executable, io_, "cancello", "--region", "NGC",
                            "--mock", pm, "--desi", pd, "--congelato", cong],
                           capture_output=True, text=True)
        check(p.returncode == 0 and "ESITO: SUPERATO" in p.stdout,
              "20 il cancello e' SUPERATO quando i numeri coincidono")
        check("tutti i campi tornano, rank compreso" in p.stdout,
              "21 e lo dice campo per campo")
        check("materializza --region SGC" in p.stdout,
              "22 e indica il passo successivo solo in caso di successo")

        # cancello fallito: record congelato di un'altra produzione
        got2 = compute(*load_pairs(out), 8000.0)
        got2["spectral_fraction"] = float(got2["spectral_fraction"]) * (1 + 1e-9)
        got2.update({"schema": "paper2_gate53_v1", "region": "NGC", "desi": 8000.0,
                     "source": "altro", "utc": "2026-07-25T19:56:45Z"})
        cong2 = os.path.join(base, "gate53_altro.jsonl")
        with open(cong2, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(got2, default=float) + "\n")
        p = subprocess.run([sys.executable, io_, "cancello", "--region", "NGC",
                            "--mock", pm, "--desi", pd, "--congelato", cong2],
                           capture_output=True, text=True)
        check(p.returncode == 1 and "ESITO: FALLITO" in p.stdout,
              "23 uno scarto di 1e-9 fa FALLIRE il cancello")
        check("NON RISOLTA" in p.stdout and "paper1_rev_n10_phases.py" in p.stdout,
              "24 e in quel caso dice che la predizione resta non risolta, e come produrla")
        check("materializza --region SGC" not in p.stdout,
              "25 e NON indica il passo successivo")

        # il desi del cancello viene dal record, non dal default del codice
        check("dal record congelato, non dal default del codice" in p.stdout,
              "26 il valore DESI usato dal cancello e' quello del record")

        p = subprocess.run([sys.executable, io_, "cancello", "--region", "SGC"],
                           capture_output=True, text=True)
        check(p.returncode == 2 and "il cancello sta su NGC" in (p.stdout + p.stderr),
              "27 il cancello su SGC e' rifiutato")

        # sola lettura sulle sorgenti
        sha_m, sha_d = _sha256(pm), _sha256(pd)
        cmd_materializza(x)
        check(_sha256(pm) == sha_m and _sha256(pd) == sha_d,
              "28 le sorgenti di Fase 5 non vengono toccate")
        avanzi = []
        for radice, _d, files in os.walk(base):
            avanzi += [f for f in files if f.endswith(".tmp")]
        check(not avanzi, "29 nessun temporaneo lasciato indietro")

        # niente compute() importata qui: questo strumento non calcola scienza
        testo = open(io_, encoding="utf-8").read()
        check("from paper2_gate53 import load_pairs, compute" not in
              testo.split("def cmd_selftest")[0],
              "30 fuori dal selftest non importa compute(): non calcola nulla di scientifico")

    finally:
        shutil.rmtree(base, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="paper2_fase5_a_coppie.py",
        description="Rimette il campo 'tipo' che la divisione in due file ha sostituito.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("materializza")
    q.add_argument("--region", required=True, choices=["NGC", "SGC"])
    q.add_argument("--mock", default=None)
    q.add_argument("--desi", default=None)
    q.add_argument("--out", default=None)
    q.set_defaults(func=cmd_materializza)

    q = sub.add_parser("cancello", help="prova l'equivalenza dei produttori su NGC")
    q.add_argument("--region", required=True, choices=["NGC", "SGC"])
    q.add_argument("--mock", default=None)
    q.add_argument("--desi", default=None)
    q.add_argument("--congelato", default=None)
    q.set_defaults(func=cmd_cancello)

    q = sub.add_parser("selftest")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
