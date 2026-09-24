#!/usr/bin/env python3
"""
paper2_append_amend78.py  -  record 78 del ledger: le misure della Fase 7

Nove voci (A-I):
  A  7.10  il +86 di SGC idx 81 (record 76 §A) e' una divergenza fra catene, gia' a k = 0
  B  3.2   lo scarto SGC di fase3_mock attribuito al «rumore di pareggio»: sono due mock
  C  7.11  la riga 6 del budget ha un registro, e non misura un cono di luce
  D  7.12  il «34 volte» del budget e' un artefatto di cancellazione; previsione sul clipping FALSIFICATA
  E  7.3   la limitazione (ii) riguarda w_a, che nwLH non varia: resta aperta
  F  D8    il fattore scatola / cut-sky: ~22, banda da N = 3, due convenzioni
  G  processo: un verdetto scritto e mai letto; un parametro cambiato fuori dal record
  H  7.13  la mappa dei terminatori del ledger
  I  per la revisione documentale

Differenze dall'appender del 77, per la regola 9 della consegna del 23 set:
  - il terminatore si EREDITA dall'ultima riga (term = CRLF se il file finisce in CRLF, altrimenti LF),
    e si scrive in binario riga + term;
  - dopo l'append i primi len(raw) byte devono avere ancora lo sha di prima, e il file deve essere
    lungo esattamente len(raw) + len(riga) + len(term);
  - lo sha del reference si rimisura;
  - ogni percorso che il record nomina e' controllato: sotto results/ e src/ deve essere tracciato in
    git; sotto papers/ e logs/ deve essere fra quelli che hanno gia' un'eccezione del rilascio
    (regola 3); sotto data/ non ne sono ammessi. I log di lavoro si citano per nome e digest.

Ogni numero del record si RICALCOLA dai registri prima dell'append; il dry-run rifiuta se uno solo
non si riproduce. Gli sha dei registri si misurano all'append e si scrivono nel record.

Uso:
  python src\\paper2_append_amend78.py selftest
  python src\\paper2_append_amend78.py dry-run
  python src\\paper2_append_amend78.py apply
  python src\\paper2_append_amend78.py verify
"""
import argparse, hashlib, json, math, os, re, statistics, subprocess, sys, tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "src" / "paper2_v1_amendments.jsonl"
LEDGER_SHA = "9e178837aca9e56a16cf006e3ffe6e25b424ecca2cf94bf18dc40ec05982a923"
LEDGER_RIGHE = 77
LEDGER_BYTE = 651850
REF_FILE = ROOT / "src" / "paper2_v1_reference.json"
REF_FILE_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REF_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DOCUMENTI = {  # nome -> (percorso relativo, sha256, byte): ancorati per digest, fuori dal rilascio
 "checklist_paper2.md":            ("papers/paper2/checklist_paper2.md", "325602227db36512532df562e4901efc22d7b854010bec20913bb6e7328d7391", 269517),
 "paper2_stato.md":                ("papers/paper2/paper2_stato.md", "9d5014c43f58c00277c2845bb1536a80070b9cd7a87052459c2914b69315f40e", 109907),
 "paper2_budget_5_1.md":           ("papers/paper2/paper2_budget_5_1.md", "97b59d0b3c89be7f55fd80809fa1fc5a5b3f96071d8764c6070eebc5b88dc95b", 27802),
 "modifiche_paper1.md":            ("papers/paper2/modifiche_paper1.md", "2425045c373ed22c04be649835814419cad3306dc5c3d442fc3b47fd89b0600f", 83564),
 "canovaccio_paper2.md":           ("papers/paper2/canovaccio_paper2.md", "7cbc0877ebcd4b1b0ac0ed61262dd204667a241f09715b0441d7dff30fbfa1db", 20518),
 "canovaccio_4_paper_followup.md": ("papers/paper2/canovaccio_4_paper_followup.md", "cc9b0fa8542ff3604a0ac8cb7315c52423e2ef964fa24a243ca2db05c3cb8b95", 20503),
}

REGISTRI = {  # etichetta -> percorso relativo, tutti tracciati in git; sha e byte misurati all'append
 "fase3_mock":        "results/paper2/fase3_mock.jsonl",
 "eros_NGC":          "results/paper1/per_mock_NGC_erosion_restrict.jsonl",
 "eros_SGC":          "results/paper1/per_mock_SGC_erosion_restrict.jsonl",
 "canon_NGC":         "results/paper1/per_mock_NGC_R5.jsonl",
 "canon_SGC":         "results/paper1/per_mock_SGC_R5.jsonl",
 "v2_NGC":            "results/paper2/ensemble_v2_NGC.jsonl",
 "v2_SGC":            "results/paper2/ensemble_v2_SGC.jsonl",
 "v2_sommario_NGC":   "results/paper2/ensemble_v2_NGC_sommario.jsonl",
 "v2_sommario_SGC":   "results/paper2/ensemble_v2_SGC_sommario.jsonl",
 "phase9":            "results/phase9_growth_mismatch.json",
 "pilota_scatola":    "results/paper1/rev_v3b_pilot_box_report.json",
 "compD_NGC":         "results/paper2/compD_NGC.jsonl",
}
NWLH_PARAMS = ROOT / "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt"

# Percorsi sotto cartelle escluse che hanno GIA' un'eccezione del rilascio (record 76 e 77, censimento 77c PULITO)
ESCLUSI_AMMESSI = {"papers/paper2/checklist_paper2.md", "papers/paper2/paper2_stato.md", "papers/paper2/paper2_budget_5_1.md"}

# -- attesi (misurati il 23 set in chat; l'appender li riproduce o si ferma) ----------------------
ATTESI_F3 = {  # fase3_mock produzione (FID) contro erosione del Paper 1
 "diversi":   {"NGC": [4, 3, 3, 2], "SGC": [6, 4, 3, 3]},
 "effetto":   {"NGC": [0.0, -0.005, -0.005, -0.01], "SGC": [0.825, 0.385, 0.375, -0.115]},
 "non_pareggi": {"NGC": [], "SGC": [24, 81]},  # |scarto| > 3, a ogni livello
 "SGC_81": [69, 86, 60, 14], "SGC_24": [92, -11, 14, -38],
 "NGC_k1": {1: -1, 91: 1, 135: -1},           # il «3 su 200» del record 76, riprodotto sulla sola produzione
}
ATTESI_STAB = {"falsi_produzione": [("SGC", 24), ("SGC", 24), ("SGC", 81), ("SGC", 81)], "max_dnu": {24: 13.68, 81: 13.67}}
ATTESI_SMOKE = {"produzione": {0: 218292, 1: 217455, 2: 217731}, "smoke_3set": {0: 218235, 1: 217587, 2: 217625}}
ATTESI_V2 = {
 "NGC": {"indici": 2000, "diversi": 60, "oltre_3": 23, "somma": -17, "somma_abs": 1927,
         "tavola": {"oltre3_clip": 14, "oltre3_noclip": 9, "entro3_clip": 1157, "entro3_noclip": 820}},
 "SGC": {"indici": 2000, "diversi": 28, "oltre_3": 14, "somma": 536, "somma_abs": 1468,
         "tavola": {"oltre3_clip": 6, "oltre3_noclip": 8, "entro3_clip": 520, "entro3_noclip": 1466}},
 "SGC_24": (92, 2), "SGC_81": (69, 0),
}
ATTESI_PHASE9 = {"growth_rate_per_unit_z": -53.27, "growth_rate_sem": 112.04, "k_pairs": 30,
                 "z_eff_reference": 0.25, "fraction_of_deficit_reference": -0.00185, "commit": "684d1f3"}
ATTESI_D8 = {"scatola_voxel": 0.1530, "scatola_fisica": 0.1602, "canon_media": 35436.686, "canon_sd": 312.989,
             "attenuation": 0.835463, "fattori": {"voxel_totale": 17.32, "fisica_totale": 18.13,
                                                  "voxel_cosmologia": 20.73, "fisica_cosmologia": 21.71},
             "banda68_fisica_cosmologia": (16.03, 51.98)}
MAPPA_TERMINATORI = [("CRLF", 1, 7), ("LF", 8, 11), ("CRLF", 12, 12), ("LF", 13, 14), ("CRLF", 15, 75), ("LF", 76, 77)]

FRASI_VECCHIE = {  # nome del documento (o «record 76») -> frase, cercata a spazi normalizzati, una volta sola
 "record 76": "il +86 di SGC idx 81 NON e' spiegato",
 "checklist_paper2.md": "In SGC lo scarto è +0.825 e +0.385, quarantacinque volte più grande: dentro il rumore di pareggio dichiarato (3 generatori)",
 "paper2_budget_5_1.md": "L'SGC scarta circa **trentaquattro volte** più del NGC",
 "paper2_budget_5_1.md#riga6": "| 6 | snapshot contro lightcone | −53 ± 112 per unità di *z*, Δ*z* ≈ 0.25 | M26 §7 (vi); Paper 1 Tab. 8 |",
 "canovaccio_4_paper_followup.md": "| (ii) | *w*_a ≠ 0 | aperta | **Paper 2**, Componente D — *come limite, non come misura* |",
 "canovaccio_paper2.md": "un fattore ~17 di soppressione",
}

# -- funzioni pure (selftest) ---------------------------------------------------------------------
def norm(s: str) -> str: return re.sub(r"\s+", " ", s)

def terminatore(raw: bytes) -> bytes:
    if not raw.endswith(b"\n"): raise ValueError("il ledger non finisce con un a capo")
    return b"\r\n" if raw.endswith(b"\r\n") else b"\n"

def mappa_terminatori(raw: bytes) -> list:
    """[(tipo, da, a)] per record 1-based; rifiuta righe vuote e CR fuori da CRLF."""
    if raw.count(b"\r") != raw.count(b"\r\n"): raise ValueError("CR isolati")
    parti = raw.split(b"\n")
    if parti[-1] != b"": raise ValueError("ultima riga senza a capo")
    tipi = []
    for i, p in enumerate(parti[:-1], 1):
        if not p.rstrip(b"\r").strip(): raise ValueError(f"riga {i} vuota")
        tipi.append("CRLF" if p.endswith(b"\r") else "LF")
    out = []
    for i, t in enumerate(tipi, 1):
        if out and out[-1][0] == t and out[-1][2] == i - 1: out[-1] = (t, out[-1][1], i)
        else: out.append((t, i, i))
    return out

def appendi(path: Path, riga: str) -> tuple:
    """Append binario col terminatore ereditato; verifica prefisso e lunghezza. Ritorna (sha, byte, term)."""
    raw = path.read_bytes()
    term = terminatore(raw)
    b = riga.encode("utf-8")
    if b"\n" in b or b"\r" in b: raise ValueError("la riga contiene un a capo")
    with path.open("ab") as f:
        f.write(b + term); f.flush(); os.fsync(f.fileno())
    nuovo = path.read_bytes()
    if hashlib.sha256(nuovo[:len(raw)]).hexdigest() != hashlib.sha256(raw).hexdigest(): raise RuntimeError("PREFISSO CAMBIATO")
    if len(nuovo) != len(raw) + len(b) + len(term): raise RuntimeError("lunghezza inattesa dopo l'append")
    return hashlib.sha256(nuovo).hexdigest(), len(nuovo), term

def banda_chi2_2gdl(p_basso=0.16, p_alto=0.84) -> tuple:
    """Fattori (min, max) per una sd vera data la sd stimata su N = 3 (2 gradi di liberta')."""
    q = lambda p: -2.0 * math.log(1.0 - p)  # quantile del chi quadro a 2 gdl, forma chiusa
    return math.sqrt(2.0 / q(p_alto)), math.sqrt(2.0 / q(p_basso))

def fisher_bilaterale(a, b, c, d) -> float:
    n1, n2, k = a + b, c + d, a + c
    tot = math.comb(n1 + n2, k)
    p = lambda x: math.comb(n1, x) * math.comb(n2, k - x) / tot
    oss = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, k - n2), min(n1, k) + 1) if p(x) <= oss * (1 + 1e-9)))

PERCORSO = re.compile(r"(?<![\w/\\.])((?:papers|logs|data|results|src)/[\w./\-]+)")
def percorsi_citati(obj) -> set:
    s = json.dumps(obj, ensure_ascii=False)
    return {m.group(1).rstrip(".") for m in PERCORSO.finditer(s)}

def jsonl(p: Path) -> list:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def sha_file(p: Path) -> tuple:
    raw = p.read_bytes(); return hashlib.sha256(raw).hexdigest(), len(raw)

# -- ricalcolo dai registri -----------------------------------------------------------------------
def misura() -> dict:
    R = {k: ROOT / v for k, v in REGISTRI.items()}
    M = {}
    F = jsonl(R["fase3_mock"])
    # A: fase3 produzione contro erosione
    diversi, effetto, nonp, prod, stab, conflitti = {}, {}, {}, {}, [], 0
    for reg in ("NGC", "SGC"):
        E = {}
        for e in jsonl(R["eros_" + reg]):
            i = int(e["key"][6:])
            for c, v in e["cells"].items():
                if c.startswith("R5_er"):
                    k = int(c[5:]); old = E.setdefault(i, {}).get(k)
                    if old is not None and old != v["N_H1"]: raise RuntimeError(f"erosione {reg} {i} k{k}: passate discordi")
                    E[i][k] = v["N_H1"]
        V = {}
        for f in F:
            if f["region"] != reg or f.get("smoke") or "FID" not in f["points"]: continue
            x = f["points"]["FID"]
            for k in range(4):
                if x.get(f"N_H1_k{k}") is not None: V.setdefault((f["index"], k), set()).add(x[f"N_H1_k{k}"])
            if x.get("D4a_stab_ok") is False: stab.append((reg, f["index"], round(x.get("D4a_max_dnu") or float("nan"), 2)))
        conflitti += sum(1 for s in V.values() if len(s) > 1)
        D = {k: {i: next(iter(V[(i, k)])) - E[i][k] for i in range(200) if next(iter(V[(i, k)])) != E[i][k]} for k in range(4)}
        diversi[reg] = [len(D[k]) for k in range(4)]
        effetto[reg] = [round(sum(D[k].values()) / 200, 3) + 0.0 for k in range(4)]
        nonp[reg] = sorted({i for k in range(4) for i, s in D[k].items() if abs(s) > 3})
        prod[reg] = D
    M["A"] = {"conflitti_produzione": conflitti, "diversi": diversi, "effetto": effetto, "non_pareggi": nonp,
              "SGC_81": [prod["SGC"][k].get(81, 0) for k in range(4)], "SGC_24": [prod["SGC"][k].get(24, 0) for k in range(4)],
              "NGC_k1": prod["NGC"][1], "k1_non_in_k0_NGC": sorted(set(prod["NGC"][1]) - set(prod["NGC"][0])),
              "k2_non_in_k0_NGC": sorted(set(prod["NGC"][2]) - set(prod["NGC"][0]))}
    M["stab"] = sorted(stab)
    # G: smoke del 3 settembre, n_sel
    ns_p, ns_s = {}, {}
    for f in F:
        if f["region"] != "NGC" or f["index"] not in (0, 1, 2) or "FID" not in f["points"]: continue
        n = f["points"]["FID"].get("n_sel")
        if not f.get("smoke"): ns_p.setdefault(f["index"], set()).add(n)
        elif f["utc"].startswith("2026-09-03T04:5"): ns_s.setdefault(f["index"], set()).add(n)
    M["smoke"] = {"produzione": {i: s.pop() for i, s in ns_p.items() if len(s) == 1},
                  "smoke_3set": {i: s.pop() for i, s in ns_s.items() if len(s) == 1}}
    # D: ramo unitario v2 contro canonico
    M["D"] = {}
    for reg in ("NGC", "SGC"):
        C = {int(c["key"][6:]): c["base"]["N_H1"] for c in jsonl(R["canon_" + reg])}
        V = {}
        for r in jsonl(R["v2_" + reg]): V.setdefault(r["index"], []).append(r)
        if any(len({x["unit"]["N_H1_k0"] for x in L}) > 1 for L in V.values()): raise RuntimeError(f"v2 {reg}: conflitti nell'unione")
        S = {i: L[0]["unit"]["N_H1_k0"] - C[i] for i, L in V.items()}
        Dg = {i: (L[0].get("diagnostica_catene") or {}).get("scarto") for i, L in V.items()}
        K = {i: (L[0].get("d5c_n_clipped") or 0) > 0 for i, L in V.items()}
        tav = Counter(("oltre3" if abs(S[i]) > 3 else "entro3") + ("_clip" if K[i] else "_noclip") for i in S)
        M["D"][reg] = {"indici": len(V), "diversi": sum(1 for s in S.values() if s), "oltre_3": sum(1 for s in S.values() if abs(s) > 3),
                       "somma": int(sum(S.values())), "somma_abs": int(sum(abs(s) for s in S.values())),
                       "vie_discordi": sum(1 for i in S if Dg[i] is not None and Dg[i] != S[i]), "tavola": dict(tav),
                       "fisher_p": round(fisher_bilaterale(tav["oltre3_clip"], tav["oltre3_noclip"], tav["entro3_clip"], tav["entro3_noclip"]), 2),
                       "media": round(sum(S.values()) / len(S), 4)}
        if reg == "SGC":
            M["D"]["SGC_24"] = (int(S[24]), V[24][0].get("d5c_n_clipped")); M["D"]["SGC_81"] = (int(S[81]), V[81][0].get("d5c_n_clipped"))
    M["D"]["nota"] = [json.loads(R["v2_sommario_" + r].read_text(encoding="utf-8").splitlines()[-1]).get("nota_divergenza", "") for r in ("NGC", "SGC")]
    # C: riga 6
    p9 = json.loads(R["phase9"].read_text(encoding="utf-8"))
    M["C"] = {"growth_rate_per_unit_z": round(p9["growth_rate_per_unit_z"], 2), "growth_rate_sem": round(p9["growth_rate_sem"], 2),
              "k_pairs": p9["k_pairs"], "z_eff_reference": p9["z_eff_reference"],
              "fraction_of_deficit_reference": round(p9["fraction_of_deficit_reference"], 5),
              "snap_z": (p9["snap_hi"]["z"], p9["snap_lo"]["z"]),
              "commit": git("log", "--format=%h", "-1", "--", REGISTRI["phase9"]).strip()[:7]}
    # F: D8
    pb = json.loads(R["pilota_scatola"].read_text(encoding="utf-8"))["pilota"]
    rv = lambda k: pb[k]["sd"] / pb[k]["media"]
    v = [c["base"]["N_H1"] for c in jsonl(R["canon_NGC"])]
    att = {round(r["attenuation"], 6) for r in jsonl(R["compD_NGC"])}
    if len(att) != 1: raise RuntimeError(f"compD_NGC: attenuation non unica {att}")
    a = att.pop(); m, sd = statistics.mean(v), statistics.stdev(v)
    tot, cos = sd / m, a * sd / m
    lo, hi = banda_chi2_2gdl()
    fisica_cos = rv("nwlh_sigma0.6400") / cos
    M["F"] = {"scatola_voxel": round(rv("nwlh_sigma0.3204"), 4), "scatola_fisica": round(rv("nwlh_sigma0.6400"), 4),
              "n_scatola": pb["nwlh_sigma0.6400"]["n"], "canon_media": round(m, 3), "canon_sd": round(sd, 3), "attenuation": a,
              "fattori": {"voxel_totale": round(rv("nwlh_sigma0.3204") / tot, 2), "fisica_totale": round(rv("nwlh_sigma0.6400") / tot, 2),
                          "voxel_cosmologia": round(rv("nwlh_sigma0.3204") / cos, 2), "fisica_cosmologia": round(fisica_cos, 2)},
              "banda68_fisica_cosmologia": (round(fisica_cos * lo, 2), round(fisica_cos * hi, 2))}
    # E: intestazione di nwLH
    testa = NWLH_PARAMS.read_text(encoding="utf-8").splitlines()[0].lstrip("#").split()
    M["E"] = {"colonne": testa}
    # H: terminatori
    M["H"] = mappa_terminatori(LEDGER.read_bytes())
    return M

def confronta(M: dict) -> list:
    err = []
    def eq(nome, a, b):
        if a != b: err.append(f"{nome}: misurato {a!r}, atteso {b!r}")
    A = M["A"]
    eq("A conflitti fra record di produzione", A["conflitti_produzione"], 0)
    for k in ("diversi", "effetto", "non_pareggi", "SGC_81", "SGC_24", "NGC_k1"): eq(f"A {k}", A[k], ATTESI_F3[k])
    eq("A k1 non in k0 (NGC)", A["k1_non_in_k0_NGC"], [91]); eq("A k2 non in k0 (NGC)", A["k2_non_in_k0_NGC"], [46])
    eq("stab_ok falso in produzione", [(r, i) for r, i, _ in M["stab"]], ATTESI_STAB["falsi_produzione"])
    eq("max Δν", {i: d for _, i, d in M["stab"]}, ATTESI_STAB["max_dnu"])
    eq("n_sel", M["smoke"], ATTESI_SMOKE)
    for reg in ("NGC", "SGC"):
        d = M["D"][reg]
        for k in ("indici", "diversi", "oltre_3", "somma", "somma_abs", "tavola"): eq(f"D {reg} {k}", d[k], ATTESI_V2[reg][k])
        eq(f"D {reg} vie discordi", d["vie_discordi"], 0)
    eq("D SGC 24", M["D"]["SGC_24"], ATTESI_V2["SGC_24"]); eq("D SGC 81", M["D"]["SGC_81"], ATTESI_V2["SGC_81"])
    if not all("cammino della geometria" in n for n in M["D"]["nota"]): err.append("D: nota_divergenza senza «cammino della geometria»")
    for k, v in ATTESI_PHASE9.items(): eq(f"C {k}", M["C"][k], v)
    eq("C snapshot", M["C"]["snap_z"], (0.5, 0.0))
    for k in ("scatola_voxel", "scatola_fisica", "canon_media", "canon_sd", "attenuation", "fattori", "banda68_fisica_cosmologia"):
        eq(f"F {k}", M["F"][k], ATTESI_D8[k])
    eq("F N scatola", M["F"]["n_scatola"], 3)
    if "w0" not in M["E"]["colonne"] or any(c.lower() in ("wa", "w_a") for c in M["E"]["colonne"]): err.append(f"E colonne {M['E']['colonne']}")
    eq("H mappa dei terminatori", M["H"], MAPPA_TERMINATORI)
    return err

# -- controlli su documenti, ledger, git ----------------------------------------------------------
def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0: raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout

def controlla_documenti() -> list:
    err = []
    for nome, (rel, s, b) in DOCUMENTI.items():
        p = ROOT / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        s2, b2 = sha_file(p)
        if (s2, b2) != (s, b): err.append(f"{nome}: {s2[:12]}... {b2} B, atteso {s[:12]}... {b} B")
    if err: return err
    righe = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    for dove, frase in FRASI_VECCHIE.items():
        testo = righe[75] if dove == "record 76" else (ROOT / DOCUMENTI[dove.split("#")[0]][0]).read_text(encoding="utf-8")
        k = norm(testo).count(norm(frase))
        if k != 1: err.append(f"{dove}: «{frase[:50]}» {k} volte")
    if "81: +86" not in righe[75]: err.append("record 76: «81: +86» assente")
    return err

def controlla_percorsi(rec: dict) -> list:
    err = []
    for p in sorted(percorsi_citati(rec)):
        radice = p.split("/")[0]
        if radice in ("results", "src"):
            if subprocess.run(["git", "ls-files", "--error-unmatch", p], cwd=ROOT, capture_output=True).returncode != 0:
                err.append(f"percorso non tracciato: {p}")
        elif p not in ESCLUSI_AMMESSI:
            err.append(f"percorso sotto cartella esclusa senza eccezione: {p}")
    return err

def ledger_stato():
    raw = LEDGER.read_bytes()
    return hashlib.sha256(raw).hexdigest(), sum(1 for l in raw.split(b"\n") if l.strip()), len(raw)

# -- il record ------------------------------------------------------------------------------------
def costruisci_record(utc: str, M: dict, digest: dict) -> dict:
    A, D, C, F = M["A"], M["D"], M["C"], M["F"]
    return {
 "type": "protocol",
 "utc": utc,
 "item": "7.10-7.11-7.12-7.3-D8",
 "key": "misure_della_fase_7_idx81_divergenza_fra_catene_riga6_con_registro_34x_cancellazione_limitazione_ii_d8",
 "document": "papers/paper2/checklist_paper2.md; papers/paper2/paper2_budget_5_1.md; papers/paper2/paper2_stato.md",
 "reference_file": "src/paper2_v1_reference.json",
 "reference_file_sha256": REF_FILE_SHA,
 "reference_self_sha256": REF_SELF_SHA,
 "numbering_rule": "The number of an amendment is its 1-based POSITION in this file. This is record 78.",
 "amends_records": [76],
 "old_value": {k.replace("#", "_"): v for k, v in FRASI_VECCHIE.items()},
 "new_value": {
  "A_7_10_idx81_divergenza_fra_catene": {
   "misura": "fase3_mock (FID, record di produzione, smoke esclusi, unione senza conflitti) contro per_mock_*_erosion_restrict R5_er0..3, 200 mock per emisfero, quattro livelli",
   "diversi_per_livello": A["diversi"], "effetto_sulla_media_per_livello": A["effetto"],
   "oltre_i_pareggi": {"NGC": "nessuno: tutti gli scarti sono +-1", "SGC": "solo idx 24 e 81, a ogni livello"},
   "SGC_81_k0_k3": A["SGC_81"], "SGC_24_k0_k3": A["SGC_24"],
   "previsione_a_erosione": "FALSIFICATA: lo scarto c'e' gia' a k = 0",
   "previsione_c_piu_record": "esclusa: un solo valore FID per livello nella produzione",
   "previsione_pareggi_k1_in_k0": "FALSIFICATA in NGC: idx 91 diverge a k = 1 e non a k = 0, idx 46 solo a k = 2. I pareggi nascono livello per livello; la previsione era scritta senza distinguerli e resta falsificata come scritta",
   "firma": "D4a_stab_ok falso in 4 record di produzione su 800, solo SGC 24 e 81 nelle due passate; max dnu 13.68 e 13.67, circa 91 livelli di filtrazione",
   "causa": "divergenza fra la catena R3 (fase3_mock, ramo unitario v2) e quella di paper1_remap: il cammino della geometria, tabella a 4001 nodi contro distanza analitica (nota_divergenza dei sommari del v2). SGC 24 e 81 sono fra le 14 divergenze SGC oltre +-3 del ramo unitario v2 (+92, +69), che coincide con fase3_mock su 400 indici",
   "il_7_su_400": "il conteggio del record 76 a k = 1 si riproduce sulla sola produzione (NGC 1, 91, 135; SGC 24, 29, 81, 111) ma sottostima: a k = 0 SGC 24 scarta +92 e a k = 1 solo -11",
   "cancello_del_record_76": "resta FALLITO; questa e' una seconda misura, dichiarata come tale",
   "conseguenze": "nessun numero del Paper 2: l'unica riga del budget costruita su fase3_mock (riga 1) appaia punti dentro fase3_mock; nessuna riga appaia fase3_mock con un registro del Paper 1. Effetto sulle medie al massimo +0.825 contro mezza SEM 7.78"},
  "B_3_2_rumore_di_pareggio": {
   "testo": "la 3.2 della checklist (30 ago) attribuisce lo scarto SGC di fase3_mock dal congelato, +0.825 e +0.385, al rumore di pareggio dichiarato",
   "misura": "161 dei 165 generatori sommati a k = 0 vengono da SGC 24 e 81 (+92, +69), divergenze fra catene; il resto sono quattro pareggi +1",
   "esito": "il «va riportata» della 3.2 era giusto, il meccanismo no"},
  "C_7_11_riga6_del_budget": {
   "registro": REGISTRI["phase9"], "commit": C["commit"],
   "valori": {"growth_rate_per_unit_z": C["growth_rate_per_unit_z"], "growth_rate_sem": C["growth_rate_sem"], "k_pairs": C["k_pairs"],
              "z_eff_reference": C["z_eff_reference"], "fraction_of_deficit_reference": C["fraction_of_deficit_reference"],
              "limite_3sigma_a_dz_0_25": round((abs(C["growth_rate_per_unit_z"]) + 3 * C["growth_rate_sem"]) * 0.25, 1)},
   "disegno": "due snapshot, z = 0.5 e z = 0, stesso seme per realizzazione nwLH (appaiato); pendenza per unita' di z scalata linearmente a dz = 0.25",
   "etichetta": "«snapshot contro lightcone» dice piu' di quanto misurato: il cono di luce non e' mai stato simulato. Si scrive «crescita, da due snapshot»",
   "perche_non_trovato_prima": "la ricerca per nome (snapshot, lightcone) non poteva trovarlo: il nome e' growth_mismatch"},
  "D_7_12_trentaquattro_volte": {
   "misura": "ramo unitario del v2 (unit.N_H1_k0) contro il canonico (base.N_H1), 2000 + 2000, due vie di calcolo concordi",
   "NGC": {k: D["NGC"][k] for k in ("diversi", "oltre_3", "somma", "somma_abs", "media")},
   "SGC": {k: D["SGC"][k] for k in ("diversi", "oltre_3", "somma", "somma_abs", "media")},
   "esito": "il rapporto delle medie, -0.0085 contro +0.268, divide per una somma che si compensa (-17 su 1927). SGC diverge MENO spesso (0.70 contro 1.15 per cento) e per meno generatori in valore assoluto",
   "previsione_clipping": {"testo": "le divergenze oltre +-3 cadono in larga parte sui mock con d5c_n_clipped > 0",
                           "esito": "FALSIFICATA", "tavola": {r: D[r]["tavola"] for r in ("NGC", "SGC")},
                           "fisher_p": {r: D[r]["fisher_p"] for r in ("NGC", "SGC")},
                           "nota": "SGC 81 ha clip 0; resta la causa scritta dal runner, che non richiede clipping"}},
  "E_7_3_limitazione_ii": {
   "programma": "canovaccio_4_paper_followup.md §3 assegna la (ii), w_a diverso da 0, al Paper 2 come limite",
   "misura": "l'intestazione di latin_hypercube_nwLH_params.txt elenca " + ", ".join(M["E"]["colonne"]) + ": nessun w_a",
   "esito": "il Paper 2 limita la sensibilita' a w0 (vincolo 1 sigma circa +-0.6), non tocca la (ii), che resta aperta",
   "limitazione_vi": "il limite dello 0.2 per cento copre la sola crescita, da due snapshot (voce C)"},
  "F_D8_scatola_cutsky": {
   "sorgenti": [REGISTRI["pilota_scatola"], REGISTRI["canon_NGC"], REGISTRI["compD_NGC"]],
   "scatola": {"n": F["n_scatola"], "sd_su_media_sigma_px_voxel_0_3204": F["scatola_voxel"], "sd_su_media_sigma_px_fisica_0_64": F["scatola_fisica"]},
   "cutsky": {"media": F["canon_media"], "sd_totale": F["canon_sd"], "attenuation_cosmologia_su_totale": F["attenuation"]},
   "fattori": F["fattori"], "banda68_fisica_cosmologia": F["banda68_fisica_cosmologia"],
   "esito": "il ~17 del canovaccio usava sigma_px in voxel (2.5 h-1 Mpc fisici) e la sd TOTALE del cut-sky (cosmologia, HOD, downsampling, realizzazione). Omogeneo: ~22, 68 per cento 16-52 da N = 3; resta un limite superiore; il tracciante (materia oscura contro HOD) e' un sesto confondente"},
  "G_processo": {
   "verdetto_non_letto": "fase3_mock scrive D4a_stab_ok dal 30 ago; quattro record di produzione portano false e nessun cancello li ha letti",
   "parametro_fuori_dal_record": {"smoke_2026_09_03_NGC": "n_sel diverso dalla produzione a parita' di gauge_version",
                                  "produzione": M["smoke"]["produzione"], "smoke": M["smoke"]["smoke_3set"]},
   "regola": "un campo di verdetto dentro un registro di dati e' un cancello solo se qualcuno lo legge; il censimento dei registri legge i verdetti dei registri di gate"},
  "H_7_13_terminatori_del_ledger": {
   "mappa_record_1_77": [{"tipo": t, "da": a, "a": b} for t, a, b in MAPPA_TERMINATORI],
   "regola_rotta_agli_append": [8, 12, 13, 15, 76],
   "questo_record": "eredita LF dall'ultima riga; l'appender verifica lo sha del prefisso e la lunghezza dopo l'append",
   "nulla_si_riscrive": "il ledger e' append-only e freeze_verify lo legge integro"},
  "I_per_la_revisione_documentale": [
   "checklist: D7 e D8 decisi (testi del 23 set); 3.2 col meccanismo; 3.6 ordine delle coperture verificato sul registro (NGC, NGC, SGC, SGC; 26 per cento di SGC k = 2) e cancello di riproduzione a livello intero; Fase 7 punti 3-7 decisi coi loro testi",
   "budget: riga 6, fonte il registro e l'etichetta; riscontro (i), frequenze e somme assolute al posto del «trentaquattro volte»",
   "stato: questo record, gli strumenti, le chiusure di Fase 7"],
 },
 "reason": "Le misure della Fase 7 correggono un'attribuzione del record 76 (il +86), una della 3.2 (il rumore di pareggio), un rapporto del budget (34 volte) e una premessa del programma (la limitazione ii), danno una fonte alla riga 6 e un numero omogeneo al fattore D8, e dichiarano la mappa dei terminatori del ledger. Nessun verdetto depositato cambia.",
 "rules": {
  "marker": "emendamento-78-misure-fase-7",
  "what_this_does_not_do": "Non modifica alcun valore congelato, non riapre alcun verdetto depositato, non tocca il reference, non riscrive record precedenti ne' documenti ancorati.",
  "evidence_files_rechecked_at_append": {v: {"sha256": digest[v][0], "byte": digest[v][1]} for v in sorted(REGISTRI.values())},
  "documents_by_digest": {k: v[1] for k, v in sorted(DOCUMENTI.items())},
  "work_logs_by_name": ["d710_confronto.json", "d712_catene.json", "d710_stab.txt"],
  "not_a_path": "latin_hypercube_nwLH_params.txt sta sotto data/, fuori dal rilascio: citato per nome, letto all'append"},
 "evidence": "Ogni numero di new_value e' ricalcolato dall'appender dai registri in rules.evidence_files_rechecked_at_append prima dell'append e confrontato con gli attesi dichiarati nel sorgente; le frasi di old_value sono cercate nei documenti in rules.documents_by_digest e nel record 76; la mappa dei terminatori e' misurata sul ledger.",
    }

# -- comandi --------------------------------------------------------------------------------------
def selftest():
    ok = 0
    with tempfile.TemporaryDirectory() as d:
        for coda, atteso in ((b"a\r\nb\r\n", b"\r\n"), (b"a\r\nb\n", b"\n")):
            p = Path(d) / "l.jsonl"; p.write_bytes(coda)
            s, n, t = appendi(p, '{"x":1}')
            assert t == atteso and p.read_bytes() == coda + b'{"x":1}' + atteso
        ok += 1
        p.write_bytes(b"a\n")
        try: appendi(p, "x\ny"); raise AssertionError
        except ValueError: pass
        assert p.read_bytes() == b"a\n"; ok += 1
        p.write_bytes(b"a")
        try: appendi(p, "x"); raise AssertionError
        except ValueError: pass
        ok += 1
    raw = b"1\r\n2\r\n3\n4\n5\r\n6\n"
    assert mappa_terminatori(raw) == [("CRLF", 1, 2), ("LF", 3, 4), ("CRLF", 5, 5), ("LF", 6, 6)]; ok += 1
    for cattivo in (b"1\r2\n", b"1\n\n2\n", b"1\n2"):
        try: mappa_terminatori(cattivo); raise AssertionError
        except ValueError: pass
    ok += 1
    lo, hi = banda_chi2_2gdl()
    assert abs(lo - 0.7387) < 1e-4 and abs(hi - 2.3949) < 1e-4; ok += 1
    assert abs(fisher_bilaterale(14, 9, 1157, 820) - 1.0) < 1e-9 and 0.15 < fisher_bilaterale(6, 8, 520, 1466) < 0.3; ok += 1
    t = {"a": "vedi papers/paper2/checklist_paper2.md; results/paper2/x.jsonl e logs/y.json.", "b": ["nome.json", "src/z.py"]}
    assert percorsi_citati(t) == {"papers/paper2/checklist_paper2.md", "results/paper2/x.jsonl", "logs/y.json", "src/z.py"}; ok += 1
    dfin = {k: 0 for k in ("diversi", "oltre_3", "somma", "somma_abs", "media", "tavola", "fisher_p")}
    Mf = {"A": {k: None for k in ("diversi", "effetto", "non_pareggi", "SGC_81", "SGC_24", "NGC_k1")},
          "D": {"NGC": dict(dfin), "SGC": dict(dfin)},
          "C": {k: 0 for k in ("commit", "k_pairs", "z_eff_reference", "fraction_of_deficit_reference")} | {"growth_rate_per_unit_z": -53.27, "growth_rate_sem": 112.04},
          "F": {k: None for k in ("scatola_voxel", "scatola_fisica", "n_scatola", "canon_media", "canon_sd", "attenuation", "fattori", "banda68_fisica_cosmologia")},
          "E": {"colonne": ["w0"]}, "smoke": {"produzione": {}, "smoke_3set": {}}}
    rec = costruisci_record("2026-01-01T00:00:00+00:00", Mf, {v: ("0" * 64, 1) for v in REGISTRI.values()})
    s = json.dumps(rec, ensure_ascii=False, separators=(",", ":")); assert json.loads(s) == rec and "\n" not in s; ok += 1
    assert rec["numbering_rule"].endswith("record 78.") and all("/" not in k for k in rec["rules"]["documents_by_digest"]); ok += 1
    esc = {p for p in percorsi_citati(rec) if p.split("/")[0] not in ("results", "src")}
    assert esc <= ESCLUSI_AMMESSI, esc; ok += 1
    assert norm("a\r\n  b\tc") == "a b c" and len(FRASI_VECCHIE) == 6; ok += 1
    print(f"selftest: {ok}/12 OK")

def dry_run(scrivi=False):
    s, n, b = ledger_stato()
    if (s, n, b) != (LEDGER_SHA, LEDGER_RIGHE, LEDGER_BYTE):
        raise SystemExit(f"STOP: ledger {s[:12]}... {n} righe {b} byte, atteso {LEDGER_SHA[:12]}... {LEDGER_RIGHE} righe {LEDGER_BYTE} byte")
    if sha_file(REF_FILE)[0] != REF_FILE_SHA: raise SystemExit("STOP: il reference ha cambiato sha")
    err = controlla_documenti()
    mancanti = [v for v in REGISTRI.values() if not (ROOT / v).exists()] + ([] if NWLH_PARAMS.exists() else ["latin_hypercube_nwLH_params.txt"])
    if mancanti: err += [f"assente: {m}" for m in mancanti]
    if err:
        print("STOP:"); [print("  -", e) for e in err]; raise SystemExit(1)
    M = misura()
    err = confronta(M)
    digest = {v: sha_file(ROOT / v) for v in REGISTRI.values()}
    utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rec = costruisci_record(utc, M, digest)
    err += controlla_percorsi(rec)
    if err:
        print("STOP, fatti non riprodotti o percorsi non ammessi:"); [print("  -", e) for e in err]; raise SystemExit(1)
    riga = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
    term = terminatore(LEDGER.read_bytes()); nome_term = "CRLF" if term == b"\r\n" else "LF"
    print(f"ledger all'ancora ({LEDGER_SHA[:12]}..., {LEDGER_RIGHE} righe, {LEDGER_BYTE} byte); reference invariato; "
          f"{len(DOCUMENTI)} documenti e {len(FRASI_VECCHIE)} frasi confermati; ogni numero del record riprodotto dai {len(REGISTRI)} registri")
    print(f"percorsi citati: {len(percorsi_citati(rec))}, tutti tracciati o gia' eccettuati; terminatore ereditato: {nome_term}")
    print(f"record 78: {len(riga.encode())} byte, utc {utc}")
    if not scrivi: print("  nessuna modifica scritta"); return
    s2, b2, _ = appendi(LEDGER, riga)
    print(f"[apply] appeso col terminatore ereditato; prefisso di {LEDGER_BYTE} byte invariato; ledger {LEDGER_RIGHE + 1} righe, {b2} byte, sha {s2}")

def verify():
    s, n, b = ledger_stato()
    raw = LEDGER.read_bytes()
    ultimo = json.loads([l for l in raw.decode("utf-8").splitlines() if l.strip()][-1])
    ok = (n == LEDGER_RIGHE + 1 and hashlib.sha256(raw[:LEDGER_BYTE]).hexdigest() == LEDGER_SHA
          and ultimo["numbering_rule"].endswith("record 78.") and ultimo["item"] == "7.10-7.11-7.12-7.3-D8"
          and mappa_terminatori(raw)[-1] == ("LF", 76, 78))
    print(f"verify {'OK' if ok else 'ANOMALIA'}: {n} righe, {b} byte, sha {s}; prefisso {'invariato' if hashlib.sha256(raw[:LEDGER_BYTE]).hexdigest() == LEDGER_SHA else 'CAMBIATO'}; "
          f"ultimo: item {ultimo['item']}, utc {ultimo['utc']}; coda {mappa_terminatori(raw)[-1]}")
    if not ok: sys.exit(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    c = ap.parse_args().cmd
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[c]()
