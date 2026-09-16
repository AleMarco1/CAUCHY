#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend64.py — appende il record 64: il record 63 dice una cosa falsa sui
conteggi delle smentite, e la ragione e' piu' grossa del conteggio.

Che cosa corregge. Il record 63 scrive «A: 12 -> 11, A-bis: 1, B: 5 -> 6», cioe' che Q1 di
D6 esce dal gruppo A ed entra nel gruppo B. **Q1 non e' mai stata nel gruppo A**: la
tabella di `paper2_5_5_smentite.md` contiene A1-A12 e nessuna di quelle voci e' una Q di
D6. E non puo' nemmeno entrare in B: ogni voce di A e di B porta in colonna il **record del
ledger** in cui e' dichiarata o risolta, e Q1 non ha un record del ledger.

Che cosa scopre. Se Q1 non e' classificata, **nessuna predizione di D6 lo e'**. La
classificazione di 5.5 e' stata costruita con `paper2_estrai.py` sui 59 record del ledger,
e le Q di D6 vivono nello script e nei risultati, fuori dal ledger. Non e' un errore di
conteggio: e' un LIMITE DI PORTATA di quella classificazione, e con esso va riletta la
frase del record 60 «i 33 record esclusi sono stati controllati uno per uno, nessuna
falsificazione e' stata mancata», che e' vera dentro il registro e non oltre.

Cancelli, oltre a quelli soliti: i conteggi di questo record si verificano **contro il
documento che li tiene**, non contro una descrizione di esso — che e' esattamente il
controllo che al record 63 e' mancato. Il file delle smentite deve avere dodici righe A,
una A-bis, cinque B, e non deve contenere nessuna Q di D6.

ORDINE: questo record PRIMA del patcher sui documenti. Il cancello asserisce lo stato
attuale del file delle smentite; se il patcher aggiunge la sezione delle Q prima
dell'append, l'append viene rifiutato — correttamente.

Uso:
    python paper2_append_amend64.py selftest
    python paper2_append_amend64.py append --ledger src\\paper2_v1_amendments.jsonl --reference src\\paper2_v1_reference.json --attesi 63 --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

CRLF = chr(13).encode() + chr(10).encode()
LF = chr(10).encode()
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"

ITEM_PREV = "6.8/D6_chiuso_stesso_stimatore_ai_due_lati_e_terzo_residuo_collocato"
ITEM_64 = "5.5/correzione_del_63_i_gruppi_delle_smentite_sono_ancorati_al_ledger"

ATTESI_A, ATTESI_ABIS, ATTESI_B = 12, 1, 5
SMENTITE = "papers/paper2/paper2_5_5_smentite.md"

# Gli script che emettono un verdetto fuori dal ledger, dal censimento del 13 set.
# Nessun conteggio di predizioni: solo i file da esaminare uno per uno.
SCRIPT_CON_VERDETTO = [
    "src/paper2_compD_nonlinear.py", "src/paper2_compD_partialcorr.py", "src/paper2_gate53.py",
    "src/paper2_phase3_preflight.py", "src/paper2_ripattern_analisi.py",
    "src/paper2_item12b_wbar.py", "src/paper2_pareggi.py", "src/paper2_runner_fase3_mock.py",
    "src/paper1_rev_v2g_frozen.py",
]

Q_DI_D6 = {
    "Q1": {"soglia": 0.05, "verso": "<", "NGC_sigma": 0.2855, "SGC_sigma": 0.1421,
           "stato": "ritirata come falsificazione: non decidibile in nessuno dei due emisferi"},
    "Q2": {"soglia": 0.03, "verso": "<", "NGC_sigma": 4.73, "SGC_sigma": 2.00,
           "stato": "falsificata a NGC, NON decidibile a SGC"},
    "Q3": {"soglia": 0.50, "verso": ">", "NGC_sigma_kernel_ensemble": 2.55,
           "stato": "falsificata per la procedura su cui era dichiarata; col kernel e il "
                    "denominatore d'insieme sta a 2.6 sigma dalla soglia"},
    "Q4": {"soglia": 0.50, "verso": ">",
           "stato": "falsificata su ogni base: dal 12.9 al 21.6 per cento contro il 50"},
}


def analizza_eol(raw):
    crlf = raw.count(CRLF)
    lf_isolati = raw.count(LF) - crlf
    termina = None if (not raw or not raw.endswith(LF)) else (CRLF if raw.endswith(CRLF) else LF)
    return {"crlf": crlf, "lf_isolati": lf_isolati, "termina": termina,
            "misto": bool(crlf and lf_isolati)}


def leggi_reference(path):
    sha_file = sha256_file(path)
    with open(path, "rb") as fh:
        ref = json.loads(fh.read().decode("utf-8"))
    self_sha = ref.get("_self_sha256") if isinstance(ref, dict) else None
    if not isinstance(self_sha, str) or len(self_sha) != 64:
        raise Rifiuto("'_self_sha256' non leggibile dal reference; usa --self-sha")
    return sha_file, self_sha


def conta_gruppi(path):
    """Conta le righe di tabella per gruppo, LEGGENDO il documento che le tiene."""
    if not os.path.isfile(path):
        raise Rifiuto("file delle smentite assente: %s" % path)
    testo = open(path, "r", encoding="utf-8").read()
    a = len(re.findall(r"^\|\s*A(\d+)\s*\|", testo, re.M))
    abis = len(re.findall(r"^\|\s*Ab(\d+)\s*\|", testo, re.M))
    b = len(re.findall(r"^\|\s*B(\d+)\s*\|", testo, re.M))
    q = sorted({m for m in re.findall(r"\bQ[1-4]\b", testo)})
    return {"A": a, "A_bis": abis, "B": b, "Q_presenti": q, "sha256": sha256_file(path)}


def cancello_conteggi(path):
    """Il controllo che al record 63 e' mancato: il numero contro il documento."""
    c = conta_gruppi(path)
    if c["A"] != ATTESI_A:
        raise Rifiuto("gruppo A: %d righe nel documento, %d attese" % (c["A"], ATTESI_A))
    if c["A_bis"] != ATTESI_ABIS:
        raise Rifiuto("gruppo A-bis: %d righe, %d attese" % (c["A_bis"], ATTESI_ABIS))
    if c["B"] != ATTESI_B:
        raise Rifiuto("gruppo B: %d righe, %d attese" % (c["B"], ATTESI_B))
    if c["Q_presenti"]:
        raise Rifiuto("il documento contiene gia' %s: questo record asserisce che NON vi "
                      "compaiono, quindi va appeso PRIMA del patcher" % ", ".join(c["Q_presenti"]))
    return c


def costruisci(n_prima, ref_file_sha, ref_self_sha, conteggi, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM_64,
        "key": "record_63_miscounted_the_falsified_predictions_and_why",
        "json_path": "%s; checklist item 5.5; records 60 and 63" % SMENTITE,
        "old_value": ("Record 63 states 'A: 12 -> 11, A-bis: 1, B: 5 -> 6', that is, that Q1 of D6 "
                      "leaves group A and joins group B."),
        "new_value": {
            "i_what_is_false_and_what_is_true": {
                "false": ("Q1 was never in group A. The table of %s holds A1-A12 and none of those "
                          "twelve entries is a Q of D6: they are the anisotropic-clipping "
                          "prediction, records 15->19, 16->37, 16->38, 18->37, 19, 30->31, "
                          "3.2e->46, 50->57, 50/58, 58->59 and 26->39." % SMENTITE),
                "also_false": ("Q1 cannot simply join group B either. Every entry of A and of B "
                               "carries in its column the LEDGER RECORD in which it is declared or "
                               "resolved - B1 record 48, B2 record 50, B3 record 54, B4 record 13, "
                               "B5 record 29 - and Q1 has no ledger record. Putting it there would "
                               "break the column that makes the group checkable."),
                "true": {"A": conteggi["A"], "A_bis": conteggi["A_bis"], "B": conteggi["B"],
                         "statement": "the counts of item 5.5 are unchanged: 12, 1 and 5"},
            },
            "ii_how_the_error_was_made": (
                "The checklist says 'D6 con P1 e Q1-Q4 smentite' at line 602; that sentence was "
                "combined with the counts of record 60 and the conclusion was drawn that Q1 was one "
                "of the twelve. The table itself was never opened. The error was then put to the "
                "author as a decision and approved on the description of the document rather than on "
                "the document - which is the worst way for a count to pass. The gates of record 63 "
                "could not catch it: they check measured numbers against their measurement "
                "registers, and this was a count checked against nothing."
            ),
            "iii_the_scope_of_item_5_5_and_what_follows": {
                "scope": ("The classification was built with paper2_estrai.py over the 59 ledger "
                          "records. The Q predictions of D6 live in the script and in "
                          "results/paper2/compD_nonlinear_NGC.jsonl, outside the ledger, so the "
                          "search could not see them. This is a limit of REACH, not a miscount."),
                "where_they_were_declared": ("prereg section 0, reported in the checklist at line 602 "
                                             "among what was already in hand at deposit: 'Componente D "
                                             "interamente eseguita (D2, D4, D5, D6 con P1 e Q1-Q4 "
                                             "smentite)'. They are declared predictions with verdicts, "
                                             "and they were never classified."),
                "consequence_for_record_60": ("'the 33 excluded records were checked one by one, no "
                                              "falsification was missed' stays true INSIDE the "
                                              "register, and the register is not the universe of "
                                              "declared predictions. The sentence needs its scope "
                                              "attached wherever it is quoted."),
                "what_is_NOT_claimed_here": ("No count of how many declared predictions lie outside "
                                             "the ledger. A census of the scripts that emit a verdict "
                                             "found the files listed below; whether each is a declared "
                                             "prediction with a threshold or merely a gate label is "
                                             "unknown until each is read, and guessing it would repeat "
                                             "the error this record corrects."),
                "scripts_to_examine": SCRIPT_CON_VERDETTO,
            },
            "iv_the_status_of_the_four_Q_predictions_today": {
                "measured_in": "results/paper2/d6_incertezze.jsonl and d6bis.jsonl, both hemispheres",
                "Q": Q_DI_D6,
                "where_they_go": ("a section of their own in %s, declared as OUTSIDE the ledger "
                                  "universe, not as rows of A or B" % SMENTITE),
            },
            "v_what_this_record_does_not_do": {
                "it_does_not_touch_D6": ("every measurement of record 63 stands: the reading of August "
                                         "was an artefact of the model class, K - P is compatible with "
                                         "zero, PK - P is not decidable on the ensemble denominator, "
                                         "and about half the available variance escapes both "
                                         "predictors. Only the sentence about the counts is wrong."),
                "it_does_not_confirm_the_anomaly": "nothing here is evidence for a physical claim",
                "it_does_not_close_the_census": "the enumeration of verdicts outside the ledger is open",
            },
        },
        "reason": (
            "Record 63 claimed that Q1 of D6 moves from group A to group B of the falsified "
            "predictions, changing the counts from 12/1/5 to 11/1/6. Q1 was never in group A, and "
            "cannot be in group B either, because both groups are anchored to ledger records and Q1 "
            "has none. The counts are unchanged. Behind the wrong number there is a real finding: "
            "item 5.5 classified the 59 ledger records, and the declared predictions of D6 live "
            "outside the ledger, so none of them was ever classified - which also bounds the scope of "
            "record 60's claim that no falsification was missed. A census of the scripts that emit a "
            "verdict is opened here and deliberately left without a count."
        ),
        "evidence": (
            "%s read at append time: %d rows in group A, %d in A-bis, %d in B, and no occurrence of "
            "Q1 to Q4 anywhere in the file (sha256 %s). Checklist line 602 for the deposit-time "
            "declaration. The census of verdict-emitting scripts is a read-only grep over src/*.py."
            % (SMENTITE, conteggi["A"], conteggi["A_bis"], conteggi["B"], conteggi["sha256"])
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": ("The number of an amendment is its 1-based POSITION in this file. "
                           "This is record %d." % numero),
        "rules": {
            "marker": "emendamento-%d-conteggi-5-5" % numero,
            "amends_records": [60, 63],
            "companion_document": "%s; checklist items 5.5 and 6.8; paper2_stato.md" % SMENTITE,
            "a_count_is_verified_against_the_document_that_holds_it": (
                "Not against a description of that document, and not against a memory of it. Where a "
                "count enters a record, the record's gate reads the file and counts."),
            "a_classification_declares_its_reach": (
                "'No falsification was missed' is meaningful only with the universe attached. Item "
                "5.5's universe was the 59 ledger records."),
            "what_this_does_not_do": "It does not touch any measurement of record 63.",
        },
    }


def serializza(rec):
    return json.dumps(rec, ensure_ascii=False, sort_keys=False).encode("utf-8")


def cmd_append(args):
    try:
        if not os.path.isfile(args.reference):
            raise Rifiuto("reference inesistente: %s" % args.reference)
        if not os.path.isfile(args.ledger):
            raise Rifiuto("ledger inesistente: %s" % args.ledger)
        ref_file_sha, ref_self_sha = ((sha256_file(args.reference), args.self_sha) if args.self_sha
                                      else leggi_reference(args.reference))
        raw, recs, _e, _c, _l = leggi_ledger(args.ledger)
        if not all(isinstance(r, dict) for r in recs):
            raise Rifiuto("leggi_ledger non restituisce dizionari")
        if len(recs) != args.attesi:
            raise Rifiuto("disco=%d attesi=%d" % (len(recs), args.attesi))
        eol = analizza_eol(raw)
        if eol["termina"] is None:
            raise Rifiuto("l'ultima riga del ledger non termina con un a capo")
        if recs[-1].get("item") != ITEM_PREV:
            raise Rifiuto("l'ultimo record non e' la chiusura di D6: item='%s'" % recs[-1].get("item"))
        if any(r.get("item") == ITEM_64 for r in recs):
            raise Rifiuto("item gia' presente: %s" % ITEM_64)
        conteggi = cancello_conteggi(args.smentite)
        rec = costruisci(len(recs), ref_file_sha, ref_self_sha, conteggi)
        b = serializza(rec)
        if CRLF in b or LF in b:
            raise Rifiuto("il record serializzato contiene un fine riga")
        json.loads(b.decode("utf-8"))
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("ledger     : %s" % args.ledger)
    print("record     : %d (disco ora: %d)" % (len(recs) + 1, len(recs)))
    print("conteggi   : A=%d  A-bis=%d  B=%d, letti da %s"
          % (conteggi["A"], conteggi["A_bis"], conteggi["B"], args.smentite))
    print("             nessuna Q di D6 nel documento, come il record asserisce")
    print("byte       : %d -> %d" % (len(raw), len(raw) + len(b) + len(eol["termina"])))

    if args.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    nuovo = raw + b + eol["termina"]
    if args.backup:
        with open(args.backup, "wb") as fh:
            fh.write(raw)
    d = os.path.dirname(os.path.abspath(args.ledger))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=os.path.basename(args.ledger) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(nuovo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, args.ledger)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    raw2, recs2, _e2, _c2, _l2 = leggi_ledger(args.ledger)
    esiti = [
        (len(recs2) == args.attesi + 1, "conteggio %d -> %d" % (args.attesi, len(recs2))),
        (raw2.startswith(raw), "i %d record precedenti sono byte-identici" % args.attesi),
        (analizza_eol(raw2)["lf_isolati"] == eol["lf_isolati"], "la mistura di fini riga e' intatta"),
        (recs2[-1].get("item") == ITEM_64, "l'item e' quello nuovo"),
        ("record %d." % (args.attesi + 1) in recs2[-1]["numbering_rule"], "numbering_rule"),
    ]
    print()
    for c, nome in esiti:
        print(("  OK  " if c else "  KO  ") + nome)
    if not all(c for c, _ in esiti):
        return 5
    print("\nOra: python src\\paper2_patch_documented_amendments.py apply --file "
          "src\\paper2_freeze_verify.py --da %d --a %d" % (args.attesi, args.attesi + 1))
    print("     python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    print("     e SOLO DOPO il patcher sui documenti, che aggiunge le Q al file delle smentite.")
    return 0


def cmd_selftest(args=None):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    FINTO = ("## 1. Gruppo A\n\n| # | riga |\n|---|---:|\n"
             + "".join("| A%d | %d | predizione | esito |\n" % (i, i) for i in range(1, 13))
             + "\n**Dodici voci.**\n\n## 2. Gruppo A-bis\n\n| Ab1 | 24 | x | y |\n"
             + "\n## 3. Gruppo B\n\n"
             + "".join("| B%d | %d | cosa | esito |\n" % (i, i) for i in range(1, 6)))

    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "amendments.jsonl")
        ref = os.path.join(td, "reference.json")
        sm = os.path.join(td, "smentite.md")
        with open(ref, "wb") as fh:
            fh.write(json.dumps({"_self_sha256": "a" * 64}).encode("utf-8"))

        def scrivi_sm(testo=FINTO):
            with open(sm, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(testo)

        def scrivi_ledger(n, prev=True):
            with open(led, "wb") as fh:
                for i in range(n):
                    r = {"item": ITEM_PREV if (prev and i == n - 1) else "x%d" % i}
                    fh.write(json.dumps(r).encode("utf-8") + (LF if i < 6 else CRLF))

        class A:
            pass

        def a(attesi=63, dry=False, backup=None):
            x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi; x.dry_run = dry
            x.backup = backup; x.self_sha = None; x.smentite = sm
            return x

        scrivi_sm(); scrivi_ledger(63)
        raw_prima = open(led, "rb").read()

        c = conta_gruppi(sm)
        ok("1 conta dodici righe A", c["A"] == 12)
        ok("2 una A-bis e cinque B", c["A_bis"] == 1 and c["B"] == 5)
        ok("3 nessuna Q nel documento", c["Q_presenti"] == [])
        ok("4 il dry-run passa", cmd_append(a(dry=True)) == 0)
        ok("5 e non scrive", open(led, "rb").read() == raw_prima)

        scrivi_sm(FINTO.replace("| A12 | 12 | predizione | esito |\n", ""))
        ok("6 DIFETTO: undici righe A -> rifiuto (il controllo che al 63 e' mancato)",
           cmd_append(a(dry=True)) == 2)
        scrivi_sm()

        scrivi_sm(FINTO + "\n## 5. Q di D6\n\n| Q1 | ... |\n")
        ok("7 DIFETTO: se il patcher ha gia' aggiunto le Q -> rifiuto, ordine sbagliato",
           cmd_append(a(dry=True)) == 2)
        scrivi_sm()

        scrivi_sm(FINTO + "| B6 | 63 | Q1 aggiunta a mano | esito |\n")
        ok("8 DIFETTO: sei righe B -> rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_sm()

        os.remove(sm)
        ok("9 DIFETTO: documento assente -> rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_sm()

        scrivi_ledger(63, prev=False)
        ok("10 senza il record 63 in coda: rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_ledger(63)

        ok("11 append: esito 0", cmd_append(a()) == 0)
        raw2, recs2, _e, _c, _l = leggi_ledger(led)
        ok("12 il conteggio cambia: 63 -> 64", len(recs2) == 64)
        ok("13 i 63 precedenti sono byte-identici", raw2.startswith(raw_prima))
        ok("14 la mistura di fini riga e' intatta",
           analizza_eol(raw2)["lf_isolati"] == analizza_eol(raw_prima)["lf_isolati"])
        ok("15 numbering_rule dice 64", "record 64." in recs2[-1]["numbering_rule"])
        ok("16 secondo append rifiutato", cmd_append(a(attesi=64)) == 2)

        nv = recs2[-1]["new_value"]
        ok("17 i conteggi restano 12/1/5",
           nv["i_what_is_false_and_what_is_true"]["true"] == {"A": 12, "A_bis": 1, "B": 5,
                                                             "statement": "the counts of item 5.5 are unchanged: 12, 1 and 5"})
        ok("18 dice perche' Q1 non puo' nemmeno entrare in B",
           "no ledger record" in nv["i_what_is_false_and_what_is_true"]["also_false"])
        ok("19 registra come l'errore e' stato fatto",
           "never opened" in nv["ii_how_the_error_was_made"])
        ok("20 dichiara la portata di 5.5",
           "59 ledger records" in nv["iii_the_scope_of_item_5_5_and_what_follows"]["scope"])
        ok("21 e NON dichiara un conteggio delle predizioni fuori dal ledger",
           "No count" in nv["iii_the_scope_of_item_5_5_and_what_follows"]["what_is_NOT_claimed_here"])
        ok("22 elenca i file da esaminare",
           len(nv["iii_the_scope_of_item_5_5_and_what_follows"]["scripts_to_examine"]) == 9)
        ok("23 le misure del record 63 restano in piedi",
           "every measurement of record 63 stands" in nv["v_what_this_record_does_not_do"]["it_does_not_touch_D6"])
        ok("24 emenda 60 e 63", recs2[-1]["rules"]["amends_records"] == [60, 63])
        ok("25 i cancelli importati sono quelli del 50",
           sys.modules["paper2_append_amend50"].sha256_file is sha256_file)

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print("selftest: %d/%d" % (passati, len(controlli)))
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_a = sub.add_parser("append")
    p_a.add_argument("--ledger", required=True)
    p_a.add_argument("--reference", required=True)
    p_a.add_argument("--attesi", type=int, default=63)
    p_a.add_argument("--smentite", default=SMENTITE.replace("/", os.sep))
    p_a.add_argument("--self-sha", default=None, dest="self_sha")
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
