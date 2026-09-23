#!/usr/bin/env python3
"""
paper2_patch_revisione_23set.py  -  revisione documentale unica dopo il record 77

Quattro documenti, un passaggio:
  checklist_paper2.md   rev. 3.32 -> 3.33: Fase 6 chiusa (6.4, 6.5, 6.6), «sedici» voci del
                        Paper 1, ultimi punti della Fase 7 estesi, sezioni 7 e 10 della Fase 7,
                        date della rev. 3.32 lette 22 settembre;
  paper2_stato.md       16a -> 17a revisione: record 77, §3, §8 «Aperti», 8-ter, §9, data nel §0;
  paper2_budget_5_1.md  sette date «18 settembre» -> «22 settembre»;
  modifiche_paper1.md   sette date, una riga di changelog.

Uso singolo, come gli altri patcher documentali: ogni file deve essere all'ancora «prima»
(o gia' all'ancora «dopo», e allora non si tocca). Ogni sostituzione deve trovare il suo testo
esattamente una volta; il risultato deve avere lo sha «dopo»; la sostituzione inversa deve
ridare lo sha «prima». Fine riga e BOM di ogni file sono misurati e conservati. Le precondizioni
(ledger, freeze_verify, documenti del record 77, commit) sono i fatti che la 17a revisione dello
stato dichiara, e si verificano prima di scrivere.

Uso:
  python src\\paper2_patch_revisione_23set.py selftest
  python src\\paper2_patch_revisione_23set.py dry-run
  python src\\paper2_patch_revisione_23set.py apply
  python src\\paper2_patch_revisione_23set.py verify
"""
import argparse, hashlib, os, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"

PRECONDIZIONI = {  # fatti dichiarati dalla 17a revisione dello stato
 "src/paper2_v1_amendments.jsonl": ("9e178837aca9e56a16cf006e3ffe6e25b424ecca2cf94bf18dc40ec05982a923", 651850),
 "src/paper2_freeze_verify.py":    ("a9a918c2c9bc55fc3772d36753ad94e310e80833c99fb9f58367a620a9d5394a", 52181),
 "papers/paper2/paper2_6_5_ritirati.md":    ("517e72095feb376b359f3b67df754a33ff3a048a98716a09d4466d80873d1770", 4868),
 "papers/paper2/canovaccio_paper2_rev1.md": ("1152bcc919a2186e4c6971de5399b40cb89ea9838dfba778913a5cefb14e92f1", 6112),
 "papers/paper2/canovaccio_paper5.md":      ("796fbc82f630006ab608dd23490b04180e63d0196ad92f3e1d32494c7633ea30", 9351),
}
COMMIT_77 = "d8d64ef"

# ---------------------------------------------------------------------------------------------
CHECKLIST = [
 ("### rev. 3.32 \u2014 18 settembre 2026 \u2014 record 75 e 76;",
  "### rev. 3.33 \u2014 23 settembre 2026 \u2014 record 77; **la Fase 6 \u00e8 CHIUSA**: la 6.4 per dichiarazione (`gate_preinvio.py` non \u00e8 mai esistito; contratto, scrittura ed esecuzione passano alla Fase 7), la 6.5 con `paper2_6_5_ritirati.md` contro il canovaccio del 24 luglio (`canovaccio_paper2_rev1.md`, recuperato dalla scheda di una chat), la 6.6 con `canovaccio_paper5.md` recuperato e ancorato. Le voci del Paper 1 sono **sedici**, non tredici. La rev. 3.32, scritta il 22 settembre, portava la data della sessione, «18»: corretta qui e nel testo (record 77, voce F). Ledger a 77 record, `freeze_verify` CLEAN 77/77.\n"
  "### rev. 3.32 \u2014 22 settembre 2026 \u2014 record 75 e 76;"),
 ("**\u2726\u2726 Osservazione del 18 set (voce 6.2-vi", "**\u2726\u2726 Osservazione del 22 set (voce 6.2-vi"),
 ("(decisione A del 18 set)", "(decisione A del 22 set)"),
 ("nominato il 18 set). Due passate", "nominato il 22 set). Due passate"),
 ("**b) CHIUSA il 18 set, record 75", "**b) CHIUSA il 22 set, record 75"),
 ("**\u2726\u2726 Residuo CHIUSO il 18 set (voce 6.2-vi", "**\u2726\u2726 Residuo CHIUSO il 22 set (voce 6.2-vi"),
 ("**\u2726\u2726\u2726 CHIUSA in Fase 6 il 18 set, record 76", "**\u2726\u2726\u2726 CHIUSA in Fase 6 il 22 set, record 76"),
 ("`results/paper1/n7_nfw_NGC.jsonl` (18 set,", "`results/paper1/n7_nfw_NGC.jsonl` (22 set,"),
 ("**6.2-iv \u2014 CHIUSA il 18 set**", "**6.2-iv \u2014 CHIUSA il 22 set**"),
 ("**6.2-v \u2014 CHIUSA il 18 set**", "**6.2-v \u2014 CHIUSA il 22 set**"),
 ("**6.2-vi \u2014 CHIUSA il 18 set**", "**6.2-vi \u2014 CHIUSA il 22 set**"),
 ("**a) Le tredici voci del Paper 1 si applicano", "**a) Le sedici voci del Paper 1 si applicano"),
 ("      Nessuna tocca il deficit, il suo rango o la scomposizione in persistenza.\n",
  "      Nessuna tocca il deficit, il suo rango o la scomposizione in persistenza.\n"
  "      **\u2726 rev. 3.33 \u2014 tre voci in pi\u00f9 dalla 6.2:** **P1-14** PRONTA (\u00a77.1: il 47 % \u00e8 della\n"
  "      deviazione standard, non della varianza); **P1-15** e **P1-16** BLOCCATE (Tab. 12, riga 5;\n"
  "      curve di step6 a R12, R15, R17). Le coppie vanno rilette con le tre nuove prima\n"
  "      dell'applicazione. E un controllo dalla 6.5 (riga 11): se il Paper 1 attribuisce alla\n"
  "      pesatura anche la curtosi, in una frase che P1-11 non tocca, serve una voce in pi\u00f9.\n"),
 ("- [ ] **6.4** `gate_preinvio.py` adattato al Paper 2, eseguito sul PDF finale.",
  "- [x] **6.4 \u2014 CHIUSA il 23 set per dichiarazione, record 77.** `gate_preinvio.py` non \u00e8 mai\n"
  "      esistito (disco, git `--all`, ledger, chat del progetto): «adattato» non ha oggetto, e il PDF\n"
  "      finale nasce in Fase 7. Contratto, scrittura ed esecuzione passano agli ultimi punti della\n"
  "      Fase 7. *(Testo originale: `gate_preinvio.py` adattato al Paper 2, eseguito sul PDF finale.)*"),
 ("- [ ] **6.5** Elenco esplicito dei risultati **ritirati** rispetto al canovaccio del 24 luglio.",
  "- [x] **6.5 \u2014 CHIUSA il 23 set, record 77.** Il canovaccio del 24 luglio \u00e8\n"
  "      `canovaccio_paper2_rev1.md` (`1152bcc9\u2026`), sovrascritto sul disco e mai in git, recuperato\n"
  "      dalla scheda della chat 002 dopo un controllo di fedelt\u00e0 su un gemello. L'elenco \u00e8 in\n"
  "      `papers/paper2/paper2_6_5_ritirati.md` (`517e7209\u2026`), sulle 17 affermazioni del rev1:\n"
  "      ritirati o smentiti le righe **7, 8, 9, 10, 11, 15**, cambi di disegno **1, 2, 3**. Entra nel\n"
  "      manoscritto alla sezione 7 della Fase 7."),
 ("- [ ] **\u2726 6.6** Archiviare `canovaccio_paper5.md`: il contenuto vive nella Fase 4D.",
  "- [x] **\u2726 6.6 \u2014 CHIUSA il 23 set, record 77.** `canovaccio_paper5.md` non c'era pi\u00f9 n\u00e9 sul\n"
  "      disco n\u00e9 in git: recuperato dalla scheda della chat 003, ancorato (`796fbc82\u2026`) e messo in\n"
  "      `papers/paper2`. Il contenuto vive nella Fase 4D; l'assorbimento \u00e8 dichiarato dai canovacci\n"
  "      del 25 agosto, non verificato contro il testo del file."),
 ("**\u2726\u2726 Ultimi due punti della Fase 7 (decisione del 17 set), subito prima della sottomissione:**\n"
  "(i) le tredici voci del Paper 1, in coppia (6.0a); (ii) il deposito Zenodo con la v1.1 del\n"
  "protocollo e il tag della sottomissione (6.3). GitHub, invece, si aggiorna periodicamente.",
  "**\u2726\u2726 Ultimi punti della Fase 7 (decisione del 17 set, estesa il 23 set col record 77), subito\n"
  "prima della sottomissione:** (i) le sedici voci del Paper 1, in coppia (6.0a; P1-15 e P1-16 da\n"
  "sbloccare o dichiarare); (ii) la 6.2-iii, riga 9 del budget col \u00a78.2 del Paper 1; (iii)\n"
  "`gate_preinvio.py`, ex 6.4: contratto dichiarato prima, poi scrittura ed esecuzione sul PDF;\n"
  "(iv) il deposito Zenodo con la v1.1 del protocollo e il tag della sottomissione (6.3). GitHub,\n"
  "invece, si aggiorna periodicamente."),
 ("7. Ensemble v2 e le predizioni a un punto.",
  "7. Ensemble v2 e le predizioni a un punto. **\u2726 rev. 3.33:** qui i ritirati della 6.5 (righe 7\u201311\n"
  "   e 15 di `paper2_6_5_ritirati.md`) e i tre cambi di disegno rispetto al canovaccio del 24\n"
  "   luglio: il \u00a74 del programma chiede che ogni ritiro sia dichiarato nel manoscritto che lo\n"
  "   eredita."),
 ("la mappatura (i)\u2013(xi) \u00e8 chiusa, la dichiarazione \u00e8 scrittura.",
  "la mappatura (i)\u2013(xi) \u00e8 chiusa, la dichiarazione \u00e8 scrittura. **\u2726 rev. 3.33:**\n"
  "    dichiarare anche la promozione del «3-bis» a Paper 3, davanti ai test sui sistematici DESI,\n"
  "    come riformulazione motivata dai risultati di risoluzione del Paper 1 (`canovaccio_paper3.md`\n"
  "    \u00a710; l'ordine dei *next steps* \u00e8 pubblico in M26 \u00a77 e nel Paper 1 \u00a79.4)."),
]

STATO = [
 ("aggiornato **22 settembre 2026**, sedicesima revisione", "aggiornato **23 settembre 2026**, diciassettesima revisione"),
 ("| (18 set) censimento a 75 record", "| (22 set) censimento a 75 record"),
 ("`origin/main` a **`a5fdabd`**, dieci commit nella sessione.",
  "`origin/main` a **`a5fdabd`**, dieci commit nella sessione.\n"
  "\n"
  "**Al 23 settembre (diciassettesima revisione):** registro **77 record** (`9e178837\u2026`, 651 850\n"
  "byte), `freeze_verify` **CLEAN 77/77** con `DOCUMENTED_AMENDMENTS = 77` (`a9a918c2\u2026`) \u00b7 commit\n"
  "`d8d64ef` su `origin/main` \u00b7 **la Fase 6 \u00e8 CHIUSA** (record 77): 6.4 per dichiarazione, 6.5 con\n"
  "`paper2_6_5_ritirati.md` (`517e7209\u2026`) contro il canovaccio del 24 luglio recuperato da una chat\n"
  "(`canovaccio_paper2_rev1.md`, `1152bcc9\u2026`), 6.6 con `canovaccio_paper5.md` recuperato\n"
  "(`796fbc82\u2026`); fedelt\u00e0 delle schede provata byte per byte su un gemello \u00b7 checklist **rev. 3.33**\n"
  "(`9d8aeda0\u2026`) \u00b7 le date del 22 corrette in checklist, budget, `modifiche_paper1.md` e \u00a70 \u00b7 in\n"
  "Fase 7: 6.0a (sedici voci), 6.2-iii, `gate_preinvio`, deposito Zenodo."),
 ("## 3. Il registro degli emendamenti \u2014 76 record", "## 3. Il registro degli emendamenti \u2014 77 record"),
 ("### Fase 6, record 61\u201376", "### Fase 6, record 61\u201377"),
 ("| **76** | **22 set 17:23** | **`6.2-vi`** |",
  "| **76** | **22 set 17:23** | **`6.2-vi`** |\n"
  "| **77** | **23 set 07:56** | **`6.4-6.5-6.6`** |"),
 ("> alla riga 5 del budget.",
  "> alla riga 5 del budget; il **77** chiude la Fase 6 \u2014 la 6.4 per dichiarazione, la 6.5 coi\n"
  "> ritirati contro il canovaccio del 24 luglio e la 6.6 con `canovaccio_paper5.md`, entrambi\n"
  "> recuperati dalle schede delle chat dopo un controllo di fedelt\u00e0 su un gemello \u2014 e registra\n"
  "> le date misurate della sessione del 22."),
 ("| **Z-4.2a** | **l'ensemble v2 non \u00e8 partito** |",
  "| ~~**Z-4.2a**~~ | ~~l'ensemble v2 non \u00e8 partito~~ **FATTO**: eseguito, Fase 4 decisa (record 58\u201359) |"),
 ("| **Z-P1** | **tredici voci per il Paper 1** \u2014 testo sostitutivo scritto, numeri verificati, nulla da decidere.",
  "| **Z-P1** | **sedici voci per il Paper 1** \u2014 tredici col testo sostitutivo scritto e i numeri verificati; P1-14 PRONTA; **P1-15 e P1-16 BLOCCATE** (17a revisione)."),
 ("| **X-P1-Tab12** | tre modifiche al Paper 1, in `modifiche_paper1.md` | Fase 7 | P1-1 e P1-3 PRONTE; **P1-2 BLOCCATA** sulla provenienza di +3.90/+0.20, che non esce da nessuna delle quattro restrizioni di step6; P1-4 facoltativa; P1-5 in attesa di 4.2a |",
  "| ~~**X-P1-Tab12**~~ | ~~tre modifiche al Paper 1~~ **assorbita in Z-P1**: P1-2 sbloccata (record 75), P1-5 misurata | Fase 7 | \u2014 |"),
 ("| **Z-consegna** | la consegna del 7 set porta la riga a *n*=100 | correzione | \u00a76, blocco «*n*=200»: mediana 3474.58, minimo 2417.18 |",
  "| **Z-consegna** | la consegna del 7 set porta la riga a *n*=100 | correzione | \u00a76, blocco «*n*=200»: mediana 3474.58, minimo 2417.18 |\n"
  "| **Z-ensemble-3-4** | quale ensemble per i Paper 3 e 4 | decisione | Il riferimento del Paper 2 resta v1 (11 set, record 59\u201360) e il programma presupponeva v2. Va dichiarato nella 0.1 del Paper 3, prima della sua pre-registrazione (record 77, voce B) |\n"
  "| **Z-rilascio-r50** | la citazione di `canovaccio_paper2.md` nel record 50 non compare nel censimento del rilascio | misura | 0 righe su 255 363 byte: pattern voluto o limite dell'estrattore (record 77, voce H) |\n"
  "| **Z-P1-curtosi** | la curtosi attribuita alla pesatura nel Paper 1? | lettura | Riga 11 della 6.5: se una frase del Paper 1 la attribuisce e P1-11 non la tocca, serve una voce in pi\u00f9 per la 6.0a |"),
 ("che ora ha una data misurata. Dal record 76 l'`utc` lo legge l'orologio.",
  "che ora ha una data misurata. Dal record 76 l'`utc` lo legge l'orologio.\n"
  "\n"
  "**Registrato dal record 77, voce F (23 settembre).** La correzione vive nel ledger, e la 17a\n"
  "revisione la porta nei documenti: checklist 3.33, budget, `modifiche_paper1.md` e \u00a70 di questo.\n"
  "I motivi dei 67 nel censimento dei registri restano come sono: lo strumento, ancorato dai record\n"
  "76 e 77, non si riscrive per una data."),
 ("| `paper2_patch_checklist_332.py` | checklist rev. 3.31 \u2192 3.32 | 6/6 |",
  "| `paper2_patch_checklist_332.py` | checklist rev. 3.31 \u2192 3.32 | 6/6 |\n"
  "| `paper2_patch_stato_16.py` | questo documento, 15\u00aa \u2192 16\u00aa revisione | 6/6 |\n"
  "| `paper2_append_amend77.py` | record 77: Fase 6 chiusa; ricontrolla documenti, ledger, git e albero | 8/8 |\n"
  "| `paper2_patch_revisione_23set.py` | checklist 3.33, questo documento alla 17\u00aa, date di budget e `modifiche_paper1.md` | 8/8 |"),
]

BUDGET = [
 ("**Correzione del 18 settembre (voce 6.2-vi, record 76)", "**Correzione del 22 settembre (voce 6.2-vi, record 76)"),
 ("(voce 6.2-v, 18 settembre 2026)", "(voce 6.2-v, 22 settembre 2026)"),
 ("(voce 6.2-vi, 18 settembre 2026)", "(voce 6.2-vi, 22 settembre 2026)"),
 ("(decisione del 18 settembre)", "(decisione del 22 settembre)"),
 ("chiuso il 18 settembre (voce 6.2-iv)", "chiuso il 22 settembre (voce 6.2-iv)"),
 ("chiuse il 18 settembre (voce 6.2-v, nota 10/11)", "chiuse il 22 settembre (voce 6.2-v, nota 10/11)"),
 ("riletta il 18 settembre (voce 6.2-vi, nota F)", "riletta il 22 settembre (voce 6.2-vi, nota F)"),
]

MODIFICHE = [
 ("### Verificato su file (18 settembre 2026, record 75)", "### Verificato su file (22 settembre 2026, record 75)"),
 ("*(Fino al 18 settembre questo punto chiedeva", "*(Fino al 22 settembre questo punto chiedeva"),
 ("| 18 set 2026 |", "| 22 set 2026 |"),
 ("**Da dove vengono i 2000** (18 settembre 2026, record 75)", "**Da dove vengono i 2000** (22 settembre 2026, record 75)"),
 ("nominati il 18 settembre):", "nominati il 22 settembre):"),
 ("**Il registro delle 60 coppie** (18 settembre 2026, record 76)", "**Il registro delle 60 coppie** (22 settembre 2026, record 76)"),
 ("Nata il 18 settembre 2026 dalla voce 6.2-vi", "Nata il 22 settembre 2026 dalla voce 6.2-vi"),
 ("| 11 set 2026, correzione | Snapshot",
  "| 23 set 2026 | Record 77: le date «18 settembre» di questo documento, scritte il 22, si leggono **22** e sono corrette qui. Nessun contenuto cambia |\n"
  "| 11 set 2026, correzione | Snapshot"),
]

FILE = {  # percorso -> (sha prima, sha dopo, fine riga, sostituzioni)
 "papers/paper2/checklist_paper2.md":   ("4b2b830acd82ec938ebe50b8ef18ef3ffdaf27204eb57d2b0d872627f10f7fbb", "9d8aeda07c5daf1fc90e9142464304842a17b49ec380b9ba801fe8615f0c87e5", "\n", CHECKLIST),
 "papers/paper2/paper2_stato.md":       ("18ec62b6500e21b1453fac938ae8743172bc67cbdfb924c483376e3d32fe65b5", "eadb4efcd92de81eb671ba43c892a11a23740e55330deeabcbf8d2403faa14e3", "\r\n", STATO),
 "papers/paper2/paper2_budget_5_1.md":  ("a5d60b1537e777d4c54ac1f55caf1a60b00d676d4785877ba9ac62985b45eea2", "97b59d0b3c89be7f55fd80809fa1fc5a5b3f96071d8764c6070eebc5b88dc95b", "\n", BUDGET),
 "papers/paper2/modifiche_paper1.md":   ("77849455d1d4f9fa46e61a3e3bb850daf1f763f140e22d486b5ecb8e03f141c1", "3f5a5b4e08e267232e104bfafa2989aa97d97ba8fd1ab2d019d362052d164f02", "\n", MODIFICHE),
}

# ---------------------------------------------------------------------------------------------
BOM = b"\xef\xbb\xbf"

def misura_eol(raw: bytes) -> str:
    crlf, lf = raw.count(b"\r\n"), raw.count(b"\n")
    if crlf and crlf == lf: return "\r\n"
    if not crlf and b"\r" not in raw: return "\n"
    raise ValueError(f"fine riga misti: {crlf} CRLF su {lf} LF")

def trasforma(raw: bytes, eol: str, sost: list, inversa=False) -> bytes:
    bom = raw.startswith(BOM)
    if misura_eol(raw) != eol: raise ValueError(f"fine riga misurata diversa da {eol!r}")
    t = raw[len(BOM) if bom else 0:].decode("utf-8")
    passi = [(b, a) for a, b in reversed(sost)] if inversa else sost
    for i, (a, b) in enumerate(passi):
        a2, b2 = a.replace("\n", eol), b.replace("\n", eol)
        k = t.count(a2)
        if k != 1: raise ValueError(f"sostituzione {i}: {k} occorrenze di «{a[:50]}»")
        t = t.replace(a2, b2)
    return (BOM if bom else b"") + t.encode("utf-8")

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def precondizioni() -> list:
    err = []
    for rel, (s, n) in PRECONDIZIONI.items():
        p = ROOT / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        raw = p.read_bytes()
        if sha(raw) != s or len(raw) != n: err.append(f"diverso dall'atteso: {rel}")
    r = subprocess.run(["git", "merge-base", "--is-ancestor", COMMIT_77, "HEAD"], cwd=ROOT)
    if r.returncode != 0: err.append(f"git: {COMMIT_77} non e' antenato di HEAD")
    return err

def prepara() -> dict:
    piano, err = {}, []
    for rel, (prima, dopo, eol, sost) in FILE.items():
        p = ROOT / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        raw = p.read_bytes(); s = sha(raw)
        if s == dopo: piano[rel] = None; continue
        if s != prima: err.append(f"{rel}: sha {s[:12]}..., ne' prima ne' dopo"); continue
        try:
            nuovo = trasforma(raw, eol, sost)
            if sha(nuovo) != dopo: err.append(f"{rel}: risultato {sha(nuovo)[:12]}..., atteso {dopo[:12]}..."); continue
            if sha(trasforma(nuovo, eol, sost, inversa=True)) != prima: err.append(f"{rel}: l'inversa non ridà il file"); continue
        except ValueError as e:
            err.append(f"{rel}: {e}"); continue
        piano[rel] = (raw, nuovo)
    if err:
        print("STOP:"); [print("  -", e) for e in err]; raise SystemExit(1)
    return piano

def dry_run(scrivi=False):
    err = precondizioni()
    if err:
        print("STOP, precondizioni:"); [print("  -", e) for e in err]; raise SystemExit(1)
    piano = prepara()
    for rel, v in piano.items():
        if v is None: print(f"{rel}: gia' all'ancora «dopo», non si tocca"); continue
        raw, nuovo = v
        print(f"{rel}: {sha(raw)[:12]}... {len(raw)} B -> {sha(nuovo)[:12]}... {len(nuovo)} B, "
              f"{len(FILE[rel][3])} sostituzioni, inversa OK")
    if not scrivi:
        print("[dry-run] niente scritto."); return
    LOGS.mkdir(exist_ok=True); ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for rel, v in piano.items():
        if v is None: continue
        raw, nuovo = v; p = ROOT / rel
        (LOGS / f"{p.name}.bak_{ts}").write_bytes(raw)
        tmp = p.with_name(p.name + ".tmp"); tmp.write_bytes(nuovo); os.replace(tmp, p)
        if sha(p.read_bytes()) != FILE[rel][1]: raise SystemExit(f"STOP: {rel} riletto non coincide")
        print(f"[apply] {rel}: scritto e riletto; backup logs\\{p.name}.bak_{ts}")

def verify():
    ok = True
    for rel, (prima, dopo, _, _) in FILE.items():
        s = sha((ROOT / rel).read_bytes())
        stato = "dopo" if s == dopo else ("prima" if s == prima else "ALTRO")
        ok &= stato == "dopo"; print(f"{rel}: {stato} ({s[:12]}...)")
    print("verify", "OK" if ok else "ANOMALIA"); sys.exit(0 if ok else 1)

def selftest():
    ok = 0
    lf = "a\nuno X due\nb\n".encode(); crlf = lf.replace(b"\n", b"\r\n")
    s = [("uno X", "uno Y\nriga nuova")]
    assert trasforma(lf, "\n", s) == b"a\nuno Y\nriga nuova due\nb\n"; ok += 1
    assert trasforma(crlf, "\r\n", s) == b"a\r\nuno Y\r\nriga nuova due\r\nb\r\n"; ok += 1
    assert trasforma(trasforma(crlf, "\r\n", s), "\r\n", s, inversa=True) == crlf; ok += 1
    for doppio in (b"X X\n", b"niente\n"):
        try: trasforma(doppio, "\n", [("X", "Y")]); raise AssertionError
        except ValueError: pass
    ok += 1
    try: trasforma(b"a\r\nb\n", "\n", s); raise AssertionError
    except ValueError: pass
    ok += 1
    assert trasforma(BOM + lf, "\n", s).startswith(BOM); ok += 1
    for rel, (prima, dopo, eol, sost) in FILE.items():
        assert len(prima) == 64 and len(dopo) == 64 and prima != dopo and all(a != b and "\r" not in a + b for a, b in sost)
    ok += 1
    date = [(a, b) for a, b in BUDGET + MODIFICHE if "18 set" in a]
    assert len(date) == 14 and all(b == a.replace("18 set", "22 set") for a, b in date); ok += 1
    print(f"selftest: {ok}/8 OK")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    c = ap.parse_args().cmd
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[c]()
