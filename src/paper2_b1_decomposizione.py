#!/usr/bin/env python3
"""
paper2_b1_decomposizione.py  rev. 2  -  item 3.10: di chi e' l'eccesso di B1 a k=0 in NGC?

REV. 2 (23 set). La rev. 1 ha FALLITO il cancello per due difetti del cancello, non dei dati:
(a) il controllo di coerenza dei record-dati girava su tutti i punti, e i punti del blocco A
(A0, A1, A3 e varianti M) hanno per disegno piu' record con la stessa gauge: ora gira solo sui
punti che la decomposizione usa (FID, B1, B2, B4, B5), e gli altri sono contati e riportati;
(b) la tolleranza dei valori per punto a k=1 era 0.005 mentre sono pubblicati a un decimale
(67.825 contro 67.8): ora la tolleranza segue la precisione di ciascun numero pubblicato.
Aggiunto un secondo metro indipendente: per_point del registro fase3_analisi.jsonl.
Il log della rev. 1 resta in logs/b1_decomposizione.json; la rev. 2 scrive _v2.

Con D = mock - dati (convenzione di paper2_contrasti.py) e il lato dati deterministico:
    dD(P) = D(P) - D(FID) = dm(P) - dd(P)
    dm(P) = media_i [ Nm_i(P) - Nm_i(FID) ]   con SEM appaiata sd/sqrt(n)
    dd(P) = Nd(P) - Nd(FID)                    esatto, una realizzazione

CANCELLO DI RIPRODUZIONE, prima di ogni lettura: i numeri pubblicati nella checklist (3.4, 3.10)
e nel budget (riga 1) devono uscire dai registri grezzi. Se uno non esce, niente decomposizione.

PREVISIONE dichiarata il 23 set prima del run: l'eccesso di B1 sugli altri punti della linea B a
k=0 in NGC e' portato dal lato DATI per almeno 2/3.

Sola lettura. Scrive solo logs/b1_decomposizione.json (log di lavoro, fuori dal rilascio).

Uso:
  python src\\paper2_b1_decomposizione.py selftest
  python src\\paper2_b1_decomposizione.py run
"""
import argparse, json, math, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F_MOCK = ROOT / "results/paper2/fase3_mock.jsonl"
F_DATI = ROOT / "results/paper2/fase3.jsonl"
F_ANAL = ROOT / "results/paper2/fase3_analisi.jsonl"
OUT = ROOT / "logs/b1_decomposizione_v2.json"
USATI = {"FID", "B1", "B2", "B4", "B5"}
PUNTI = ["B1", "B2", "B4", "B5"]

# (regione, k) -> {punto: (dD, sem)} e dDmax B5-B1 (valore, sem), come pubblicati
PUBBLICATI = {
 ("NGC", 0): {"punti": {"B1": (153.2, 11.7), "B2": (5.3, None), "B4": (7.6, None), "B5": (39.2, None)},
              "ddmax": (-114.0, 11.6), "tol": 0.05, "tol_punti": 0.05},
 ("NGC", 1): {"punti": {"B1": (73.6, None), "B2": (53.4, None), "B4": (67.8, None), "B5": (-24.7, None)},
              "ddmax": (-98.30, 11.249), "tol": 0.005, "tol_punti": 0.05},
 ("SGC", 0): {"punti": {}, "ddmax": (-75.0, 9.2), "tol": 0.05, "tol_punti": 0.05},
 ("SGC", 1): {"punti": {}, "ddmax": (-91.13, 8.708), "tol": 0.005, "tol_punti": 0.05},
}

def leggi(p): return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def unione_mock(righe):
    """(regione, indice) -> {punto: {campo: valore}}; unione delle passate, smoke esclusi."""
    u, conflitti, gv = {}, 0, set()
    for r in righe:
        if r.get("smoke"): continue
        gv.add(r.get("gauge_version"))
        cella = u.setdefault((r["region"], int(r["index"])), {})
        for pt, campi in r["points"].items():
            dst = cella.setdefault(pt.upper(), {})
            for k, v in campi.items():
                if k in dst and dst[k] != v: conflitti += 1
                dst[k] = v
    return u, conflitti, gv

def n_ladder(r, k):
    lad = r.get("ladder")
    if isinstance(lad, dict):
        x = lad.get(str(k), lad.get(k))
    elif isinstance(lad, list):
        x = next((e for e in lad if isinstance(e, dict) and e.get("k") == k), None)
        if x is None and k < len(lad): x = lad[k]
    else:
        x = None
    if isinstance(x, dict): x = x.get("N_H1")
    return x

def dati_per_punto(righe, gv):
    """(regione, punto) -> {k: N}; rifiuta se due record della stessa gauge non coincidono."""
    out, err, altri = {}, [], set()
    for r in righe:
        if gv and r.get("gauge_version") not in gv: continue
        chiave = (r["region"], str(r["point"]).upper())
        if chiave[1] not in USATI: altri.add(chiave); continue
        lad = {k: n_ladder(r, k) for k in range(4)}
        if lad[0] is not None and r.get("N_H1_k0") is not None and lad[0] != r["N_H1_k0"]:
            err.append(f"dati {chiave}: ladder k0 {lad[0]} contro N_H1_k0 {r['N_H1_k0']}")
        if chiave in out and any(out[chiave][k] != lad[k] for k in range(4) if lad[k] is not None):
            err.append(f"dati {chiave}: due record della stessa gauge non coincidono")
        out.setdefault(chiave, {}).update({k: v for k, v in lad.items() if v is not None})
    return out, err, altri

def decomponi(u, dati, reg, k, punti):
    campo = f"N_H1_k{k}"
    nd_fid = dati[(reg, "FID")][k]
    ris = {}
    for p in punti:
        diff = [c[p][campo] - c["FID"][campo] for (rg, _), c in sorted(u.items())
                if rg == reg and p in c and "FID" in c and campo in c[p] and campo in c["FID"]]
        n = len(diff); dm = st.mean(diff); sem = st.stdev(diff) / math.sqrt(n)
        dd = dati[(reg, p)][k] - nd_fid
        ris[p] = {"n": n, "dm": dm, "sem": sem, "dd": dd, "dD": dm - dd}
    return ris

def ddmax(u, reg, k):
    campo = f"N_H1_k{k}"
    diff = [c["B5"][campo] - c["B1"][campo] for (rg, _), c in sorted(u.items())
            if rg == reg and "B5" in c and "B1" in c and campo in c["B5"] and campo in c["B1"]]
    return st.mean(diff), st.stdev(diff) / math.sqrt(len(diff)), len(diff)

def eccesso(ris, p="B1", altri=("B2", "B4", "B5")):
    m = lambda key: st.mean(ris[a][key] for a in altri)
    E_D = ris[p]["dD"] - m("dD")
    E_mock = ris[p]["dm"] - m("dm")
    E_dati = -(ris[p]["dd"] - m("dd"))
    return E_D, E_mock, E_dati

def run():
    u, conflitti, gv = unione_mock(leggi(F_MOCK))
    dati, err, altri = dati_per_punto(leggi(F_DATI), gv)
    print(f"mock: {len(u)} (regione, indice), conflitti fra passate {conflitti}, gauge {sorted(map(str, gv))}")
    print(f"dati: {len(dati)} (regione, punto) usati sulla stessa gauge; {len(altri)} altri, non giudicati")
    if conflitti: err.append(f"mock: {conflitti} conflitti fra passate")
    tabella, gate = {}, []
    for (reg, k), pub in PUBBLICATI.items():
        ris = decomponi(u, dati, reg, k, PUNTI)
        m, s, n = ddmax(u, reg, k); dd5, dd1 = ris["B5"]["dd"], ris["B1"]["dd"]
        ddm = m - (dd5 - dd1)
        tabella[f"{reg}_k{k}"] = {"punti": ris, "ddmax": {"valore": ddm, "sem": s, "n": n}}
        tol = pub["tol"]
        if abs(ddm - pub["ddmax"][0]) > tol or abs(s - pub["ddmax"][1]) > tol:
            gate.append(f"{reg} k{k} dDmax: {ddm:.3f} +- {s:.3f} contro {pub['ddmax']}")
        for p, (v, e) in pub["punti"].items():
            if abs(ris[p]["dD"] - v) > pub["tol_punti"] or (e is not None and abs(ris[p]["sem"] - e) > pub["tol_punti"]):
                gate.append(f"{reg} k{k} {p}: {ris[p]['dD']:.3f} +- {ris[p]['sem']:.3f} contro {v} +- {e}")
    try:
        A = leggi(F_ANAL)
        for (reg, k) in PUBBLICATI:
            ultimo = [r for r in A if r.get("region") == reg][-1]["levels"][f"k{k}"]["per_point"]
            for p in PUNTI:
                x, r = ultimo[p], tabella[f"{reg}_k{k}"]["punti"][p]
                if abs(x["estimate"] - r["dD"]) > 1e-6 or abs(x["mock_mean_diff"] - r["dm"]) > 1e-6 or x["desi_offset"] != r["dd"]:
                    gate.append(f"analisi {reg} k{k} {p}: {x['estimate']}/{x['mock_mean_diff']}/{x['desi_offset']} contro i registri grezzi")
    except Exception as e:
        gate.append(f"analisi: secondo metro non leggibile ({e})")
    print("\ncancello di riproduzione:", "PASS" if not (gate or err) else "FALLITO")
    for e in err + gate: print("  -", e)
    print(f"\n{'':9} {'punto':5} {'n':>4} {'dm (mock)':>11} {'sem':>6} {'dd (dati)':>10} {'dD = dm - dd':>13}")
    for chiave, t in tabella.items():
        for p, r in t["punti"].items():
            print(f"{chiave:9} {p:5} {r['n']:4d} {r['dm']:11.1f} {r['sem']:6.1f} {r['dd']:10.1f} {r['dD']:13.1f}")
        d = t["ddmax"]; print(f"{chiave:9} B5-B1 {d['n']:4d} {'':11} {d['sem']:6.1f} {'':10} {d['valore']:13.1f}")
    esito = None
    if not (gate or err):
        E_D, E_mock, E_dati = eccesso(tabella["NGC_k0"]["punti"])
        quota = E_dati / E_D
        esito = {"eccesso_dD": E_D, "parte_mock": E_mock, "parte_dati": E_dati, "quota_dati": quota,
                 "previsione": "quota_dati >= 2/3", "verificata": quota >= 2 / 3}
        print(f"\nNGC k0, eccesso di B1 sulla media di B2, B4, B5: {E_D:+.1f} = mock {E_mock:+.1f} + dati {E_dati:+.1f}")
        print(f"quota del lato dati {quota:.3f}; previsione (>= 2/3): {'CONFERMATA' if esito['verificata'] else 'FALSIFICATA'}")
        mono = {}
        for chiave, t in tabella.items():
            ordine = ["B1", "B2", None, "B4", "B5"]
            val = lambda key: [0.0 if q is None else t["punti"][q][key] for q in ordine]
            dec = lambda v: all(v[i] >= v[i + 1] for i in range(len(v) - 1))
            mono[chiave] = {"mock_monotono": dec(val("dm")), "dati_monotono": dec(val("dd"))}
        esito["seconda_misura_dichiarata_dopo_la_tabella"] = mono
        print("seconda misura, dichiarata come tale dopo aver visto la tabella: monotonia lungo F (B1, B2, FID, B4, B5)")
        for chiave, m in mono.items():
            print(f"  {chiave}: lato mock {'monotono' if m['mock_monotono'] else 'NON monotono'}, lato dati {'monotono' if m['dati_monotono'] else 'NON monotono'}")
    else:
        print("\nnessuna decomposizione letta: il cancello non e' passato")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"cancello": {"pass": not (gate or err), "errori": err + gate},
                               "tabella": tabella, "esito": esito}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nscritto {OUT.relative_to(ROOT)}")
    sys.exit(0 if not (gate or err) else 1)

def selftest():
    ok = 0
    righe = [{"region": "NGC", "index": i, "gauge_version": "g", "points": {"FID": {"N_H1_k0": 100 + i}, "B1": {"N_H1_k0": 110 + i + (i % 2)}}}
             for i in range(4)] + [{"region": "NGC", "index": 0, "gauge_version": "g", "points": {"B5": {"N_H1_k0": 90}}},
                                    {"region": "NGC", "index": 0, "smoke": True, "points": {"FID": {"N_H1_k0": -1}}}]
    u, c, gv = unione_mock(righe); assert c == 0 and set(u[("NGC", 0)]) == {"FID", "B1", "B5"} and gv == {"g"}; ok += 1
    u2, c2, _ = unione_mock(righe + [{"region": "NGC", "index": 1, "gauge_version": "g", "points": {"FID": {"N_H1_k0": 0}}}]); assert c2 == 1; ok += 1
    assert n_ladder({"ladder": {"0": {"N_H1": 5}}}, 0) == 5 and n_ladder({"ladder": [{"N_H1": 7}, {"N_H1": 8}]}, 1) == 8; ok += 1
    dati = {("NGC", "FID"): {0: 200}, ("NGC", "B1"): {0: 180}}
    r = decomponi(u, dati, "NGC", 0, ["B1"])["B1"]
    assert r["n"] == 4 and abs(r["dm"] - 10.5) < 1e-12 and r["dd"] == -20 and abs(r["dD"] - 30.5) < 1e-12; ok += 1
    assert abs(r["sem"] - st.stdev([10, 11, 10, 11]) / 2) < 1e-12; ok += 1
    fin = {"B1": {"dD": 150, "dm": 10, "dd": -140}, "B2": {"dD": 5, "dm": 2, "dd": -3},
           "B4": {"dD": 8, "dm": 4, "dd": -4}, "B5": {"dD": 40, "dm": 30, "dd": -10}}
    E_D, E_m, E_d = eccesso(fin); assert abs(E_D - (E_m + E_d)) < 1e-12 and E_d / E_D > 2 / 3; ok += 1
    print(f"selftest: {ok}/6 OK")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "run"])
    {"selftest": selftest, "run": run}[ap.parse_args().cmd]()
