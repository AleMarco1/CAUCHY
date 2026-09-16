#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_checklist_fase4.py

Allinea le voci 4.2b e 4.2c di checklist_paper2.md ai record 50 e 54.

PERCHE'
-------
La checklist e' ferma alla rev. 3.18, che PRECEDE i record 50-55. Il suo §4.2b
chiede ancora di registrare le quattro predizioni che il record 50 ha ritirato
prima di qualunque misura, e il §4.2c porta ancora «~4000 -> ~0», riscritta dal
record 54. Chi seguisse la checklist senza il registro rifarebbe esattamente il
lavoro ritirato.

COME
----
Non riproduce il testo esistente per sostituirlo: lo LOCALIZZA per riga di
apertura e lo rimpiazza fino alla voce successiva. Cosi' l'ancora non dipende
dagli a capo, che in un file a righe rifluite sono la cosa piu' facile da
sbagliare. Rifiuta se le occorrenze non sono esattamente una per voce.

Ogni voce passa a [~]: la dichiarazione e' fatta, la misura su v2 no. Nessuna
delle due si chiude finche' 4.2a non gira.

Il marcatore di revisione e' un PARAMETRO: la convenzione della checklist e' che
le voci nuove portino il segno della revisione che le introduce, e quale sia lo
decide chi apre la revisione, non questo script.

USO
    python src\\paper2_patch_checklist_fase4.py selftest
    python src\\paper2_patch_checklist_fase4.py applica --file checklist_paper2.md ^
        --marca "✦✦" --dry-run
    python src\\paper2_patch_checklist_fase4.py applica --file checklist_paper2.md ^
        --marca "✦✦" --backup logs\\checklist_pre_fase4.md

Uscita: 0 se applicato, 2 se rifiutato, 3 se la rilettura non torna.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile

# Le voci si aprono cosi'. Il gruppo 1 e' lo stato della casella.
APRE_4_2B = re.compile(r"^- \[([ x~])\] \*\*(?:[^*]*?)4\.2b —", re.M)
APRE_4_2C = re.compile(r"^- \[([ x~])\] \*\*(?:[^*]*?)4\.2c —", re.M)
# Una voce finisce dove ne comincia un'altra, o dove comincia un titolo.
PROSSIMA = re.compile(r"^(?:- \[[ x~]\] |#{1,6} |---\s*$)", re.M)


def nuovo_4_2b(marca):
    m = (marca + " ") if marca else ""
    return f"""- [~] **{m}4.2b — Le predizioni a un punto. RITIRATE, RISCRITTE, e il lato v1 MISURATO.**
      Le quattro elencate qui fino alla rev. 3.18 — varianza da 1085 verso 1, curtosi da +3.90 verso
      +0.20, ν₉₉−ν₁ da 5.6σ verso 3.22σ, massimo δ da 32 244 verso ~125 — sono state **ritirate nel
      record 50, prima di qualunque misura**: erano scritte su restrizione, statistica o lato diversi
      da quelli che il run avrebbe misurato. **Non si riaprono** (`paper2_stato.md` §5).
      **Le soglie in vigore** (record 50 per 4.2b-5, record 54 per 4.2b-1; 4.2b-2 invariata):

      | regola | soglia | v1 misurato, *n*=2000 |
      |---|---|---|
      | 4.2b-1 varianza di δ | successo *R*+3σ < **7.2924** (NGC), **16.1314** (SGC) | *R*_full 975.41 / 2052.99 |
      | 4.2b-2 curtosi di ν | successo \\|*z*\\| < 3, fallimento > 5 | *z* = **−7.108** / **−8.150** |
      | ~~4.2b-3~~ ν₉₉−ν₁ | **RITIRATA come falsificazione**, resta diagnostica | *r*_f *z* = −9.666 / −11.840 |
      | 4.2b-4 massimo di δ | rango nel 95% centrale | rango **0/2000** in entrambi |
      | 4.2b-5 Box–Cox | successo < 45.8 gen, fallimento > 137.5 | invariata dal record 50 |

      **4.2b-1 è ricalibrata a *n*=2000** perché v2 sarà misurata su 2000 e non su 200: la base a P10
      passa da 3.6791/8.1016 a **3.6462/8.0657**, e la revisione va nel verso **più stretto**.
      **4.2b-3 è ritirata per collinearità**, non per debolezza: curtosi e *r*_f danno Pearson +0.9988
      in NGC e +0.9985 in SGC, su maschere e geometrie diverse. Il criterio della scelta è dichiarato
      nel record 54 **e non è il *z***, che avrebbe premiato *r*_f.
      **Su v1 nessuna delle regole soddisfa la condizione di successo**: va saputo prima di leggere
      v2, perché un fallimento su v2 non è informativo se nulla si è mosso.
      *(Misure: `results/paper2/onepoint_v1_{{NGC,SGC}}.jsonl` e le due righe DESI, prodotte da
      `src/paper2_passata_1punto.py` in 4.1 minuti per emisfero, con 1850 ancore riprodotte in NGC e
      zero in SGC, dove nessun cubo ν congelato esiste.)*
"""


def nuovo_4_2c(marca):
    m = (marca + " ") if marca else ""
    return f"""- [~] **{m}4.2c — Voxel patologici. SOGLIA DICHIARATA (record 54).**
      «~4000 per mock (1.3%) → ~0» era un attraversamento senza denominatore né zona di indecisione,
      cioè la forma delle quattro ritirate nel record 50 e l'unica sopravvissuta. Non era
      riscrivibile prima perché `n_patologici` non esisteva in nessun registro.
      Misurato su 2000 realizzazioni: **4048.21 ± 84.66** (NGC, SEM 1.893, min 3314) e
      **2811.56 ± 71.45** (SGC, SEM 1.598, min 2195), cioè l'1.3152% e l'1.6325% dei voxel.
      **Successo sotto un terzo, fallimento sopra due terzi** della media v1: **1349.40 / 2698.81**
      (NGC) e **937.19 / 1874.37** (SGC), sulla media d'ensemble come *P*_mock in 4.3b. Le frazioni
      sono quelle già dichiarate per 4.3b: **nessuna frazione nuova**.
      **Invalidazione:** se su v2 la dispersione per realizzazione supera un terzo della media v2, la
      regola smette di decidere. Su v1 vale 2.09% e 2.54%, lontanissima.
      **È l'unica regola interamente lato mock.** La soglia è il massimo di δ di DESI in maschera —
      125.47415161132812 e 161.6696 — fissa sotto ripesatura, e il conteggio viene tutto dal campo
      mock: frazione invariante **zero**. È per questo la sola che porta informazione non già
      contenuta nelle altre, che coprono tre direzioni e non cinque.
      **Una regola in σ non funzionerebbe**: SEM 1.893 su 4048.21, quindi ogni effetto reale vale
      migliaia di σ e la soglia non separerebbe successo da fallimento.
"""


def valida_marca(marca, testo=None):
    """Una marca con < o > e' quasi sempre un segnaposto copiato da un messaggio.
    E' successo tre volte. Il rimedio e' un rifiuto, non la prudenza."""
    if marca and ("<" in marca or ">" in marca):
        raise SystemExit("RIFIUTO: la marca %r sembra un segnaposto, non un segno di "
                         "revisione. Passa il glifo vero, o '' per nessuna marca." % marca)
    if len(marca) > 12:
        raise SystemExit("RIFIUTO: marca lunga %d caratteri: e' un segno, non una frase."
                         % len(marca))
    if testo is not None and marca:
        # LA MARCA NON DEV'ESSERE INDISTINGUIBILE DA UNA PRECEDENTE.
        # L'11 settembre la rev. 3.20 e' stata scritta con ✦✦✦, che e'
        # sottostringa delle ✦✦✦✦ della rev. 3.17: le due revisioni sarebbero
        # state indistinguibili, e una sostituzione cieca avrebbe corrotto le
        # marche altrui. Se ne e' accorto un assert scritto a mano.
        #
        # RIFIUTO solo in quel caso. La presenza ISOLATA della marca non e' un
        # difetto: dentro una revisione la stessa marca si usa con piu' patcher,
        # ed e' il flusso normale. Li' si avvisa e basta — un rifiuto
        # bloccherebbe l'uso legittimo, e un cancello che ferma il lavoro giusto
        # viene disattivato, non rispettato.
        glifo = marca[0]
        piu_lunga = max((len(m.group()) for m in
                         re.finditer(re.escape(glifo) + "+", testo)), default=0)
        if piu_lunga > len(marca):
            raise SystemExit(
                "RIFIUTO: la marca %r cade dentro una sequenza di %d %r gia'"
                " presente: le due sarebbero indistinguibili, e una"
                " sostituzione cieca corromperebbe quella vecchia."
                % (marca, piu_lunga, glifo))
        n = testo.count(marca)
        if n:
            print("    [avviso] la marca %r compare gia' %d volte: se e' di"
                  " questa revisione va bene, se e' di una precedente le due"
                  " diventano indistinguibili." % (marca, n))
    return marca


def blocco(testo, apre, nome):
    """Estremi del blocco della voce. Rifiuta se le occorrenze non sono una."""
    trovate = list(apre.finditer(testo))
    if len(trovate) != 1:
        raise SystemExit(f"RIFIUTO: {nome} trovata {len(trovate)} volte, attesa 1")
    i = trovate[0].start()
    dopo = PROSSIMA.search(testo, trovate[0].end())
    if dopo is None:
        raise SystemExit(f"RIFIUTO: non trovo dove finisce {nome}")
    return i, dopo.start()


def applica(path, marca, dry_run=False, backup=None):
    valida_marca(marca)
    if not os.path.isfile(path):
        raise SystemExit(f"RIFIUTO: file inesistente: {path}")
    with open(path, "rb") as fh:
        grezzo = fh.read()
    testo = grezzo.decode("utf-8")
    valida_marca(marca, testo)   # la marca dev'essere LIBERA: serve il testo, che ora c'e'

    # ordine decrescente: sostituire la seconda prima non sposta la prima
    ib, fb = blocco(testo, APRE_4_2B, "4.2b")
    ic, fc = blocco(testo, APRE_4_2C, "4.2c")
    if not ib < fb <= ic < fc:
        raise SystemExit("RIFIUTO: 4.2b e 4.2c non sono in ordine e disgiunte")

    print(f"file    : {os.path.abspath(path)}")
    print(f"4.2b    : byte {ib}-{fb}, {fb - ib} byte, casella "
          f"'{APRE_4_2B.search(testo).group(1)}' -> '~'")
    print(f"4.2c    : byte {ic}-{fc}, {fc - ic} byte, casella "
          f"'{APRE_4_2C.search(testo).group(1)}' -> '~'")
    print(f"marca   : {marca!r}")

    nuovo = testo[:ib] + nuovo_4_2b(marca) + testo[fb:ic] + nuovo_4_2c(marca) + testo[fc:]
    print(f"byte    : {len(grezzo)} -> {len(nuovo.encode('utf-8'))}")

    # cio' che sta fuori dai due blocchi non si muove
    if testo[:ib] != nuovo[:ib] or testo[fc:] != nuovo[len(nuovo) - len(testo[fc:]):]:
        raise SystemExit("RIFIUTO: la sostituzione tocca testo fuori dai due blocchi")

    if dry_run:
        print("dry-run: nessuna scrittura")
        return 0

    if backup:
        os.makedirs(os.path.dirname(os.path.abspath(backup)) or ".", exist_ok=True)
        with open(backup, "wb") as fh:
            fh.write(grezzo)
        print(f"backup  : {os.path.abspath(backup)}")

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nuovo)

    with open(path, "r", encoding="utf-8") as fh:
        riletto = fh.read()
    if riletto != nuovo:
        print("ERRORE: la rilettura non coincide con lo scritto")
        return 3
    for frammento, dove in (("7.2924", "4.2b"), ("1349.40", "4.2c"),
                            ("RITIRATA come falsificazione", "4.2b"),
                            ("frazione invariante", "4.2c")):
        if frammento.lower() not in riletto.lower():
            print(f"ERRORE: '{frammento}' assente dopo la scrittura ({dove})")
            return 3
    # La guardia NON puo' cercare «da 1085 verso 1»: il testo nuovo la cita, perche'
    # dice quali predizioni sono state ritirate. Cerca l'APERTURA vecchia, che il
    # testo nuovo non contiene.
    for vecchio in ("Le predizioni a un punto, mai misurate",
                    "Voxel patologici:** ~4000 per mock"):
        if vecchio in riletto:
            print(f"ERRORE: l'apertura vecchia e' ancora presente: {vecchio!r}")
            return 3
    print("riletto : le due voci sono nuove e le aperture vecchie non ci sono piu'")
    print("APPLICATO")
    print()
    print("Da fare a mano, perche' non e' materia di uno script:")
    print("  - aprire il blocco di changelog della revisione nuova, senza riscrivere i precedenti")
    print("  - aggiornare il numero di revisione in testa")
    return 0


CHECKLIST_FINTA = """# Titolo

## Fase 4 — Componente B

### 4.1 — Cosa il Paper 1 ha gia' fatto

testo che non si tocca.

### 4.2 — Cosa resta

- [ ] **4.2a — Ensemble v2 completo** sui 2000. ~2 h/emisfero.
- [ ] **4.2b — Le predizioni a un punto, mai misurate.** Registrarle **prima**: varianza di delta
      mock/DESI da 1085 verso 1; curtosi in eccesso; massimo delta da 32 244 verso ~125.
- [ ] **4.2c — Voxel patologici:** ~4000 per mock (1.3%) -> ~0.
- [ ] **4.2d — Tab. 12 su v2 come cancello interno.**

### 4.3 — Componente C

- [ ] **4.3a** Erosione k = 0-3.
"""


def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print(f"  [ok ] {tot:2d} {n}")
        else:
            print(f"  [FAIL] {tot:2d} {n}  {det}")

    print("selftest paper2_patch_checklist_fase4")


    for cattiva in ("<segno vero>", "<idem>", "<il segno della revisione nuova>"):
        try:
            applica("/nonesiste", cattiva)
            chk(f"segnaposto {cattiva!r} respinto", False, "non ha rifiutato")
        except SystemExit as e:
            chk(f"segnaposto {cattiva!r} respinto", "segnaposto" in str(e), str(e))
    try:
        applica("/nonesiste", "\u2726\u2726")
        chk("un glifo vero passa la guardia", False)
    except SystemExit as e:
        chk("un glifo vero passa la guardia", "inesistente" in str(e), str(e))
    chk("marca vuota ammessa", valida_marca("") == "")
    base = tempfile.mkdtemp(prefix="chk_")
    f = os.path.join(base, "checklist.md")

    def scrivi(t=CHECKLIST_FINTA):
        with open(f, "w", encoding="utf-8", newline="") as fh:
            fh.write(t)

    scrivi()
    prima = open(f, "rb").read()

    chk("il testo ritirato e' nella checklist finta", b"da 1085 verso 1" in prima)
    chk("dry-run non scrive",
        applica(f, "M", dry_run=True) == 0 and open(f, "rb").read() == prima)

    bk = os.path.join(base, "bk.md")
    chk("applica riesce", applica(f, "M", backup=bk) == 0)
    dopo = open(f, "r", encoding="utf-8").read()
    chk("il backup e' il file di prima", open(bk, "rb").read() == prima)
    chk("l'apertura vecchia non c'e' piu'",
        "Le predizioni a un punto, mai misurate" not in dopo)
    chk("il testo nuovo CITA le predizioni ritirate, e deve",
        "da 1085 verso 1" in dopo)
    chk("le soglie nuove ci sono", "7.2924" in dopo and "1349.40" in dopo)
    chk("le caselle passano a [~]",
        "- [~] **M 4.2b" in dopo and "- [~] **M 4.2c" in dopo, dopo[:0])
    chk("4.2a non e' stata toccata", "- [ ] **4.2a — Ensemble v2 completo** sui 2000." in dopo)
    chk("4.2d non e' stata toccata", "- [ ] **4.2d — Tab. 12 su v2 come cancello interno.**" in dopo)
    chk("4.3a non e' stata toccata", "- [ ] **4.3a** Erosione k = 0-3." in dopo)
    chk("il testo prima della Fase 4 e' intatto", dopo.startswith("# Titolo\n\n## Fase 4"))
    chk("4.1 non e' stata toccata", "testo che non si tocca." in dopo)
    chk("l'ordine delle voci e' conservato",
        dopo.index("4.2a") < dopo.index("4.2b") < dopo.index("4.2c") < dopo.index("4.2d"))

    # senza marca
    scrivi()
    applica(f, "")
    d2 = open(f, "r", encoding="utf-8").read()
    chk("senza marca la riga non ha spazio doppio", "- [~] **4.2b —" in d2)

    # rifiuti
    scrivi(CHECKLIST_FINTA.replace("- [ ] **4.2c — Voxel patologici:** ~4000 per mock (1.3%) -> ~0.\n", ""))
    try:
        applica(f, "M", dry_run=True)
        chk("voce assente: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("voce assente: rifiuto", "4.2c trovata 0 volte" in str(e), str(e))

    scrivi(CHECKLIST_FINTA + "\n- [ ] **4.2c — Voxel patologici:** doppione.\n")
    try:
        applica(f, "M", dry_run=True)
        chk("voce doppia: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("voce doppia: rifiuto", "trovata 2 volte" in str(e), str(e))

    try:
        applica(os.path.join(base, "inesistente.md"), "M")
        chk("file inesistente: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("file inesistente: rifiuto", "inesistente" in str(e))

    # idempotenza: una seconda passata non deve raddoppiare nulla
    scrivi()
    applica(f, "M")
    una = open(f, "rb").read()
    applica(f, "M")
    due = open(f, "rb").read()
    chk("una seconda passata e' byte-identica alla prima", una == due,
        f"{len(una)} contro {len(due)}")
    chk("la seconda passata non raddoppia le voci",
        due.decode("utf-8").count("4.2b — Le predizioni") == 1)

    print(f"\n{ok}/{tot} controlli superati")
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("applica")
    a.add_argument("--file", required=True)
    a.add_argument("--marca", default="")
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--backup", default=None)
    sub.add_parser("selftest")
    x = ap.parse_args(argv)
    if x.cmd == "applica":
        return applica(x.file, x.marca, x.dry_run, x.backup)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
