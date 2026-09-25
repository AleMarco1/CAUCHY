#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_censimento_16.py -- censimento dei registri 1.5 -> 1.6: i registri di figura.

Z-censimento-fig. Il censimento del 25 set esce 1: `fig_F1.jsonl` e' un file nuovo, non classificato,
e il run di F7 ne ha aggiunto un secondo, `fig_F7.jsonl`. Questo patcher li dichiara PER NOME ESATTO,
come i 67 della 1.5: una figura nuova (F2, F3, ...) resta non classificata e fa fallire il censimento
finche' non viene dichiarata anche lei.

Classe e scopo, e perche':
  - classe `log`, come fv.jsonl: uno script di figura appende un record per run con i numeri disegnati,
    gli sha degli ingressi e quello del PDF, e `verify` trova il record che descrive la figura su disco.
    Non e' un run di misura: i numeri vengono da registri gia' censiti.
  - fuori dallo scopo di 6.1: le proprieta' si misurano e si stampano comunque, e l'append storico resta
    protetto dalla baseline per tutti i file.
  - ripresa `na_una_passata` SENZA `record_al_15set`: ogni rilancio della figura appende per disegno
    (fig_F1 ne ha gia' quattro), e un conteggio dichiarato darebbe DA_RIVEDERE a ogni rilancio.

Quattro sostituzioni atomiche sul sorgente, ognuna su un'ancora che compare una volta:
  1. CLASSI_DICHIARATE: due righe in coda;
  2. RIPRESA_DICHIARATA: due voci dopo onepoint_v1_DESI_SGC;
  3. VERSIONE 1.5 -> 1.6;
  4. selftest del censimento: controllo 46 (classe, scopo, ripresa, nessun conteggio, rilancio -> NA,
     una figura nuova resta non classificata).
Prima di scrivere, il sorgente modificato si importa da un temporaneo e il SUO selftest deve passare.

Sottocomandi: selftest | dry-run | apply | verify. Dalla radice del repository.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

J = os.path.join
TOOL = J("src", "paper2_censimento_registri.py")
RECEIPT = J("logs", "patch_censimento_16.json")
SHA_BEFORE = "738c309c3f22344e22cddbad3797c140bffafa627101e2303c0d2af08e1a7681"

OLD_CLASSI = '''    ("tabres_probe.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 14, 51"),
)
'''
NEW_CLASSI = '''    ("tabres_probe.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 14, 51"),
    # --- registri di figura, Fase 7 (1.6, 25 set 2026, Z-censimento-fig) -----
    # Nome ESATTO, come i 67: una figura nuova resta non classificata finche' non
    # e' dichiarata. Uno script di figura appende un record per run (numeri
    # disegnati, sha degli ingressi e del PDF); non e' un run di misura.
    ("fig_F1.jsonl", "log", False,
     "registro di figura F1, src/paper2_fig_F1.py; non in scopo 6.1: un record per run, "
     "i numeri vengono da registri gia' censiti, verify cerca il record per sha del PDF"),
    ("fig_F7.jsonl", "log", False,
     "registro di figura F7, src/paper2_fig_F7.py; non in scopo 6.1: un record per run, "
     "i numeri vengono da registri gia' censiti, verify cerca il record per sha del PDF"),
)
'''

OLD_RIPRESA = '''    "onepoint_v1_DESI_SGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_passata_1punto.py (sub desi)",
                                   "record_al_15set": 1, "motivo": "la riga DESI, un record."},
'''
NEW_RIPRESA = '''    "onepoint_v1_DESI_SGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_passata_1punto.py (sub desi)",
                                   "record_al_15set": 1, "motivo": "la riga DESI, un record."},
    # registri di figura (1.6): nessun `record_al_15set`, perche' ogni rilancio
    # appende per disegno e un conteggio dichiarato darebbe DA_RIVEDERE a ogni run.
    "fig_F1.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_fig_F1.py (cmd_run)",
                     "motivo": "una corsa per figura, un record per corsa; si rilancia, non si riprende."},
    "fig_F7.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_fig_F7.py (cmd_run)",
                     "motivo": "una corsa per figura, un record per corsa; si rilancia, non si riprende."},
'''

OLD_VERSIONE = 'VERSIONE = "1.5"\n'
NEW_VERSIONE = 'VERSIONE = "1.6"\n'

OLD_SELFTEST = '''    totale = c.ok + len(c.ko)
    print("selftest: %d/%d" % (c.ok, totale))
'''
NEW_SELFTEST = '''    # ---- 46. registri di figura (1.6, 25 set): nome esatto, log, fuori scopo --
    for nome in ("fig_F1.jsonl", "fig_F7.jsonl"):
        cl, scopo, _ = classe_dichiarata(nome)
        c.uguale("%s: classe log" % nome, cl, "log")
        c.uguale("%s: fuori scopo" % nome, scopo, False)
        d = _dichiarazione_ripresa(nome)
        c.uguale("%s: ripresa" % nome, d["modo"], "na_una_passata")
        c.verifica("%s: nessun conteggio dichiarato" % nome, "record_al_15set" not in d)
        e = valuta_ripresa(nome, [{"schema": "x"} for _ in range(7)])
        c.uguale("%s: un rilancio non rende vecchia la dichiarazione" % nome, e["esito"], "NA")
    c.uguale("una figura nuova resta non classificata", classe_dichiarata("fig_F2.jsonl")[0], None)
    c.uguale("una figura nuova non ha ripresa dichiarata", _dichiarazione_ripresa("fig_F2.jsonl"), None)

    totale = c.ok + len(c.ko)
    print("selftest: %d/%d" % (c.ok, totale))
'''

EDITS = [("CLASSI_DICHIARATE", OLD_CLASSI, NEW_CLASSI),
         ("RIPRESA_DICHIARATA", OLD_RIPRESA, NEW_RIPRESA),
         ("VERSIONE", OLD_VERSIONE, NEW_VERSIONE),
         ("selftest del censimento", OLD_SELFTEST, NEW_SELFTEST)]


class PatchError(Exception):
    pass


def patch_text(text):
    if "\r\n" in text:
        raise PatchError("il sorgente ha CRLF: atteso LF (regola *.py text eol=lf, record 69)")
    out = text
    for nome, old, new in EDITS:
        c = out.count(old)
        if c != 1:
            raise PatchError("ancora '%s': %d occorrenze invece di 1" % (nome, c))
        out = out.replace(old, new)
    return out


def run_tool_selftest(source_text):
    """Importa il sorgente modificato da un temporaneo e ne esegue il selftest. (esito, riga finale)"""
    d = tempfile.mkdtemp(prefix="censimento16_")
    p = J(d, "censimento_16_prova.py")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(source_text)
    spec = importlib.util.spec_from_file_location("censimento_16_prova", p)
    mod = importlib.util.module_from_spec(spec)
    buf = io.StringIO()
    with redirect_stdout(buf):
        spec.loader.exec_module(mod)
        rc = mod.comando_selftest(None)
    righe = [l for l in buf.getvalue().splitlines() if l.strip()]
    finale = next((l for l in reversed(righe) if l.startswith("selftest:")), "(nessuna riga di esito)")
    falliti = [l for l in righe if l.startswith("  ")][-10:] if rc else []
    return rc == 0, finale, falliti, mod


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def prepare():
    if not os.path.isdir("src"):
        raise PatchError("lanciare dalla radice del repository")
    raw = open(TOOL, "rb").read()
    sha = sha_bytes(raw)
    if os.path.exists(RECEIPT):
        rc = json.load(open(RECEIPT, encoding="utf-8"))
        if sha == rc.get("sha_after"):
            raise PatchError("gia' applicata: lo strumento ha lo sha registrato dopo la patch (%s)" % sha[:12])
    if sha != SHA_BEFORE:
        raise PatchError("sha dello strumento %s..., atteso %s... (versione 1.5 del 22 set)" % (sha[:12], SHA_BEFORE[:12]))
    new = patch_text(raw.decode("utf-8"))
    ok, finale, falliti, mod = run_tool_selftest(new)
    if not ok:
        raise PatchError("il selftest dello strumento modificato non passa: %s %s" % (finale, falliti))
    if mod.VERSIONE != "1.6":
        raise PatchError("versione dopo la patch: %r" % mod.VERSIONE)
    return raw, new.encode("utf-8"), finale


def report(raw, new_raw, finale):
    print("strumento: %s  %d -> %d byte" % (TOOL, len(raw), len(new_raw)))
    print("sha: %s... -> %s..." % (sha_bytes(raw)[:12], sha_bytes(new_raw)[:12]))
    print("ancore: 4/4 sostituite; versione 1.5 -> 1.6")
    print("selftest dello strumento modificato, da temporaneo: %s" % finale)


def cmd_dry():
    raw, new_raw, finale = prepare()
    report(raw, new_raw, finale)
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    raw, new_raw, finale = prepare()
    tmp = TOOL + ".tmp_patch_16"
    with open(tmp, "wb") as fh:
        fh.write(new_raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, TOOL)
    if sha_bytes(open(TOOL, "rb").read()) != sha_bytes(new_raw):
        raise PatchError("dopo la scrittura lo sha non coincide")
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_censimento_16_v1", "utc": datetime.now(timezone.utc).isoformat(),
          "tool": TOOL, "sha_before": sha_bytes(raw), "sha_after": sha_bytes(new_raw),
          "bytes_before": len(raw), "bytes_after": len(new_raw), "tool_selftest": finale,
          "declared": ["fig_F1.jsonl", "fig_F7.jsonl"],
          "script_sha": sha_bytes(open(os.path.abspath(__file__), "rb").read())}
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    report(raw, new_raw, finale)
    print("ricevuta: %s" % RECEIPT)
    print("ESITO: APPLICATA")


def cmd_verify():
    if not os.path.exists(RECEIPT):
        raise PatchError("ricevuta assente: la patch non e' stata applicata")
    rc = json.load(open(RECEIPT, encoding="utf-8"))
    raw = open(TOOL, "rb").read()
    same = sha_bytes(raw) == rc["sha_after"]
    ok, finale, falliti, _ = run_tool_selftest(raw.decode("utf-8"))
    print("strumento: %s...  %s" % (sha_bytes(raw)[:12], "= sha dopo la patch" if same else "DIVERSO"))
    print("selftest dello strumento: %s" % finale)
    esito = same and ok
    print("ESITO: %s" % ("PASS" if esito else "FAIL"))
    return 0 if esito else 1


# ----------------------------------------------------------------------------- selftest

def _fixture(eol="\n"):
    t = ('VERSIONE = "1.5"\n' + "CLASSI_DICHIARATE = (\n" + OLD_CLASSI + "\nRIPRESA_DICHIARATA = {\n" +
         OLD_RIPRESA + "}\n\ndef comando_selftest(args):\n" + OLD_SELFTEST)
    return t.replace("\n", eol)


def _t_quattro():
    new = patch_text(_fixture())
    ok = all(n in new for _, _, n in EDITS) and 'VERSIONE = "1.6"' in new
    try:
        patch_text(new)
    except PatchError:
        return ok
    return False


def _t_crlf():
    try:
        patch_text(_fixture("\r\n"))
    except PatchError:
        return True
    return False


def _t_doppia():
    try:
        patch_text(_fixture() + OLD_VERSIONE)
    except PatchError:
        return True
    return False


def _t_sessantasette():
    # le righe nuove non devono entrare nel conteggio dei 67 (selftest 45 dello strumento)
    return "fuori scopo 6.1;" not in NEW_CLASSI.replace(OLD_CLASSI.rstrip(")\n"), "")


def _t_python():
    import ast
    src = ("CLASSI_DICHIARATE = (\n" + NEW_CLASSI + "\nRIPRESA_DICHIARATA = {\n" + NEW_RIPRESA + "}\n")
    ns = {}
    exec(compile(ast.parse(src), "<fixture>", "exec"), ns)
    cl = {g: (c, s) for g, c, s, _ in ns["CLASSI_DICHIARATE"]}
    rp = ns["RIPRESA_DICHIARATA"]
    return (cl.get("fig_F1.jsonl") == ("log", False) and cl.get("fig_F7.jsonl") == ("log", False)
            and all(rp[n]["modo"] == "na_una_passata" and "record_al_15set" not in rp[n]
                    for n in ("fig_F1.jsonl", "fig_F7.jsonl")))


TESTS = [
    ("quattro sostituzioni; seconda applicazione -> errore", _t_quattro),
    ("sorgente CRLF -> errore (atteso LF)", _t_crlf),
    ("ancora doppia -> errore", _t_doppia),
    ("le righe nuove non entrano fra i 67", _t_sessantasette),
    ("le dichiarazioni nuove sono Python valido: log, fuori scopo, na_una_passata senza conteggio", _t_python),
]


def selftest():
    ok = 0
    for nome, fn in TESTS:
        try:
            esito = bool(fn())
        except Exception as e:
            esito = False
            nome += " [%s: %s]" % (type(e).__name__, e)
        ok += esito
        if not esito:
            print("  FAIL  " + nome)
    print("selftest: %d/%d %s" % (ok, len(TESTS), "PASS" if ok == len(TESTS) else "FAIL"))
    return ok == len(TESTS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("comando", choices=["selftest", "dry-run", "apply", "verify"])
    a = ap.parse_args()
    try:
        if a.comando == "selftest":
            return 0 if selftest() else 1
        if not selftest():
            raise PatchError("selftest non superato")
        if a.comando == "dry-run":
            cmd_dry()
            return 0
        if a.comando == "apply":
            cmd_apply()
            return 0
        return cmd_verify()
    except PatchError as e:
        print("ERRORE: %s" % e)
        print("ESITO: FALLITO")
        return 2


if __name__ == "__main__":
    sys.exit(main())
