#!/usr/bin/env python3
"""
paper2_forma_lato_mock.py  rev. 3  -  il fit della forma regge sul solo lato mock? k = 1, 0 e poi 2, 3

REV. 3 (23 set). Esito della rev. 2, logs/forma_lato_mock_v2.json: cancello PASS; chi2 del lato
mock 0.7, 5.6, 0.9, 2.4 contro il limite 11.34 (3 dof), previsione CONFERMATA in 4 casi su 4;
chi2 di D 74.6, 107.1, 143.0, 149.7. La rev. 3 estende la stessa misura ai livelli diagnostici
k = 2, 3, dove la copertura del pavimento del blocco A cala (item 3.6).
SECONDA PREVISIONE, dichiarata il 23 set prima di vedere k = 2, 3: il chi2 del lato mock sta
sotto il limite anche a k = 2, 3 in entrambi gli emisferi. Base: il lato mock regge a k = 0, 1
con margine (massimo 5.6); nient'altro.
LETTURE DICHIARATE PRIMA: lato mock sotto e D sopra -> la struttura non liscia resta nel lato
dati anche dove il pavimento copre poco; lato mock sopra -> a erosione alta compare struttura
anche sul lato mock; D sotto -> a quel livello non c'e' struttura da attribuire.

REV. 2 (23 set). La rev. 1 ha FALLITO il cancello con chi2 e gradi di liberta' identici al
registro: il terzo controllo confrontava i punti come LISTE, cioe' anche nell'ordine delle chiavi,
e il registro JSON le porta in un ordine diverso da quello del fit. Il cancello chiedeva una
proprieta' che non e' in questione. Ora i punti si confrontano come insiemi, e ogni condizione ha
il suo messaggio. Il log della rev. 1 resta in logs/forma_lato_mock.json; la rev. 2 scrive _v2.

Il fit di simmetria del 3.4, D(F) = D0 + a(F-1) + b(F-1)^2 in GLS con la covarianza piena della
media dei mock, non descrive i dati: chi2 fra 29.3 e 135.9 (5 punti), e peggio col sesto. Con
D = mock - dati il fit e' LINEARE nella risposta, quindi il residuo si spezza esattamente:
    resid(D) = resid(lato mock) + resid(-lato dati)
Il lato mock si ottiene chiamando LA STESSA funzione, `symmetry_fit` di paper2_fase3_analisi.py,
con il lato dati posto a zero; il residuo del lato dati e' la differenza. Nessuna seconda
implementazione del fit.

CANCELLO DI RIPRODUZIONE: il fit su D deve ridare il chi2 dell'ultimo record per emisfero di
results/paper2/fase3_analisi.jsonl, stessi punti, stessi gradi di liberta'.

PREVISIONE, dichiarata il 23 set prima di vedere qualunque fit: sul solo lato mock il chi2 sta
sotto il limite al 99% in tutti e quattro i casi (NGC, SGC; k = 1, 0). Base debole: il lato mock
e' monotono in F in 4 casi su 4 (paper2_b1_decomposizione.py rev. 2), ma la monotonia non
garantisce la forma quadratica, e con 200 coppie una curvatura vera si vede.
DICHIARATO ANCHE PRIMA: il residuo del lato dati si riporta in unita' di SEM, come descrizione.

Sola lettura. Scrive solo logs/forma_lato_mock.json.

Uso:
  python src\\paper2_forma_lato_mock.py selftest
  python src\\paper2_forma_lato_mock.py run
"""
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FA_SHA = "31bc9d0a2799820ef4f00681aa1c6663739872cf98eefac7acfb37bcf7dce762"
F_MOCK = ROOT / "results/paper2/fase3_mock.jsonl"
F_DATI = ROOT / "results/paper2/fase3.jsonl"
F_ANAL = ROOT / "results/paper2/fase3_analisi.jsonl"
OUT = ROOT / "logs/forma_lato_mock_v3.json"
LIVELLI = (1, 0, 2, 3)

def importa_fa(src=SRC, sha_atteso=FA_SHA):
    p = Path(src) / "paper2_fase3_analisi.py"
    s = hashlib.sha256(p.read_bytes()).hexdigest()
    if sha_atteso and s != sha_atteso:
        raise SystemExit(f"STOP: paper2_fase3_analisi.py e' {s[:12]}..., atteso {sha_atteso[:12]}...: "
                         f"non e' lo strumento che ha prodotto il registro")
    sys.path.insert(0, str(src))
    import paper2_fase3_analisi as FA
    return FA

def lato_mock(FA, mock, desi, key, ki):
    zero = {p: {k: 0 for k in v} for p, v in desi.items()}
    return FA.symmetry_fit(mock, zero, key, ki)

def residuo_dati(fD, fM):
    sem = {p: fD["residuals"][p] / fD["residuals_in_sem"][p] for p in fD["residuals"]}
    r = {p: fD["residuals"][p] - fM["residuals"][p] for p in fD["residuals"]}
    return r, {p: r[p] / sem[p] for p in r}

def run():
    FA = importa_fa()
    A = [json.loads(l) for l in F_ANAL.read_text(encoding="utf-8").splitlines() if l.strip()]
    out, gate, righe = {}, [], []
    for reg in ("NGC", "SGC"):
        mock = FA.load(F_MOCK, reg); desi = FA.desi_side(F_DATI, reg)
        ultimo = [r for r in A if r.get("region") == reg][-1]
        for ki in LIVELLI:
            key = f"N_H1_k{ki}"
            pub = ultimo.get("levels", {}).get(f"k{ki}", {}).get("symmetry")
            if pub is None:
                gate.append(f"{reg} k{ki}: il registro non ha il fit di simmetria a questo livello"); continue
            fD = FA.symmetry_fit(mock, desi, key, ki)
            if abs(fD["chi2"] - pub["chi2"]) > 1e-6 * max(1.0, abs(pub["chi2"])):
                gate.append(f"{reg} k{ki}: chi2 {fD['chi2']:.6f} contro {pub['chi2']:.6f}")
            if fD["chi2_dof"] != pub["chi2_dof"]:
                gate.append(f"{reg} k{ki}: {fD['chi2_dof']} gradi di liberta' contro {pub['chi2_dof']}")
            if "residuals" in pub and set(fD["residuals"]) != set(pub["residuals"]):
                gate.append(f"{reg} k{ki}: punti {sorted(fD['residuals'])} contro {sorted(pub['residuals'])}")
            fM = lato_mock(FA, mock, desi, key, ki)
            rd, rd_sem = residuo_dati(fD, fM)
            out[f"{reg}_k{ki}"] = {"punti": list(fD["residuals"]), "dof": fD["chi2_dof"], "limite": fD["chi2_limit"],
                                   "chi2_D": fD["chi2"], "chi2_mock": fM["chi2"],
                                   "residui_mock_sem": fM["residuals_in_sem"], "residui_dati_sem": rd_sem,
                                   "residui_mock": fM["residuals"], "residui_dati": rd}
            righe.append((reg, ki, fD, fM, rd_sem))
    print("\ncancello di riproduzione (chi2 su D contro fase3_analisi.jsonl):", "PASS" if not gate else "FALLITO")
    for g in gate: print("  -", g)
    esito = None
    if not gate:
        print(f"\n{'caso':8} {'punti':>5} {'dof':>3} {'limite':>7} {'chi2 D':>8} {'chi2 mock':>10}   residui in SEM: mock | dati")
        for reg, ki, fD, fM, rd_sem in righe:
            pts = list(fD["residuals"])
            rm = " ".join(f"{fM['residuals_in_sem'][p]:+5.1f}" for p in pts)
            rdd = " ".join(f"{rd_sem[p]:+5.1f}" for p in pts)
            print(f"{reg}_k{ki:<3} {len(pts):5d} {fD['chi2_dof']:3d} {fD['chi2_limit']:7.2f} {fD['chi2']:8.1f} {fM['chi2']:10.1f}   {rm} | {rdd}")
        print(f"  ordine dei punti: {', '.join(pts)}")
        tiene = {k: v["chi2_mock"] <= v["limite"] for k, v in out.items()}
        prima = {k: v for k, v in tiene.items() if k.endswith(("_k0", "_k1"))}
        seconda = {k: v for k, v in tiene.items() if k.endswith(("_k2", "_k3"))}
        esito = {"previsione_k01": {"per_caso": prima, "confermata": all(prima.values())},
                 "previsione_k23": {"per_caso": seconda, "confermata": all(seconda.values())},
                 "D_sopra_il_limite": {k: v["chi2_D"] > v["limite"] for k, v in out.items()}}
        for nome, pr in (("k = 0, 1 (rev. 2)", prima), ("k = 2, 3 (rev. 3)", seconda)):
            print(f"\nprevisione {nome}, chi2 del lato mock sotto il limite: "
                  f"{'CONFERMATA' if all(pr.values()) else 'FALSIFICATA'} - " + ", ".join(f"{k} {'si' if v else 'no'}" for k, v in pr.items()))
    else:
        print("\nnessun fit letto: il cancello non e' passato")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"fa_sha256": FA_SHA, "cancello": {"pass": not gate, "errori": gate},
                               "casi": out, "esito": esito}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nscritto {OUT.relative_to(ROOT)}")
    sys.exit(0 if not gate else 1)

def selftest():
    import numpy as np
    FA = importa_fa(sha_atteso=None)
    ok = 0
    rng = np.random.default_rng(1)
    pts = ["B1", "B2", "FID", "B4", "B5", "B6"]; x = np.array([FA.LINE_B[p] - 1 for p in pts])
    def righe(media):
        base = rng.normal(30000, 300, 200)
        return [{"index": i, "points": {p: {"N_H1_k1": float(base[i] + media[j] + rng.normal(0, 150))} for j, p in enumerate(pts)}} for i in range(200)]
    mq = 100 - 3000 * x + 20000 * x ** 2
    mock = righe(mq)
    d_quad = {p: {1: float(28000 + 50 - 900 * xi + 5000 * xi ** 2)} for p, xi in zip(pts, x)}
    fD = FA.symmetry_fit(mock, d_quad, "N_H1_k1", 1, n_boot=50); fM = lato_mock(FA, mock, d_quad, "N_H1_k1", 1)
    rd, rds = residuo_dati(fD, fM)
    assert max(abs(v) for v in rd.values()) < 1e-6; ok += 1          # lato dati quadratico: nessun residuo
    assert abs(fD["chi2"] - fM["chi2"]) < 1e-6; ok += 1               # e il chi2 e' tutto del lato mock
    d_bump = {p: {1: v[1] + (150.0 if p == "B2" else 0.0)} for p, v in d_quad.items()}
    fD2 = FA.symmetry_fit(mock, d_bump, "N_H1_k1", 1, n_boot=50); rd2, _ = residuo_dati(fD2, fM)
    assert fD2["chi2"] > fM["chi2"] and max(abs(v) for v in rd2.values()) > 10; ok += 1
    assert all(abs(fD2["residuals"][p] - (fM["residuals"][p] + rd2[p])) < 1e-9 for p in pts); ok += 1
    print(f"selftest: {ok}/4 OK")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "run"])
    {"selftest": selftest, "run": run}[ap.parse_args().cmd]()
