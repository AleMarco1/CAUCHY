#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_318.py - porta checklist_paper2.md alla rev. 3.18.

Quattro modifiche, atomiche:
  1. l'intestazione, da rev. 3.17 a rev. 3.18;
  2. il blocco di changelog nuovo, PRIMA della Fase 0 come gli altri quindici:
     il changelog e' storico e append-only, non si riscrive;
  3. la voce 3.2b nella Fase 1, dove il numero del pilot e' descritto male in
     tre modi;
  4. la voce 3.2b nella Fase 3, che va LIMITATA: resta vera per cio' che
     afferma, ma non e' la chiusura del §4.6.

Le due voci si muovono INSIEME al changelog: una checklist che nel changelog
dice «tre correzioni alla 3.2b» e nelle voci non le ha e' peggio di una che non
le ha affatto.

MARCATORE: quello della rev. 3.18, verificato assente prima di scrivere. Ogni
marcatore a quattro simboli contiene sottostringhe di marcatori a tre gia' in
uso: e' una proprieta' del sistema, non di questa revisione.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "checklist_paper2.md"
MARCATORE = "\u2726\u2726\u2726\u2727"

INTESTAZIONE_VECCHIA = ("### rev. 3.17 \u2014 4 settembre 2026 \u2014 record 32-38; "
                        "TRE meccanismi esclusi e il fattore 2-6 sopravvive; D5c chiuso")
INTESTAZIONE_NUOVA = ("### rev. 3.18 \u2014 5 settembre 2026 \u2014 record 39-46; \u00a73.9, "
                      "\u00a74.6 e risposta 5 chiuse; DUE predizioni dichiarate smentite")

ANCORA_FASE0 = "---\n\n## Fase 0 \u2014 Prerequisiti e ri-perimetrazione dello scopo\n"

PILOT_VECCHIO = (
    "      **\u2727\u2727 Il 3.2b \u00e8 gi\u00e0 fatto:** `tiling.replica_randomised` su 100 mock d\u00e0 spostamento della media\n"
    "      **\u221213 generatori** (0.037% contro un deficit di 7181) e rapporto di dispersione 0.97. Il tiling\n"
    "      non \u00e8 l'anomalia.")

PILOT_NUOVO = (
    "      **\u2727\u2727 Il 3.2b \u00e8 gi\u00e0 fatto**, ma la descrizione era sbagliata in tre modi, corretti nella\n"
    "      rev. 3.18 (**\u2726\u2726\u2726\u2727**). Lo script **non \u00e8** `tiling.replica_randomised`, che non esiste: \u00e8\n"
    "      `src/rev1_r11_pilot.py`, con uscita in `results/revision/rev1_r11_pilot.json`, e mappa ogni\n"
    "      replica attraverso una **permutazione segnata degli assi** \u2014 simmetria esatta del box\n"
    "      periodico \u2014 con un cancello nullo bit-esatto. Su 100 mock lo spostamento della media \u00e8\n"
    "      **\u221212.8 \u00b1 20.1** generatori, cio\u00e8 **compatibile con zero**: \u00e8 un **limite superiore**, non uno\n"
    "      spostamento misurato. E lo **0.037% \u00e8 rispetto alla media dell'ensemble**, non al deficit;\n"
    "      rispetto al deficit vale **0.178%**. Il rapporto di dispersione \u00e8 0.97 con IC95\n"
    "      [0.849, 1.118] \u2014 ed \u00e8 quel limite superiore che M26 \u00a77(vii) riporta come «sotto il 12%».\n"
    "      **Il tiling non \u00e8 l'anomalia**, e questo non cambia.")

DECADUTO_VECCHIO = (
    "      su 100 mock) copre l'intera griglia **per costruzione**. Non risolto: **dissolto dal gauge**,\n"
    "      come il criterio del limite pratico.")

DECADUTO_NUOVO = (
    "      su 100 mock) copre l'intera griglia **per costruzione**. Non risolto: **dissolto dal gauge**,\n"
    "      come il criterio del limite pratico.\n"
    "\n"
    "      **\u2726\u2726\u2726\u2727 LIMITATO, non ritirato (rev. 3.18).** Il referee ha ragione al \u00a74.6: questo\n"
    "      argomento vincola le **statistiche di molteplicit\u00e0**, non il **ripattern**. Sotto deformazione\n"
    "      cambia *quali* celle del box finiscono dove, a molteplicit\u00e0 invariata, e il **58.757%** dei\n"
    "      voxel in-survey sta su celle riusate \u2014 il nostro numero, da `rev1_r11_tiling.json`. Le celle\n"
    "      riusate sono riusate **poco**, media 1.437, ma sono **tante**: una molteplicit\u00e0 quasi\n"
    "      invariata \u00e8 compatibile con una riassegnazione estesa. La voce resta vera per ci\u00f2 che\n"
    "      afferma e **cessa di essere la chiusura del \u00a74.6**, che ora \u00e8 chiuso da una misura:\n"
    "      item 3.2d, emendamento 44, \u0394_ripattern sotto la soglia di 53 a tutti e quattro i livelli.")

CHANGELOG = "> **Cosa cambia nella rev. 3.18.** Voci marcate **✦✦✦✧**. Giornata del 5 settembre: otto record,\n> tre sezioni del referee chiuse, e **due predizioni dichiarate smentite** — che è il modo in cui\n> questo programma vorrebbe fallire.\n>\n> 1. **Registro a quarantasei record.** 39 il termine (c) indipendente dal punto; 40 il pavimento a\n>    sei punti; 41 il budget ai quattro livelli; 42 la vitalità posizionale nel registro compD; 43 la\n>    Componente D tracciata; 44 il ripattern del tiling sotto soglia; 45 la sua scala geometrica e il\n>    limite di quella scala; 46 il terzo canale misurato. `DOCUMENTED_AMENDMENTS = 46`.\n> 2. **✦✦✦✧ Il §3.9 è chiuso e la Componente D resta nel paper.** L'input non era tracciato: il\n>    manifest hash i 2000 campi e del file dei parametri porta **solo un percorso**, per giunta un\n>    percorso che **non risolve**. Tre cancelli in ordine obbligato — digest, etichette, riproduzione\n>    — e le quattordici correlazioni parziali si riproducono **a precisione piena** a nove giorni di\n>    distanza. Il tracciamento è **a posteriori per riproduzione**, non congelamento contemporaneo, e\n>    la differenza va scritta invece che lasciata implicita.\n> 3. **✦✦✦✧ Il §4.6 è chiuso da una MISURA, e il rilievo del referee era fondato.** La voce 3.2b\n>    non chiudeva la domanda: il gauge fissa il **numero** di repliche, non la **mappa di\n>    assegnazione**, e il 59% dei voxel in-survey sta su celle riusate. Con la randomizzazione delle\n>    repliche dentro `carve_cutsky`, 200 realizzazioni per emisfero a B1 e B5:\n>    Δ_ripattern = +6.96 ± 16.40, −9.38 ± 15.72, −33.84 ± 13.50, −28.63 ± 12.92, tutti sotto la\n>    soglia di 53 dichiarata prima. Il termine (d) resta zero **per misura**.\n> 4. **E due cose del §4.6 non sono andate come previste.** L'**appaiamento fra i bracci è fallito**\n>    — correlazione zero, SEM 13–16 invece dei 2–4 attesi — perché randomizzare le repliche produce\n>    di fatto una realizzazione indipendente. E la **soglia è stata fortunata**: 53 era la più stretta\n>    fra due candidate, ma il 3σ naturale è 39–49, quindi 53 è leggermente più larga. Registrato come\n>    fortuna.\n> 5. **✦✦✦✧ SMENTITA, la prima: il termine PARI dell'attesa a priori.** L'elasticità al volume\n>    prevede un contrasto pari di 84.1, 75.8, 44.8 e 39.6 generatori sul lato mock; la misura dà\n>    −60.6 ± 34.0, −36.9 ± 34.0, −26.2 ± 30.1 e +25.1 ± 27.8 — **compatibile con zero in tutti e\n>    quattro i casi**. L'elasticità, misurata per una **dilatazione**, non trasferisce a uno shear a\n>    **volume conservato**.\n> 6. **✦✦✦✧ SMENTITA, la seconda: la firma del terzo canale.** L'item 3.2e dichiarava, prima dei\n>    run, che |*D*(*C*) − *D*(*C*_aff)| dovesse stare **sopra** soglia a C1 e C4 e **sotto** a C2 e C3.\n>    L'ordinamento è **rovesciato**: C4, secondo canale più grande, sta sotto in tutti e quattro i\n>    casi (22, 5, 4, 13); C2 e C3, i due più piccoli, stanno sopra in tre su quattro. Riprodotto in\n>    due emisferi indipendenti. Il fitter **riproduce** 0.082 e 0.047 a quattro cifre: quei numeri\n>    sono giusti, semplicemente **non predicono**.\n> 7. **Il contrasto in *D* non si cancella, e ora ha un'attesa contro cui misurarlo.** L'attesa dice\n>    −0.6 sul dispari e −16.8 sul pari; la misura dà +84 … +222 e −139 … −242. Con **due\n>    denominatori**, come la risposta 1 impone: 4.6–16.4σ contro la SEM della media, ma\n>    **0.33–1.16σ** contro la dispersione mock-a-mock. La discrepanza è di livello **medio**, non\n>    fra il campo osservato e la popolazione da cui potrebbe provenire.\n> 8. **Il termine (e) ha quasi prodotto un verdetto sbagliato.** Il primo confronto della risposta 5\n>    metteva un |Δ*N*| **grezzo** contro un pavimento costruito su residui **già corretti** per (e).\n>    Le maschere differiscono fino a **1686 voxel**, 170 generatori, e il verdetto cambiava segno.\n>    Correggere con la pendenza media non bastava (elasticità locale 1.71 contro globale 1.08): il\n>    rimedio è stata la **maschera fissa**, che toglie il termine invece di sottrarlo.\n> 9. **Tre correzioni alla voce 3.2b**, tutte di descrizione e nessuna di sostanza: `tiling.replica_randomised`\n>    **non esiste** — lo script è `rev1_r11_pilot.py` con uscita in `results/revision/rev1_r11_pilot.json`;\n>    lo 0.037% è rispetto alla **media dell'ensemble** e non al deficit, che dà 0.178%; e i −13\n>    generatori vanno scritti **−12.8 ± 20.1**, cioè compatibili con zero. È un **limite superiore**,\n>    non uno spostamento misurato.\n> 10. **Due derive documentali sul terzo canale.** `paper2_item13.md` dà **0.008** per C2/C3 dove\n>     l'item 1.4 e la pre-registrazione danno **0.006 e 0.005** — gauge vecchio contro nuovo, non\n>     segnalato come tale; e `paper2_item12a_emenda_gauge.md:158` elenca quattro percentuali senza\n>     dire a quale angolo appartengano.\n> 11. **Il registro degli emendamenti ha sei righe con fine riga anomalo** — 8, 9, 10, 11, 13 e 14,\n>     terminate da LF dove le altre trentasette hanno CRLF. Le prime quattro condividono anche lo\n>     stesso `utc` segnaposto `2026-08-27T00:00:00Z`. Oggi è inerte: il registro sta in `src/`, nessun\n>     tier lo hasha byte per byte, e `.gitattributes` copre `results/**`. Diventa una mina se un\n>     domani si aggiunge un digest del registro. **Da registrare prima di allora.**\n> 12. **Resta la riga cosmetica del budget** — `[rms coppia depositata nan contro None]` a *k*=2,3,\n>     che dovrebbe dire «cancello non applicabile» — e la decisione di scrittura su **B1 anomalo**,\n>     +153.2 ± 11.7 contro il fiduciale a *k*=0 in NGC mentre gli altri quattro punti stanno entro\n>     ±40, con Δ*D*_max definito come B5 − B1 e quindi dominato dal punto più fuori linea.\n\n---\n\n"

EDITS = [
    ("1. intestazione rev. 3.18", INTESTAZIONE_VECCHIA, INTESTAZIONE_NUOVA,
     "### rev. 3.18 \u2014 5 settembre 2026"),
    ("2. blocco di changelog", ANCORA_FASE0, CHANGELOG + ANCORA_FASE0,
     "**Cosa cambia nella rev. 3.18.**"),
    ("3. voce 3.2b, Fase 1: il numero del pilot", PILOT_VECCHIO, PILOT_NUOVO,
     "\u221212.8 \u00b1 20.1"),
    ("4. voce 3.2b, Fase 3: limitata dal \u00a74.6", DECADUTO_VECCHIO, DECADUTO_NUOVO,
     "LIMITATO, non ritirato (rev. 3.18)"),
]

def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_target(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    txt = raw.decode("utf-8")
    n_crlf = txt.count("\r\n")
    n_lf = txt.count("\n") - n_crlf
    return txt, ("\r\n" if n_crlf >= n_lf else "\n"), n_crlf, n_lf


def norm(t):
    return t.replace("\r\n", "\n")


def plan(txt):
    n = norm(txt)
    ok, done, bad = [], [], []
    for name, old, new, marker in EDITS:
        if marker in n:
            done.append(name)
        elif n.count(old) == 1:
            ok.append(name)
        else:
            bad.append("%s: %d occorrenze dell'ancora" % (name, n.count(old)))
    return ok, done, bad


def apply_all(txt):
    ok, done, bad = plan(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    if len(ok) != len(EDITS):
        fail("applicazione PARZIALE gia' presente (%s). Changelog e voci si "
             "muovono insieme: non proseguo." % ", ".join(done))
    n = norm(txt)
    for name, old, new, marker in EDITS:
        n = n.replace(old, new, 1)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  righe     : %d" % len(n.splitlines()))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    print("  marcatore della 3.18 gia' usato: %s" % (MARCATORE in n))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    if MARCATORE in n and "rev. 3.18" not in n:
        fail("il marcatore della 3.18 e' gia' usato altrove: sceglierne un "
             "altro, altrimenti le voci nuove si confondono con quelle.")
    if n_crlf and n_lf and not args.allow_eol_normalise:
        fail("fine riga MISTI (CRLF=%d, LF=%d): --allow-eol-normalise."
             % (n_crlf, n_lf))
    new_n, done = apply_all(txt)
    print("=== PATCH %s ===" % args.target)
    print("  sha256 prima : %s" % sha256_file(args.target))
    if new_n is None:
        print("  [OK] niente da fare (%s)." % ", ".join(done))
        return 0
    out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
    print("  %d -> %d righe, %d -> %d byte, 4 modifiche"
          % (len(n.splitlines()), len(new_n.splitlines()),
             len(txt.encode("utf-8")), len(out.encode("utf-8"))))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".rev317"
    if args.backup and not os.path.exists(bak):
        with open(bak, "wb") as fh:
            fh.write(txt.encode("utf-8"))
        print("  copia rev. 3.17 : %s" % bak)
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(out.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  sha256 dopo  : %s" % sha256_file(args.target))
    print("  [OK] scritto")
    return cmd_verify(args)


def piatto(t):
    """Spazi collassati E prefissi di citazione rimossi. Collassare e basta non
    basta: in un blocco `>` una frase a cavallo di due righe diventa
    «come > fortuna». Stessa classe del fine riga, con un carattere in piu'."""
    righe = [l.lstrip().lstrip(">").strip() for l in norm(t).split("\n")]
    return " ".join(" ".join(righe).split())


def cmd_verify(args):
    n = norm(read_target(args.target)[0])
    f = piatto(n)
    ok = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("l'intestazione dice rev. 3.18", "### rev. 3.18" in n),
        ("il changelog della 3.18 c'e'", "Cosa cambia nella rev. 3.18." in n),
        ("e precede la Fase 0",
         n.index("rev. 3.18.") < n.index("## Fase 0 \u2014")),
        ("i changelog precedenti sono intatti",
         all(("rev. 3.%d." % i) in n for i in range(11, 18))),
        ("il registro e' dichiarato a 46 record",
         "DOCUMENTED_AMENDMENTS = 46" in f),
        ("le DUE smentite sono nominate",
         "SMENTITA, la prima" in f and "SMENTITA, la seconda" in f),
        ("l'appaiamento fallito e la soglia fortunata ci sono",
         "appaiamento fra i bracci \u00e8 fallito" in f and "come fortuna" in f),
        ("i due denominatori della risposta 1 ci sono",
         "0.33\u20131.16" in f and "4.6\u201316.4" in f),
        ("le tre correzioni a 3.2b sono nel changelog",
         "non esiste" in f and "0.178%" in f and "\u221212.8 \u00b1 20.1" in f),
        ("e sono anche NELLA VOCE 3.2b della Fase 1",
         "rev1_r11_pilot.py" in n and "limite superiore" in f),
        ("la voce 3.2b della Fase 3 e' LIMITATA, non ritirata",
         "LIMITATO, non ritirato" in n and "cessa di essere la chiusura" in f),
        ("il 58.757% e' riconosciuto come nostro numero", "58.757%" in n),
        ("le derive documentali e i fine riga sono registrati",
         "0.008" in n and "fine riga anomalo" in f),
        ("le due cose ancora aperte sono nominate",
         "riga cosmetica del budget" in f and "B1 anomalo" in f),
        ("il marcatore della 3.18 e' nel changelog e nelle voci",
         n.count(MARCATORE) >= 5),
    ]
    for name, cond in checks:
        print("  [%s] %s" % ("ok" if cond else "NO", name))
        ok &= bool(cond)
    print("  esito: %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    corpo = ("# Paper 2 \u2014 Checklist\n"
             + INTESTAZIONE_VECCHIA + "\n\n"
             + "".join("> **Cosa cambia nella rev. 3.%d.** testo\n" % i
                       for i in range(11, 18))
             + "\n" + ANCORA_FASE0 + "\ntesto della fase 0\n\n"
             + PILOT_VECCHIO + "\n\ntesto\n\n"
             + DECADUTO_VECCHIO + "\n\nfine\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "c_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))
            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s le quattro ancore sono uniche" % lab,
                len(ok) == 4 and not bad, "ok=%d bad=%s" % (len(ok), bad))
            new_n, _ = apply_all(txt)
            out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
            with open(p, "wb") as fh:
                fh.write(out.encode("utf-8"))

            class A:
                target = p
            chk("3%s verify passa dopo la patch" % lab, cmd_verify(A()) == 0)
            n2 = norm(read_target(p)[0])
            chk("4%s il changelog sta fra il 3.17 e la Fase 0" % lab,
                n2.index("rev. 3.17.") < n2.index("rev. 3.18.")
                < n2.index("## Fase 0 \u2014"))
            chk("5%s fine riga preservati" % lab,
                (read_target(p)[0].count("\r\n") == 0) if eol == "\n"
                else (read_target(p)[0].count("\n")
                      == read_target(p)[0].count("\r\n")))
            ok2, _, bad2 = plan(read_target(p)[0])
            chk("6%s idempotenza" % lab, not ok2 and not bad2,
                "ok=%s bad=%s" % (ok2, bad2))

        p2 = os.path.join(td, "parziale.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace(PILOT_VECCHIO, PILOT_NUOVO).encode("utf-8"))
        chk("7  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p2)[0])))

        p3 = os.path.join(td, "marcatore.md")
        with open(p3, "wb") as fh:
            fh.write((corpo + "\nuna voce marcata " + MARCATORE
                      + " altrove\n").encode("utf-8"))

        class B:
            target = p3
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("8  marcatore gia' usato altrove: la patch rifiuta",
            _exits(lambda: cmd_patch(B())))

    fc = " ".join(CHANGELOG.split())
    chk("9  il changelog dichiara le due smentite come smentite",
        "SMENTITA, la prima" in fc and "SMENTITA, la seconda" in fc)
    chk("9b e non le reinterpreta in successi", "successo" not in fc.lower())
    chk("9c nomina cio' che resta aperto",
        "riga cosmetica del budget" in fc and "B1 anomalo" in fc
        and "fine riga anomalo" in fc)
    chk("9d le tre correzioni a 3.2b sono dette di DESCRIZIONE",
        "di descrizione e nessuna di sostanza" in fc)

    print("=== SELFTEST paper2_checklist_318 ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _exits(fn):
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(description="Porta la checklist alla rev. 3.18")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", default=DEFAULT_TARGET)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect", parents=[common]).set_defaults(func=cmd_inspect)
    sub.add_parser("verify", parents=[common]).set_defaults(func=cmd_verify)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)
    pa = sub.add_parser("patch", parents=[common])
    pa.add_argument("--apply", action="store_true")
    pa.add_argument("--backup", action="store_true", default=True)
    pa.add_argument("--allow-eol-normalise", action="store_true")
    pa.set_defaults(func=cmd_patch)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
