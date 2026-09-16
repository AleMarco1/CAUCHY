#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_sgcpred_documenti.py — SGC_PRED nei documenti: B6 e la 3-bis allargata.

CHE COSA TOCCA
    papers/paper2/paper2_5_5_smentite.md   cinque modifiche
    papers/paper2/checklist_paper2.md      due modifiche (rev. 3.25 -> 3.26)
    papers/paper2/paper2_stato.md          due modifiche (nona -> decima revisione)

LA COLLOCAZIONE, COME LA FISSA IL RECORD 67
    La clausola |z| > 3 va nel gruppo B come **B6**, ancorata alla riga 66: le voci di B
    sono ancorate al record che fa la ritirata, non a quello che dichiara la predizione.
    La frazione spettrale va nella **3-bis**, non nel gruppo A, perche' il gruppo A chiede
    il record in cui la predizione e' DICHIARATA e SGC_PRED e' dichiarata nel sorgente,
    come Q1-Q5.

    I conteggi passano da 12 / 1 / 5 a **12 / 1 / 6**.

    Le due meta' di una sola prova cieca finiscono in due sezioni. Il costo e' dichiarato
    dal record 67, e il rimedio e' un rimando incrociato: ciascuna meta' nomina l'altra.
    Il patcher lo scrive in entrambi i posti e lo verifica.

ORDINE
    Dopo il record 67 e dopo freeze_verify. Il cancello lo impone: 67 record, l'item del
    67 in coda, e i tre file agli sha che il patcher precedente ha lasciato.

USO
    python src\\paper2_patch_sgcpred_documenti.py selftest
    python src\\paper2_patch_sgcpred_documenti.py apply --dir papers\\paper2 ^
        --ledger src\\paper2_v1_amendments.jsonl --dry-run
    (poi senza --dry-run, con --backup-dir logs)
    python src\\paper2_patch_sgcpred_documenti.py verifica --dir papers\\paper2
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

REV = "paper2_patch_sgcpred_documenti rev.1"
ITEM_67 = "6.9/rettifica_dei_conteggi_del_66_e_collocazione_completa_di_SGC_PRED"

SMENTITE = "paper2_5_5_smentite.md"
CHECKLIST = "checklist_paper2.md"
STATO = "paper2_stato.md"

SHA_ATTESI = {
    SMENTITE: "02c2151ecf29e04314a2064c2ee41e308caed738915b9b49b9293454c90738b0",
    CHECKLIST: "a5368c80a7fdd843d395140add4b7a175d27e1f786c6f8bb83bcbf8182f8b455",
    STATO: "cf6c4f21d0aeffdaf4f1b6da0d998803e9bc1a2a8b67d62517503e589b482c6c",
}

RIGA_Q5 = ("| Q5 | *R*²cv di *P*(*k*) **sotto** il tetto dei predittori misurati (la costante "
           "vale 0.8320530984290949; il docstring la cita come 0.832) | emessa dal run e "
           "**mai raccolta**: il dizionario `SOGLIE` di `paper2_d6_incertezze.py` ne conteneva "
           "quattro | **regge, e non marginalmente.** Sulla procedura su cui era dichiarata: "
           "0.3177 (NGC) e 0.3081 (SGC), a **70.2σ e 88.8σ** sotto la soglia. Con lo stesso "
           "stimatore ai due lati: *K* = 0.3808 e 0.3612, a **9.7σ e 11.0σ** sul denominatore "
           "d'insieme. Record 65 |\n")

RIGA_SGC = ("| SGC | frazione spettrale in [0.70, 0.82], dichiarata in `SGC_PRED` prima del run "
            "| **mai risolta fino al 14 set**: `results/paper1/n10_phases_SGC.jsonl` non "
            "esisteva quando lo strumento girò, il 31 agosto | **SMENTITA.** 0.843171 contro "
            "l'estremo superiore: **5.58σ** ricampionando i soli mock, **3.84σ** ricampionando "
            "anche le estrazioni DESI. L'altra metà della stessa predizione, la clausola "
            "\\|*z*\\| > 3, sta in **B6**. Record 66 |\n")

M_SMENTITE = [
    (
        "gruppo B: la voce B6",
        """| B5 | 29 | l'«offset costante» del report di Fase 3 in NGC | non è né costante né crescente: lettura ritirata come non supportata |
""",
        """| B5 | 29 | l'«offset costante» del report di Fase 3 in NGC | non è né costante né crescente: lettura ritirata come non supportata |
| B6 | 66 | la clausola \\|*z*\\| > 3 di `SGC_PRED`, che il run del 14 set riporta come CONFERMATA | **ritirata come conferma**: il margine è **0.66σ**. La soglia non ha mai avuto l'incertezza della quantità testata, e *z* = residuo/σ_Δ con σ_Δ stimata su 100 mock, cioè ±7.1 %: *z* = 3.66 ± 0.26 da quella sola componente. Stessa forma di B1 col segno rovesciato — là una falsificazione a 0.22σ, qui una conferma dentro il rumore. L'altra metà della stessa predizione, la frazione spettrale, sta nella **3-bis** |
""",
    ),
    (
        "3-bis: il titolo si allarga",
        """## 3-bis. Predizioni dichiarate FUORI dal ledger — le Q di D6
""",
        """## 3-bis. Predizioni dichiarate FUORI dal ledger — le Q di D6 e SGC_PRED
""",
    ),
    (
        "3-bis: l'intestazione della tabella non è più solo del record 63",
        """| # | soglia dichiarata | esito di agosto | esito con l'incertezza (record 63) |
""",
        """| # | soglia dichiarata | esito emesso al run | esito con l'incertezza |
""",
    ),
    (
        "3-bis: la riga SGC_PRED",
        RIGA_Q5,
        RIGA_Q5 + RIGA_SGC,
    ),
    (
        "3-bis: il censimento dopo la risoluzione di SGC_PRED",
        """**Restano da classificare tre candidati**, tutti senza record nel registro: le due soglie di
`paper2_gate53.py` — frazione spettrale in [0.70, 0.82] e |*z*| > 3, dichiarate prima del run in
`SGC_PRED` — e l'escursione < 0.005 di `paper2_item12b_wbar.py`. La verifica è per **item**, non
per nome di file: i record citano l'item, e una ricerca sul nome dello script dà zero anche per
verdetti che nel registro ci sono. Per questi due si è cercato il contenuto della soglia, e non
c'è: nessun record contiene l'intervallo di `SGC_PRED`, nessuno contiene 0.005, 0.99 o
`frac_below`, e la parola «scalinata» compare in zero record.
""",
        """Dei tre candidati lasciati aperti dal record 65 ne resta **uno**. La verifica è per **item**, non
per nome di file: i record citano l'item, e una ricerca sul nome dello script dà zero anche per
verdetti che nel registro ci sono. Per i candidati si è cercato il contenuto della soglia: nessun
record contiene l'intervallo di `SGC_PRED`, nessuno contiene 0.005, 0.99 o `frac_below`, e la
parola «scalinata» compare in zero record.

**`SGC_PRED` non era un verdetto fuori dal ledger: era una predizione mai risolta.** Il 31 agosto,
quando `paper2_gate53.py` girò, `results/paper1/n10_phases_SGC.jsonl` non esisteva e lo script
stampava che il file SGC andava prodotto; i suoi ingressi sono comparsi il 9 settembre, dalla
catena di Fase 5. È quindi una **prova cieca**: la predizione è stata scritta quando il dato non
era nemmeno producibile. Risolta il 14 settembre, per la prima volta — frazione spettrale nella
3-bis, clausola \\|*z*\\| in **B6**. Record 66 e 67.

Questo è anche il **limite del censimento**, e va detto: l'AST distingue i siti che *possono*
emettere un verdetto, non quelli che l'hanno emesso. Verificare l'esecuzione richiede i registri,
non il codice.

**Resta `paper2_item12b_wbar.py`**, escursione < 0.005, senza record e con il **margine non
misurabile** — non per costo. La quantità si calcola sulla maschera DESI e l'escursione è
max − min sui punti della griglia AP: è già una dispersione, e su cosmologie fiduciali, non su
realizzazioni. Un denominatore d'insieme richiederebbe maschere mock, che per questa quantità non
esistono, perché i mock condividono la maschera della survey per costruzione.
""",
    ),
]

BLOCCO_69_VECCHIO = """- [ ] **✦✦ 6.9 — Censimento dei verdetti emessi FUORI dal ledger** *(aperto il 13 set, record 64;
      **censimento chiuso il 14 set, record 65**; restano tre voci da classificare e una causa da
      correggere)*."""

BLOCCO_69_NUOVO = """- [ ] **✦✦ 6.9 — Censimento dei verdetti emessi FUORI dal ledger** *(aperto il 13 set, record 64;
      **censimento chiuso il 14 set, record 65**; `SGC_PRED` risolta e la causa corretta,
      record 66 e 67; resta una voce)*.
      **RISOLTO IL 14 SET.** `SGC_PRED` non era un verdetto fuori dal ledger: era una predizione
      **mai risolta**, perché il 31 agosto il suo ingresso non esisteva. Prova cieca: dichiarata
      prima che il dato fosse producibile. **Frazione spettrale SMENTITA** — 0.843171 contro
      [0.70, 0.82], a 5.58σ e 3.84σ dall'estremo superiore sui due denominatori. **Clausola
      \\|*z*\\| > 3 NON DECIDIBILE** a 0.66σ: va in **B6**, e i conteggi delle smentite passano a
      **12 / 1 / 6** (record 67). Due osservazioni non previste: la deconvoluzione in SGC non è
      calcolabile, perché la sd delle estrazioni **pubblicata** (157.0) supera la dispersione
      mock-to-mock di SGC (153.272) — da verificare ovunque compaia nel manoscritto; e la quota
      spettrale differisce fra gli emisferi, NGC 0.7625 contro SGC 0.8432, quindi il 76.3 % del
      Paper 1 **non è emisfero-indipendente**.
      **CAUSA CORRETTA.** `SOGLIE` di `src\\paper2_d6_incertezze.py` ha cinque voci e lo schema
      del registro è `paper2_d6_incertezze_v2`, con la nota che dichiara che un margine di Q5
      prodotto da lì **non è una misura nuova**: quella sta nel record 66.
      **LIMITE DEL CENSIMENTO.** L'AST distingue i siti che *possono* emettere un verdetto, non
      quelli che l'hanno emesso. L'esecuzione si verifica sui registri, non sul codice."""

M_CHECKLIST = [
    (
        "testata: rev. 3.25 -> 3.26",
        """### rev. 3.25 — 14 settembre 2026 — record 65; **il censimento del 6.9 è fatto**: i «nove script» erano 39 col pattern stretto e 76 con quello largo, i siti che emettono un verdetto sono 55 su 25 file, e **le predizioni dichiarate di D6 sono cinque** — Q5 era dichiarata, emessa e mai raccolta, ed è misurata ora: **regge** a 9.7σ e 11.0σ sul denominatore d'insieme
""",
        """### rev. 3.26 — 14 settembre 2026 — record 67; **`SGC_PRED` non era un verdetto fuori dal ledger, era una predizione mai risolta**: dichiarata il 31 agosto quando il suo ingresso non esisteva, risolta oggi per la prima volta — frazione spettrale **SMENTITA** a 5.58σ e 3.84σ, clausola \\|*z*\\| > 3 **non decidibile** a 0.66σ e quindi in B6, conteggi a **12 / 1 / 6**
""",
    ),
    (
        "voce 6.9: SGC_PRED risolta, causa corretta, una voce residua",
        BLOCCO_69_VECCHIO,
        BLOCCO_69_NUOVO,
    ),
]

M_STATO = [
    (
        "testata: nona -> decima revisione",
        """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **14 settembre 2026**, nona revisione
""",
        """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **14 settembre 2026**, decima revisione
""",
    ),
    (
        "blocco della decima revisione",
        """> **Cosa è cambiato nella nona revisione (14 settembre) — IL CENSIMENTO DEL 6.9, E UNA QUINTA
""",
        """> **Cosa è cambiato nella decima revisione (14 settembre) — UNA PREDIZIONE DICHIARATA PRIMA CHE
> IL DATO FOSSE PRODUCIBILE, RISOLTA OGGI PER LA PRIMA VOLTA.** `SGC_PRED` — frazione spettrale in
> [0.70, 0.82] e \\|*z*\\| > 3 — era nell'elenco dei verdetti da classificare. Non lo era: **il
> verdetto non esisteva**. Il 31 agosto `results/paper1/n10_phases_SGC.jsonl` non c'era e lo
> script stampava che andava prodotto; gli ingressi sono comparsi il 9 settembre. È la forma più
> forte di pre-registrazione che si possa avere, ed è caduta su metà: **frazione spettrale
> SMENTITA**, 0.843171 contro l'estremo superiore, a 5.58σ ricampionando i soli mock e 3.84σ
> ricampionando anche le estrazioni. L'altra metà, \\|*z*\\| = 3.66 > 3, il run la stampa come
> CONFERMATA ma il margine è **0.66σ**: non decidibile, e la soglia non ha mai avuto l'incertezza
> della quantità testata — va in **B6**, e i conteggi passano a **12 / 1 / 6**. **Due cose che
> nessuno aveva previsto:** in SGC la deconvoluzione non è calcolabile, perché la sd delle
> estrazioni *pubblicata* (157.0) supera la dispersione mock-to-mock di SGC (153.272), e va
> verificata ovunque compaia nel manoscritto; e la quota spettrale non è la stessa nei due
> emisferi — NGC 0.7625, SGC 0.8432 — quindi il **76.3 % del Paper 1 non è
> emisfero-indipendente** e non va citato come se lo fosse. **Causa corretta:** `SOGLIE` ha
> cinque voci e lo schema del registro è `v2`. **Limite del censimento, dichiarato:** l'AST dice
> quali siti *possono* emettere un verdetto, non quali l'hanno emesso. Record 66 e 67,
> `freeze_verify` CLEAN a 67/67.

> **Cosa è cambiato nella nona revisione (14 settembre) — IL CENSIMENTO DEL 6.9, E UNA QUINTA
""",
    ),
]

MODIFICHE = {SMENTITE: M_SMENTITE, CHECKLIST: M_CHECKLIST, STATO: M_STATO}


class Rifiuto(Exception):
    pass


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def leggi(path):
    if not os.path.isfile(path):
        raise Rifiuto("file assente: %s" % path)
    with open(path, "rb") as fh:
        return fh.read()


def cancello_ledger(path):
    if not os.path.isfile(path):
        raise Rifiuto("ledger assente: %s" % path)
    recs = []
    for linea in leggi(path).split(b"\n"):
        s = linea.strip()
        if s:
            recs.append(json.loads(s.decode("utf-8")))
    if len(recs) != 67:
        raise Rifiuto("il ledger ha %d record, attesi 67: appendere prima il record 67"
                      % len(recs))
    if recs[-1].get("item") != ITEM_67:
        raise Rifiuto("l'ultimo record non e' il 67: item='%s'" % recs[-1].get("item"))
    r = recs[-1].get("rules", {})
    if r.get("counts_after") != [12, 1, 6]:
        raise Rifiuto("il record 67 porta counts_after=%s, atteso [12, 1, 6]"
                      % r.get("counts_after"))
    return len(recs)


def prepara(cartella, sha_attesi=None):
    attesi = sha_attesi or SHA_ATTESI
    piano = {}
    for nome, mods in MODIFICHE.items():
        path = os.path.join(cartella, nome)
        raw = leggi(path)
        sha = sha256_bytes(raw)
        if sha != attesi[nome]:
            raise Rifiuto("%s: sha256 %s..., atteso %s.... Le ancore sono costruite sul "
                          "file come lo hanno lasciato i patcher precedenti."
                          % (nome, sha[:16], attesi[nome][:16]))
        testo = raw.decode("utf-8")
        fatte = []
        for etichetta, vecchio, nuovo in mods:
            n = testo.count(vecchio)
            if n == 0:
                raise Rifiuto("%s: ancora non trovata — %s" % (nome, etichetta))
            if n > 1:
                raise Rifiuto("%s: ancora presente %d volte — %s" % (nome, n, etichetta))
            if nuovo in testo:
                raise Rifiuto("%s: il testo nuovo c'e' gia' — %s" % (nome, etichetta))
            testo = testo.replace(vecchio, nuovo, 1)
            fatte.append(etichetta)
        piano[nome] = {"path": path, "prima": raw, "dopo": testo.encode("utf-8"),
                       "fatte": fatte}
    return piano


def controlli(piano):
    sm = piano[SMENTITE]["dopo"].decode("utf-8")
    ck = piano[CHECKLIST]["dopo"].decode("utf-8")
    st = piano[STATO]["dopo"].decode("utf-8")
    a = len(re.findall(r"^\|\s*A(\d+)\s*\|", sm, re.M))
    ab = len(re.findall(r"^\|\s*Ab(\d+)\s*\|", sm, re.M))
    b = len(re.findall(r"^\|\s*B(\d+)\s*\|", sm, re.M))
    q = len(re.findall(r"^\|\s*Q(\d)\s*\|", sm, re.M))
    return [
        (a == 12, "il gruppo A ha ancora 12 righe (ne ha %d)" % a),
        (ab == 1, "il gruppo A-bis ha ancora una riga (ne ha %d)" % ab),
        (b == 6, "il gruppo B ha SEI righe (ne ha %d)" % b),
        (q == 5, "le Q nella 3-bis sono ancora cinque (ne ha %d)" % q),
        (sm.count("\n| SGC |") == 1, "la riga SGC_PRED c'e' una volta sola nella 3-bis"),
        ("sta in **B6**" in sm and "sta nella **3-bis**" in sm,
         "il rimando incrociato c'e' in entrambe le meta'"),
        ("mai risolta" in sm, "la 3-bis dice che non era un verdetto ma una predizione non risolta"),
        ("quelli che l'hanno emesso" in sm and "quelli che l'hanno emesso" in ck,
         "il limite del censimento e' in smentite e in checklist"),
        ("12 / 1 / 6" in ck, "la checklist porta i conteggi nuovi"),
        ("rev. 3.26" in ck and "rev. 3.25 — 14 settembre" not in ck,
         "la checklist e' alla rev. 3.26"),
        ("decima revisione" in st and "nona revisione\n" not in st.split("\n")[1],
         "lo stato e' alla decima revisione"),
        ("Cosa è cambiato nella nona revisione" in st,
         "il blocco della nona revisione e' rimasto"),
        ("emisfero-indipendente" in st and "emisfero-indipendente" in ck,
         "l'avvertenza sul 76.3 % del Paper 1 e' in entrambi"),
        ("157.0" in st and "153.272" in st,
         "i due numeri che rendono impossibile la deconvoluzione sono nello stato"),
    ]


def cmd_apply(a):
    try:
        n = None if a.salta_ledger else cancello_ledger(a.ledger)
        piano = prepara(a.dir, None)
    except (Rifiuto, json.JSONDecodeError) as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("=== %s ===" % REV)
    print("  ledger     : %s" % ("%s, %d record, ultimo = il 67" % (a.ledger, n)
                                 if n else "controllo saltato"))
    for nome in (SMENTITE, CHECKLIST, STATO):
        p = piano[nome]
        print("  %-24s %d byte -> %d byte" % (nome, len(p["prima"]), len(p["dopo"])))
        for et in p["fatte"]:
            print("      - %s" % et)

    esiti = controlli(piano)
    print("")
    print("  controlli sul risultato:")
    for ok, testo in esiti:
        print("    [%s] %s" % ("ok" if ok else "FALLITO", testo))
    if not all(ok for ok, _t in esiti):
        print("\nESITO: CONTROLLI FALLITI — niente scritto.")
        return 3

    if a.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    if a.backup_dir:
        os.makedirs(a.backup_dir, exist_ok=True)
        for nome in MODIFICHE:
            with open(os.path.join(a.backup_dir, nome + ".prima_del_67"), "wb") as fh:
                fh.write(piano[nome]["prima"])

    temporanei = {}
    try:
        for nome in MODIFICHE:
            p = piano[nome]
            d = os.path.dirname(os.path.abspath(p["path"]))
            fd, tmp = tempfile.mkstemp(dir=d, prefix=nome + ".", suffix=".tmp")
            temporanei[nome] = tmp
            with os.fdopen(fd, "wb") as fh:
                fh.write(p["dopo"])
                fh.flush()
                os.fsync(fh.fileno())
        for nome in MODIFICHE:
            os.replace(temporanei.pop(nome), piano[nome]["path"])
    finally:
        for tmp in temporanei.values():
            if os.path.exists(tmp):
                os.unlink(tmp)

    print("")
    print("  verifica dopo la scrittura:")
    tutto = True
    for nome in MODIFICHE:
        raw = leggi(piano[nome]["path"])
        ok = raw == piano[nome]["dopo"]
        tutto = tutto and ok
        print("    [%s] %-24s" % ("ok" if ok else "KO", nome))
    if not tutto:
        return 5
    print("")
    print("  Nuovi sha, da riportare nella consegna:")
    for nome in (CHECKLIST, STATO, SMENTITE):
        raw = leggi(piano[nome]["path"])
        print("    %-24s %s  %d byte" % (nome, sha256_bytes(raw), len(raw)))
    print("")
    print("ESITO: CLEAN")
    return 0


def cmd_verifica(a):
    print("=== %s — verifica ===" % REV)
    tutto = True
    piano = {}
    for nome, mods in MODIFICHE.items():
        path = os.path.join(a.dir, nome)
        try:
            raw = leggi(path)
        except Rifiuto as e:
            print("  [KO] %s" % e)
            return 1
        piano[nome] = {"dopo": raw}
        testo = raw.decode("utf-8")
        for etichetta, vecchio, nuovo in mods:
            c_new, c_old = testo.count(nuovo), testo.count(vecchio)
            additiva = vecchio in nuovo
            ok = c_new == 1 and (additiva or c_old == 0)
            tutto = tutto and ok
            print("  [%s] %-22s %s  (nuovo x%d, vecchio x%d%s)"
                  % ("ok" if ok else "KO", nome, etichetta, c_new, c_old,
                     ", additiva" if additiva else ""))
    for ok, t in controlli(piano):
        tutto = tutto and ok
        print("  [%s] %s" % ("ok" if ok else "KO", t))
    print("")
    print("ESITO: %s" % ("CLEAN" if tutto else "FALLITO"))
    return 0 if tutto else 1


def cmd_selftest(a=None):
    import shutil
    esiti = []

    def ok(nome, cond):
        esiti.append((bool(cond), nome))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", nome))

    class A(object):
        dry_run = False
        backup_dir = None
        salta_ledger = False

    td = tempfile.mkdtemp(prefix="sgcdoc_")
    veri = dict(SHA_ATTESI)
    try:
        cart = os.path.join(td, "papers")
        os.makedirs(cart)
        led = os.path.join(td, "ledger.jsonl")

        def costruisci():
            for nome, mods in MODIFICHE.items():
                corpo = "# %s\n\n" % nome
                for _et, vecchio, _n in mods:
                    corpo += vecchio + "\n"
                if nome == SMENTITE:
                    corpo += "\n" + "".join("| A%d | x | y | z | w |\n" % i
                                            for i in range(1, 13))
                    corpo += "| Ab1 | x | y | z | w |\n"
                    corpo += "".join("| B%d | x | y | z |\n" % i for i in range(1, 5))
                    corpo += "".join("| Q%d | a | b | c |\n" % i for i in range(1, 5))
                if nome == STATO:
                    corpo += "\n> **Cosa è cambiato nell'ottava revisione.**\n"
                with open(os.path.join(cart, nome), "wb") as fh:
                    fh.write(corpo.encode("utf-8"))
            for nome in MODIFICHE:
                with open(os.path.join(cart, nome), "rb") as fh:
                    SHA_ATTESI[nome] = sha256_bytes(fh.read())

        def scrivi_ledger(n=67, ultimo=ITEM_67, counts=None):
            with open(led, "wb") as fh:
                for i in range(1, n + 1):
                    r = {"item": ultimo if i == n else "item_%d" % i}
                    if i == n:
                        r["rules"] = {"counts_after": counts or [12, 1, 6]}
                    fh.write(json.dumps(r).encode("utf-8") + b"\n")

        def args(dry=False, backup=None):
            x = A()
            x.dir, x.ledger, x.dry_run, x.backup_dir = cart, led, dry, backup
            return x

        costruisci()
        scrivi_ledger()
        prima = {n: leggi(os.path.join(cart, n)) for n in MODIFICHE}
        ok("01 dry-run esce con 0", cmd_apply(args(dry=True)) == 0)
        ok("02 dry-run non scrive", all(leggi(os.path.join(cart, n)) == prima[n]
                                        for n in MODIFICHE))
        ok("03 apply esce con 0", cmd_apply(args()) == 0)

        dopo = {n: leggi(os.path.join(cart, n)).decode("utf-8") for n in MODIFICHE}
        ok("04 il gruppo B ha sei righe",
           len(re.findall(r"^\|\s*B(\d+)\s*\|", dopo[SMENTITE], re.M)) == 6)
        ok("05 la riga SGC c'e' una volta sola", dopo[SMENTITE].count("\n| SGC |") == 1)
        ok("06 le Q restano cinque",
           len(re.findall(r"^\|\s*Q(\d)\s*\|", dopo[SMENTITE], re.M)) == 5)
        ok("07 il titolo della 3-bis nomina SGC_PRED",
           "le Q di D6 e SGC_PRED" in dopo[SMENTITE])
        ok("08 l'intestazione non attribuisce piu' tutto al record 63",
           "esito con l'incertezza (record 63)" not in dopo[SMENTITE])
        ok("09 il rimando incrociato e' in entrambe le meta'",
           "sta in **B6**" in dopo[SMENTITE] and "sta nella **3-bis**" in dopo[SMENTITE])
        ok("10 la checklist e' alla rev. 3.26", "rev. 3.26" in dopo[CHECKLIST])
        ok("11 e porta i conteggi nuovi", "12 / 1 / 6" in dopo[CHECKLIST])
        ok("12 lo stato e' alla decima revisione", "decima revisione" in dopo[STATO])
        ok("13 il blocco della nona e' rimasto sotto",
           "nona revisione (14 settembre)" in dopo[STATO])
        ok("14 il limite del censimento e' in due documenti",
           "quelli che l'hanno emesso" in dopo[SMENTITE]
           and "quelli che l'hanno emesso" in dopo[CHECKLIST])
        ok("15 l'avvertenza sul Paper 1 e' in due documenti",
           "emisfero-indipendente" in dopo[STATO]
           and "emisfero-indipendente" in dopo[CHECKLIST])
        ok("16 item12b resta con il margine non misurabile, e la ragione",
           "misurabile**" in dopo[SMENTITE] and "non per costo" in dopo[SMENTITE])
        ok("17 i file restano a fine riga LF puro",
           all(b"\r\n" not in leggi(os.path.join(cart, n)) for n in MODIFICHE))
        ok("18 verifica esce con 0", cmd_verifica(args()) == 0)
        ok("19 riapplicare e' rifiutato", cmd_apply(args()) == 2)

        costruisci()
        scrivi_ledger(n=66, ultimo="item_66")
        ok("20 ledger a 66 -> rifiuto", cmd_apply(args()) == 2)
        scrivi_ledger(counts=[12, 1, 5])
        ok("21 record 67 con counts_after sbagliati -> rifiuto", cmd_apply(args()) == 2)

        scrivi_ledger()
        with open(os.path.join(cart, STATO), "ab") as fh:
            fh.write(b"\nriga in piu'\n")
        ok("22 sha diverso -> rifiuto", cmd_apply(args()) == 2)
        ok("23 e nessun file e' stato toccato",
           "| SGC |" not in leggi(os.path.join(cart, SMENTITE)).decode("utf-8"))

        costruisci()
        t = leggi(os.path.join(cart, CHECKLIST)).decode("utf-8").replace(
            BLOCCO_69_VECCHIO, "altro")
        with open(os.path.join(cart, CHECKLIST), "wb") as fh:
            fh.write(t.encode("utf-8"))
        for nome in MODIFICHE:
            SHA_ATTESI[nome] = sha256_bytes(leggi(os.path.join(cart, nome)))
        scrivi_ledger()
        prima = {n: leggi(os.path.join(cart, n)) for n in MODIFICHE}
        ok("24 ancora mancante in un file -> rifiuto", cmd_apply(args()) == 2)
        ok("25 atomicita': gli altri due non sono stati toccati",
           all(leggi(os.path.join(cart, n)) == prima[n] for n in MODIFICHE))

        costruisci()
        scrivi_ledger()
        bdir = os.path.join(td, "logs")
        ok("26 apply con backup esce con 0", cmd_apply(args(backup=bdir)) == 0)
        ok("27 i tre file precedenti sono nel backup",
           all(os.path.isfile(os.path.join(bdir, n + ".prima_del_67")) for n in MODIFICHE))
        ok("28 nessun temporaneo lasciato indietro",
           not [x for x in os.listdir(cart) if x.endswith(".tmp")])

        costruisci()
        ok("29 verifica esce con 1 su file non patchati", cmd_verifica(args()) == 1)

    finally:
        SHA_ATTESI.update(veri)
        shutil.rmtree(td, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper2_patch_sgcpred_documenti.py",
                                description="SGC_PRED nei tre documenti: B6 e 3-bis allargata.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("apply")
    q.add_argument("--dir", default=os.path.join("papers", "paper2"))
    q.add_argument("--ledger", default=os.path.join("src", "paper2_v1_amendments.jsonl"))
    q.add_argument("--backup-dir", default=None)
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--salta-ledger", action="store_true")
    q.set_defaults(func=cmd_apply)

    q = sub.add_parser("verifica")
    q.add_argument("--dir", default=os.path.join("papers", "paper2"))
    q.set_defaults(func=cmd_verifica)

    q = sub.add_parser("selftest")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
