#!/usr/bin/env python3
"""
paper2_append_amend76.py  —  record 76 del ledger: chiusura della voce 6.2-vi

Un record, dieci voci (A–J): la correzione del record 50 §vii con il suo cancello
FALLITO e l'effetto misurato; il superamento del gate53; lo strumento della 6.1 alla
1.5 e i 67; i domini dei record 64 e 69; il registro della riga 5 del budget; la
catena di P1-9; i manifest e i dodici file non-JSON; i verdetti nei report; la lettura
di erosion_restrict; due correzioni sui record 75 e sulla costante del cancello.

Il dry-run e l'apply RIFIUTANO se: il ledger non e' all'ancora; un file ancorato ha
cambiato sha; uno qualunque dei numeri del record non si riproduce dai file sul disco.

Uso:
  python src\\paper2_append_amend76.py selftest
  python src\\paper2_append_amend76.py dry-run
  python src\\paper2_append_amend76.py apply
  python src\\paper2_append_amend76.py verify
"""
import argparse, hashlib, json, math, statistics as st, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "src" / "paper2_v1_amendments.jsonl"
LEDGER_SHA = "8fbfb58ed1e194cc53450390914bc5484b696645cc9b3064e6a06fb0add60e8d"
LEDGER_RIGHE = 75
REF_FILE_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REF_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

ANCORE = {  # percorso relativo -> sha256
 "results/paper1/per_mock_NGC_erosion_restrict.jsonl": "94456c6f371895bf18e7c25d5abf81ddea227def9be755f80fb821e39421078e",
 "results/paper1/per_mock_SGC_erosion_restrict.jsonl": "75a55b534f439bd1004460a341021d1028a6ca05f27f867448376c91a13546f7",
 "results/paper2/fase3_mock.jsonl": "937c5bad084d54fa692d54585733fc0c91e29b4d196a7513f02ca6ac31894556",
 "results/paper1/n7_nfw_NGC.jsonl": "efe9ee50fd7ad9047bae0bf9112b7d496c03618c517a50c8c181991dfe1f4e2b",
 "results/paper1/n6_fkp_NGC.jsonl": "78fae4e12bea8e9d10bfbd45ad7e225f846e9de9cdc88749e06a352216d4a10f",
 "results/paper2/gate53.jsonl": "8508336c6a1e63c604559336639da01ed00bf0fde14a52952f800c58c1031f2b",
 "src/paper2_censimento_registri.py": "738c309c3f22344e22cddbad3797c140bffafa627101e2303c0d2af08e1a7681",
 "logs/censimento_v15.jsonl": "d285551e2075e6bdd7e0398576e51a1888c30b406149bc73d4147639570dd5f1",
 "logs/censimento_v14.jsonl": "b1d8192deacc589cbad0464bdf723f215d4df2d9d0633dfcb83b6ad5be2fbedd",
 "logs/inventario_6_2vi.json": "5985663e8a2db791190f3ed079e62ab33cd9bd9a3ea42e4a6c1fa879090100e1",
}

# numeri che il record dichiara, riverificati sui file prima dell'append
ATTESI = {
 "n7": {"n": 40, "idx": [200, 239], "gate_ok": 40, "media": -56.475, "sem": 23.530857740967306, "z": -2.400040007962686,
        "riduzione_sd": 0.46655, "riduzione_var_braccio": 0.715, "riduzione_var_non_appaiata": 0.862},
 "n6": {"n": 60, "idx": [200, 259], "gate_ok": 60, "media": -77.96666666666667, "sem": 8.000634391042606},
 "unione": {"NGC": {"passate": 3, "celle_unione": 22, "celle_ultimo": 4, "conflitti": 0},
            "SGC": {"passate": 2, "celle_unione": 13, "celle_ultimo": 4, "conflitti": 0}},
 "giunzione": {"NGC": {"diversi": [[1, -1], [91, 1], [135, -1]], "effetto": -0.005, "mezza_sem": 12.81},
               "SGC": {"diversi": [[24, -11], [29, 1], [81, 86], [111, 1]], "effetto": 0.385, "mezza_sem": 7.78}},
 "gate53": [["NGC", False], ["NGC", True], ["SGC", True]],
 "censimento_v15": {"n_file": 121, "n_righe": 78075, "n_file_in_scopo": 53, "n_righe_in_scopo": 67915},
}

def costruisci_record(utc: str) -> dict:
    return {
 "type": "protocol",
 "utc": utc,
 "item": "6.2-vi",
 "key": "chiusura_della_6_2_vi_record_50_vii_corretto_gate53_censimento_1_5_riga5_del_budget",
 "document": "papers/paper2/checklist_paper2.md (6.2-vi); papers/paper2/paper2_budget_5_1.md (nota 5/6); papers/paper2/paper2_stato.md",
 "reference_file": "src/paper2_v1_reference.json",
 "reference_file_sha256": REF_FILE_SHA,
 "reference_self_sha256": REF_SELF_SHA,
 "numbering_rule": "The number of an amendment is its 1-based POSITION in this file. This is record 76.",
 "amends_records": [50, 58, 68, 75],
 "old_value": {
  "record_50_vii": "per_mock_*_erosion_restrict carry cells R5_er0, R5_er2, R5_er3 - there is NO er1; k=1 per realisation exists only in fase3_mock.jsonl, so P requires a JOIN across two registers",
  "record_58_e_stato": "ripetono la giunzione del record 50 §vii come premessa della soglia del 4.3b a n=200",
  "censimento_6_1": "67 registri non classificati, descritti come «Paper 1, smoke, item»; gate53 e gate53_margini «gate senza verdetto», frazione 0.0; gate25 in DISCORDANZA lasciata dal record 68; uscita 1",
  "nota_5_6_del_budget": "riga 5 (NFW) ASSENTE su entrambi i metri; la 6.2-i chiusa su quella base",
 },
 "new_value": {
  "A_record_50_vii_e_falso": {
   "fatto": "R5_er1 esiste per 200 mock su 200 in entrambi gli emisferi, scritto dalla passata del 26 luglio (NGC 12:25, SGC 12:22). Il record 23, due settimane prima del 50, usava gia' «the frozen R5_er0/R5_er1 values». Il 50 ha letto la PRIMA passata, che porta R5_er0, er2, er3.",
   "passate": {"NGC": ["2026-07-24T01:34 R5,R20,R30 x er0,2,3", "2026-07-24T06:12 R10,R12,R15,R17 x er0,2,3", "2026-07-26T12:25 R5 x er0,1,2,3"],
               "SGC": ["2026-07-24T06:25 R5,R10,R15,R20 x er0,2,3", "2026-07-26T12:22 R5 x er0,1,2,3"]},
   "cancello_dichiarato_prima": "tolleranza ZERO fra fase3_mock points.FID.N_H1_k1 e R5_er1, 400 valori",
   "esito": "FALLITO. Diversi 3 su 200 in NGC (idx 1: -1; 91: +1; 135: -1) e 4 su 200 in SGC (idx 24: -11; 29: +1; 81: +86; 111: +1).",
   "effetto_sulla_media": "NGC -0.005, SGC +0.385 generatori, contro mezza SEM dell'ensemble 12.81 e 7.78 (criterio del record 36): 2 500 e 20 volte sotto. Nessun verdetto poggia sulla giunzione a n=200: la soglia del 4.3b e' stata ricalcolata su v2 a n=2000 da un registro solo (record 58-59).",
   "fatto_nuovo": "N_H1 a k=1 per realizzazione esiste in DUE registri con due implementazioni (runner di Fase 3, script di erosione del Paper 1) che non coincidono in 7 mock su 400. Gli scarti di +-1 hanno la forma dei pareggi gia' noti; il +86 di SGC idx 81 NON e' spiegato. Dichiarato, non riparato.",
   "fallito_non_reinterpretato": "Il cancello a tolleranza zero resta fallito. L'effetto sulla media e' una seconda misura, dichiarata come tale, non una riformulazione del primo cancello."},
  "B_superamento_del_gate53": {
   "record": {"1": "NGC 2026-08-31T12:48 pass=false: tre scarti relativi 4.05e-05, 4.05e-05, 6.25e-05, dall'ingresso esatto sd_draw 157.0098 contro gli attesi costruiti sul pubblicato 157.0",
              "2": "NGC 2026-08-31T12:50 pass=true: stesso calcolo con l'ingresso pubblicato; gli esatti restano in *_exact; residuo 1710.49 identico",
              "3": "SGC 2026-09-14T14:09 pass=true"},
   "verdetto": {"NGC": "record 2, che SUPERA il record 1", "SGC": "record 3"},
   "perche_qui": "La convenzione `supersedes` dei compD non e' stata applicata; il registro e' append-only e chiuso, quindi non si riscrive: la marcatura e' questo record, come il record 68 chiedeva."},
  "C_censimento_1_5": {
   "strumento": {"path": "src/paper2_censimento_registri.py", "sha256": ANCORE["src/paper2_censimento_registri.py"], "byte": 105803,
                 "patcher": "src/paper2_patch_censimento_15.py", "commit": "431d3a2", "selftest": "162/162 (150 alla 1.4)"},
   "difetti_corretti": ["il segnale di verdetto guardava solo il primo livello e non conosceva `pass`: gate53 e gate53_margini risultavano «senza verdetto»; ora fino a 3 livelli, nome per uguaglianza",
                        "un gate dichiarato si confrontava con una classe misurata che per costruzione non puo' essere `gate`: DISCORDANZA permanente di gate25 (record 68). Ora si giudica dal verdetto, e gate_senza_verdetto pesa sull'uscita",
                        "il controllo 20 del selftest attende GATE_SENZA_VERDETTO invece di DISCORDANZA: stesso principio, il file non passa"],
   "i_67": "dichiarati per nome esatto, fuori scopo 6.1 perche' chiusi (fasi 3-5 chiuse, record 59-60; revisione del Paper 1 chiusa); append storico verificato dalla baseline per tutti; 34 citati, 33 non citati al 18 set, la citazione nel motivo. Non erano «Paper 1, smoke, item»: almeno diciotto sono registri del Paper 2 di Fase 3 e 5.",
   "esito": {"log": "censimento_v15.jsonl, nella cartella dei log di lavoro (fuori dal rilascio, decisione del 16 set)",
             "sha256": ANCORE["logs/censimento_v15.jsonl"], "file": 121, "righe": 78075,
             "in_scopo": "53 file, 67 915 righe", "non_classificati": 0, "discordanze": 0, "gate_senza_verdetto": 0,
             "baseline": "121 coperti, 0 falliti, contro censimento_v14.jsonl (log di lavoro, sha " + ANCORE["logs/censimento_v14.jsonl"] + ")",
             "cancello_di_riproduzione": "PASS", "uscita": 0}},
  "D_domini_dei_record_64_e_69": {
   "natura": "src/*.py nel record 64 («a read-only grep over src/*.py») ed ensemble_v1_manifest_*.jsonl nel record 69 («cercando i tre nomi in …») sono DOMINI DI RICERCA, non citazioni di file",
   "ancora": {"commit": "3e43e38", "src_tree": "c0c7f75e96c6a6fd24130023ab5260e4f906bac6", "file_py": 279,
              "manifest_blob": {"diagrams": "1ed21fd1ce8baaaf0e8ae501dd74ca6da20712a3", "features": "21209c882bd7fab3d1833d21ef4c55cd33a178b8",
                                "fields": "f27f2aa8c5eefb2e79c626edeb8b48c115e247aa", "records": "3f1d86cbb338234e932b96a99115abc480ebce79",
                                "superseded": "f27c2c526abd0359fabd6f59fc29da8ccf4d9f95"}},
   "limite": "3e43e38 porta i record 64-69 insieme: ancora lo stato committato piu' vicino, non l'albero di lavoro del 13 settembre in cui il grep del 64 e' stato fatto"},
  "E_riga_5_del_budget_ha_un_registro": {
   "registro": {"path": "results/paper1/n7_nfw_NGC.jsonl", "sha256": ANCORE["results/paper1/n7_nfw_NGC.jsonl"], "byte": 5690,
                "record": 40, "idx": "200-239", "gate_ok": "40/40"},
   "riprodotto": "Delta = media(nfw - uniform) = -56.475; SEM appaiata = sd(ddof=1)/sqrt(40) = 23.531; z = -2.400. Budget e Paper 1 §7.1: -56.5 +- 23.5, 2.4 sigma.",
   "correzione": "la nota 5/6 del budget e la chiusura della 6.2-i dicevano la riga 5 ASSENTE su due metri: e' falso. La ricerca per valore del 17 set cercava tre valori sullo stesso record, e un registro per realizzazione non contiene mai l'aggregato: cieca per costruzione a questa specie di fonte. La riga 6 resta senza registro.",
   "per_il_paper_1": "«the pairing cancels 47 per cent of the variance»: il 47 si riproduce come 1 - sd(delta)/sd(uniform) = 46.7 %, cioe' sulla deviazione standard; sulla varianza l'appaiamento toglie il 71.5 % rispetto a un braccio e l'86.2 % rispetto alla differenza non appaiata. Voce candidata per modifiche_paper1.md."},
  "F_catena_di_P1_9": {"registro": {"path": "results/paper1/n6_fkp_NGC.jsonl", "sha256": ANCORE["results/paper1/n6_fkp_NGC.jsonl"],
                                   "record": 60, "idx": "200-259", "gate_ok": "60/60"},
                       "riprodotto": "Delta = -77.967, SEM = 8.001: il -78.0 +- 8.0 del Paper 1 §7.2 e di M26 R1, gia' citato dal record 56. P1-9 ha ora le due estremita' su file."},
  "G_manifest_e_file_non_json": {
   "phase_manifest": "13 file results/phase*_manifest*.json, 8 contenuti distinti: sei byte-identici (919249c07f70…) sotto sei nomi, phase_r51_manifest e _v3 identici. Tutti tracciati. phase0_data_manifest citato dai record 42-43; gli altri dodici, di epoca M26, non citati da record ne' documenti: nessun numero del Paper 2 vi poggia.",
   "review_non_json": "i dodici results/phase*_review*.json non sono JSON: primi byte ```, CAU, Que, **R, cioe' testo e markdown con estensione .json. Epoca M26, tracciati, non citati. Dichiarati, non rinominati: sono storia di M26 dentro il rilascio."},
  "H_verdetti_nei_report": {
   "popolazione": "113 file con chiavi di verdetto (token esatto); del Paper 2: 44, di cui 19 citati per nome, 8 per graffe, 2 per famiglia, 15 da nessuno",
   "i_15": {"smoke": 6, "falsi_positivi_dell_inventario": ["fase3_surrogato_pass1.jsonl (mask_pass)", "item13a.jsonl (F_ap_passed)"],
            "verdetti_riferiti_a_parole_senza_il_file": ["cammini_desi_NGC.json", "cammini_desi_SGC.json", "fase3_intersezione_verdetto.jsonl",
                                                         "p10_definizione_NGC.json", "p10_definizione_SGC.json", "pareggi_NGC.json", "pareggi_NGC_mock1999.json"]},
   "rimedio": "documentale: il nome del file accanto al verdetto, nella revisione unica di checklist, stato e modifiche_paper1",
   "fuori_dal_paper_2": "48 file di M26, 16 del Paper 1, 2 di revision con verdetti non citati: hanno la loro storia; il Paper 2 non vi poggia"},
  "I_lettura_di_erosion_restrict": {
   "unione": "NGC 3 passate, 22 celle per mock; SGC 2 passate, 13. L'ultimo record ne porta 4. Celle ripetute fra passate: 600 per emisfero, valore diverso 0.",
   "regola": "si legge SOLO per unione. La domanda del record 68 — quale record e' la fonte di quale numero — ha risposta univoca: ogni cella ha un solo valore in tutte le passate, quindi la fonte e' l'unione."},
  "J_due_correzioni_di_contabilita": {
   "utc_del_record_75": "il record 75 porta utc 2026-09-18T00:00:00+00:00 scritto a mano nell'appender, non l'ora dell'append (commit 50a8707). Da questo record l'utc e' letto dall'orologio al momento dell'append.",
   "DOCUMENTED_AMENDMENTS": "dopo il record 75 la costante di paper2_freeze_verify.py e' rimasta a 74: freeze_verify del 18 set DISCREPANCY su «disco == documentati», 75 contro 74, previsto e misurato. Si porta a 76 subito dopo questo record, con paper2_patch_documented_amendments.py --da 74 --a 76."},
 },
 "reason": "Chiusura della voce 6.2-vi. Il censimento della colonna fonte del budget e dei registri ha trovato un'affermazione falsa nel ledger (record 50 §vii), un'affermazione falsa nei documenti (riga 5 assente), un superamento non marcato (gate53), tre difetti dello strumento della 6.1 e 67 registri da classificare. Le correzioni si registrano, non si cancellano; il cancello a tolleranza zero fallito resta fallito.",
 "rules": {
  "marker": "emendamento-76-chiusura-6-2-vi",
  "what_this_does_not_do": "Non modifica alcun valore congelato, non riapre alcun verdetto depositato, non tocca il reference. Il registro gate53.jsonl non si riscrive.",
  "evidence_files_rechecked_at_append": sorted(k for k in ANCORE if not k.startswith("logs/")),
  "working_logs_by_digest": {k.split("/")[-1]: v for k, v in sorted(ANCORE.items()) if k.startswith("logs/")}},
 "evidence": "Ancore sha256 dei file in rules.evidence_files_rechecked_at_append e dei log di lavoro in rules.working_logs_by_digest, riverificate dall'appender prima dell'append, insieme a ogni numero di new_value A, B, C, E, F e I ricalcolato dai file. Inventario: src/paper2_inventario_6_2vi.py (commit 411bc6f). I log di lavoro stanno fuori dal rilascio e il ledger li ancora per digest, non per percorso.",
    }

# ── ricalcolo dai file ─────────────────────────────────────────────────────
def leggi_jsonl(p): return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def ricalcola(base: Path) -> list:
    err = []
    def vicino(a, b, tol, nome):
        if abs(a - b) > tol: err.append(f"{nome}: ricalcolato {a!r}, atteso {b!r}")
    # E, F: test appaiati
    for chiave, fn, a, b in (("n7", "results/paper1/n7_nfw_NGC.jsonl", "uniform", "nfw"),
                             ("n6", "results/paper1/n6_fkp_NGC.jsonl", "unit", "fkp")):
        R = leggi_jsonl(base / fn); x = ATTESI[chiave]
        d = [r[b] - r[a] for r in R]; m = st.mean(d); sem = st.stdev(d) / math.sqrt(len(d))
        if len(R) != x["n"] or [R[0]["idx"], R[-1]["idx"]] != x["idx"] or sum(r["gate_ok"] for r in R) != x["gate_ok"]:
            err.append(f"{chiave}: n, idx o gate_ok diversi")
        vicino(m, x["media"], 1e-9, f"{chiave} media"); vicino(sem, x["sem"], 1e-9, f"{chiave} SEM")
        if "riduzione_sd" in x:
            A_ = [r[a] for r in R]; B_ = [r[b] for r in R]
            vicino(1 - st.stdev(d) / st.stdev(A_), x["riduzione_sd"], 5e-5, f"{chiave} riduzione della sd")
            vicino(1 - st.variance(d) / st.variance(A_), x["riduzione_var_braccio"], 5e-4, f"{chiave} riduzione della varianza, un braccio")
            vicino(1 - st.variance(d) / (st.variance(A_) + st.variance(B_)), x["riduzione_var_non_appaiata"], 5e-4,
                   f"{chiave} riduzione della varianza, non appaiata")
    # I, A: unione e giunzione
    fid = {}
    for r in leggi_jsonl(base / "results/paper2/fase3_mock.jsonl"):
        if r.get("smoke"): continue
        p = r["points"].get("FID")
        if p and "N_H1_k1" in p: fid[(r["region"], r["index"])] = p["N_H1_k1"]
    for reg in ("NGC", "SGC"):
        E = leggi_jsonl(base / f"results/paper1/per_mock_{reg}_erosion_restrict.jsonl")
        per = {}
        for r in E: per.setdefault(r["key"], []).append(r["cells"])
        passate = {len(v) for v in per.values()}
        unione = {k: {} for k in per}; conflitti = 0
        for k, lista in per.items():
            for celle in lista:
                for n, v in celle.items():
                    if n in unione[k] and unione[k][n] != v: conflitti += 1
                    unione[k][n] = v
        x = ATTESI["unione"][reg]
        if passate != {x["passate"]} or {len(u) for u in unione.values()} != {x["celle_unione"]} \
           or {len(v[-1]) for v in per.values()} != {x["celle_ultimo"]} or conflitti != x["conflitti"]:
            err.append(f"unione {reg}: passate {passate}, conflitti {conflitti}")
        er1 = {int(k.split("_")[1]): u["R5_er1"]["N_H1"] for k, u in unione.items() if "R5_er1" in u}
        if len(er1) != 200: err.append(f"{reg}: R5_er1 su {len(er1)} mock, attesi 200")
        idx = sorted(er1); d = [fid[(reg, i)] - er1[i] for i in idx]
        diversi = [[i, int(fid[(reg, i)] - er1[i])] for i in idx if fid[(reg, i)] != er1[i]]
        y = ATTESI["giunzione"][reg]
        if diversi != y["diversi"]: err.append(f"giunzione {reg}: {diversi}")
        vicino(st.mean(d), y["effetto"], 5e-4, f"effetto {reg}")
        vicino(st.stdev(list(er1.values())) / math.sqrt(200) / 2, y["mezza_sem"], 5e-3, f"mezza SEM {reg}")
    # B: gate53
    G = leggi_jsonl(base / "results/paper2/gate53.jsonl")
    if [[g["region"], g["pass"]] for g in G] != ATTESI["gate53"]: err.append("gate53: record diversi dall'atteso")
    # C: censimento v15
    som = leggi_jsonl(base / "logs/censimento_v15.jsonl")[-1]
    for k, v in ATTESI["censimento_v15"].items():
        if som.get(k) != v: err.append(f"censimento v15 {k}: {som.get(k)} contro {v}")
    for k in ("non_classificati", "discordanze_classe", "gate_senza_verdetto", "in_scopo_con_difetti"):
        if som.get(k): err.append(f"censimento v15 {k} non vuoto")
    if som["baseline"]["falliti"] or som["baseline"]["file_coperti"] != 121: err.append("censimento v15: baseline")
    return err

def controlla_ancore(base: Path) -> list:
    err = []
    for rel, s in ANCORE.items():
        p = base / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != s: err.append(f"sha cambiato: {rel}")
    return err

def ledger_ok():
    raw = LEDGER.read_bytes()
    righe = [l for l in raw.decode("utf-8").splitlines() if l.strip()]
    return hashlib.sha256(raw).hexdigest(), len(righe)

def selftest():
    ok = 0
    r = costruisci_record("2026-01-01T00:00:00+00:00")
    s = json.dumps(r, ensure_ascii=False, separators=(",", ":")); assert json.loads(s) == r; ok += 1
    assert r["numbering_rule"].endswith("record 76."); ok += 1
    g = ATTESI["giunzione"]
    assert abs(g["NGC"]["effetto"]) * 2500 < g["NGC"]["mezza_sem"] * 1.05 and g["SGC"]["effetto"] * 20 < g["SGC"]["mezza_sem"]; ok += 1
    x = ATTESI["n7"]; assert abs(x["media"] / x["sem"] - x["z"]) < 1e-12 and round(x["media"], 1) == -56.5 and round(x["sem"], 1) == 23.5; ok += 1
    y = ATTESI["n6"]; assert round(y["media"], 1) == -78.0 and round(y["sem"], 1) == 8.0; ok += 1
    assert abs(195.16018047776708 / 195.16807545489525 - 1 + 4.05e-5) < 1e-6 and abs(157.009813810007 / 157.0 - 1 - 6.25e-5) < 1e-6; ok += 1
    assert "*" not in json.dumps(r["new_value"]["E_riga_5_del_budget_ha_un_registro"]["registro"]); ok += 1
    print(f"selftest: {ok}/7 OK")

def dry_run(scrivi=False):
    sha, n = ledger_ok()
    if sha != LEDGER_SHA or n != LEDGER_RIGHE:
        raise SystemExit(f"STOP: ledger {sha[:12]}… {n} righe, atteso {LEDGER_SHA[:12]}… {LEDGER_RIGHE}")
    err = controlla_ancore(ROOT)
    if not err:
        err = ricalcola(ROOT)
    if err:
        print("STOP:"); [print("  -", e) for e in err]; raise SystemExit(1)
    utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    riga = json.dumps(costruisci_record(utc), ensure_ascii=False, separators=(",", ":"))
    print(f"ledger all'ancora ({LEDGER_SHA[:12]}…, {LEDGER_RIGHE} righe); {len(ANCORE)} ancore coincidono; ogni numero si riproduce dai file")
    print(f"record 76: {len(riga.encode())} byte, utc {utc}")
    if not scrivi:
        print("  nessuna modifica scritta"); return
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(riga + "\n")
    sha2, n2 = ledger_ok()
    print(f"[apply] appeso: ledger {n2} righe, sha {sha2}")

def verify():
    sha, n = ledger_ok()
    ultimo = json.loads([l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()][-1])
    ok = n == LEDGER_RIGHE + 1 and ultimo["numbering_rule"].endswith("record 76.") and ultimo["item"] == "6.2-vi"
    print(f"verify {'OK' if ok else 'ANOMALIA'}: {n} righe, sha {sha}; ultimo: item {ultimo['item']}, utc {ultimo['utc']}")
    if not ok: sys.exit(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    c = ap.parse_args().cmd
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[c]()
