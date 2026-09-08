#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Emendamento: ri-freeze del tier `records`, 25 ago 2026.

COSA REGISTRA
  Il tier `records` fu congelato due volte lo stesso giorno. Fra i due passaggi
  un file uscì dal set. QUESTA DOCSTRING AFFERMAVA che il secondo freeze non fu
  mai committato e che in git era rimasto il primo: è falso, vedi la RETTIFICA
  qui sotto. La discrepanza (225 contro 224 file, due `aggregate_sha256`
  diversi) non era registrata da nessuna parte se non nel messaggio di un
  commit, ed è esattamente ciò che il file degli emendamenti esiste per
  impedire.

CRONOLOGIA, RICOSTRUITA AL SECONDO
  12:44:26Z  freeze n. 1 - 225 file, 20 721 562 byte
  14:43:05Z  commit 312218b rimuove results/phase8_test2_permock.csv:
             byte-identico a phase8_test2_permock_hodfit.csv (stesso sha256
             ae733e1e...), conteneva il sottoinsieme HOD-refit
             (35304.6 +/- 1033.0, N=200), NON la baseline test2.
  14:43:06Z  freeze n. 2 - 224 file, 20 710 671 byte.

  Differenza: 10 891 byte, cioè esattamente la dimensione del file rimosso.

RETTIFICA — record 12 del file degli emendamenti, 28 ago 2026
  Il freeze n. 2 FU committato, in 6522204. L'attribuzione a 312218b della
  rimozione di results/phase8_test2_permock.csv, e l'affermazione che il n. 2
  non fosse in git, sono errate e sono rettificate nel record 12.

  Il PAYLOAD qui sotto non viene corretto. La stringa `reason` di RECORD è ciò
  che ha prodotto il record 11, già scritto su un file append-only: riscriverla
  farebbe emettere a questo script un record diverso da quello su disco, e la
  prossima esecuzione non sarebbe più la riproduzione di ciò che è stato fatto.
  La storia leggibile — valore sbagliato, rettifica, motivo — è il prodotto
  dell'item 0.12, non un residuo da ripulire. Chi legge il file SOVRAPPONE il
  record 12 all'11; nessuno li fonde.

IDEMPOTENZA (aggiunta 29 ago 2026)
  Questo script ha già girato con --apply: il suo record è l'11 di 13. Rilanciarlo
  appenderebbe un doppione, che il conteggio di paper2_freeze_verify.py
  intercetterebbe a valle, ma dopo la scrittura e su un file che non si corregge.
  Il cancello sotto lo impedisce a monte.

PERCHE' LA VERSIONE SU DISCO E' QUELLA AUTOREVOLE
  I cinque tier su disco sommano a 34 836 file e 26.771 GiB, cioè i valori
  dichiarati per l'ensemble v1. Con 225 file nel tier records il totale sarebbe
  34 837. E `reference_sha256` è IDENTICO nelle due versioni: il reference
  congelato non è mai stato toccato, in ballo era solo la contabilità di un tier.

  Nota metodologica: un manifest troncato SUPERA la verifica proprio perché
  verifica meno cose. Il fatto che il pre-volo passasse non era una prova che la
  copia fosse corretta. La prova è il confronto col totale dichiarato.

Uso:
    python src\\paper2_amend_freeze.py            # anteprima
    python src\\paper2_amend_freeze.py --apply
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REF = "src/paper2_v1_reference.json"
REF_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
AMEND = "src/paper2_v1_amendments.jsonl"
FREEZE = "results/paper2/ensemble_v1_freeze_records.json"
UTC = "2026-08-27T00:00:00Z"

EXPECTED = {
    "n_files": 224,
    "total_bytes": 20710671,
    "aggregate_sha256": "5364cf2ef1cac16c66e2f80dcd897bee8d14324100f15d0c9b471085f4b876f0",
    "frozen_at_utc": "2026-08-25T14:43:06+00:00",
}
TIERS_TOTAL_FILES = 34836
TIERS_TOTAL_BYTES_GIB = 26.771

RECORD = {
    "item": "0.1",
    "type": "amendment",
    "json_path": "ensemble_v1_freeze_records",
    "key": "n_files / total_bytes / aggregate_sha256 / frozen_at_utc",
    "old_value": {
        "n_files": 225,
        "total_bytes": 20721562,
        "aggregate_sha256": "e905d7fd085b23e9a7e534e2583a4940a40904d1a6cf3bdc3a0e9011ffe882ce",
        "frozen_at_utc": "2026-08-25T12:44:26+00:00",
    },
    "new_value": dict(EXPECTED),
    "reason": ("Il tier `records` fu congelato due volte il 25 ago 2026. Fra i due passaggi "
               "il commit 312218b (14:43:05Z) rimosse results/phase8_test2_permock.csv, "
               "byte-identico a phase8_test2_permock_hodfit.csv (sha256 ae733e1e...): "
               "conteneva il sottoinsieme HOD-refit (35304.6 +/- 1033.0, N=200), non la "
               "baseline test2. Il freeze n. 2 (14:43:06Z) non fu mai committato, quindi in "
               "git e' rimasto il n. 1. La differenza di 10 891 byte e' esattamente la "
               "dimensione del file rimosso. La versione su DISCO e' autorevole."),
    "evidence": ("I cinque tier su disco sommano a 34 836 file e 26.771 GiB, i valori "
                 "dichiarati per l'ensemble v1; con 225 file il totale sarebbe 34 837. "
                 "diagrams 16221, features 12189, fields 2202, records 224, superseded 4000. "
                 "`reference_sha256` identico nelle due versioni: il reference non e' mai "
                 "stato toccato. Commit di correzione: vedi git log su "
                 "results/paper2/ensemble_v1_freeze_records.json."),
    "note": ("Un manifest troncato supera la verifica perche' verifica meno cose: il "
             "pre-volo passato non era una prova di correttezza. Per i freeze futuri, "
             "confrontare sempre il TOTALE sui tier col valore dichiarato."),
    "reference_file": REF,
    "reference_sha256": REF_SHA,
    "utc": UTC,
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Emendamento: ri-freeze del tier records")
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = Path(args.project_root).resolve()

    ref = root / REF
    got = sha256_file(ref)
    print("reference sha256 = %s" % got)
    if got != REF_SHA:
        sys.exit("[FATAL] il reference NON e' quello congelato. Non scrivo.")
    print("  intatto.\n")

    fz = json.loads((root / FREEZE).read_text(encoding="utf-8"))
    print("stato su disco di %s:" % FREEZE)
    bad = []
    for k, v in EXPECTED.items():
        ok = fz.get(k) == v
        bad += [] if ok else [k]
        print("  %-18s %-70s %s" % (k, str(fz.get(k))[:70], "ok" if ok else "DIVERSO"))
    if bad:
        sys.exit("\n[FATAL] il freeze su disco non e' quello atteso (%s).\n"
                 "        L'emendamento descriverebbe uno stato che non esiste." % ", ".join(bad))

    tot_f = tot_b = 0
    for f in sorted((root / "results" / "paper2").glob("ensemble_v1_freeze_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        tot_f += d["n_files"]
        tot_b += d["total_bytes"]
        print("  %-52s %6d file" % (f.name, d["n_files"]))
    print("  %-52s %6d file  %.3f GiB" % ("TOTALE", tot_f, tot_b / 1024 ** 3))
    if tot_f != TIERS_TOTAL_FILES:
        sys.exit("[FATAL] totale %d, atteso %d: non confermo l'autorevolezza del disco."
                 % (tot_f, TIERS_TOTAL_FILES))
    print("  -> combacia con l'ensemble v1 dichiarato (%d file, %.3f GiB).\n"
          % (TIERS_TOTAL_FILES, TIERS_TOTAL_BYTES_GIB))

    path = root / AMEND
    n0 = sum(1 for ln in open(path, encoding="utf-8") if ln.strip()) if path.exists() else 0
    print("emendamenti gia' presenti: %d" % n0)

    # Il file e' append-only: un doppione non si toglie. Se il record di questo
    # script c'e' gia', non se ne scrive un altro. Il confronto e' sul CONTENUTO
    # (json_path + old_value), non sulla posizione, perche' la posizione e' il
    # numero dell'emendamento e non un identificatore.
    if path.exists():
        for i, ln in enumerate(
                (l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()), 1):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if (isinstance(r, dict)
                    and r.get("json_path") == RECORD["json_path"]
                    and r.get("old_value") == RECORD["old_value"]):
                print("\n[gia' applicato] il record di questo script e' il n. %d." % i)
                print("                 Nessuna scrittura: il file e' append-only e")
                print("                 un doppione non si toglie.")
                return 0
    print("\n--- da appendere: item %s -> %s" % (RECORD["item"], RECORD["json_path"]))
    print("    %s..." % RECORD["reason"][:160])

    if not args.apply:
        print("\n[anteprima] nessuna scrittura. Rilanciare con --apply.")
        return 0

    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(RECORD, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    if sha256_file(ref) != REF_SHA:
        sys.exit("[FATAL] il reference e' cambiato durante la scrittura. Indagare.")
    print("\n[scritto] 1 record; totale %d. Reference invariato." % (n0 + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
