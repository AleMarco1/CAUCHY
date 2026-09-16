# -*- coding: utf-8 -*-
"""
paper2_estrai.py -- due estrazioni in SOLA LETTURA, a grana di RECORD e non di file.
Servono a chiudere la practice 6 (voce 5.4) e il conto delle predizioni (voce 5.5).

  clipped     legge i JSONL dei run di Fase 3 e tira fuori ogni conteggio di posizioni fuori
              dal cubo che vi sia stato scritto (d5c_n_clipped, n_clipped, clipped_rand,
              n_clip, n_clip_inmask), raggruppato per punto della griglia e per regione.
              Dice se il FIDUCIALE ha il suo numero, che e' cio' che manca alla practice 6.

  predizioni  legge il ledger degli emendamenti record per record e elenca quelli che
              contengono una predizione dichiarata insieme al suo riscontro. La ricerca per
              file non discrimina (ogni script di append cita predizioni ed esiti); l'unita'
              giusta e' il record.

  esclusi     il complemento di predizioni: i record che NON contengono entrambe le cose, con
              un estratto, per verificare a mano che nessuna predizione dichiarata sia sfuggita
              alle parole cercate.

  risali      dato un elenco di righe del ledger, riporta per intero i campi che citano il testo
              originale della predizione (json_path, key, old_value) e cerca nel ledger stesso i
              record che quel json_path nomina. Serve quando il record contiene il riassunto di
              una predizione formulata altrove.

Scrive un solo report JSONL nuovo (rifiuta di sovrascriverne uno esistente). Non modifica
nulla. Non emette verdetti: ordina record da leggere.

Uso:
  python src\\paper2_estrai.py selftest
  python src\\paper2_estrai.py clipped --root D:\\projects\\cauchy
  python src\\paper2_estrai.py predizioni --ledger D:\\projects\\cauchy\\src\\paper2_v1_amendments.jsonl
  python src\\paper2_estrai.py predizioni --ledger ...\\paper2_v1_amendments.jsonl --completo
  python src\\paper2_estrai.py esclusi --ledger ...\\paper2_v1_amendments.jsonl
  python src\\paper2_estrai.py risali --ledger ...\\paper2_v1_amendments.jsonl --righe 13,19,31,37,48
"""
import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sys
import tempfile

VERSIONE = "1.0"

# chiavi che, in qualunque punto dell'albero JSON, portano un conteggio di clipping
CHIAVI_CLIP = re.compile(r"^(d5c_)?n_clip(ped)?(_inmask)?$|^clipped_rand$|^n_fuori$", re.I)
# testo che segnala una predizione dichiarata e il suo riscontro, dentro UN record
PRED_A = re.compile(r"predizion[ei]|prediction|predicted|prevediamo|attesa dichiarata|"
                    r"dichiarat[ao] prima del run|declared before", re.I)
PRED_B = re.compile(r"smentit[ao]|falsificat[ao]|ritirat[ao]|confermat[ao]|verdetto|"
                    r"falsified|refuted|withdrawn", re.I)


class Errore(Exception):
    pass


def leggi_jsonl(path):
    """[(numero_riga, oggetto)] saltando righe vuote; segnala quelle malformate."""
    righe, rotte = [], 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, l in enumerate(f, 1):
            l = l.strip()
            if not l:
                continue
            try:
                righe.append((i, json.loads(l)))
            except ValueError:
                rotte += 1
    return righe, rotte


def cammina_json(o, prefisso=""):
    """Genera (percorso_chiave, valore) per ogni foglia di un oggetto JSON annidato."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from cammina_json(v, f"{prefisso}.{k}" if prefisso else str(k))
    elif isinstance(o, list):
        for n, v in enumerate(o):
            yield from cammina_json(v, f"{prefisso}[{n}]")
    else:
        yield prefisso, o


def clip_da_record(obj):
    """[(percorso, chiave, valore)] per ogni conteggio di clipping nel record."""
    out = []
    for perc, val in cammina_json(obj):
        ultima = perc.split(".")[-1].split("[")[0]
        if CHIAVI_CLIP.match(ultima) and isinstance(val, (int, float)) and not isinstance(val, bool):
            out.append((perc, ultima, val))
    return out


def scrivi_report(out, righe):
    d = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(d):
        raise Errore(f"cartella del report inesistente: {d}")
    with open(out, "x", encoding="utf-8") as f:
        for r in righe:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _prepara_out(out, nome):
    if out is None:
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = os.path.join("results", "paper2", f"estrazione_{nome}_{stamp}.jsonl")
    if os.path.exists(out):
        raise Errore(f"report gia' esistente, non lo sovrascrivo: {out}")
    return out


# ---------------------------------------------------------------------------
# clipped
# ---------------------------------------------------------------------------

def cmd_clipped(roots, out, stampa=True):
    out = _prepara_out(out, "clipped")
    out_abs = os.path.abspath(out)
    trovati, per_file, rotte_tot = [], {}, 0
    for root in roots:
        if not os.path.isdir(root):
            raise Errore(f"radice non trovata: {root}")
        for d, sub, files in os.walk(root):
            sub[:] = sorted(s for s in sub if s not in {".git", "__pycache__", ".venv", "venv"})
            for f in sorted(files):
                if not f.lower().endswith((".jsonl", ".json")):
                    continue
                p = os.path.join(d, f)
                if os.path.abspath(p) == out_abs:
                    continue
                try:
                    if f.lower().endswith(".json"):
                        righe = [(1, json.load(open(p, encoding="utf-8", errors="replace")))]
                        rotte = 0
                    else:
                        righe, rotte = leggi_jsonl(p)
                except (OSError, ValueError):
                    continue
                rotte_tot += rotte
                n_qui = 0
                for nl, obj in righe:
                    if not isinstance(obj, (dict, list)):
                        continue
                    hits = clip_da_record(obj)
                    if not hits:
                        continue
                    n_qui += 1
                    etich = {}
                    if isinstance(obj, dict):
                        for k in ("point", "punto", "region", "regione", "index", "mock",
                                  "label", "name", "treatment", "F", "alpha"):
                            if k in obj:
                                etich[k] = obj[k]
                    trovati.append({"tipo": "clip", "file": os.path.relpath(p, root), "radice": root,
                                    "riga": nl, "etichette": etich,
                                    "valori": [{"percorso": a, "chiave": b, "valore": c} for a, b, c in hits]})
                if n_qui:
                    per_file[os.path.relpath(p, root)] = n_qui
    somma = {}
    for t in trovati:
        for v in t["valori"]:
            s = somma.setdefault(v["chiave"], {"record": 0, "zero": 0, "max": 0})
            s["record"] += 1
            s["zero"] += 1 if v["valore"] == 0 else 0
            s["max"] = max(s["max"], v["valore"])
    testa = {"tipo": "intestazione", "strumento": "paper2_estrai", "versione": VERSIONE,
             "comando": "clipped", "radici": roots, "chiavi": CHIAVI_CLIP.pattern,
             "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    coda = {"tipo": "riepilogo", "record_con_conteggio": len(trovati), "file": per_file,
            "per_chiave": somma, "righe_malformate": rotte_tot}
    scrivi_report(out, [testa] + trovati + [coda])
    if stampa:
        print(f"record con un conteggio di clipping: {len(trovati)}")
        for k, v in sorted(somma.items()):
            print(f"  {k:18s} record={v['record']:6d}  a zero={v['zero']:6d}  massimo={v['max']}")
        print("\nper file:")
        for f, n in sorted(per_file.items(), key=lambda x: -x[1])[:20]:
            print(f"  {n:6d}  {f}")
        if not trovati:
            print("\nNESSUN conteggio trovato nei registri: il numero della practice 6 non esiste,")
            print("e per averlo serve un run, non una ricerca.")
        print(f"\nreport: {out}")
    return out, trovati, coda


# ---------------------------------------------------------------------------
# predizioni
# ---------------------------------------------------------------------------

def cmd_predizioni(ledger, out, completo=False, stampa=True):
    if not os.path.isfile(ledger):
        raise Errore(f"ledger non trovato: {ledger}")
    out = _prepara_out(out, "predizioni")
    righe, rotte = leggi_jsonl(ledger)
    sel = []
    for nl, obj in righe:
        testo = json.dumps(obj, ensure_ascii=False, default=str)
        a = PRED_A.search(testo)
        b = PRED_B.search(testo)
        if not (a and b):
            continue
        rec = {"tipo": "record", "riga": nl,
               "id": obj.get("record") or obj.get("id") or obj.get("n") if isinstance(obj, dict) else None,
               "item": (obj.get("item") or obj.get("voce")) if isinstance(obj, dict) else None,
               "predizione": a.group(0), "riscontro": sorted(set(m.group(0).lower() for m in PRED_B.finditer(testo))),
               "byte": len(testo)}
        if isinstance(obj, dict):
            for k in ("utc", "date", "data", "titolo", "title"):
                if k in obj:
                    rec[k] = obj[k]
        if completo:
            rec["record_intero"] = obj
        sel.append(rec)
    testa = {"tipo": "intestazione", "strumento": "paper2_estrai", "versione": VERSIONE,
             "comando": "predizioni", "ledger": ledger, "record_letti": len(righe), "completo": completo,
             "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    coda = {"tipo": "riepilogo", "record_letti": len(righe), "con_predizione_e_riscontro": len(sel),
            "righe_malformate": rotte}
    scrivi_report(out, [testa] + sel + [coda])
    if stampa:
        print(f"record nel ledger: {len(righe)}   con predizione E riscontro: {len(sel)}")
        for r in sel:
            print(f"  riga {r['riga']:4d}  id={r['id']}  item={str(r['item'])[:52]:52s}  {r['riscontro']}")
        print(f"\nreport: {out}")
    return out, sel, coda


# ---------------------------------------------------------------------------
# esclusi
# ---------------------------------------------------------------------------

def cmd_esclusi(ledger, out, stampa=True):
    if not os.path.isfile(ledger):
        raise Errore(f"ledger non trovato: {ledger}")
    out = _prepara_out(out, "esclusi")
    righe, rotte = leggi_jsonl(ledger)
    sel = []
    for nl, obj in righe:
        testo = json.dumps(obj, ensure_ascii=False, default=str)
        a = PRED_A.search(testo)
        b = PRED_B.search(testo)
        if a and b:
            continue
        rec = {"tipo": "escluso", "riga": nl,
               "item": obj.get("item") if isinstance(obj, dict) else None,
               "key": obj.get("key") if isinstance(obj, dict) else None,
               "ha_predizione": bool(a), "ha_riscontro": bool(b),
               "estratto": (obj.get("reason") or testo)[:400] if isinstance(obj, dict) else testo[:400]}
        sel.append(rec)
    testa = {"tipo": "intestazione", "strumento": "paper2_estrai", "versione": VERSIONE,
             "comando": "esclusi", "ledger": ledger, "record_letti": len(righe),
             "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    coda = {"tipo": "riepilogo", "record_letti": len(righe), "esclusi": len(sel),
            "solo_predizione": sum(1 for r in sel if r["ha_predizione"]),
            "solo_riscontro": sum(1 for r in sel if r["ha_riscontro"]),
            "ne_uno_ne_altro": sum(1 for r in sel if not r["ha_predizione"] and not r["ha_riscontro"]),
            "righe_malformate": rotte}
    scrivi_report(out, [testa] + sel + [coda])
    if stampa:
        print(f"record nel ledger: {len(righe)}   esclusi da 'predizioni': {len(sel)}")
        print(f"  con la sola predizione: {coda['solo_predizione']}   con il solo riscontro: "
              f"{coda['solo_riscontro']}   con nessuno dei due: {coda['ne_uno_ne_altro']}")
        for r in sel:
            m = "P" if r["ha_predizione"] else ("R" if r["ha_riscontro"] else "-")
            print(f"  [{m}] riga {r['riga']:3d}  {str(r['item'])[:28]:28s}  {str(r['key'])[:48]}")
        print(f"\nreport: {out}")
    return out, sel, coda


# ---------------------------------------------------------------------------
# risali
# ---------------------------------------------------------------------------

CHIAVI_PRED = re.compile(r"predict|prediction|declared_prediction|predizione", re.I)


def cmd_risali(ledger, righe_volute, out, stampa=True):
    if not os.path.isfile(ledger):
        raise Errore(f"ledger non trovato: {ledger}")
    out = _prepara_out(out, "risali")
    righe, _ = leggi_jsonl(ledger)
    per_riga = dict(righe)
    mancanti = [n for n in righe_volute if n not in per_riga]
    if mancanti:
        raise Errore(f"righe non presenti nel ledger: {mancanti} (il ledger ne ha {len(righe)})")
    # indice: ogni campo il cui NOME parla di predizione, in qualunque record
    indice = []
    for nl, obj in righe:
        for perc, val in cammina_json(obj):
            ultima = perc.split(".")[-1].split("[")[0]
            if CHIAVI_PRED.search(ultima) and isinstance(val, str):
                indice.append({"riga": nl, "item": obj.get("item") if isinstance(obj, dict) else None,
                               "campo": perc, "testo": val})
    fuori = []
    for n in righe_volute:
        o = per_riga[n]
        fuori.append({"tipo": "risalita", "riga": n,
                      "item": o.get("item"), "key": o.get("key"),
                      "json_path": o.get("json_path"), "document": o.get("document"),
                      "old_value": o.get("old_value"),
                      "campi_predizione_qui": [c for c in indice if c["riga"] == n]})
    testa = {"tipo": "intestazione", "strumento": "paper2_estrai", "versione": VERSIONE,
             "comando": "risali", "ledger": ledger, "righe": righe_volute,
             "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    coda = {"tipo": "riepilogo", "righe_chieste": len(righe_volute),
            "campi_predizione_nel_ledger": len(indice),
            "indice": indice}
    scrivi_report(out, [testa] + fuori + [coda])
    if stampa:
        for f in fuori:
            print(f"\n=== riga {f['riga']}  {f['item']}")
            print(f"  key:        {f['key']}")
            print(f"  json_path:  {f['json_path']}")
            print(f"  old_value:  {str(f['old_value'])[:600]}")
        print(f"\n=== campi con un nome di predizione, in tutto il ledger: {len(indice)}")
        for c in indice:
            print(f"  riga {c['riga']:3d}  {str(c['item'])[:24]:24s}  {c['campo'][:56]:56s}  {c['testo'][:60]}")
        print(f"\nreport: {out}")
    return out, fuori, coda


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest():
    checks = []

    def chk(c, m):
        checks.append((bool(c), m))

    # unita'
    chk([k for _, k, _ in clip_da_record({"points": {"B1": {"d5c_n_clipped": 28}}})] == ["d5c_n_clipped"],
        "chiave annidata trovata a qualunque profondita'")
    chk(clip_da_record({"a": {"b": [{"n_clipped": 0}]}})[0][2] == 0, "un conteggio a zero E' un dato, non un'assenza")
    chk(not clip_da_record({"n_clipped_note": "testo"}), "chiave simile ma diversa: non conta")
    chk(not clip_da_record({"n_clipped": True}), "booleano non e' un conteggio")
    chk(clip_da_record({"clipped_rand": 3})[0][1] == "clipped_rand", "clipped_rand riconosciuto")

    tmp = tempfile.mkdtemp(prefix="estrai_selftest_")
    _so = sys.stdout
    try:
        os.makedirs(os.path.join(tmp, "results", "paper2"))
        os.makedirs(os.path.join(tmp, "logs"))
        rp = os.path.join(tmp, "results", "paper2", "run.jsonl")
        with open(rp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"index": 0, "region": "NGC", "points": {"B1": {"d5c_n_clipped": 0},
                                                                        "B5": {"d5c_n_clipped": 28}}}) + "\n")
            f.write("\n")
            f.write("{rotto\n")
            f.write(json.dumps({"index": 1, "region": "SGC", "points": {"B1": {"d5c_n_clipped": 5}}}) + "\n")
        json.dump({"clipped_rand": 0}, open(os.path.join(tmp, "results", "paper2", "f2.json"), "w"))
        out = os.path.join(tmp, "results", "paper2", "r.jsonl")
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            _, trov, coda = cmd_clipped([tmp], out)
        finally:
            sys.stdout.close(); sys.stdout = _so
        chk(len(trov) == 3, f"clipped: tre record con conteggio (trovati {len(trov)})")
        chk(coda["righe_malformate"] == 1, "clipped: riga malformata contata, non fatale")
        chk(coda["per_chiave"]["d5c_n_clipped"]["max"] == 28, "clipped: massimo corretto")
        chk(coda["per_chiave"]["d5c_n_clipped"]["zero"] == 1, "clipped: gli zeri sono contati a parte")
        chk(any(t["etichette"].get("region") == "SGC" for t in trov), "clipped: etichette di regione riportate")
        chk(coda["per_chiave"]["clipped_rand"]["record"] == 1, "clipped: legge anche i .json")
        # niente conteggi -> riepilogo a zero, non errore
        v = os.path.join(tmp, "vuoto"); os.makedirs(v)
        json.dump({"a": 1}, open(os.path.join(v, "x.json"), "w"))
        o2 = os.path.join(tmp, "results", "paper2", "r2.jsonl")
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            _, t2, c2 = cmd_clipped([v], o2)
        finally:
            sys.stdout.close(); sys.stdout = _so
        chk(t2 == [] and c2["record_con_conteggio"] == 0, "clipped: nessun conteggio -> riepilogo vuoto, non errore")
        # predizioni
        lp = os.path.join(tmp, "logs", "led.jsonl")
        with open(lp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"record": 30, "item": "6/potenza", "testo": "la predizione dichiarata e' FALSIFICATA"}) + "\n")
            f.write(json.dumps({"record": 31, "item": "x", "testo": "nessuna attesa qui, solo una misura"}) + "\n")
            f.write(json.dumps({"record": 32, "item": "y", "testo": "predizione dichiarata prima del run"}) + "\n")
            f.write(json.dumps({"record": 33, "item": "z", "testo": "esito: confermata la predizione"}) + "\n")
        o3 = os.path.join(tmp, "results", "paper2", "r3.jsonl")
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            _, sel, c3 = cmd_predizioni(lp, o3)
        finally:
            sys.stdout.close(); sys.stdout = _so
        chk([r["id"] for r in sel] == [30, 33], "predizioni: solo i record con predizione E riscontro")
        chk(c3["record_letti"] == 4, "predizioni: tutti i record letti")
        chk(sel[0]["item"] == "6/potenza", "predizioni: item riportato")
        chk("record_intero" not in sel[0], "predizioni: senza --completo il record non e' incluso")
        o4 = os.path.join(tmp, "results", "paper2", "r4.jsonl")
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            _, sel4, _ = cmd_predizioni(lp, o4, completo=True)
        finally:
            sys.stdout.close(); sys.stdout = _so
        chk(sel4[0]["record_intero"]["record"] == 30 and [r["id"] for r in sel4] == [30, 33],
            "predizioni: con --completo il record c'e' e la selezione non cambia")
        # rifiuto di sovrascrittura, e sola lettura
        prima = open(o3, "rb").read()
        try:
            cmd_predizioni(lp, o3, stampa=False); chk(False, "report esistente -> rifiuto")
        except Errore:
            chk(open(o3, "rb").read() == prima, "report esistente -> rifiuto, file intatto")
        chk(len(open(rp, encoding="utf-8").read().splitlines()) == 4, "sola lettura: i registri non cambiano")
        o5 = os.path.join(tmp, "results", "paper2", "r5.jsonl")
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            _, esc, c5 = cmd_esclusi(lp, o5)
        finally:
            sys.stdout.close(); sys.stdout = _so
        chk([r["riga"] for r in esc] == [2, 3], "esclusi: il complemento esatto di predizioni")
        chk(c5["solo_predizione"] == 1 and c5["ne_uno_ne_altro"] == 1,
            "esclusi: distingue chi ha solo la predizione da chi non ha nulla")
        lp2 = os.path.join(tmp, "logs", "led2.jsonl")
        with open(lp2, "w", encoding="utf-8") as f:
            f.write(json.dumps({"item": "15", "key": "b6", "json_path": "prereg §5",
                                "old_value": "vecchio testo",
                                "rules": {"declared_prediction": "il residuo cresce con la deformazione"}}) + "\n")
            f.write(json.dumps({"item": "19", "key": "x", "json_path": "record 15",
                                "old_value": "la predizione di record 15"}) + "\n")
        o6 = os.path.join(tmp, "results", "paper2", "r6.jsonl")
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            _, ris, c6 = cmd_risali(lp2, [2], o6)
        finally:
            sys.stdout.close(); sys.stdout = _so
        chk(ris[0]["json_path"] == "record 15" and ris[0]["old_value"] == "la predizione di record 15",
            "risali: riporta json_path e old_value della riga chiesta")
        chk(c6["campi_predizione_nel_ledger"] == 1 and c6["indice"][0]["riga"] == 1,
            "risali: indicizza declared_prediction anche nei record non chiesti")
        try:
            cmd_risali(lp2, [99], None, stampa=False)
            chk(False, "risali: riga inesistente -> errore")
        except Errore:
            chk(True, "risali: riga inesistente -> errore")
        try:
            cmd_predizioni(os.path.join(tmp, "non_esiste.jsonl"), None, stampa=False)
            chk(False, "ledger inesistente -> errore")
        except Errore:
            chk(True, "ledger inesistente -> errore")
    finally:
        sys.stdout = _so
        shutil.rmtree(tmp, ignore_errors=True)

    n_ok = sum(ok for ok, _ in checks)
    for ok, m in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {m}")
    print(f"SELFTEST: {n_ok}/{len(checks)}")
    return 0 if n_ok == len(checks) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    c = sub.add_parser("clipped")
    c.add_argument("--root", action="append", required=True)
    c.add_argument("--out", default=None)
    e = sub.add_parser("esclusi")
    e.add_argument("--ledger", required=True)
    e.add_argument("--out", default=None)
    r = sub.add_parser("risali")
    r.add_argument("--ledger", required=True)
    r.add_argument("--righe", required=True, help="numeri di riga separati da virgola, es. 13,19,31")
    r.add_argument("--out", default=None)
    p = sub.add_parser("predizioni")
    p.add_argument("--ledger", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--completo", action="store_true",
                   help="includi nel report il record per intero, non solo le etichette")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    try:
        if a.cmd == "selftest":
            return selftest()
        if a.cmd == "clipped":
            cmd_clipped(a.root, a.out)
        elif a.cmd == "esclusi":
            cmd_esclusi(a.ledger, a.out)
        elif a.cmd == "risali":
            try:
                nums = [int(x) for x in a.righe.split(",") if x.strip()]
            except ValueError:
                raise Errore(f"--righe vuole numeri separati da virgola, ricevuto: {a.righe!r}")
            if not nums:
                raise Errore("--righe e' vuoto")
            cmd_risali(a.ledger, nums, a.out)
        else:
            cmd_predizioni(a.ledger, a.out, a.completo)
        return 0
    except Errore as e:
        print(f"RIFIUTO: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
