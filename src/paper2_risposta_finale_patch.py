#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_risposta_finale_patch.py - le tre cose che restano prima di spedire.

  1. Risposta 8 punto 3 e' SCADUTO: dice che il surrogato affine «non esiste» e
     che il test di completezza «e' saltato». Esiste, il test e' stato fatto, e
     la risposta 5 dello STESSO documento lo racconta. Due sezioni che si
     contraddicono sono peggio di una sbagliata.
  2. L'ATTESA D'ORDINE DI GRANDEZZA non c'e'. E' il punto 8 della lista «Cosa
     manca» del referee, ed e' l'unico degli otto senza una sezione.
  3. La risposta 3 scrive «entrambi i contrasti escludono zero» senza dire con
     QUALE denominatore - e la risposta 1, nello stesso documento, stabilisce
     che nessun sigma si scriva senza dirlo.

CONVENZIONE DI SEGNO
--------------------
La sezione nuova usa D = mock - dati, la stessa della risposta 3 e coerente col
deficit positivo. Il documento paper2_attesa_ordine_grandezza.md usa la
convenzione opposta: va allineato a QUESTA, non il contrario - una convenzione
contro quattro sezioni.

Le tre modifiche si muovono INSIEME: senza la 1 il documento si contraddice,
senza la 3 la sezione nuova userebbe un denominatore che il resto non usa.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"

ANCORA_SEZIONI = "---\n\n## Sezioni ancora aperte\n"

PUNTO3_VECCHIO = (
    "3. **Il terzo canale, gli angoli.** Il test di completezza \u00e8 saltato: un angolo \u00e8 una **traiettoria**\n"
    "   in *F*(*z*), non un valore, e il surrogato affine come punto di griglia non esiste.")

PUNTO3_NUOVO = (
    "3. **Il terzo canale, gli angoli.** Fatto, e con un esito che non ci aspettavamo. Il surrogato\n"
    "   affine **esiste** ora come punto di griglia, e la differenza *D*(*C*) \u2212 *D*(*C*_aff) \u00e8 stata\n"
    "   misurata sui quattro angoli. La firma dichiarata prima dei run \u2014 sopra soglia dove il canale\n"
    "   non modellato \u00e8 grande, sotto dove \u00e8 piccolo \u2014 \u00e8 **falsificata nel verso opposto**. Resta\n"
    "   quindi aperto **il meccanismo**: sappiamo che il residuo minimax non predice dove la\n"
    "   differenza \u00e8 grande, non sappiamo che cosa lo faccia. Vedi risposta 5.")

R3_VECCHIO = (
    "La risposta ha **entrambe** le componenti, e al nord domina quella pari. Il verdetto era emettibile,\n"
    "ma non \u00e8 quello che lui si aspetta. \u00c8 la stessa cosa che dice la non-monotonia del \u00a73.6.")

R3_NUOVO = (
    "**Con quale denominatore \u00abescludono zero\u00bb.** Con la **SEM della media** dei mock, che risponde a\n"
    "\u00abla media dell'ensemble risponde come il campo osservato?\u00bb: 4.6\u201316.4\u03c3, no. Con la **dispersione\n"
    "mock-a-mock**, che risponde a \u00abil campo osservato \u00e8 un'estrazione strana?\u00bb: **0.33\u20131.16\u03c3**, no\n"
    "\u2014 il suo contrasto \u00e8 del tutto ordinario per una singola realizzazione. Le due letture non si\n"
    "contraddicono e vanno scritte insieme, come la risposta 1 impone: la discrepanza \u00e8 **di livello\n"
    "medio**, fra la media dei 200 mock e il campo osservato, non fra il campo osservato e la\n"
    "popolazione da cui potrebbe provenire.\n"
    "\n"
    "La risposta ha **entrambe** le componenti, e al nord domina quella pari. Il verdetto era emettibile,\n"
    "ma non \u00e8 quello che lui si aspetta. \u00c8 la stessa cosa che dice la non-monotonia del \u00a73.6.")

SEZIONE = "---\n\n## Attesa a priori — l'ordine di grandezza **[SCRITTA]** — *e due predizioni smentite*\n\n> *«Un lettore si chiederà perché servano dodici punti e 2.400 run per stabilire che uno shear del 3%\n> non toglie il 20% degli anelli. Datele una stima a priori. Se l'attesa e la misura coincidono, la\n> misura acquista credibilità; se non coincidono, avete un risultato.»*\n\n**Non coincidono.** La stima si costruisce da tre numeri già misurati altrove, e ogni passo è citato\ncon la sua provenienza.\n\n### I due canali, e perché in *D* dovrebbero quasi cancellarsi\n\n**Isotropo: zero per costruzione.** Sulla linea B α_iso = 1, il volume è conservato, e l'elasticità\n**1.08 ± 0.02** del cancello 2.7 moltiplica una variazione nulla. Fuori dal gauge lo stesso canale\nvarrebbe +391 in NGC e +254 in SGC (§3.4): l'attesa «zero» è un'affermazione **sul gauge**.\n\n**Pari — quadratico nello shear.** Δ*N* ≈ *N* · η · ε², con ε = |*F* − 1|, sommato sui quattro punti:\n**84.1** sul lato mock e **67.3** sul lato dati a *k*=0. **Scala con *N***, quindi in *D* resta\n+16.8.\n\n**Dispari — lo shear accoppiato alla linea di vista.** M26 §7(viii) misura **123 generatori** per\n±20% sulla dispersione satellitare; sotto *F* ≠ 1 l'ampiezza RSD comovente cambia del ±3%, quindi\n123 × 0.0885/0.20 = **54.4** sul contrasto. **Non scala con *N***, ed è la sua debolezza: in *D* si\ncancella quasi del tutto, e resta **+0.6**.\n\nL'attesa per *D* è dunque **piccola**: se i due lati rispondono allo stesso modo, la loro differenza\nnon risponde.\n\n### La prima smentita: il termine pari non c'è\n\n| lato mock | attesa | misurato |\n|---|---:|---:|\n| NGC *k*=0 | 84.1 | **−60.6 ± 34.0** |\n| NGC *k*=1 | 75.8 | **−36.9 ± 34.0** |\n| SGC *k*=0 | 44.8 | **−26.2 ± 30.1** |\n| SGC *k*=1 | 39.6 | **+25.1 ± 27.8** |\n\n*z* dallo zero: 1.8, 1.1, 0.9, 0.9. **Compatibile con zero in tutti e quattro i casi**, contro\nun'attesa di 40–84. L'elasticità al volume è misurata per una **dilatazione** e non trasferisce a\nuno shear a **volume conservato**. La predizione si registra come smentita.\n\n### E in *D* nulla si cancella — con due denominatori\n\n| | in *D* | attesa | SEM della media | sd mock-a-mock |\n|---|---:|---:|---:|---:|\n| dispari NGC *k*=0 | −111.7 | +0.6 | 7.0σ | **0.49σ** |\n| dispari NGC *k*=1 | −83.9 | +0.7 | 5.6σ | **0.40σ** |\n| dispari SGC *k*=0 | −221.8 | +0.3 | 16.4σ | **1.16σ** |\n| dispari SGC *k*=1 | −206.4 | +0.4 | 16.0σ | **1.13σ** |\n| pari NGC *k*=0 | +205.4 | +16.8 | 6.0σ | **0.43σ** |\n| pari NGC *k*=1 | +170.1 | +19.0 | 5.0σ | **0.35σ** |\n| pari SGC *k*=0 | +138.8 | +8.4 | 4.6σ | **0.33σ** |\n| pari SGC *k*=1 | +242.1 | +10.5 | 8.7σ | **0.62σ** |\n\n*(Segni nella convenzione* D *= mock − dati, la stessa della risposta 3 e coerente col deficit\npositivo.)*\n\n**Con la SEM: la media dell'ensemble non risponde come il campo osservato**, a 4.6–16.4σ. È la\nscoperta centrale del Paper 2, ora con un numero a priori contro cui misurarla.\n\n**Con la dispersione mock-a-mock: il campo osservato non è un'estrazione strana**, a 0.33–1.16σ. Il\nsuo contrasto è ordinario per una singola realizzazione dell'ensemble.\n\nLe due letture non si contraddicono. La discrepanza è **di livello medio**: sta fra la media dei 200\nmock e il campo osservato, non fra il campo osservato e la popolazione da cui potrebbe provenire. È\nla distinzione che regge anche il rango 1/2001 del deficit — dove invece il campo osservato **è**\nun'estrazione estrema — e tacerla qui farebbe leggere «anomalo» dove il dato dice «ordinario».\n\n### Dove l'attesa è debole\n\n**Il segno.** Né l'elasticità né lo scaling RSD lo fissano: il confronto è fra moduli.\n\n**La calibrazione del dispari non scala con *N*.** I 123 generatori sono misurati sull'ensemble NGC;\napplicarli a SGC, che ha *N* quasi dimezzato, è una scelta. Se scalasse con *N*, l'attesa SGC\nscenderebbe a ≈ 29 e la discrepanza **crescerebbe** da 3.8× a 7×. La versione riportata è la\nconservativa.\n\n**Il travaso fra i contrasti.** La linea B non è perfettamente simmetrica — |*F*₅−1| supera |*F*₁−1|\ndello 0.9%, confondente strumentale già dichiarato — quindi il quadratico versa 1.4–2.9 generatori\nnel dispari e il lineare 0.88 nel pari. Sotto ogni SEM in gioco, e dichiarato.\n\n### Cosa compra\n\nDodici punti e 2400 run non servono a scoprire che uno shear del 3% non toglie il 20% degli anelli.\nServono a stabilire che il termine **pari** — quello che l'elasticità prevede — **non c'è**, con un\nlimite di ~34 generatori a 1σ; che il **dispari** c'è ed è 3–6 volte l'attesa; e che in *D*\n**nessuno dei due si cancella**, contro un'attesa che dice che dovrebbero. Il terzo punto è la\nscoperta, e ora ha un termine di paragone dichiarato invece di essere un numero senza contesto.\n\n"

EDITS = [
    ("1. Risposta 8 punto 3, scaduto", PUNTO3_VECCHIO, PUNTO3_NUOVO,
     "falsificata nel verso opposto"),
    ("2. la sezione dell'attesa a priori", ANCORA_SEZIONI, SEZIONE + ANCORA_SEZIONI,
     "## Attesa a priori \u2014 l'ordine di grandezza"),
    ("3. risposta 3: con quale denominatore", R3_VECCHIO, R3_NUOVO,
     "Con quale denominatore \u00abescludono zero\u00bb"),
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


def piatto(t):
    """Spazi collassati e prefissi `>` tolti: una frase a cavallo di due righe
    in un blocco citato diventa altrimenti «come > fortuna»."""
    righe = [l.lstrip().lstrip(">").strip() for l in norm(t).split("\n")]
    return " ".join(" ".join(righe).split())


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
        fail("applicazione PARZIALE gia' presente (%s): non proseguo."
             % ", ".join(done))
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
    print("  righe     : %d   sezioni: %d"
          % (len(n.splitlines()), n.count("\n## ")))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    print("")
    print("  stati non SCRITTA nel corpo: %d"
          % sum(n.count(s) for s in ("[BLOCCATA]", "[DA CERCARE]", "[IN ATTESA")))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    if "## Risposta 5 \u2014 Il terzo canale" not in n:
        fail("la risposta 5 non c'e' ancora: lancia prima "
             "paper2_risposta_5_patch.py. Il punto 3 di Risposta 8 rimanda a lei.")
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
    print("  %d -> %d righe, %d -> %d byte, 3 modifiche"
          % (len(n.splitlines()), len(new_n.splitlines()),
             len(txt.encode("utf-8")), len(out.encode("utf-8"))))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".prefin"
    if args.backup and not os.path.exists(bak):
        with open(bak, "wb") as fh:
            fh.write(txt.encode("utf-8"))
        print("  copia    : %s" % bak)
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(out.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  sha256 dopo  : %s" % sha256_file(args.target))
    print("  [OK] scritto")
    return cmd_verify(args)


def cmd_verify(args):
    n = norm(read_target(args.target)[0])
    f = piatto(n)
    ok = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("Risposta 8 punto 3 non dice piu' che il surrogato non esiste",
         "surrogato affine come punto di griglia non esiste" not in f),
        ("e rimanda alla risposta 5", "Vedi risposta 5" in f),
        ("e non rivendica il meccanismo",
         "Resta quindi aperto **il meccanismo**" in f),
        ("la sezione dell'attesa a priori esiste",
         "## Attesa a priori \u2014 l'ordine di grandezza" in n),
        ("e precede «Sezioni ancora aperte»",
         n.index("## Attesa a priori") < n.index("## Sezioni ancora aperte")),
        ("i tre ingredienti sono citati con la provenienza",
         "1.08 \u00b1 0.02" in f and "123 generatori" in f and "cancello 2.7" in f),
        ("la prima smentita e' dichiarata",
         "Compatibile con zero in tutti e quattro i casi" in f
         and "si registra come smentita" in f),
        ("i due denominatori sono nella sezione nuova",
         "sd mock-a-mock" in f and "0.33\u20131.16\u03c3" in f),
        ("e anche nella risposta 3",
         "Con quale denominatore" in f and "4.6\u201316.4\u03c3" in f),
        ("la convenzione di segno e' dichiarata",
         "mock \u2212 dati" in f),
        ("i segni della sezione nuova concordano con la risposta 3",
         "| dispari NGC *k*=1 | \u221283.9 |" in n and "+170.1 contro \u221283.9" in n),
        ("le debolezze sono scritte",
         "non scala con *N*" in f and "crescerebbe" in f and "travaso" in f),
        ("la risposta 5 e le altre sezioni sono intatte",
         "## Risposta 5 \u2014 Il terzo canale" in n
         and "## \u00a74.6 \u2014 Il ripattern del tiling" in n
         and "## \u00a73.9 \u2014 Componente D" in n),
        ("nessuno stato aperto resta nel corpo",
         "[BLOCCATA]**" not in n.replace("Le **[BLOCCATA]**", "")
         and "[DA CERCARE]" not in n),
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

    corpo = ("# Risposta\n\n> Le **[BLOCCATA]** aspettano una decisione.\n\n"
             "## Risposta 8 \u2014 Cosa manca **[SCRITTA]**\n\n"
             "2. **Altro.**\n" + PUNTO3_VECCHIO + "\n"
             "4. **Il tiling.** Fatto.\n\n"
             "## Risposta 3 \u2014 Il modello **[SCRITTA]**\n\n"
             "| | dispari | pari |\n|---|---:|---:|\n"
             "| NGC *k*=1 | \u221283.9 | **+170.1** |\n\n"
             "+170.1 contro \u221283.9 a *k*=1.\n\n" + R3_VECCHIO + "\n\n"
             "## Risposta 5 \u2014 Il terzo canale, misurato **[SCRITTA]**\n\ntesto\n\n"
             "## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**\n\ntesto\n\n"
             "## \u00a73.9 \u2014 Componente D **[SCRITTA]**\n\ntesto\n\n"
             + ANCORA_SEZIONI + "\n| rilievo | stato |\n|---|---|\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "r_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))
            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s le tre ancore sono uniche" % lab,
                len(ok) == 3 and not bad, "ok=%d bad=%s" % (len(ok), bad))
            new_n, _ = apply_all(txt)
            out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
            with open(p, "wb") as fh:
                fh.write(out.encode("utf-8"))

            class A:
                target = p
            chk("3%s verify passa dopo la patch" % lab, cmd_verify(A()) == 0)
            chk("4%s fine riga preservati" % lab,
                (read_target(p)[0].count("\r\n") == 0) if eol == "\n"
                else (read_target(p)[0].count("\n")
                      == read_target(p)[0].count("\r\n")))
            ok2, _, bad2 = plan(read_target(p)[0])
            chk("5%s idempotenza" % lab, not ok2 and not bad2,
                "ok=%s bad=%s" % (ok2, bad2))

        p2 = os.path.join(td, "senza5.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace(
                "## Risposta 5 \u2014 Il terzo canale, misurato **[SCRITTA]**",
                "## Altro **[SCRITTA]**").encode("utf-8"))

        class B:
            target = p2
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("6  senza la risposta 5 la patch rifiuta", _exits(lambda: cmd_patch(B())))

        p3 = os.path.join(td, "parziale.md")
        with open(p3, "wb") as fh:
            fh.write(corpo.replace(PUNTO3_VECCHIO, PUNTO3_NUOVO).encode("utf-8"))
        chk("7  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p3)[0])))

    fs = piatto(SEZIONE)
    chk("8  la sezione dichiara la smentita come smentita",
        "si registra come smentita" in fs and "successo" not in fs.lower())
    chk("8b e riporta ENTRAMBI i denominatori",
        "SEM della media" in fs and "sd mock-a-mock" in fs)
    chk("8c e dichiara la convenzione di segno", "mock \u2212 dati" in fs)
    chk("8d e dice dove l'attesa e' debole",
        "Il segno." in fs and "non scala con *N*" in fs)
    # i segni della sezione nuova devono concordare con la risposta 3
    chk("9  segni concordi con la risposta 3: dispari NEGATIVO, pari POSITIVO",
        "| dispari NGC *k*=1 | \u221283.9 |" in SEZIONE
        and "| pari NGC *k*=1 | +170.1 |" in SEZIONE)

    print("=== SELFTEST paper2_risposta_finale_patch ===")
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
    p = argparse.ArgumentParser(description="Le tre cose che restano prima di spedire")
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
