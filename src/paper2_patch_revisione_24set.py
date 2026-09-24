#!/usr/bin/env python3
"""
paper2_patch_revisione_24set.py  -  passata documentale del 24 settembre (dopo il record 78)

Tre file, un passaggio:
  checklist_paper2.md    rev. 3.34 -> 3.35: D7 e D8 decisi coi testi; 3.2 col meccanismo; 3.6 ordine
                         delle coperture verificato; Fase 7 punti 1, 4, 5, 6, 7, 10 coi testi decisi
  paper2_stato.md        18a -> 19a revisione: paragrafo del 24, §3 record 78, §8 (Z-ancore-SGC,
                         Z-collinearita', F-copertura, Z-verdetti-nei-dati), §9, §12 errori 40-44, §13
  paper2_budget_5_1.md   riga 6 (fonte ed etichetta), riscontro (i) (il «trentaquattro volte»)

Stesso motore di paper2_patch_revisione_23set_b.py: ancora «prima» o «dopo»; ogni testo trovato
esattamente una volta; sha «dopo» atteso; inversa che ridà «prima»; fine riga e BOM misurati e
conservati. Precondizioni = i fatti che la 19a revisione dichiara.

Uso:
  python src\\paper2_patch_revisione_24set.py selftest
  python src\\paper2_patch_revisione_24set.py dry-run
  python src\\paper2_patch_revisione_24set.py apply
  python src\\paper2_patch_revisione_24set.py verify
"""
import argparse, hashlib, json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"

PRECONDIZIONI = {
 "src/paper2_v1_amendments.jsonl":  ("fb70459fca476145a791407e3bd1f5bd82f0dbc04e3f3d250309930bcf3f20a5", 663194),
 "src/paper2_append_amend78.py":    ("c24954afdb8d55bbc9620ed2f2fb35be8cbdff2a277d568405c7ff900bc14536", 34981),
 "src/paper2_freeze_verify.py":     ("d15a7a41c4dc4ea2b2c22d3364c3ea63731048add4e74bc591d42de7aaeaff40", 52181),
}
COMMIT = "95bc01d"
CENSIMENTO_78B = ROOT / "logs" / "censimento_rilascio_78b.jsonl"

# -- testi per il manoscritto (decisi il 23-24 set) ------------------------------------------------
T_D7 = ("      > *Proposition 1 is usually read as a restriction. It is also a guarantee: any error that acts on\n"
        "      > the filtered field as an increasing map of its cell values leaves the persistence diagram\n"
        "      > unchanged. This covers a global rescaling or re-normalization of the field, and any monotone\n"
        "      > remapping of its one-point distribution. It does not cover errors that act before smoothing,\n"
        "      > such as a luminosity-dependent bias, or weight errors that vary across the survey: these change\n"
        "      > the ordering of cell values and are not protected. For a linear bias the protection holds only\n"
        "      > approximately, in the regime where log(1 + δ) is linear in δ.*\n")
T_D8 = ("      > *A box pilot shows how much of the cosmological signal the cut-sky protocol compresses. Across\n"
        "      > three nwLH cosmologies in boxes of 1 h⁻¹Gpc (cell 7.81 h⁻¹Mpc, smoothing 5.0 h⁻¹Mpc), the\n"
        "      > relative dispersion of N_H1 is 16.0 per cent. Across the 2000 cut-sky mocks (cell 15.60 h⁻¹Mpc,\n"
        "      > same physical smoothing), the cosmological part of the dispersion is 0.74 per cent of the mean,\n"
        "      > and 0.88 per cent once HOD, downsampling and realization are included. The ratio, ~22, is an\n"
        "      > upper bound on the compression due to density matching, not a measurement of it. The two\n"
        "      > configurations also differ in tracer (dark matter against HOD galaxies), volume, cell size,\n"
        "      > boundary treatment and masked filtration. With three box realizations, its 68 per cent interval\n"
        "      > spans 16 to 52. If the smoothing is matched in grid units instead, the box dispersion is 15.3\n"
        "      > per cent and the ratio ~21.*\n")
T_73 = ("    > *Of the eleven limitations listed in M26 (§7), this paper closes (ix), the dependence on the\n"
        "    > fiducial cosmology through the Alcock–Paczyński response. It bounds, without closing, the\n"
        "    > sensitivity of the statistic to w₀: across the nwLH hypercube (w₀ from −1.3 to −0.7) the implied\n"
        "    > 1σ constraint is about ±0.6, an order of magnitude weaker than DESI BAO. Limitation (ii) concerns\n"
        "    > w_a ≠ 0, which that suite does not vary, and remains open. Limitation (vii) was closed in the\n"
        "    > revised M26, and (xi) largely by Paper 1 (§5.2). Open after this paper are fiber assignment (i),\n"
        "    > a single survey (iii), the error budget beyond cosmic variance (iv), the HOD calibration (v),\n"
        "    > the snapshot treatment (vi), and satellite profiles and redshift-space distortions (viii). For\n"
        "    > (vi) we bound only the growth term, at 0.2 per cent of the deficit, from two snapshots; (viii)\n"
        "    > is bounded at −0.8 per cent by Paper 1. Limitations (x) and (xi) are the subject of a\n"
        "    > forthcoming paper on point-cloud filtrations; (i), (iii)–(vi) and (viii) of one on survey\n"
        "    > systematics and additional tracers.*\n")
T_74 = ("    > *M26 (§7) points to point-cloud filtrations as the route to H₂ (limitation x). Paper 1 found that\n"
        "    > the deficit does not converge under grid refinement, falling from 20.3 to 14.2 per cent between\n"
        "    > 128³ and 256³, which makes the question whether the deficit is a property of the lattice the most\n"
        "    > direct one to answer next. A forthcoming paper takes it up; the other directions listed in M26\n"
        "    > remain planned.*\n")
T_75 = ("   > *The five one-point rules are not five independent tests. Across the 2000 realizations of each\n"
        "   > cap, two of them measure the same shape functional of ν: the standardized width (ν₉₉ − ν₁)/σ_ν\n"
        "   > and the excess kurtosis correlate at r = 0.999 (NGC) and 0.998 (SGC). The variance and the\n"
        "   > maximum of δ correlate at r = 0.88 and 0.83, a link carried by the tails (0.63 in rank in NGC),\n"
        "   > and the count of pathological voxels stands apart (|r| ≤ 0.65 with the others). The first\n"
        "   > principal component of the five carries 70 and 68 per cent of their variance, and three\n"
        "   > components carry 98 and 97 per cent. Their joint failure is evidence along about three\n"
        "   > directions, not five.*\n")
T_76 = ("   > *In the northern cap every stage of the pipeline reproduces a frozen value: the FKP weights to\n"
        "   > 3 × 10⁻¹⁰ on 60 realizations, the DESI field bit for bit. In the southern cap these two stages\n"
        "   > have no independent anchor and rely on the same code verified in the north. The mock-side counts\n"
        "   > are anchored in both caps.*\n")
T_77 = ("   > *Planning this analysis, we expected the weighting of the mocks to explain their one-point\n"
        "   > disagreement with the data. An asymmetric weighting would let the denominator of δ collapse in\n"
        "   > sparse cells and produce extreme voxels, so that reweighting would remove the extreme tail of δ,\n"
        "   > bring the variance ratio towards one, and reduce the leptokurtosis of the mocks in ν (+2.82 ±\n"
        "   > 0.46, against −0.44 in the data). None of this happened. The tail criterion gives R − 3σ = 967\n"
        "   > (NGC) and 2063 (SGC) against a threshold of 100; the maximum of δ ranks 0; reweighting increases\n"
        "   > the variance of δ slightly (2845.0 to 2857.7 in NGC); and the kurtosis moves by −0.013, leaving\n"
        "   > the data at z = −7.1 and −8.2. Two numerical bases of those expectations are also withdrawn:\n"
        "   > 32 244 was the maximum over realizations of the per-realization maximum of δ, and the factor 1085\n"
        "   > came from one of two implementations of the variance ratio. The weighting is corrected in the v2\n"
        "   > ensemble and its effect on N_H1 is measured (Table 8, row 4), but the reference ensemble remains\n"
        "   > v1, and the one-point disagreement between mocks and data remains open. Three design choices\n"
        "   > also changed with respect to that plan: the title; the statistic, N_H1 at k = 1 with empirical\n"
        "   > ranks in place of β₁^max; and the fiducial grid, (α_iso, F_AP) in place of Ω_m × w₀, since\n"
        "   > Proposition 2 fixes the isotropic part.*\n")

CHECKLIST = [
 ("### rev. 3.34 — 23 settembre 2026, sera — Fase 7 aperta:",
  "### rev. 3.35 — 24 settembre 2026 — record 78; **le misure della Fase 7 sono finite**: il +86 di SGC `idx` 81 è una divergenza fra catene (R3 contro `paper1_remap`, cammino della geometria), già a *k* = 0; la riga 6 del budget ha un registro (`phase9_growth_mismatch.json`) e misura due snapshot, non un cono di luce; il «trentaquattro volte» del budget è un artefatto di cancellazione; la limitazione (ii) riguarda *w*_a, che nwLH non varia, e resta aperta; D8 vale ~22 (68 % 16–52) e non ~17. **D7 e D8 decisi**; ordine delle coperture verificato sul registro (26 % confermato); **Fase 7, punti 1, 4, 5, 6, 7 e 10 coi testi decisi**. Restano gli ultimi punti.\n"
  "### rev. 3.34 — 23 settembre 2026, sera — Fase 7 aperta:"),
 ("- [ ] **✦ D7 — Invarianza monotona come pregio.** Riformulare la Prop. 1 anche come **garanzia di\n"
  "      robustezza**: immunità per teorema agli errori di calibrazione dell'ampiezza, al bias di\n"
  "      luminosità e a qualunque errore moltiplicativo nei pesi.\n",
  "- [x] **✦ D7 — Invarianza monotona come pregio. DECISA il 23 set (rev. 3.35).** *(Testo originale:\n"
  "      riformulare la Prop. 1 come garanzia di robustezza, «immunità per teorema agli errori di\n"
  "      calibrazione dell'ampiezza, al bias di luminosità e a qualunque errore moltiplicativo nei pesi».)*\n"
  "      **Correzione:** la Prop. 1 copre una *g* crescente applicata ai **valori di cella** del campo\n"
  "      filtrato, cioè dopo log(1+δ), lisciatura e sottrazione della media. Un bias *b*δ entra prima del\n"
  "      log e della convoluzione, e un errore di peso che varia con la posizione cambia il campo invece\n"
  "      di riparametrizzarlo: nessuno dei due è coperto per teorema; il bias lineare solo dove il log è\n"
  "      lineare. Testo per il §2, dopo la Prop. 1:\n" + T_D7),
 ("- [ ] **✦ D8 — Il confronto scatola/cut-sky con la sua riserva.** 15.3% contro 0.88%, fattore ~17.\n"
  "      **Non attribuibile al density matching da solo**: volume, geometria, cella (7.81 contro 15.60),\n"
  "      bordo e mascheratura differiscono. È un **limite superiore**, e va scritto così.\n",
  "- [x] **✦ D8 — Il confronto scatola/cut-sky con la sua riserva. DECISA il 23 set, record 78 F.**\n"
  "      *(Testo originale: 15.3% contro 0.88%, fattore ~17; non attribuibile al density matching da solo;\n"
  "      limite superiore.)* **Il ~17 usava due scelte che abbassano il numero:** σ_px in voxel (0.3204,\n"
  "      cioè 2.5 h⁻¹Mpc fisici in scatola contro 5.0 nel cut-sky) e la sd **totale** del cut-sky (0.883 %:\n"
  "      cosmologia, HOD, downsampling, realizzazione). Omogeneo: scatola a 0.64 voxel = 5.0 h⁻¹Mpc,\n"
  "      **16.0 %**, contro la sola parte cosmologica, **0.738 %** (`attenuation` 0.8355): **~22, 68 % da\n"
  "      16 a 52** con *N* = 3 (2 gradi di libertà). Resta un limite superiore; il tracciante (materia\n"
  "      oscura contro galassie HOD) è un sesto confondente. Sorgenti: `rev_v3b_pilot_box_report.json`\n"
  "      (pilota del Paper 1), `per_mock_NGC_R5.jsonl` (35 436.686, sd 313.0), `compD_NGC.jsonl`.\n"
  "      Testo per il §6:\n" + T_D8),
 ("      pareggio dichiarato (3 generatori), ma **è un'asimmetria fra emisferi e va riportata**, non\n"
  "      nascosta nell'arrotondamento.\n",
  "      pareggio dichiarato (3 generatori), ma **è un'asimmetria fra emisferi e va riportata**, non\n"
  "      nascosta nell'arrotondamento.\n"
  "      **✦ rev. 3.35 — meccanismo corretto (record 78, voci A e B):** non è rumore di pareggio. 161 dei\n"
  "      165 generatori sommati a *k* = 0 vengono da **due mock**, SGC 24 (+92) e 81 (+69), il cui campo in\n"
  "      `fase3_mock` non è quello del Paper 1 (`D4a_stab_ok` falso, Δν fino a 13.7, circa 91 livelli):\n"
  "      divergenze fra catene, le stesse del ramo unitario v2. Il «va riportata» regge; il meccanismo no.\n"),
 ("      coperture, letto qui come NGC, NGC, SGC, SGC (da cui il 26 % di SGC *k* = 2).\n",
  "      coperture, letto qui come NGC, NGC, SGC, SGC (da cui il 26 % di SGC *k* = 2).\n"
  "      **✦ rev. 3.35 — verificato il 24 set** su `fase3_budget.jsonl`, passata 18/19 del 6 set\n"
  "      (`k0`–`k3`): copertura = `prop2_floor` / `unattributed_rms`, carving escluso. NGC 85.5, 79.9,\n"
  "      84.6, 44.4 %; SGC 83.5, 51.6, **25.9**, 10.5 %. L'ordine è quello letto. Con `total_systematic_on_b`\n"
  "      i valori scendono di 0.1–1.3 punti: nel paper si dice quale denominatore. Il cancello di\n"
  "      riproduzione regge a **livello intero** (`k0`, `k1` identici fra le passate 16/17 e 18/19), non\n"
  "      solo sul pavimento.\n"),
 ("1. Introduzione: la domanda della funzione di risposta; le limitazioni (ix) e (ii).",
  "1. Introduzione: la domanda della funzione di risposta; la limitazione (ix) e il limite su *w*₀.\n"
  "   **✦ rev. 3.35:** non «(ix) e (ii)»: la (ii) è *w*_a ≠ 0, che nwLH non varia (record 78 E)."),
 ("4. Il canale anisotropo: griglia (α_iso, *F*_AP), w̄ per punto, esclusioni, tiling, **test di\n"
  "   completezza della parametrizzazione**.\n",
  "4. Il canale anisotropo: griglia (α_iso, *F*_AP), w̄ per punto, esclusioni, tiling, **test di\n"
  "   completezza della parametrizzazione**.\n"
  "   **✦ rev. 3.35 — ancore di SGC (Z-ancore-SGC), dichiarate e non prodotte:** in SGC non esiste un\n"
  "   valore congelato da cui partire, e produrlo sarebbe una ricostruzione. Testo:\n" + T_76),
 ("   `forma_lato_mock_v3.json`, e il 26 % dell'ultimo aspetta la verifica dell'ordine delle coperture:\n",
  "   `forma_lato_mock_v3.json`, e il 26 % dell'ultimo è **verificato sul registro** (rev. 3.35, vedi 3.6):\n"),
 ("   come parametro guida, il tetto di sensibilità, il tetto di *R*².\n",
  "   come parametro guida, il tetto di sensibilità, il tetto di *R*².\n"
  "   **✦ rev. 3.35:** qui il testo di D8 (Fase 4D).\n"),
 ("   luglio: il §4 del programma chiede che ogni ritiro sia dichiarato nel manoscritto che lo\n"
  "   eredita.\n",
  "   luglio: il §4 del programma chiede che ogni ritiro sia dichiarato nel manoscritto che lo\n"
  "   eredita.\n"
  "   **✦ rev. 3.35 — deciso il 24 set.** Nel testo un paragrafo; le tabelle delle smentite (A 12, A-bis\n"
  "   1, B 6, D6 e `SGC_PRED` 6, §5-bis) in appendice. **La riga 11 della 6.5 resta fuori dal\n"
  "   manoscritto:** il Paper 1 non attribuisce la curtosi alla pesatura (Z-P1-curtosi), e dichiararla\n"
  "   ritirata gli attribuirebbe in pubblico una frase che non contiene. Resta nel documento 6.5 e nel\n"
  "   ledger. Testo:\n" + T_77 +
  "   **Z-collinearità, misurata il 24 set** su `onepoint_v1_{NGC,SGC}.jsonl` (le cinque statistiche\n"
  "   identificate riproducendo 2845.0, 4048.21, 2811.56, 9886.23 e il *r* = 0.9988 del B3): i blocchi\n"
  "   con |*r*| ≥ 0.8 sono tre, il secondo solo in Pearson. Testo:\n" + T_75),
 ("la dichiarazione è scrittura. **✦ rev. 3.33:**\n"
  "    dichiarare anche la promozione del «3-bis» a Paper 3, davanti ai test sui sistematici DESI,\n"
  "    come riformulazione motivata dai risultati di risoluzione del Paper 1 (`canovaccio_paper3.md`\n"
  "    §10; l'ordine dei *next steps* è pubblico in M26 §7 e nel Paper 1 §9.4).",
  "la dichiarazione è scrittura. **✦ rev. 3.33:**\n"
  "    dichiarare anche la promozione del «3-bis» a Paper 3, davanti ai test sui sistematici DESI,\n"
  "    come riformulazione motivata dai risultati di risoluzione del Paper 1 (`canovaccio_paper3.md`\n"
  "    §10; l'ordine dei *next steps* è pubblico in M26 §7 e nel Paper 1 §9.4).\n"
  "    **✦ rev. 3.35 — decisi il 24 set.** Limitazioni: la mappa del programma assegnava la (ii) al\n"
  "    Paper 2, ma la (ii) è *w*_a e nwLH varia solo *w*₀ (record 78 E): resta aperta. La (vi) è limitata\n"
  "    solo sulla crescita. Testo:\n" + T_73 +
  "    Nota sul «3-bis»: **non** dice che M26 prevedeva un altro ordine e **non** cita il §9.4 del Paper 1\n"
  "    (nessuna voce di `modifiche_paper1.md` lo tocca; se ne nascerà una, il testo si riapre). Testo:\n"
  + T_74.rstrip("\n")),
]

STATO = [
 ("aggiornato **23 settembre 2026**, diciottesima revisione", "aggiornato **24 settembre 2026**, diciannovesima revisione"),
 ("checklist **rev. 3.34** (`32560222…`) · `modifiche_paper1.md` `2425045c…` · commit fino a `5344b96`.",
  "checklist **rev. 3.34** (`32560222…`) · `modifiche_paper1.md` `2425045c…` · commit fino a `5344b96`.\n"
  "\n"
  "**Al 24 settembre (diciannovesima revisione):** **record 78** (ledger 78 righe, `fb70459f…`, 663 194\n"
  "byte, coda LF ereditata, prefisso verificato; freeze_verify CLEAN 78/78; rilascio **PULITO** su 154\n"
  "percorsi dopo il commit `95bc01d`) · **le misure della Fase 7 sono finite**: il +86 di SGC `idx` 81\n"
  "è una divergenza fra catene già a *k* = 0; la riga 6 ha un registro; il «trentaquattro volte» è un\n"
  "artefatto di cancellazione (SGC diverge **meno** spesso); la (ii) riguarda *w*_a e resta aperta; D8\n"
  "vale ~22 (68 % 16–52) · D7, D8 e i testi dei punti 1, 4–7 e 10 della Fase 7 decisi · checklist\n"
  "**rev. 3.35** · restano gli ultimi punti: 6.0a, 6.2-iii, `gate_preinvio`, Zenodo."),
 ("## 3. Il registro degli emendamenti — 77 record\n\n### Fase 6, record 61–77\n",
  "## 3. Il registro degli emendamenti — 78 record\n\n"
  "### Fase 7, record 78\n\n"
  "| # | utc | item (reso dal ledger) |\n"
  "|---|---|---|\n"
  "| 78 | 24 set 04:10 | `7.10-7.11-7.12-7.3-D8/misure_della_fase_7_idx81_divergenza_fra_catene_riga6_con_registro_34x_cancellazione_limitazione_ii_d8` |\n\n"
  "### Fase 6, record 61–77\n"),
 ("| **Z-ancore-SGC** | SGC non ha ancore proprie | dipende | Se un cubo ν congelato per SGC è producibile, l'eredità dal percorso NGC diventa una verifica. Altrimenti va dichiarato nel manoscritto |",
  "| ~~**Z-ancore-SGC**~~ | ~~SGC non ha ancore proprie~~ **CHIUSA il 24 set** | scrittura | Dichiarata, non prodotta: pesi FKP e cubo ν di SGC ereditano dal codice verificato in NGC (`n_confronti_n6_wfkp` = 0 in SGC); il lato mock è ancorato in entrambi. Testo nella checklist, Fase 7 punto 4 |"),
 ("| **Z-collinearità** | tre direzioni, non cinque | scrittura | Le cinque regole a un punto coprono tre direzioni. Va detto nel testo: cinque test correlati non sono cinque prove |",
  "| ~~**Z-collinearità**~~ | ~~tre direzioni, non cinque~~ **MISURATA il 24 set** | scrittura | Il «tre» non aveva sorgente. Su `onepoint_v1_*`: larghezza standardizzata–curtosi *r* = 0.999/0.998, varianza–massimo di δ 0.88/0.83 (0.63 in rango, NGC), `n_patologici` a parte; prima componente 70/68 %, tre 98/97 %. Testo nella checklist, Fase 7 punto 7 |\n"
  "| **Z-verdetti-nei-dati** | un verdetto scritto in un registro di dati e mai letto | contratto di `gate_preinvio` | `D4a_stab_ok` falso in 4 record di produzione di `fase3_mock` dal 30 ago, senza che un cancello lo leggesse (record 78 G). Il censimento dei registri legge i verdetti dei registri di gate, non i campi di verdetto dentro i dati: va nel contratto, prima di scrivere lo strumento |"),
 ("Resta aperta, con numeri; l'ordine delle coperture è da verificare sul registro |",
  "Resta aperta, con numeri. **Ordine delle coperture verificato il 24 set** sul registro: NGC, NGC, SGC, SGC; il 26 % di SGC *k* = 2 regge (25.9 %) |"),
 ("| `paper2_patch_revisione_23set_b.py` | checklist 3.34, questo documento alla 18ª, P1-11 punto 5, due voci delle eccezioni | 8/8 |",
  "| `paper2_patch_revisione_23set_b.py` | checklist 3.34, questo documento alla 18ª, P1-11 punto 5, due voci delle eccezioni | 8/8 |\n"
  "| `paper2_append_amend78.py` | record 78: ricalcola ogni numero da 12 registri; terminatore ereditato e prefisso verificato; percorsi citati tracciati o già eccettuati | 12/12 |\n"
  "| `paper2_patch_revisione_24set.py` | checklist 3.35, questo documento alla 19ª, budget righe 6 e riscontro (i) | 7/7 |"),
 ("| **34** | una grandezza con due nomi dentro lo stesso registro | `ancora_n6_wfkp` e `diagnostica_n6_wfkp`: il difetto del record 52, in un registro invece che fra due |",
  "| **34** | una grandezza con due nomi dentro lo stesso registro | `ancora_n6_wfkp` e `diagnostica_n6_wfkp`: il difetto del record 52, in un registro invece che fra due |\n"
  "| **40** | chiave presunta da **un** record letto | tre volte in una sessione (`FID`, `D4a_max_dnu`, `$n` scalare): la forma della 22, sui nomi invece che sui valori |\n"
  "| **41** | `fase3_mock` letto con lo smoke | il §13 di questo documento lo diceva, coi sei conflitti e il 35318 contro 35538: **una regola scritta e non letta** |\n"
  "| **42** | rapporto con un denominatore che si compensa | il «trentaquattro volte»: −17 netti su 1 927 in valore assoluto. La base del confronto va scelta prima |\n"
  "| **43** | censimento del rilascio prima del commit | `citati_committati` FAIL sui due file appena scritti: la forma della 17 |\n"
  "| **44** | un verdetto scritto e mai letto | `D4a_stab_ok` falso dal 30 ago: un campo di verdetto non è un cancello finché nessuno lo legge |"),
 ("| `fase3_mock.jsonl` | 2038 record, `k0…k3` su sedici punti, **due emisferi**, **38 record `smoke`** |",
  "| `fase3_mock.jsonl` | 2038 record, `k0…k3` su sedici punti, **due emisferi**, **38 record `smoke`**; nella produzione `D4a_stab_ok` è falso solo per SGC 24 e 81 (divergenze fra catene, record 78) |"),
]

BUDGET = [
 ("| 6 | snapshot contro lightcone | −53 ± 112 per unità di *z*, Δ*z* ≈ 0.25 | M26 §7 (vi); Paper 1 Tab. 8 |",
  "| 6 | crescita, da due snapshot (*z* = 0.5 e 0) | −53 ± 112 per unità di *z*, Δ*z* ≈ 0.25 | `phase9_growth_mismatch.json` (30 coppie appaiate, record 78 C); M26 §7 (vi) |"),
 ("(+0.27). L'SGC scarta circa **trentaquattro volte** più del NGC — vale la pena sapere perché, ma\n"
  "su qualunque",
  "(+0.27). Il rapporto fra i due scarti, circa trentaquattro, **non misura un'asimmetria** (record 78,\n"
  "voce D): le divergenze fra catene sono l'1.15 % in NGC e lo 0.70 % in SGC, 1 927 e 1 468 generatori\n"
  "in valore assoluto, e in NGC si compensano di segno (−17) mentre in SGC no (+536). In ogni caso,\n"
  "su qualunque"),
]

FILE = {  # percorso -> (sha prima, sha dopo, fine riga, sostituzioni, json)
 "papers/paper2/checklist_paper2.md":  ("325602227db36512532df562e4901efc22d7b854010bec20913bb6e7328d7391", "d4fcdb963229992bf2df653133d2d5c6859acb8206fc5a9629e8a12155e09b6d", "\n", CHECKLIST, False),
 "papers/paper2/paper2_stato.md":      ("9d5014c43f58c00277c2845bb1536a80070b9cd7a87052459c2914b69315f40e", "c99be01367c400745b7e6604b09ab9610e288b8c8e052483e76ae5456c5e8454", "\r\n", STATO, False),
 "papers/paper2/paper2_budget_5_1.md": ("97b59d0b3c89be7f55fd80809fa1fc5a5b3f96071d8764c6070eebc5b88dc95b", "0c7eef5b083cc443bc26cff9488164d21b13e00b46731f491ee85ec52e9427a7", "\n", BUDGET, False),
}

BOM = b"\xef\xbb\xbf"
def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def serializza(d): return (json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

def misura_eol(raw: bytes) -> str:
    crlf, lf = raw.count(b"\r\n"), raw.count(b"\n")
    if crlf and crlf == lf: return "\r\n"
    if not crlf and b"\r" not in raw: return "\n"
    raise ValueError(f"fine riga misti: {crlf} CRLF su {lf} LF")

def trasforma(raw: bytes, eol: str, sost: list, inversa=False, is_json=False) -> bytes:
    bom = raw.startswith(BOM)
    if misura_eol(raw) != eol: raise ValueError(f"fine riga misurata diversa da {eol!r}")
    if is_json and serializza(json.loads(raw.decode("utf-8"))) != raw: raise ValueError("JSON: formato non riprodotto")
    t = raw[len(BOM) if bom else 0:].decode("utf-8")
    passi = [(b, a) for a, b in reversed(sost)] if inversa else sost
    for i, (a, b) in enumerate(passi):
        a2, b2 = a.replace("\n", eol), b.replace("\n", eol)
        k = t.count(a2)
        if k != 1: raise ValueError(f"sostituzione {i}: {k} occorrenze di «{a[:50]}»")
        t = t.replace(a2, b2)
    out = (BOM if bom else b"") + t.encode("utf-8")
    if is_json and serializza(json.loads(out.decode("utf-8"))) != out: raise ValueError("JSON: il risultato non si riserializza uguale")
    return out

def precondizioni() -> list:
    err = []
    for rel, (s, n) in PRECONDIZIONI.items():
        p = ROOT / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        raw = p.read_bytes()
        if sha(raw) != s or len(raw) != n: err.append(f"diverso dall'atteso: {rel}")
    c = [json.loads(l) for l in CENSIMENTO_78B.read_text(encoding="utf-8").splitlines() if l.strip()][-1] if CENSIMENTO_78B.exists() else {}
    if c.get("esito") != 0 or c.get("percorsi_distinti") != 154:
        err.append("censimento del rilascio 78b: non e' PULITO su 154 percorsi")
    r = subprocess.run(["git", "merge-base", "--is-ancestor", COMMIT, "HEAD"], cwd=ROOT)
    if r.returncode != 0: err.append(f"git: {COMMIT} non e' antenato di HEAD")
    return err

def prepara() -> dict:
    piano, err = {}, []
    for rel, (prima, dopo, eol, sost, js) in FILE.items():
        p = ROOT / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        raw = p.read_bytes(); s = sha(raw)
        if s == dopo: piano[rel] = None; continue
        if s != prima: err.append(f"{rel}: sha {s[:12]}..., ne' prima ne' dopo"); continue
        try:
            nuovo = trasforma(raw, eol, sost, is_json=js)
            if sha(nuovo) != dopo: err.append(f"{rel}: risultato {sha(nuovo)[:12]}..., atteso {dopo[:12]}..."); continue
            if sha(trasforma(nuovo, eol, sost, inversa=True, is_json=js)) != prima: err.append(f"{rel}: l'inversa non ridà il file"); continue
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
        print(f"{rel}: {sha(raw)[:12]}... {len(raw)} B -> {sha(nuovo)[:12]}... {len(nuovo)} B, {len(FILE[rel][3])} sostituzioni, inversa OK")
    if not scrivi: print("[dry-run] niente scritto."); return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for rel, v in piano.items():
        if v is None: continue
        raw, nuovo = v; p = ROOT / rel
        (LOGS / f"{p.name}.bak_{ts}").write_bytes(raw)
        tmp = p.with_name(p.name + ".tmp"); tmp.write_bytes(nuovo); os.replace(tmp, p)
        if sha(p.read_bytes()) != FILE[rel][1]: raise SystemExit(f"STOP: {rel} riletto non coincide")
        print(f"[apply] {rel}: scritto e riletto; backup logs\\{p.name}.bak_{ts}")

def verify():
    ok = True
    for rel, (prima, dopo, _, _, _) in FILE.items():
        s = sha((ROOT / rel).read_bytes())
        st = "dopo" if s == dopo else ("prima" if s == prima else "ALTRO")
        ok &= st == "dopo"; print(f"{rel}: {st} ({s[:12]}...)")
    print("verify", "OK" if ok else "ANOMALIA"); sys.exit(0 if ok else 1)

def selftest():
    ok = 0
    lf = "a\nuno X due\nb\n".encode(); crlf = lf.replace(b"\n", b"\r\n"); s = [("uno X", "uno Y\nriga nuova")]
    assert trasforma(lf, "\n", s) == b"a\nuno Y\nriga nuova due\nb\n"; ok += 1
    assert trasforma(crlf, "\r\n", s) == b"a\r\nuno Y\r\nriga nuova due\r\nb\r\n"; ok += 1
    assert trasforma(trasforma(crlf, "\r\n", s), "\r\n", s, inversa=True) == crlf; ok += 1
    for doppio in (b"X X\n", b"niente\n"):
        try: trasforma(doppio, "\n", [("X", "Y")]); raise AssertionError
        except ValueError: pass
    ok += 1
    try: trasforma(b"a\r\nb\n", "\n", [("a", "c")]); raise AssertionError
    except ValueError: pass
    ok += 1
    for rel, (prima, dopo, eol, sost, js) in FILE.items():
        assert len(prima) == 64 and len(dopo) == 64 and prima != dopo and all(a != b and "\r" not in a + b for a, b in sost)
    ok += 1
    testi = T_D7 + T_D8 + T_73 + T_74 + T_75 + T_76 + T_77
    assert "§9.4" not in T_74 and "planned" in T_74 and "remains open" in T_73 and "22" in T_D8 and "attribu" not in T_77; ok += 1
    print(f"selftest: {ok}/7 OK")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[ap.parse_args().cmd]()
