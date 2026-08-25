#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper1_rev2_residual_significance.py — significativita' del residuo
oltre-due-punti (Referee 3, seconda tornata, punto nuovo 1).

IL PUNTO
--------
Il manoscritto quotava il residuo come "1710.5 +/- 40.6 (42 sigma)". Il
referee ha ragione: il +/-40.6 e' la SEM delle estrazioni di fase (50 lato
dati, 100 lato mock) e misura la *precisione della decomposizione*, non
l'anomalia. La significativita' pertinente richiede la dispersione dello
stesso residuo da mock a mock, trattando ogni mock a turno come "dati".

L'ALGEBRA
---------
Il residuo e' esattamente la differenza fra i guadagni di gaussianizzazione:

    Delta N   =  N_phi  -  N                       (per campo)
    residuo   =  Delta N_DESI  -  <Delta N>_mock

Verifica sui numeri pubblicati:
    DESI :  33 719.4 - 28 256.0 = 5463.4
    mock :  39 211.8 - 35 458.9 = 3752.9
    residuo = 5463.4 - 3752.9   = 1710.5      <- riproduce la Tabella 3

Quindi il denominatore corretto e' sigma_Delta = sd(Delta N) sull'ensemble,
NON sd(N_H1). sigma_Delta e' molto piu' piccolo di sd(N_H1) perche' N e
N_phi sono fortemente correlati: un mock ricco di generatori resta ricco
dopo la gaussianizzazione, e la differenza cancella quella covarianza.

STIMA A PRIORI (per sanity check del risultato)
    sd(N) = 258, sd(N_phi) = 340 dalle SEM di Tabella 3 con n = 100:
      rho = 0.50  ->  sigma_Delta = 307  ->  z =  5.6
      rho = 0.70  ->  sigma_Delta = 244  ->  z =  7.0
      rho = 0.80  ->  sigma_Delta = 204  ->  z =  8.4
      rho = 0.90  ->  sigma_Delta = 156  ->  z = 11.0
Il referee si aspetta z ~ 5-10: se il risultato cade fuori da 4-14,
controllare prima l'appaiamento degli indici che il risultato.

USO
---
Adattare load_pairs(). Servono, per gli stessi mock e nello stesso ordine,
N_H1 originale e N_H1 con fasi randomizzate, piu' i due valori DESI.

    python paper1_rev2_residual_significance.py

Stampa i tre numeri da inserire nei \\fillin del manoscritto
(sigma residuo, z residuo, rank residuo) e li scrive in un JSON congelato.
"""

import json
from datetime import datetime, timezone

import numpy as np

# valori pubblicati (Tabella 3), usati come gate
REF = dict(desi=28256.0, desi_phi=33719.4,
           mock_mean=35458.9, mock_phi_mean=39211.8, residual=1710.5)


def load_pairs():
    """
    ADATTARE QUI. Restituire (N, N_phi, desi, desi_phi) dove N e N_phi sono
    array della stessa lunghezza e nello stesso ordine di mock.

    Esempio con il JSONL per-mock dell'esperimento di fase:

        import json
        rows = [json.loads(l) for l in
                open(r"D:\\projects\\cauchy\\results\\paper1"
                     r"\\per_mock_phase_NGC_R5.jsonl")]
        rows.sort(key=lambda r: r["mock_id"])          # ordine garantito
        N     = np.array([r["n_h1"]     for r in rows], float)
        N_phi = np.array([r["n_h1_phi"] for r in rows], float)
        return N, N_phi, 28256.0, 33719.4

    ATTENZIONE all'appaiamento: N e N_phi devono riferirsi alla STESSA
    realizzazione riga per riga. Se le fasi sono state estratte piu' volte
    per mock, mediare per mock PRIMA di fare la differenza.
    """
    raise NotImplementedError("load_pairs() va adattata alla sorgente locale.")


def main():
    N, N_phi, desi, desi_phi = load_pairs()
    N, N_phi = np.asarray(N, float), np.asarray(N_phi, float)
    assert N.shape == N_phi.shape, "array non appaiati"
    n = N.size

    dN = N_phi - N                       # guadagno per mock
    dN_desi = desi_phi - desi
    residual = dN_desi - dN.mean()

    sd_dN = dN.std(ddof=1)
    z = residual / sd_dN
    rho = np.corrcoef(N, N_phi)[0, 1]

    # rank empirico: quanti mock hanno un guadagno >= quello di DESI
    n_ge = int((dN >= dN_desi).sum())
    rank = n_ge + 1
    p_one_sided = rank / (n + 1)

    # ---- gate sui valori pubblicati ----
    checks = {
        "media mock N_H1":     (N.mean(),     REF["mock_mean"],     3.0),
        "media mock N_H1 phi": (N_phi.mean(), REF["mock_phi_mean"], 3.0),
        "residuo":             (residual,     REF["residual"],      1.0),
    }
    bad = [f"{k}: {g:.1f} contro {w:.1f}"
           for k, (g, w, tol) in checks.items() if abs(g - w) > tol]
    if bad:
        print("ATTENZIONE, i gate non tornano (indici disallineati?):")
        for b in bad:
            print("   -", b)

    print(f"\nn mock                      : {n}")
    print(f"guadagno mock  <Delta N>    : {dN.mean():9.1f}  (sd {sd_dN:.1f})")
    print(f"guadagno DESI   Delta N     : {dN_desi:9.1f}")
    print(f"corr(N, N_phi)              : {rho:9.4f}")
    print( "-" * 52)
    print(f"residuo                     : {residual:9.1f}")
    print(f"sigma del residuo (mock)    : {sd_dN:9.1f}   -> \\fillin{{sigma residuo}}")
    print(f"significativita'            : {z:9.2f} sigma -> \\fillin{{z residuo}}")
    print(f"rank empirico               : {rank}/{n+1} (p <= {p_one_sided:.2g})"
          f"   -> \\fillin{{rank residuo}}")
    if not 4.0 <= abs(z) <= 14.0:
        print("\nNB: z fuori dall'intervallo atteso 4-14: verificare "
              "l'appaiamento prima di usare il numero.")

    out = dict(n_mock=n, gain_mock_mean=float(dN.mean()),
               gain_mock_sd=float(sd_dN), gain_desi=float(dN_desi),
               corr_N_Nphi=float(rho), residual=float(residual),
               z_residual=float(z), rank=f"{rank}/{n+1}",
               p_one_sided=float(p_one_sided),
               gates_failed=bad,
               generated=datetime.now(timezone.utc).isoformat())
    with open("paper1_rev2_residual_significance.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nscritto paper1_rev2_residual_significance.json")


if __name__ == "__main__":
    main()
