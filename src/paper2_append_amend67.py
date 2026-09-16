#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_append_amend67.py — record 67: il record 66 dichiara due cose incompatibili.

CHE COSA CORREGGE
    Il record 66, nella sezione iii, colloca la clausola |z| > 3 nel GRUPPO B di
    papers/paper2/paper2_5_5_smentite.md. Nello stesso record, `rules.counts_unchanged`
    dice [12, 1, 5]. Se la clausola entra nel gruppo B, il gruppo B diventa sei.

    Le due affermazioni stanno nello stesso record. Il campo dei conteggi e' stato portato
    dal record 65 per inerzia, dove era corretto perche' Q5 andava nella sezione 3-bis e
    non in un gruppo ancorato al ledger.

    Esiste una lettura che le concilia — «questo record non cambia i conteggi, li cambia il
    documento» — ma `counts_unchanged` e' un campo che si legge A FREDDO: fra sei mesi si
    legge [12, 1, 5] nel registro e B=6 nel documento. E' la stessa forma della riga 602
    della checklist: un'enumerazione corta di uno, lasciata dove qualcuno la ricopiera'.

CHE COSA COMPLETA
    Il record 66 dichiara dove va la clausola |z|, ma non dove va l'altra meta' di
    SGC_PRED. La frazione spettrale e' una predizione dichiarata NEL SORGENTE e non in un
    record del ledger: per la regola fissata dal record 64 non puo' entrare nel gruppo A,
    che richiede il record in cui la predizione e' dichiarata. Va nella sezione 3-bis,
    accanto alle Q di D6, che e' la sezione delle predizioni dichiarate fuori dal ledger.

    Le voci del gruppo B sono ancorate al record che fa la RITIRATA, non a quello che
    dichiara la predizione — B4 alla riga 13, B5 alla riga 29. Quindi B6 e' ancorata alla
    riga 66.

CHE COSA NON FA
    Non rivede il verdetto: la frazione spettrale resta smentita a 5.58 e 3.84 sigma, e la
    clausola |z| resta non decidibile a 0.66 sigma. Non tocca i documenti. Non sposta Q5.

USO
    python src\\paper2_append_amend67.py selftest
    python src\\paper2_append_amend67.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 66 --dry-run
"""

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

ITEM_PREV = "6.9/SGC_PRED_risolta_e_tre_decisioni_di_protocollo"
ITEM_67 = "6.9/rettifica_dei_conteggi_del_66_e_collocazione_completa_di_SGC_PRED"

SEZIONE_III = "iii_the_z_threshold_is_NOT_DECIDABLE_and_moves_to_group_B"
PRIMA = [12, 1, 5]
DOPO = [12, 1, 6]
SMENTITE = "papers/paper2/paper2_5_5_smentite.md"


def analizza_eol(raw):
    crlf = raw.count(CRLF)
    return {"crlf": crlf, "lf_isolati": raw.count(LF) - crlf,
            "termina": None if (not raw or not raw.endswith(LF))
            else (CRLF if raw.endswith(CRLF) else LF)}


def leggi_reference(path):
    sha_file = sha256_file(path)
    with open(path, "rb") as fh:
        ref = json.loads(fh.read().decode("utf-8"))
    s = ref.get("_self_sha256") if isinstance(ref, dict) else None
    if not isinstance(s, str) or len(s) != 64:
        raise Rifiuto("'_self_sha256' non leggibile dal reference; usa --self-sha")
    return sha_file, s


def cancello_record_66(rec66):
    """Il record da emendare deve DAVVERO dire quello che diciamo che dice."""
    esiti = {}
    r = rec66.get("rules", {})
    if r.get("counts_unchanged") != PRIMA:
        raise Rifiuto("il record 66 porta counts_unchanged=%s, atteso %s. Se e' gia' stato "
                      "corretto, questo record non serve."
                      % (r.get("counts_unchanged"), PRIMA))
    esiti["counts_unchanged"] = r["counts_unchanged"]

    nv = rec66.get("new_value", {})
    if SEZIONE_III not in nv:
        raise Rifiuto("il record 66 non ha la sezione '%s'" % SEZIONE_III)
    coll = nv[SEZIONE_III].get("placement", "")
    if "group B" not in coll:
        raise Rifiuto("la sezione iii del record 66 non colloca la clausola nel gruppo B: "
                      "'%s'" % coll[:120])
    esiti["placement"] = coll
    esiti["verdetto_z"] = nv[SEZIONE_III].get("verdict")
    ii = nv.get("ii_spectral_fraction_FALSIFIED", {})
    if ii.get("verdict") != "FALSIFIED":
        raise Rifiuto("il record 66 non dichiara la frazione spettrale FALSIFIED")
    esiti["verdetto_frazione"] = ii["verdict"]
    esiti["misura_frazione"] = ii.get("measured")
    return esiti


def cancello_smentite(path):
    if not os.path.isfile(path):
        raise Rifiuto("file delle smentite assente: %s" % path)
    t = open(path, "r", encoding="utf-8").read()
    c = {"A": len(re.findall(r"^\|\s*A(\d+)\s*\|", t, re.M)),
         "A_bis": len(re.findall(r"^\|\s*Ab(\d+)\s*\|", t, re.M)),
         "B": len(re.findall(r"^\|\s*B(\d+)\s*\|", t, re.M)),
         "sha256": sha256_file(path)}
    if [c["A"], c["A_bis"], c["B"]] != PRIMA:
        raise Rifiuto("gruppi nel documento: A=%d A-bis=%d B=%d, attesi %s. Il patcher sui "
                      "documenti deve girare DOPO questo record."
                      % (c["A"], c["A_bis"], c["B"], PRIMA))
    q = sorted(set(re.findall(r"^\|\s*(Q[1-5])\s*\|", t, re.M)))
    if q != ["Q1", "Q2", "Q3", "Q4", "Q5"]:
        raise Rifiuto("righe Q nella 3-bis: %s, attese Q1-Q5" % (q or "nessuna"))
    return c


def costruisci(n_prima, ref_file_sha, ref_self_sha, r66, smentite, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM_67,
        "key": "record_66_declares_two_things_that_do_not_hold_together",
        "json_path": "record 66, rules.counts_unchanged; %s" % SMENTITE,
        "old_value": (
            "Record 66 places the |z| > 3 clause in group B of %s (section iii, field "
            "'placement') and, in the same record, states rules.counts_unchanged = %s."
            % (SMENTITE, PRIMA)),
        "new_value": {
            "i_the_two_statements_do_not_hold_together": {
                "what_the_record_says": {
                    "placement": r66["placement"],
                    "counts_unchanged": r66["counts_unchanged"]},
                "why_it_is_wrong": ("if the clause enters group B, group B becomes six. The "
                                    "counts field was carried over from record 65 by "
                                    "inertia, where it was correct because Q5 went into "
                                    "section 3-bis and not into a group anchored to the "
                                    "ledger."),
                "the_reading_that_reconciles_them_is_not_enough": (
                    "'this record does not change the counts, the document does' is what "
                    "was meant. But counts_unchanged is a field read COLD: in six months it "
                    "reads [12, 1, 5] in the register against B=6 in the document. Same "
                    "shape as checklist line 602 — an enumeration short by one, left where "
                    "somebody will copy it."),
                "corrected_counts": DOPO,
            },
            "ii_the_complete_placement_of_SGC_PRED": {
                "z_clause": {
                    "where": "group B of %s, as B6" % SMENTITE,
                    "anchored_to": ("row 66. Group B entries are anchored to the record that "
                                    "performs the RETIREMENT, not to the one declaring the "
                                    "prediction — B4 to row 13, B5 to row 29."),
                    "verdict_unchanged": r66["verdetto_z"],
                    "why_group_B": ("not nature giving way but the way the clause was "
                                    "written: a threshold on a quantity that is already a "
                                    "ratio to a dispersion, declared without the "
                                    "uncertainty of that quantity."),
                },
                "spectral_fraction": {
                    "where": "section 3-bis of %s, alongside the Q of D6" % SMENTITE,
                    "why_not_group_A": ("group A requires the ledger record in which the "
                                        "prediction is DECLARED — the rule fixed by record "
                                        "64. SGC_PRED is declared in the source, like Q1 to "
                                        "Q5, and has no such record. Section 3-bis is "
                                        "exactly the section for predictions declared "
                                        "outside the ledger."),
                    "verdict_unchanged": r66["verdetto_frazione"],
                    "measured": r66["misura_frazione"],
                    "consequence_for_the_section_title": (
                        "section 3-bis is headed 'the Q of D6'. With SGC_PRED in it the "
                        "heading no longer covers its content and must widen. That is the "
                        "document patcher's job, and this record is what it checks against."),
                },
                "why_the_halves_are_separated": (
                    "the two halves of one blind test end up in two sections, and that is a "
                    "real cost: read separately, they no longer show that a prediction "
                    "written before the datum was producible fell on one half and did not "
                    "decide on the other. The document must carry a cross reference in both "
                    "places. Keeping them together in a section of their own was the "
                    "alternative and was not taken."),
            },
            "iii_what_this_record_does_not_do": [
                "it does not revisit either verdict: the spectral fraction stays falsified, "
                "the |z| clause stays not decidable",
                "it does not patch the documents: smentite with B6 and the widened 3-bis, "
                "checklist rev. 3.26 and the tenth revision of paper2_stato.md follow",
                "it does not move Q5, which stays in section 3-bis where record 65 put it",
                "it does not touch anything measured: no register is read for numbers here, "
                "because nothing measured is in question",
            ],
        },
        "reason": (
            "The error is not in a measurement but in a field of a record, and it is the "
            "kind that survives precisely because nobody re-reads it: a counts field carried "
            "forward from the previous record while the surrounding text changed what the "
            "counts should be. It is caught here before the document patcher writes B=6 "
            "against a register that says B=5. The placement of the other half of SGC_PRED, "
            "which record 66 left unstated, is fixed at the same time so that the patcher "
            "has one thing to be checked against instead of two."),
        "evidence": (
            "Record 66 read from the ledger: rules.counts_unchanged = %s; new_value.%s."
            "placement = '%s'; new_value.ii_spectral_fraction_FALSIFIED.verdict = '%s', "
            "measured %s. Counts read from %s (sha256 %s): A=%d, A-bis=%d, B=%d, with rows "
            "Q1 to Q5 in section 3-bis — the document patcher has not run."
            % (r66["counts_unchanged"], SEZIONE_III, r66["placement"][:80],
               r66["verdetto_frazione"], r66["misura_frazione"], SMENTITE,
               smentite["sha256"], smentite["A"], smentite["A_bis"], smentite["B"])),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": ("The number of an amendment is its 1-based POSITION in this file. "
                           "This is record %d." % numero),
        "rules": {
            "amends_records": [66],
            "field_amended": "rules.counts_unchanged of record 66",
            "counts_before": PRIMA,
            "counts_after": DOPO,
            "a_counts_field_is_read_cold": (
                "it must agree with the document without needing the surrounding text. Any "
                "future record carrying a counts field states the number the documents will "
                "hold after the patchers run, not the number they hold while it is written."),
            "order_of_operations": (
                "this record first; then paper2_patch_documented_amendments.py from %d to "
                "%d; then freeze_verify; then, in one pass, smentite with B6 and the widened "
                "3-bis, checklist rev. 3.26 and the tenth revision of paper2_stato.md."
                % (n_prima, numero)),
        },
    }


def serializza(rec):
    return json.dumps(rec, ensure_ascii=False, sort_keys=False,
                      allow_nan=False).encode("utf-8")


def cmd_append(args):
    try:
        if not os.path.isfile(args.reference):
            raise Rifiuto("reference inesistente: %s" % args.reference)
        if not os.path.isfile(args.ledger):
            raise Rifiuto("ledger inesistente: %s" % args.ledger)
        ref_file_sha, ref_self_sha = ((sha256_file(args.reference), args.self_sha)
                                      if args.self_sha else leggi_reference(args.reference))
        raw, recs, _e, _c, _l = leggi_ledger(args.ledger)
        if len(recs) != args.attesi:
            raise Rifiuto("disco=%d attesi=%d" % (len(recs), args.attesi))
        eol = analizza_eol(raw)
        if eol["termina"] is None:
            raise Rifiuto("l'ultima riga del ledger non termina con un a capo")
        if recs[-1].get("item") != ITEM_PREV:
            raise Rifiuto("l'ultimo record non e' il 66: item='%s'" % recs[-1].get("item"))
        if any(r.get("item") == ITEM_67 for r in recs):
            raise Rifiuto("item gia' presente: %s" % ITEM_67)

        r66 = cancello_record_66(recs[-1])
        smentite = cancello_smentite(args.smentite)

        rec = costruisci(len(recs), ref_file_sha, ref_self_sha, r66, smentite)
        b = serializza(rec)
        if CRLF in b or LF in b:
            raise Rifiuto("il record serializzato contiene un fine riga")
        json.loads(b.decode("utf-8"))
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("ledger     : %s" % args.ledger)
    print("record     : %d (disco ora: %d)" % (len(recs) + 1, len(recs)))
    print("record 66  : counts_unchanged=%s, e la clausola |z| collocata nel gruppo B"
          % r66["counts_unchanged"])
    print("             le due cose non stanno insieme: B diventa sei")
    print("conteggi   : %s -> %s" % (PRIMA, DOPO))
    print("collocazione completa di SGC_PRED:")
    print("             |z| > 3            -> gruppo B come B6, ancorata alla riga 66")
    print("             frazione spettrale -> sezione 3-bis, accanto alle Q di D6")
    print("documento  : A=%d A-bis=%d B=%d, Q1-Q5 nella 3-bis (il patcher non ha girato)"
          % (smentite["A"], smentite["A_bis"], smentite["B"]))
    print("byte       : %d -> %d" % (len(raw), len(raw) + len(b) + len(eol["termina"])))

    if args.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    nuovo = raw + b + eol["termina"]
    if args.backup:
        with open(args.backup, "wb") as fh:
            fh.write(raw)
    d = os.path.dirname(os.path.abspath(args.ledger))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=os.path.basename(args.ledger) + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(nuovo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, args.ledger)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    raw2, recs2, _a, _b, _c = leggi_ledger(args.ledger)
    e2 = analizza_eol(raw2)
    esiti = [
        (len(recs2) == args.attesi + 1, "conteggio %d -> %d" % (args.attesi, len(recs2))),
        (raw2.startswith(raw), "i %d record precedenti sono byte-identici" % args.attesi),
        (e2["lf_isolati"] == eol["lf_isolati"] + (1 if eol["termina"] == LF else 0),
         "i fini riga preesistenti sono intatti, il nuovo e' ereditato (%s)"
         % ("LF" if eol["termina"] == LF else "CRLF")),
        (e2["crlf"] == eol["crlf"] + (1 if eol["termina"] == CRLF else 0),
         "nessun CRLF preesistente e' stato normalizzato"),
        (recs2[-1].get("item") == ITEM_67, "l'item e' quello nuovo"),
        ("record %d." % (args.attesi + 1) in recs2[-1]["numbering_rule"], "numbering_rule"),
        (recs2[-1]["rules"]["amends_records"] == [66], "emenda il 66"),
        (recs2[-1]["rules"]["counts_after"] == DOPO, "i conteggi corretti sono %s" % DOPO),
        ("counts_unchanged" not in recs2[-1]["rules"],
         "non usa piu' il campo che ha causato lo sbaglio"),
    ]
    print()
    for c, nome in esiti:
        print(("  OK  " if c else "  KO  ") + nome)
    if not all(c for c, _ in esiti):
        return 5
    print("\nOra: python src\\paper2_patch_documented_amendments.py apply --file "
          "src\\paper2_freeze_verify.py --da %d --a %d" % (args.attesi, args.attesi + 1))
    print("     python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    print("     poi i tre documenti in un colpo, con B=6.")
    return 0


# --------------------------------------------------------------------------- selftest


def _finto_66(counts=None, placement="group B of %s — thresholds badly posed." % SMENTITE,
              verdetto_z="NOT DECIDABLE — not a confirmation", frazione="FALSIFIED"):
    return {"item": ITEM_PREV, "n": 66,
            "new_value": {
                SEZIONE_III: {"placement": placement, "verdict": verdetto_z},
                "ii_spectral_fraction_FALSIFIED": {"verdict": frazione,
                                                   "measured": 0.8431707582648605}},
            "rules": {"counts_unchanged": PRIMA if counts is None else counts}}


def _finta_3bis(b=5, q=5):
    t = "# smentite\n\n"
    t += "".join("| A%d | x | y | z | w |\n" % i for i in range(1, 13))
    t += "| Ab1 | x | y | z | w |\n"
    t += "".join("| B%d | x | y | z |\n" % i for i in range(1, b + 1))
    t += "".join("| Q%d | a | b | c |\n" % i for i in range(1, q + 1))
    return t


def cmd_selftest(args=None):
    import shutil
    esiti = []

    def ok(nome, cond):
        esiti.append((bool(cond), nome))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", nome))

    class A(object):
        self_sha = None
        backup = None
        dry_run = False

    td = tempfile.mkdtemp(prefix="amend67_")
    try:
        led = os.path.join(td, "ledger.jsonl")
        ref = os.path.join(td, "reference.json")
        sm = os.path.join(td, "smentite.md")
        with open(ref, "wb") as fh:
            fh.write(json.dumps({"_self_sha256": "c" * 64}).encode("utf-8"))

        def scrivi_ledger(n=66, ultimo=None, termina=CRLF, lf_isolati=6):
            ultimo = ultimo if ultimo is not None else _finto_66()
            fuori = b""
            for i in range(1, n + 1):
                r = ultimo if i == n else {"item": "item_%d" % i, "n": i}
                bb = json.dumps(r).encode("utf-8")
                fuori += bb + (termina if i == n else (LF if i <= lf_isolati else CRLF))
            with open(led, "wb") as fh:
                fh.write(fuori)

        def scrivi_sm(testo=None):
            with open(sm, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(testo if testo is not None else _finta_3bis())

        def argomenti(attesi=66, dry=False):
            x = A()
            x.ledger, x.reference, x.smentite = led, ref, sm
            x.attesi, x.dry_run = attesi, dry
            return x

        scrivi_ledger()
        scrivi_sm()
        prima = open(led, "rb").read()
        ok("01 dry-run esce con 0", cmd_append(argomenti(dry=True)) == 0)
        ok("02 dry-run non scrive", open(led, "rb").read() == prima)
        ok("03 apply esce con 0", cmd_append(argomenti()) == 0)

        raw2, recs2, _a, _b, _c = leggi_ledger(led)
        rec = recs2[-1]
        ok("04 il ledger ha 67 record", len(recs2) == 67)
        ok("05 i 66 precedenti sono byte-identici", raw2.startswith(prima))
        ok("06 l'item e' quello del 67", rec["item"] == ITEM_67)
        ok("07 emenda il 66", rec["rules"]["amends_records"] == [66])
        ok("08 dichiara quale campo emenda",
           rec["rules"]["field_amended"] == "rules.counts_unchanged of record 66")
        ok("09 i conteggi vanno da 12/1/5 a 12/1/6",
           rec["rules"]["counts_before"] == PRIMA and rec["rules"]["counts_after"] == DOPO)
        ok("10 non riusa il campo che ha causato lo sbaglio",
           "counts_unchanged" not in rec["rules"])
        ok("11 e fissa la regola per i record futuri",
           "after the patchers run" in rec["rules"]["a_counts_field_is_read_cold"])

        nv = rec["new_value"]
        i = nv["i_the_two_statements_do_not_hold_together"]
        ok("12 il record cita testualmente cio' che il 66 dice",
           i["what_the_record_says"]["counts_unchanged"] == PRIMA
           and "group B" in i["what_the_record_says"]["placement"])
        ok("13 e spiega che il campo veniva dal 65 per inerzia",
           "inertia" in i["why_it_is_wrong"])
        ok("14 la lettura che concilia e' respinta, con la ragione",
           "read COLD" in i["the_reading_that_reconciles_them_is_not_enough"])
        ok("15 e il paragone con la riga 602 e' fatto",
           "line 602" in i["the_reading_that_reconciles_them_is_not_enough"])

        ii = nv["ii_the_complete_placement_of_SGC_PRED"]
        ok("16 la clausola |z| va in B6 ancorata alla riga 66",
           "B6" in ii["z_clause"]["where"] and "row 66" in ii["z_clause"]["anchored_to"])
        ok("17 la frazione spettrale va nella 3-bis, non nel gruppo A",
           "3-bis" in ii["spectral_fraction"]["where"]
           and "record 64" in ii["spectral_fraction"]["why_not_group_A"])
        ok("18 il titolo della 3-bis dovra' allargarsi, ed e' detto",
           "must widen" in ii["spectral_fraction"]["consequence_for_the_section_title"])
        ok("19 il costo di separare le due meta' e' dichiarato, non taciuto",
           "real cost" in ii["why_the_halves_are_separated"]
           and "cross reference" in ii["why_the_halves_are_separated"])
        ok("20 i due verdetti restano quelli del 66",
           ii["z_clause"]["verdict_unchanged"].startswith("NOT DECIDABLE")
           and ii["spectral_fraction"]["verdict_unchanged"] == "FALSIFIED")
        ok("21 cio' che il record NON fa e' elencato",
           len(nv["iii_what_this_record_does_not_do"]) == 4)
        ok("22 e dice che non legge registri, perche' non c'e' nulla di misurato in gioco",
           "no register is read" in nv["iii_what_this_record_does_not_do"][3])

        # rifiuti
        ok("23 un secondo apply e' rifiutato", cmd_append(argomenti(attesi=67)) == 2)

        scrivi_ledger()
        scrivi_sm()
        ok("24 attesi sbagliati -> rifiuto", cmd_append(argomenti(attesi=65)) == 2)

        scrivi_ledger(ultimo=_finto_66(counts=DOPO))
        scrivi_sm()
        ok("25 se il 66 avesse gia' i conteggi corretti -> rifiuto",
           cmd_append(argomenti()) == 2)

        scrivi_ledger(ultimo=_finto_66(placement="section 3-bis"))
        scrivi_sm()
        ok("26 se il 66 non collocasse la clausola nel gruppo B -> rifiuto",
           cmd_append(argomenti()) == 2)

        scrivi_ledger(ultimo=_finto_66(frazione="confermata"))
        scrivi_sm()
        ok("27 se il 66 non dichiarasse la frazione FALSIFIED -> rifiuto",
           cmd_append(argomenti()) == 2)

        scrivi_ledger()
        scrivi_sm(_finta_3bis(b=6))
        ok("28 se il documento avesse gia' B=6 -> rifiuto: il patcher gira DOPO",
           cmd_append(argomenti()) == 2)

        scrivi_ledger()
        scrivi_sm(_finta_3bis(q=4))
        ok("29 se mancasse Q5 dalla 3-bis -> rifiuto", cmd_append(argomenti()) == 2)

        scrivi_ledger(ultimo={"item": "item_altro", "n": 66})
        scrivi_sm()
        ok("30 se l'ultimo record non e' il 66 -> rifiuto", cmd_append(argomenti()) == 2)

        # fini riga, due regimi
        scrivi_ledger()
        scrivi_sm()
        prima = open(led, "rb").read()
        e0 = analizza_eol(prima)
        ok("31 ledger misto con ultima riga CRLF: apply passa", cmd_append(argomenti()) == 0)
        e1 = analizza_eol(open(led, "rb").read())
        ok("32 i LF isolati non sono toccati e il nuovo fine riga e' CRLF",
           e1["lf_isolati"] == e0["lf_isolati"] == 6 and e1["crlf"] == e0["crlf"] + 1)

        scrivi_ledger(termina=LF)
        scrivi_sm()
        prima = open(led, "rb").read()
        e0 = analizza_eol(prima)
        ok("33 ledger misto con ultima riga LF: apply passa", cmd_append(argomenti()) == 0)
        e1 = analizza_eol(open(led, "rb").read())
        ok("34 il nuovo fine riga e' LF e i CRLF non sono normalizzati",
           e1["lf_isolati"] == e0["lf_isolati"] + 1 and e1["crlf"] == e0["crlf"])

        ok("35 nessun temporaneo lasciato indietro",
           not [x for x in os.listdir(td) if x.endswith(".tmp")])

        scrivi_ledger()
        scrivi_sm()
        x = argomenti()
        x.backup = os.path.join(td, "ledger.bak")
        ok("36 con --backup il ledger precedente e' salvato",
           cmd_append(x) == 0 and os.path.isfile(x.backup))

    finally:
        shutil.rmtree(td, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper2_append_amend67.py",
                                description="Record 67: rettifica dei conteggi del 66.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("append")
    q.add_argument("--ledger", required=True)
    q.add_argument("--reference", required=True)
    q.add_argument("--attesi", type=int, required=True)
    q.add_argument("--smentite", default=SMENTITE.replace("/", os.sep))
    q.add_argument("--self-sha", default=None)
    q.add_argument("--backup", default=None)
    q.add_argument("--dry-run", action="store_true")
    q.set_defaults(func=cmd_append)

    q = sub.add_parser("selftest")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
