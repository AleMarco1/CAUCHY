#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_fix_phase8_paths.py

PASSO 0 - CORREZIONE DEI PERCORSI DI USCITA DI phase8_test2_masked.py

IL BUG
------
In phase8_test2_masked.main() il JSON di sintesi si dirama sul tag del run:

    outp = M.RES_DIR / ("phase8_test2_hodfit.json" if args.hod_json
                        else "phase8_test2_masked.json")

ma la tabella per-mock e la directory dei campi NO:

    tbl = M.RES_DIR / "phase8_test2_permock.csv"          # sempre uguale
    np.savez(out_fields / f"test2_{i:04d}.npz", delta=nu) # sempre uguale

CONSEGUENZA ACCERTATA
---------------------
Il run definitivo (--n_pilot 2000) ha scritto phase8_test2_masked.json
(congelato, 35436.686 +/- 312.989) e una tabella da 2000 righe. Un run
successivo a 200 mock con --hod_json ha correttamente deviato il proprio JSON
su phase8_test2_hodfit.json, ma ha SOVRASCRITTO:
  - phase8_test2_permock.csv  con le proprie 200 righe
  - phase8_test2_fields/test2_0000..0199.npz  con i propri cubi

Da li' phase9_extract_features.py, facendo glob("test2_*.npz") su tutti i 2000,
ha letto 200 cubi di un run con HOD diverso e prodotto sigma = 444.81 invece di
312.99. Il suo controllo di consistenza confrontava la media (drift 0.038,
superato) e mai la deviazione standard. Quel numero e' finito nella tabella
battery di M26 e nella decomposizione della varianza.

Prova diretta: la tabella del pilota coincide con l'npz su 200/200 valori e con
la catena definitiva su 0/200.

PERCHE' ORA
-----------
E' bloccante per M2, N6 e N7, che salvano campi e tabelle per-mock: senza la
correzione la contaminazione si ripete. Ed e' bloccante per Paper 3, che gira
a protocollo pre-registrato, dove sarebbe molto piu' grave.

COSA FA QUESTA PATCH
--------------------
1. dirama tbl e out_fields sul tag del run, mantenendo i nomi attuali per il
   run canonico (senza --hod_json) per non rompere i consumatori esistenti
2. rifiuta di sovrascrivere artefatti gia' presenti a meno di --force
3. verifica che RES_DIR stia sotto --project_root: main() legge
   args.project_root ma non lo propaga mai a M.ROOT, che all'import vale
   Path("."). Lo script funziona solo se lanciato dalla radice del progetto, e
   oggi fallisce in silenzio scrivendo altrove. Meglio un errore rumoroso che
   ricostruire tutti i percorsi di M, che introdurrebbe altri rischi.
4. corregge il docstring di load_nwlh_params(), che dichiara 6 colonne mentre
   il file ne ha 7 (verificato: 0=Om 1=Ob 2=h 3=ns 4=s8 5=Mnu 6=w0)

USO
---
  python src\\paper1_rev_fix_phase8_paths.py              # anteprima
  python src\\paper1_rev_fix_phase8_paths.py --apply      # scrive, con backup
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

# (descrizione, testo_da_cercare, testo_sostitutivo)
PATCHES = [
    (
        "1a. tag del run e percorsi diramati",
        """    out_fields = M.RES_DIR / "phase8_test2_fields"
    if args.save_fields:
        out_fields.mkdir(parents=True, exist_ok=True)""",
        """    # --- tag del run: il JSON si diramava gia', la tabella e i campi no.
    # Era il bug che ha contaminato gli indici 0-199 di phase8_test2_fields/
    # e phase8_test2_permock.csv con i cubi di un run a HOD diverso.
    run_tag = "hodfit" if args.hod_json else None
    sfx = f"_{run_tag}" if run_tag else ""

    out_fields = M.RES_DIR / f"phase8_test2_fields{sfx}"
    if args.save_fields:
        if out_fields.exists() and any(out_fields.iterdir()) and not args.force:
            sys.exit(f"[FATAL] {out_fields} esiste e non e' vuota. "
                     f"Usa --force per sovrascrivere, o cambia tag.")
        out_fields.mkdir(parents=True, exist_ok=True)

    # --- RES_DIR e' costruita all'import di phase8_cutsky_mocks con
    # ROOT = Path("."): main() legge args.project_root ma non lo propaga mai.
    # Lo script funziona solo se lanciato dalla radice del progetto; oggi
    # fallisce in silenzio scrivendo altrove.
    _root = Path(args.project_root).resolve()
    if _root not in M.RES_DIR.resolve().parents and M.RES_DIR.resolve() != _root:
        sys.exit(f"[FATAL] RES_DIR = {M.RES_DIR.resolve()} non sta sotto "
                 f"{_root}.\\n         Lancia lo script dalla radice del "
                 f"progetto: cd {_root}")""",
    ),
    (
        "1b. tabella per-mock diramata, con guardia sulla sovrascrittura",
        """    tbl = M.RES_DIR / "phase8_test2_permock.csv\"""",
        """    tbl = M.RES_DIR / f"phase8_test2_permock{sfx}.csv"
    if tbl.exists() and not args.force:
        sys.exit(f"[FATAL] {tbl} esiste gia'. Usa --force per sovrascrivere.")""",
    ),
    (
        "2. opzione --force",
        """    ap.add_argument("--save_fields", action="store_true")""",
        """    ap.add_argument("--save_fields", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="consenti di sovrascrivere tabella e campi esistenti")""",
    ),
    (
        "3. docstring di load_nwlh_params: 7 colonne, non 6",
        """    \"\"\"Load per-simulation (Om, s8, w0) from the nwLH params file. The Quijote
    nwLH latin hypercube params are columns (Om, Ob, h, ns, s8, w0). Returns a""",
        """    \"\"\"Load per-simulation (Om, s8, w0) from the nwLH params file. The Quijote
    nwLH latin hypercube params file has SEVEN columns, verified against
    phase9_likeforlike_arrays.npz on indices 0-199 (max|diff| = 0.0):
        0=Om  1=Ob  2=h  3=ns  4=s8  5=Mnu  6=w0
    (il docstring precedente ne dichiarava sei: era errato; gli indici usati
    sotto, tab[:,0] tab[:,4] tab[:,6], erano invece corretti). Returns a""",
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--target", default="src\\phase8_test2_masked.py")
    ap.add_argument("--apply", action="store_true",
                    help="senza questo flag mostra solo l'anteprima")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    parts = [q for q in args.target.replace("\\", "/").split("/") if q]
    tgt = root.joinpath(*parts)
    if not tgt.exists():
        print(f"[FATAL] {tgt} non trovato")
        return 1

    src = tgt.read_text(encoding="utf-8")
    print("=" * 78)
    print(f"PATCH DI {tgt}")
    print("=" * 78)

    new = src
    applied, missing = [], []
    for desc, old, rep in PATCHES:
        n = new.count(old)
        if n == 1:
            new = new.replace(old, rep, 1)
            applied.append(desc)
            print(f"\n  [OK]      {desc}")
        elif n == 0:
            missing.append(desc)
            print(f"\n  [ASSENTE] {desc}")
            print(f"            blocco non trovato: gia' applicata, oppure il")
            print(f"            file e' cambiato. Verifica a mano.")
        else:
            missing.append(desc)
            print(f"\n  [AMBIGUA] {desc}: {n} occorrenze, non tocco nulla.")

    if "import sys" not in new.split("def ")[0]:
        new = new.replace("import argparse", "import argparse\nimport sys", 1)
        print("\n  [OK]      aggiunto 'import sys' (serve ai sys.exit)")

    print("\n" + "-" * 78)
    print(f"  applicate: {len(applied)}/{len(PATCHES)}")
    if missing:
        print(f"  non applicate: {missing}")

    if not args.apply:
        print("\n  ANTEPRIMA: nessun file scritto. Rilancia con --apply.")
        print("\n  Dopo la patch, i percorsi diventano:")
        print("    run canonico  : phase8_test2_permock.csv, phase8_test2_fields/")
        print("    run --hod_json: phase8_test2_permock_hodfit.csv,")
        print("                    phase8_test2_fields_hodfit/")
        print("  I nomi del run canonico restano invariati, quindi i")
        print("  consumatori esistenti continuano a funzionare.")
        return 0

    if new == src:
        print("\n  nessuna modifica da scrivere.")
        return 0

    bak = tgt.with_suffix(
        f".py.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(tgt, bak)
    tgt.write_text(new, encoding="utf-8")
    print(f"\n  backup : {bak}")
    print(f"  scritto: {tgt}")

    import py_compile
    try:
        py_compile.compile(str(tgt), doraise=True)
        print("  compilazione: OK")
    except Exception as e:
        print(f"  *** COMPILAZIONE FALLITA: {e}")
        print(f"  *** ripristino dal backup")
        shutil.copy2(bak, tgt)
        return 1

    print("\n  NOTA: i campi 0-199 attualmente in phase8_test2_fields/ restano")
    print("  quelli contaminati. La patch impedisce che accada di nuovo, non")
    print("  li ripara. Per Paper 1 non serve ripararli (la nostra catena ha")
    print("  gia' i valori corretti per tutti i 2000); servono per rigenerare")
    print("  i prodotti a valle di M26.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
