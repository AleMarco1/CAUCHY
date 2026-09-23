#!/usr/bin/env python3
"""
paper2_append_amend77.py  -  record 77 del ledger: chiusura della Fase 6

Un record, otto voci (A-H): la 6.4 chiusa per dichiarazione; la 6.5 con il documento dei
ritirati contro il rev1 del 24 luglio; la 6.6 con canovaccio_paper5.md recuperato e ancorato;
il controllo di fedelta' dei recuperi dalle schede delle chat; i nomi dei canovacci; le date
della sessione del 22 settembre; la Fase 6 senza voci aperte; l'elenco per la revisione
documentale.

Il dry-run e l'apply RIFIUTANO se: il ledger non e' all'ancora; un file ancorato manca o ha
cambiato sha; uno qualunque dei fatti che il record dichiara non si riproduce dai file o da git.

I documenti di papers/ sono fuori dal rilascio: il record li ancora per digest (chiave = nome
del file), non per percorso, come il record 76 fa con i log di lavoro.

Uso:
  python src\\paper2_append_amend77.py selftest
  python src\\paper2_append_amend77.py dry-run
  python src\\paper2_append_amend77.py apply
  python src\\paper2_append_amend77.py verify
"""
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "src" / "paper2_v1_amendments.jsonl"
LEDGER_SHA = "a2dba4f7adbdfa9967de2c380f183ec7dd51a323682161068d0fe21f52808780"
LEDGER_RIGHE = 76
LEDGER_BYTE = 641594
REF_FILE_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REF_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

ANCORE = {  # percorso relativo -> (sha256, byte o None)
 "papers/paper2/paper2_6_5_ritirati.md":         ("517e72095feb376b359f3b67df754a33ff3a048a98716a09d4466d80873d1770", 4868),
 "papers/paper2/canovaccio_paper2_rev1.md":      ("1152bcc919a2186e4c6971de5399b40cb89ea9838dfba778913a5cefb14e92f1", 6112),
 "papers/paper2/canovaccio_paper5.md":           ("796fbc82f630006ab608dd23490b04180e63d0196ad92f3e1d32494c7633ea30", 9351),
 "papers/paper2/canovaccio_paper1.md":           ("1512e1da391066103ec15fef79055e094e4abe5d92ca53e38032e89d840d8137", 10438),
 "papers/paper2/canovaccio_paper2.md":           ("7cbc0877ebcd4b1b0ac0ed61262dd204667a241f09715b0441d7dff30fbfa1db", 20518),
 "papers/paper2/canovaccio_paper3.md":           ("a2f90c89d7360304fb7a06563776d083f8d1f2fff472f044ea6ce348faf124c5", 10130),
 "papers/paper2/canovaccio_4_paper_followup.md": ("cc9b0fa8542ff3604a0ac8cb7315c52423e2ef964fa24a243ca2db05c3cb8b95", 20503),
 "papers/paper2/checklist_paper2.md":            ("4b2b830acd82ec938ebe50b8ef18ef3ffdaf27204eb57d2b0d872627f10f7fbb", 261080),
 "papers/paper2/paper2_budget_5_1.md":           ("a5d60b1537e777d4c54ac1f55caf1a60b00d676d4785877ba9ac62985b45eea2", 27802),
 "papers/paper2/modifiche_paper1.md":            ("77849455d1d4f9fa46e61a3e3bb850daf1f763f140e22d486b5ecb8e03f141c1", 82006),
 "papers/paper2/paper2_stato.md":                ("18ec62b6500e21b1453fac938ae8743172bc67cbdfb924c483376e3d32fe65b5", 105646),
 "src/paper2_censimento_registri.py":            ("738c309c3f22344e22cddbad3797c140bffafa627101e2303c0d2af08e1a7681", 105803),
}

VOCI_CHECKLIST = {
 "6.4": "- [ ] **6.4** `gate_preinvio.py` adattato al Paper 2, eseguito sul PDF finale.",
 "6.5": "- [ ] **6.5** Elenco esplicito dei risultati **ritirati** rispetto al canovaccio del 24 luglio.",
 "6.6": "- [ ] **\u2726 6.6** Archiviare `canovaccio_paper5.md`: il contenuto vive nella Fase 4D.",
}

CLASSI_6_5 = {
 "cambi_di_disegno": [1, 2, 3],
 "confermati": [4, 5, 6, 12, 13, 14, 16],
 "ritirati_o_smentiti": [7, 8, 9, 10, 11, 15],
 "non_realizzati": [17],
}

COMMIT_22_SET = ["01543c6", "50a8707", "b459cf5", "4055215", "c5c0379", "b41bf75",
                 "411bc6f", "431d3a2", "4409375", "a5fdabd", "73fdf8c"]

def sha(nome): return ANCORE[nome][0]

def costruisci_record(utc: str) -> dict:
    p = "papers/paper2/"
    return {
 "type": "protocol",
 "utc": utc,
 "item": "6.4-6.5-6.6",
 "key": "chiusura_della_fase_6_6_4_dichiarata_6_5_ritirati_contro_il_rev1_6_6_canovaccio_paper5_recuperato",
 "document": "papers/paper2/paper2_6_5_ritirati.md; papers/paper2/checklist_paper2.md (6.4, 6.5, 6.6); papers/paper2/paper2_stato.md",
 "reference_file": "src/paper2_v1_reference.json",
 "reference_file_sha256": REF_FILE_SHA,
 "reference_self_sha256": REF_SELF_SHA,
 "numbering_rule": "The number of an amendment is its 1-based POSITION in this file. This is record 77.",
 "amends_records": [75, 76],
 "old_value": {
  "checklist_6_4": VOCI_CHECKLIST["6.4"],
  "checklist_6_5": VOCI_CHECKLIST["6.5"],
  "checklist_6_6": VOCI_CHECKLIST["6.6"],
  "date": "«18 settembre» nei documenti della sessione scritta il 22 settembre e nel testo del record 76; utc del record 75 2026-09-18T00:00:00+00:00",
 },
 "new_value": {
  "A_6_4_chiusa_per_dichiarazione": {
   "misure": {"disco": "zero file *preinvio* sotto D:\\projects (sonda del 23 set) e sotto la radice del repository (ricontrollato all'append)",
              "git": "zero commit che tocchino *preinvio* su --all (ricontrollato all'append)",
              "ledger": "zero righe con «preinvio» nei record 1-76 (ricontrollato all'append)",
              "chat_del_progetto": "compare solo come voce della checklist; nessuna versione per M26 o per il Paper 1"},
   "premessa_falsa": "«adattato al Paper 2» presuppone uno strumento da adattare: non e' mai esistito",
   "decisione": "i controlli dipendono dal PDF del Paper 2, che nasce in Fase 7. Il contratto (che cosa controlla) si dichiara prima di scrivere lo strumento; scrittura ed esecuzione sul PDF sono Fase 7, prima della sottomissione, accanto a 6.0a, 6.2-iii e al deposito Zenodo.",
   "esito": "6.4 chiusa in Fase 6 per dichiarazione"},
  "B_6_5_ritirati_contro_il_rev1": {
   "documento": {"nome": "paper2_6_5_ritirati.md", "sha256": sha(p + "paper2_6_5_ritirati.md"), "byte": 4868},
   "riferimento": {"nome": "canovaccio_paper2_rev1.md", "sha256": sha(p + "canovaccio_paper2_rev1.md"), "byte": 6112,
                   "identificazione": "la rev. 1 della checklist (chat 005, nota del 3 agosto) nomina nella base documentale «canovaccio_paper2.md (24 luglio 2026)»; il file porta la «Nota di revisione (24 luglio 2026)»",
                   "origine": "scheda file della chat 002 del progetto; sostituiva la sezione Paper 2 di canovaccio_5_paper_followup.md",
                   "perche_recuperato": "sul disco sovrascritto dalla rev. 25 agosto; in git solo quella (aggiunta in 73c8213, tolta dal tracciamento in 900335e, ricontrollato all'append)"},
   "popolazione": "le 17 affermazioni del rev1, non l'unione degli elenchi di ritiri esistenti",
   "classi": CLASSI_6_5,
   "aperti": ["riga 11: se il Paper 1 attribuisce alla pesatura anche la curtosi in una frase che P1-11 non tocca, serve una voce in piu' per la 6.0a",
              "riga 15: il riferimento del Paper 2 resta v1 (11 set, record 59-60); Paper 3 (0.1, 3.3) e Paper 4 devono dichiarare l'ensemble prima della pre-registrazione del Paper 3"],
   "nessun_numero_nuovo": "i numeri del documento sono citati da checklist rev. 3.32, budget, modifiche_paper1.md e stato §5; nessuno ricalcolato"},
  "C_6_6_canovaccio_paper5": {
   "file": {"nome": "canovaccio_paper5.md", "sha256": sha(p + "canovaccio_paper5.md"), "byte": 9351},
   "origine": "scheda file della chat 003 del progetto (ultimo aggiornamento 26 luglio 2026)",
   "prima_del_recupero": "assente da D:\\projects con qualunque estensione (sonda del 23 set); mai in git --all (ricontrollato all'append); zero righe nel ledger e nelle eccezioni del rilascio; assente dal project",
   "perche_archiviato": "canovaccio_4_paper_followup.md §10: «archiviare, il contenuto vive nella Componente D del Paper 2»; canovaccio_paper2.md rev. 25 ago: il canovaccio del Paper 5 assorbito come Componente D. Il programma e' passato da sei a quattro paper.",
   "archiviazione": "recupero e ancoraggio per digest; il file sta in papers/paper2, fuori dal rilascio come tutto papers/",
   "limite": "l'assorbimento nella Componente D e' dichiarato dai canovacci del 25 agosto e non e' verificato contro il testo del file. Questo record ancora il documento e non ne cita i numeri, che non hanno un registro sul disco.",
   "esito": "6.6 chiusa"},
  "D_controllo_di_fedelta_dei_recuperi": {
   "cancello": "canovaccio_paper1_rev3.md scaricato dalla stessa scheda della chat 002, confrontato byte per byte con papers/paper2/canovaccio_paper1.md",
   "previsione_ritirata_prima_della_misura": "«il download e' un prefisso del file sul disco, che ha in piu' \\n\\n---\\n»: la base era il separatore stampato dal comando di lettura, non il file. Ritirata prima di vedere il download.",
   "previsione": "identici, 1512e1da..., 10 438 byte",
   "esito": "PASS: 10 438 byte su 10 438, identici",
   "indipendenza": "LastWriteTime dei quattro download fra 2026-09-23T07:00:23 e 07:03:26: scaricati, non copiati dal disco, dove il gemello porta 2026-07-24T18:28:54",
   "conseguenza": "le schede restituiscono i byte scritti a luglio: rev1 e canovaccio_paper5.md si ancorano cosi' come sono",
   "file_di_controllo": "non e' un'ancora di questo record: e' identico al gemello ancorato, e la scheda della chat 002 lo riproduce"},
  "E_nomi_dei_canovacci": {
   "canovaccio_paper2.md": "resta la rev. 25 agosto (" + sha(p + "canovaccio_paper2.md")[:12] + "..., 20 518 byte), in tre copie identiche: e' il file citato dal record 50, e la citazione si risolve in un documento solo",
   "canovaccio_paper2_rev1.md": "il rev1 tiene il proprio nome: con due documenti sotto lo stesso nome la citazione del record 50 smetterebbe di risolversi",
   "cartella": "i canovacci stanno in papers/paper2 (decisione del 23 set)"},
  "F_date_misurate": {
   "sessione_precedente": "aperta col freeze_verify del 18 set 07:44Z, scritta il 22 set: undici commit da 01543c6 a 73fdf8c, date di committer ricontrollate all'append",
   "dove_18_si_legge_22": ["note 10/11, F e correzione della 5/6 di paper2_budget_5_1.md",
                           "checklist rev. 3.32 (intestazione compresa)",
                           "changelog e voci nuove di modifiche_paper1.md",
                           "15a revisione di paper2_stato.md",
                           "record 76, voce C («33 non citati al 18 set»)",
                           "i motivi dei 67 in src/paper2_censimento_registri.py 1.5 («al 18 set»)"],
   "record_75": "utc 2026-09-18T00:00:00+00:00 scritto a mano; l'append e' il commit 50a8707 del 22 settembre",
   "nessun_numero_dipende_da_una_data": "non si riscrive nulla: la correzione vive qui, e nei documenti entra con la prossima revisione",
   "questa_sessione": "23 settembre: freeze_verify 2026-09-23T00:40:36Z CLEAN 76/76; ledger 641 594 byte a 76 record"},
  "G_fase_6": {
   "chiusa": "con questo record la Fase 6 non ha voci aperte: 6.0b, 6.0d, 6.1, 6.2, 6.3 (a meno del deposito), 6.4, 6.5, 6.6, 6.7, 6.8, 6.9 chiuse; 6.0c ritirata",
   "in_fase_7": "6.0a (sedici voci del Paper 1 in coppia; P1-15 e P1-16 bloccate); 6.2-iii; contratto, scrittura ed esecuzione di gate_preinvio; deposito Zenodo con la v1.1 del protocollo e il tag della sottomissione"},
  "H_per_la_revisione_documentale": [
   "«tredici voci» -> «sedici» in checklist (6.0a e ultimi punti della Fase 7) e stato (§8, Z-P1); P1-14, P1-15, P1-16 negli indici degli aperti",
   "stato §8 «Aperti»: righe superate senza barratura (Z-4.2a, X-P1-Tab12)",
   "Fase 7, punto 10: dichiarare la promozione del «3-bis» a Paper 3 come riformulazione motivata dal Paper 1 (canovaccio_paper3.md §10)",
   "la citazione di canovaccio_paper2.md nel record 50 non compare nel censimento del rilascio (0 righe): da spiegare prima della prossima esecuzione",
   "le date del punto F"],
 },
 "reason": "Chiusura della Fase 6. La 6.4 chiedeva di adattare uno strumento che non e' mai esistito e di eseguirlo su un PDF che nasce in Fase 7: si chiude per dichiarazione. La 6.5 e la 6.6 poggiavano su due documenti assenti dal disco e da git, recuperati dalle schede delle chat dopo un controllo di fedelta' su un gemello, e ancorati per digest.",
 "rules": {
  "marker": "emendamento-77-chiusura-fase-6",
  "what_this_does_not_do": "Non modifica alcun valore congelato, non riapre alcun verdetto depositato, non tocca il reference. Non riscrive i documenti con la data sbagliata: la correzione vive in questo record e nei documenti entra con la prossima revisione.",
  "evidence_files_rechecked_at_append": sorted(k for k in ANCORE if not k.startswith("papers/")),
  "documents_by_digest": {k.split("/")[-1]: v[0] for k, v in sorted(ANCORE.items()) if k.startswith("papers/")},
  "git_rechecked_at_append": ["log --all -- *preinvio*: vuoto", "log --all -- *canovaccio_paper5*: vuoto",
                              "log --all --diff-filter=AD -- papers/paper2/canovaccio_paper2.md: 73c8213 e 900335e",
                              "data di committer degli undici commit del 22 settembre"]},
 "evidence": "Ancore sha256 e byte dei file in rules.evidence_files_rechecked_at_append e dei documenti in rules.documents_by_digest, riverificate dall'appender prima dell'append, insieme alle voci della checklist citate in old_value, al conteggio e alle classi delle righe del documento 6.5, alle frasi dei canovacci citate in B, C ed E, alle occorrenze del 18 nel record 76 e nel censimento, e ai fatti di git in rules.git_rechecked_at_append.",
    }

# -- ricalcolo -------------------------------------------------------------------------------
def righe_tabella(testo: str) -> list:
    return [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", testo, flags=re.M)]

def data_di(iso: str) -> str:
    return iso.strip()[:10]

def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0: raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout

def controlla_ancore(base: Path) -> list:
    err = []
    for rel, (s, b) in ANCORE.items():
        p = base / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        raw = p.read_bytes()
        if hashlib.sha256(raw).hexdigest() != s: err.append(f"sha cambiato: {rel}")
        elif b is not None and len(raw) != b: err.append(f"byte diversi: {rel}")
    return err

def controlla_documenti(base: Path) -> list:
    err = []
    t = lambda rel: (base / rel).read_text(encoding="utf-8")
    p = "papers/paper2/"
    doc = t(p + "paper2_6_5_ritirati.md")
    if sha(p + "canovaccio_paper2_rev1.md") not in doc: err.append("6.5: il documento non cita lo sha del rev1")
    if righe_tabella(doc) != list(range(1, 18)): err.append(f"6.5: righe {righe_tabella(doc)}")
    classi = sorted(n for v in CLASSI_6_5.values() for n in v)
    if classi != list(range(1, 18)): err.append("6.5: le classi non partizionano 1-17")
    for frase in ("righe **7, 8, 9, 10, 11, 15**", "righe **1, 2, 3**"):
        if frase not in doc: err.append(f"6.5: manca «{frase}»")
    rev1 = t(p + "canovaccio_paper2_rev1.md")
    if rev1.count("Nota di revisione (24 luglio 2026)") != 1: err.append("rev1: nota del 24 luglio")
    if not rev1.startswith("# Paper 2 \u2014 sezione aggiornata"): err.append("rev1: prima riga")
    if t(p + "canovaccio_paper5.md").splitlines()[0] != "# canovaccio_paper5.md": err.append("paper5: prima riga")
    frasi = {p + "canovaccio_4_paper_followup.md": "`canovaccio_paper5.md` \u2192 **archiviare**",
             p + "canovaccio_paper2.md": "Il canovaccio del Paper 5 \u00e8 assorbito qui come **Componente D**",
             p + "canovaccio_paper3.md": "**Nota di trasparenza da riportare nel Paper 2.**",
             p + "checklist_paper2.md": "### rev. 3.32 \u2014 18 settembre 2026"}
    for rel, frase in frasi.items():
        if t(rel).count(frase) != 1: err.append(f"{rel}: «{frase[:40]}» non una volta sola")
    ck = t(p + "checklist_paper2.md").splitlines()
    for v, riga in VOCI_CHECKLIST.items():
        if ck.count(riga) != 1: err.append(f"checklist: voce {v} non trovata una volta sola")
    if "al 18 set" not in t("src/paper2_censimento_registri.py"): err.append("censimento: «al 18 set» assente")
    return err

def controlla_ledger() -> list:
    err = []
    righe = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    if any("preinvio" in l.lower() for l in righe): err.append("ledger: «preinvio» presente")
    if "33 non citati al 18 set" not in righe[75]: err.append("record 76: «33 non citati al 18 set» assente")
    if json.loads(righe[74]).get("utc") != "2026-09-18T00:00:00+00:00": err.append("record 75: utc diverso dall'atteso")
    return err

def controlla_git() -> list:
    err = []
    if git("log", "--all", "--format=%h", "--", "*preinvio*").strip(): err.append("git: *preinvio* toccato da qualche commit")
    if git("log", "--all", "--format=%h", "--", "*canovaccio_paper5*").strip(): err.append("git: *canovaccio_paper5* toccato")
    ad = git("log", "--all", "--diff-filter=AD", "--format=%h", "--", "papers/paper2/canovaccio_paper2.md").split()
    if len(ad) != 2 or not ad[0].startswith("900335e") or not ad[1].startswith("73c8213"):
        err.append(f"git: A/D di canovaccio_paper2.md {ad}")
    for h in COMMIT_22_SET:
        d = data_di(git("show", "-s", "--format=%cI", h))
        if d != "2026-09-22": err.append(f"git: {h} datato {d}")
    return err

def controlla_albero() -> list:
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for f in filenames + dirnames:
            if "preinvio" in f.lower(): return [f"albero: {Path(dirpath, f)}"]
    return []

def ledger_ok():
    raw = LEDGER.read_bytes()
    righe = [l for l in raw.decode("utf-8").splitlines() if l.strip()]
    return hashlib.sha256(raw).hexdigest(), len(righe), len(raw)

# -- comandi ---------------------------------------------------------------------------------
def selftest():
    ok = 0
    r = costruisci_record("2026-01-01T00:00:00+00:00")
    s = json.dumps(r, ensure_ascii=False, separators=(",", ":")); assert json.loads(s) == r; ok += 1
    assert r["numbering_rule"].endswith("record 77."); ok += 1
    assert sorted(n for v in CLASSI_6_5.values() for n in v) == list(range(1, 18)); ok += 1
    assert not any(k.startswith("papers/") for k in r["rules"]["evidence_files_rechecked_at_append"]) \
       and len(r["rules"]["documents_by_digest"]) == 11 and "papers/" not in json.dumps(r["rules"]["documents_by_digest"]); ok += 1
    assert righe_tabella("| # | a |\n|---|---|\n| 1 | x |\n| 2 | y |\n| 10 | z |\n") == [1, 2, 10]; ok += 1
    assert data_di("2026-09-22T12:40:12+02:00\n") == "2026-09-22" and len(set(COMMIT_22_SET)) == 11; ok += 1
    assert all(len(v[0]) == 64 and int(v[0], 16) >= 0 for v in ANCORE.values()) and len(ANCORE) == 12; ok += 1
    assert all(riga.startswith("- [ ] **") for riga in VOCI_CHECKLIST.values()); ok += 1
    print(f"selftest: {ok}/8 OK")

def dry_run(scrivi=False):
    s, n, b = ledger_ok()
    if s != LEDGER_SHA or n != LEDGER_RIGHE or b != LEDGER_BYTE:
        raise SystemExit(f"STOP: ledger {s[:12]}... {n} righe {b} byte, atteso {LEDGER_SHA[:12]}... {LEDGER_RIGHE} righe {LEDGER_BYTE} byte")
    err = controlla_ancore(ROOT)
    if not err:
        err = controlla_documenti(ROOT) + controlla_ledger() + controlla_git() + controlla_albero()
    if err:
        print("STOP:"); [print("  -", e) for e in err]; raise SystemExit(1)
    utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    riga = json.dumps(costruisci_record(utc), ensure_ascii=False, separators=(",", ":"))
    print(f"ledger all'ancora ({LEDGER_SHA[:12]}..., {LEDGER_RIGHE} righe, {LEDGER_BYTE} byte); "
          f"{len(ANCORE)} ancore coincidono; documenti, ledger, git e albero confermano ogni fatto del record")
    print(f"record 77: {len(riga.encode())} byte, utc {utc}")
    if not scrivi:
        print("  nessuna modifica scritta"); return
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(riga + "\n")
    s2, n2, b2 = ledger_ok()
    print(f"[apply] appeso: ledger {n2} righe, {b2} byte, sha {s2}")

def verify():
    s, n, b = ledger_ok()
    ultimo = json.loads([l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()][-1])
    ok = n == LEDGER_RIGHE + 1 and ultimo["numbering_rule"].endswith("record 77.") and ultimo["item"] == "6.4-6.5-6.6"
    print(f"verify {'OK' if ok else 'ANOMALIA'}: {n} righe, {b} byte, sha {s}; ultimo: item {ultimo['item']}, utc {ultimo['utc']}")
    if not ok: sys.exit(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    c = ap.parse_args().cmd
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[c]()
