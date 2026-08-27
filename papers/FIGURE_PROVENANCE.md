# CAUCHY — provenienza delle figure

**Ricostruita il 27 agosto 2026.** Dodici figure, tutte con provenienza dichiarata.
Base per i `README.md` di `papers/m26/` e `papers/paper1/`.

---

## M26 — MN-26-2100-P (`papers/m26/MNRAS/figures/`)

| figura | provenienza |
|---|---|
| `fig1_sigmapx.pdf` | **script non conservato.** Dipendenza della persistenza media *H*₁ dei mock dal parametro adimensionale σ_px = *R*/Δ*x*. Dato in `results/phase6_sigma_px_test.json`. Rigenerabile. |
| `fig2_boundary.pdf` | **nessuno script, per costruzione.** La didascalia lo dichiara: *«demonstrated on a two-dimensional Gaussian random field (an illustration, not survey data)»*. Figura didattica su campo sintetico: non c'è un risultato dietro. |
| `fig3_dissolve.pdf` | **script non conservato, ma rigenerabile in poche righe.** La didascalia: *«Mock distributions in (a) and (b) are drawn as Gaussian densities from the frozen summary statistics (mean, scatter, N)»*. Servono cinque numeri, tutti in `src/paper2_v1_reference.json`: il rango empirico 98.0% del pannello (b) è `amplitude_statistic_retired.empirical_rank_pct`, con `pers1_DESI_NGC` 0.7246 contro `pers1_mock_mean` 0.6299 ± 0.0439. |
| `fig_phase9_beta1max_empirical.pdf` | `src/phase9_replot_beta1max.py` |
| `fig_phase9_w0_response.pdf` | `src/phase9_w0_response_curve.py` |

*Nota:* `src/cauchy_figures.py` produce una serie diversa (`fig2_betti_curve`, `fig4_feature_zscore`,
`fig5_hist_pers1`, `fig7_ramo_b`, `fig8_pk_vs_tda`): sono le figure del **preprint JCAP-B**, non del
manoscritto MNRAS. Le figure di M26 furono rifatte per la stesura MNRAS e quello script non è in `src/`.

---

## Paper 1 — MN-26-2388-P (`papers/paper1/MNRAS/figures/`)

| figura | provenienza |
|---|---|
| `fig_phase.pdf` | `src/paper1_rev_figures.py` |
| `fig_persistence.pdf` | `src/paper1_rev_figures.py` |
| `fig_spectral.pdf` | `src/paper1_rev_figures.py` |
| `fig_wbar.pdf` | `src/paper1_rev_figures.py` |
| `fig_resolution.pdf` | `src/paper1_rev_figures.py` |
| `fig_betti_matched.pdf` | `src/paper1_rev_fig_betti.py`, flag `--out` con default proprio quel nome. **Ha i cancelli incorporati:** `--no-gates` *«scrive la figura anche se i valori congelati non tornano»*, quindi in condizioni normali la figura è verificata contro i valori congelati. |
| `fig_retention_w.pdf` | **esclusa deliberatamente**, non orfana. `paper1_rev_figures.py:23`: *«Le figure esistenti (fig_betti_matched.pdf, fig_retention_w.pdf) NON vengono toccate.»* Documentato alla fonte. |

---

## Riepilogo

| | |
|---|---|
| con script identificato | **9** |
| illustrativa, nessun dato dietro | **1** (`fig2_boundary`) |
| rigenerabili dal dato congelato, script di impaginazione perduto | **2** (`fig1_sigmapx`, `fig3_dissolve`) |
| esclusa deliberatamente dalla rigenerazione | **1** (`fig_retention_w`) |
| **orfane senza spiegazione** | **0** |

---

## Due difetti trovati ricostruendo la mappa

1. **Il `.tex` di MNRAS non compilava.** Includeva `figures/fig1_sigmapx.pdf` e le altre quattro, ma
   quella cartella era finita sotto il preprint JCAP durante l'importazione. Corretto in `f0d9473`.
2. **`paper1_rev2.tex` include le figure senza prefisso di cartella** (`fig_phase.pdf`, non
   `figures/fig_phase.pdf`), mentre i file stanno in `figures/`. **Ancora da sistemare** — o
   spostando le figure accanto al `.tex`, o con `\graphicspath`. Sono modifiche a un manoscritto in
   revisione, quindi vanno fatte consapevolmente e non di passaggio.

---

## Nota per i README

`src/` contiene ~165 script, fra cui sonde diagnostiche usate una volta sola (`sonda_null_sgc.py`,
`trova_null_sgc.py`, `verifica_outlier_m26.py`) accanto a quelli che producono risultati citati. I
README devono distinguere i due gruppi: altrimenti chi apre `src/` trova 165 file senza gerarchia e
non sa da dove cominciare.
