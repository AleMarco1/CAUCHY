# Paper 1 — MN-26-2388-P

**Struttura a un punto contro topologia *H*₁ nella DESI BGS.** Preprint 31 luglio 2026;
ri-sottomesso dopo revisione maggiore.

I sorgenti del manoscritto, le figure, il proof e la corrispondenza editoriale **non sono in questo
repository**: il lavoro è sotto valutazione. Stanno in `papers/paper1/MNRAS/` sul disco dell'autore,
esclusi via `.gitignore`, e saranno depositati alla pubblicazione.

## Record di lavoro, versionati

| file | contenuto |
|---|---|
| `paper1_preregistration_protocol.md` | protocollo pre-registrato, predizioni dichiarate prima dei risultati |
| `paper1_frozen_record.md` | valori congelati e loro provenienza |
| `paper1_record_consolidato.md`, `paper1_record_finale.md` | verbali consolidati delle misure |
| `paper1_sigma_discrepancy_resolution.md` | risoluzione della discrepanza di dispersione NGC (445 in M26 contro 313 qui) |
| `paper1_variance_decomposition.md` | decomposizione della varianza dell'ensemble |
| `stato_revisione_paper1.md` | stato della revisione |

## Il risultato primario

*N*_H1 = numero di generatori *H*₁ a *R* = 5 h⁻¹Mpc, erosione *k* = 1 come primaria, con **rango
empirico** nell'ensemble dei mock come statistica di significatività — non z parametrico.

| | DESI | mock (*n* = 2000) | deficit | rango |
|---|---|---|---|---|
| NGC | 28 256 | 35 436.686 ± 312.989 | 20.26% | 1/2001 |
| SGC | 15 122 | 18 712.9675 ± 197.787 | 19.19% | 1/2001 |

Sorgenti: `results/paper1/per_mock_{NGC,SGC}_R5.jsonl` → `base.N_H1`, deviazione standard con
`ddof = 1`. I record di M26 (35 467.15 / 18 693.595) sono **superseded**: differiscono di ∓0.10 σ
con segno opposto nei due emisferi, firma di una collisione di percorsi in cui i mock 0–199 furono
sovrascritti da un run con un HOD diverso.

## Figure

Vedi `papers/FIGURE_PROVENANCE.md`. Cinque figure da `src/paper1_rev_figures.py`,
`fig_betti_matched.pdf` da `src/paper1_rev_fig_betti.py` (che porta i cancelli incorporati), e
`fig_retention_w.pdf` esclusa deliberatamente dalla rigenerazione, come dichiarato alla riga 23 di
`paper1_rev_figures.py`.

## Script della revisione

I `src/paper1_rev_*.py` rispondono ai rilievi dei referee: `n1`/`n1b`/`n1c` spettrali e bandpower,
`n2` persistenza, `n4n5` stabilità di Tabella 3 e incertezze omogenee, `n6` FKP, `n7` NFW, `n8`
maschere, `n9` risoluzione, `n10` fasi, `m1` risposta cosmologica, `m2`/`m2b` fiduciale e scatter
HOD. Gli output corrispondenti sono in `results/paper1/`.

## Da correggere alla prossima revisione

`paper1_rev2.tex` include le figure **senza prefisso di cartella** (`fig_phase.pdf` invece di
`figures/fig_phase.pdf`), mentre i file stanno in `figures/`: il manoscritto non compila così com'è.
Si risolve con `\graphicspath` o spostando le figure accanto al `.tex`.

**Voce aperta, R2.6.** Il taglio della maschera è descritto come «P10 della densità dei random». Non
è un percentile: la regola è `field_r > 0.01 * field_r.mean()` sul cubo intero
(`phase6_bgs_voxelize.py:182-183`), che taglia NGC a P3.914 e SGC a P3.403 — percentili **diversi
nei due emisferi**. Il P10 non riproduce la maschera congelata (288 307 voxel contro 307 805,
Jaccard 0.9367). E fra P5 e P10 lo z della **skewness inverte segno** (−4.58 → +7.69), mentre media,
deviazione standard e curtosi mantengono il segno su P5–P15. La maschera realmente usata sta dal
lato P5, quindi il valore pubblicato è sul lato giusto della propria maschera: a richiedere
correzione sono l'etichetta e l'affermazione di stabilità. Evidenza in
`results/paper1/rev_n4n5_report.json` (`p10_riproduce_congelata: false`).
