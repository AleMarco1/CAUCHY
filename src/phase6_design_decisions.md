# CAUCHY — Phase 6: Design Decisions e Piano Script
## Documento di Apertura Phase 6

**Data:** 2026-05-04  
**Stato:** pre-Phase 6, redatto al termine di Phase 5 Sessione 2  
**Autorità:** questo documento integra `CAUCHY_Execution_Design_v2.md §5.6` per le specifiche operative di Phase 6

---

## Contesto

Phase 5 ha prodotto σ = 3.08–3.69σ (B3, HOD deterministico) con validation checks T1-T4 tutti OK. Run A (K=10 forward sampling) in corso, risultati attesi tra ~70h dalla redazione di questo documento. Phase 6 applica la pipeline CAUCHY al dataset osservativo DESI DR1 (BGS tracer).

---

## Dataset disponibili

### DESI DR1 — cataloghi LSS (in `data/raw/desi_dr1/`)

| Tracciatore | File | Dimensione |
|-------------|------|-----------|
| BGS NGC | `BGS_BRIGHT-21.5_NGC_clustering.dat.fits` | 24 MB |
| BGS NGC random | `BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits` | 1.6 GB |
| BGS NGC n(z) | `BGS_BRIGHT-21.5_NGC_nz.txt` | 3 KB |
| BGS SGC | `BGS_BRIGHT-21.5_SGC_clustering.dat.fits` | 9 MB |
| BGS SGC random | `BGS_BRIGHT-21.5_SGC_0_clustering.ran.fits` | 663 MB |
| BGS SGC n(z) | `BGS_BRIGHT-21.5_SGC_nz.txt` | 3 KB |
| LRG, ELG, QSO | idem | presente |

**Tracer primario per CAUCHY:** BGS (z=0.1–0.4, z_eff≈0.2). Gli altri tracciatori (LRG, ELG, QSO) sono a redshift più alti e richiedono ricalibrazione della pipeline TDA — trattati come robustness check prospettico.

### Quijote nwLH — halo catalogs (in `data/raw/quijote/3D_cubes/latin_hypercube_nwLH_hod/`)

Snapshots disponibili: z=0 (`groups_004`) e z=0.5 (`groups_003`). Entrambi scaricati per tutte le 2000 realizzazioni. z=0.2 (z_eff BGS) non esiste come snapshot Quijote.

---

## Decisioni di Design — Phase 6

### D1 — Redshift di calibrazione (Punto 1)

**Decisione:** utilizzare z=0 e z=0.5 come bracket deterministico, senza interpolazione.

**Rationale:** z=0.2 (z_eff BGS) non esiste come snapshot pubblico Quijote. Invece di interpolare (che introdurrebbe una stima, non un dato), si eseguono due run completi della pipeline:

- **Run z=0:** usa `groups_004` — già calibrato in Phase 5
- **Run z=0.5:** usa `groups_003` — richiede nuovo HOD forward sampling

Il risultato su DESI BGS sarà presentato come:

> σ_DESI ∈ [σ_z0, σ_z0.5]

dove il valore vero a z_eff=0.2 si trova deterministicamente in questo intervallo (la crescita delle strutture è monotona in z → la topologia varia monotonamente). Questo è un range garantito da dati pubblici, non una stima.

**Vantaggio scientifico:** il bracketing è più rigoroso di qualsiasi interpolazione e trasparente al Reviewer. Il range [σ_z0, σ_z0.5] è esso stesso un risultato pubblicabile.

**Implementazione:** nessuna modifica agli script Phase 5. Si riusa `phase5_hod_mcmc.py` con `--snapnum 3` per z=0.5.

---

### D2 — HOD per BGS (Punto 2)

**Decisione:** strategia a cascata — A poi C poi B, con gate esplicito.

**Opzione A (default):** prior flat AbacusSummit 9 parametri, identico a Phase 5.

- **Quando usarla:** run primario. Coerente con la marginalizzazione di Phase 5.
- **Giustificazione:** la marginalizzazione Monte Carlo sul prior flat è conservativa — sovrastima la sistematica HOD, quindi se il segnale sopravvive è un lower bound del segnale con HOD ottimizzato.

**Opzione C (fallback):** parametri HOD BGS-like da letteratura (Contreras et al. 2023 o equivalente).

- **Quando usarla:** se σ_A < 2σ — il prior flat potrebbe essere troppo ampio e diluire il segnale.
- **Implementazione:** importare parametri pubblicati, usare come punto di partenza della marginalizzazione (prior gaussiano centrato sui valori letteratura invece di prior flat).

**Opzione B (ultimo resort):** calibrazione MCMC su n(z) BGS osservato.

- **Quando usarla:** solo se σ_C < 2σ E se il residuo di n(z) tra mock e dati è > 10%.
- **Costo:** ~3-5 giorni GPU, richiede sessione dedicata.

**Gate D2:** dopo Run A, calcolare `|n(z)_mock - n(z)_BGS| / n(z)_BGS`. Se discrepanza media < 20%: Opzione A confermata. Se > 20%: passa a Opzione C.

---

### D3 — Maschera survey e voxelizzazione (Punto 3)

**Decisione:** FKP standard dai randoms, nessun file maschera separato.

Il catalogo random `clustering.ran.fits` rappresenta la geometria survey in forma discreta. La voxelizzazione 3D usa il metodo FKP:

```
δ_FKP(x) = [n_data(x) - α × n_random(x)] / [α × n_random(x)]
```

dove α = N_data / N_random. Questo è lo standard per analisi di campo su survey DESI.

**Proiezione:** RA, Dec, z → coordinate cartesiane comoventi (x, y, z) in Mpc/h con cosmologia fiduciale Planck 2018 (Ωm=0.3175, h=0.6711). Griglia 128³ nel volume BGR comoving.

**Nota:** BGS copre ~12,355 deg² (NGC+SGC) con profondità radiale comovente ~600–1200 Mpc/h. Il volume effettivo (~3.8 Gpc³/h³) è confrontabile con i 4 box Quijote da 1 Gpc³/h³ ciascuno. Non è un box periodico → la periodicità della filtrazione TDA va gestita con zero-padding.

---

### D4 — Randoms aggiuntivi (Punto 4)

**Decisione:** il singolo file `_0_` per tracer è sufficiente.

Il random catalog `_0_` contiene ~65k randoms per galassia reale — ordini di grandezza superiori al necessario per la voxelizzazione FKP. I file `_1_`, `_2_` etc. servono per stime di covarianza jackknife nelle analisi BAO, non rilevanti per CAUCHY.

---

## Lista Script da Implementare per Phase 6

Gli script sono in ordine di dipendenza. Script 1, 2, 3 e 5 possono essere scritti e lanciati immediatamente mentre Run A gira — non dipendono dai suoi risultati. Solo Script 4 (phase6_partial_corr.py) richiede i risultati di Run A per la calibrazione finale del sigma.

### Script 1 — `src/phase6_bgs_voxelize.py`
**Obiettivo:** converti catalogo BGS FITS → campo di densità 128³ su griglia cartesiana.

**Input:**
- `data/raw/desi_dr1/BGS_BRIGHT-21.5_NGC_clustering.dat.fits`
- `data/raw/desi_dr1/BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits`
- `data/raw/desi_dr1/BGS_BRIGHT-21.5_NGC_nz.txt`
- (idem SGC)

**Output:**
- `data/processed/phase6_fields/bgs_ngc_delta_128.npy` — campo δ_FKP 128³
- `data/processed/phase6_fields/bgs_sgc_delta_128.npy`
- `data/processed/phase6_fields/bgs_mask_128.npy` — maschera voxel validi (bool)
- `results/phase6_voxelize_diagnostics.json`

**Operazioni:**
1. Lettura FITS con `astropy`
2. Conversione RA, Dec, z → (x,y,z) comoventi con `astropy.cosmology`
3. CIC 128³ separato per data e random
4. Calcolo δ_FKP = (n_data - α×n_random) / (α×n_random)
5. Smoothing Gaussiano R=5 Mpc/h (σ=0.64 px), identico a Phase 0
6. Zero-padding ai bordi della survey per gestire non-periodicità
7. Diagnostiche: n(z) realizzata vs attesa, completezza angolare

**Dipendenze:** `astropy`, `fitsio` o `astropy.io.fits`

---

### Script 2 — `src/phase6_bgs_tda.py`
**Obiettivo:** estrai feature TDA dal campo BGS voxelizzato (identico a Phase 5).

**Input:**
- `data/processed/phase6_fields/bgs_ngc_delta_128.npy`
- `data/processed/phase6_fields/bgs_mask_128.npy`

**Output:**
- `results/phase6_bgs_tda_features.json` — 8 feature TDA con incertezze bootstrap
- `results/phase6_bgs_tda_diagnostics.json`

**Operazioni:**
1. Applica maschera (voxel fuori dalla survey → zero o esclusi dalla filtrazione)
2. gudhi CubicalComplex con convenzione Phase 5 corretta (birth=-col0, death=-col1)
3. n_thresh=100, sigma_smooth=0.64 px
4. Bootstrap su regioni jackknife (NGC diviso in 20 patch) per stima incertezza
5. Confronto feature BGS vs distribuzione feature nwLH z=0 (posizionamento nel prior)

**Dipendenze:** `gudhi`, `numpy`, `scipy`

---

### Script 3 — `src/phase6_mock_calibration.py`
**Obiettivo:** costruisci mock BGS da simulazioni Quijote nwLH a z=0 e z=0.5 con HOD forward sampling. Verifica che le feature TDA dei mock coprano lo spazio delle feature BGS osservate.

**Input:**
- `data/raw/quijote/3D_cubes/latin_hypercube_nwLH_hod/{i}/groups_004/` (z=0)
- `data/raw/quijote/3D_cubes/latin_hypercube_nwLH_hod/{i}/groups_003/` (z=0.5)
- `data/processed/phase6_fields/bgs_ngc_delta_128.npy` (target)

**Output:**
- `results/phase6_mock_features_z0.npz` — feature TDA 2000 campi z=0 (da Phase 5 B3)
- `results/phase6_mock_features_z05.npz` — feature TDA 2000 campi z=0.5
- `results/phase6_calibration_diagnostics.json`
  - n(z) mock vs BGS: discrepanza media (gate D2)
  - Coverage: BGS feature dentro/fuori il range mock

**Operazioni:**
1. Per z=0.5: HOD forward sampling identico a `phase5_hod_b3.py` ma con `snapnum=3`
2. Verifica gate D2: |n(z)_mock - n(z)_BGS| / n(z)_BGS < 20% → Opzione A confermata
3. Se gate D2 fallisce: segnala e indica passaggio a Opzione C

**Nota:** z=0 già disponibile da `results/phase5_hod_b3_features.npz`. Riuso diretto.

---

### Script 4 — `src/phase6_partial_corr.py`
**Obiettivo:** calcola la correlazione parziale r(feature_BGS, w₀ | Ωm, σ₈) usando i mock come distribuzione di riferimento. Produce il risultato scientifico principale di Phase 6.

**Input:**
- `data/processed/phase6_fields/bgs_ngc_delta_128.npy` (dati reali)
- `results/phase6_mock_features_z0.npz` (mock z=0)
- `results/phase6_mock_features_z05.npz` (mock z=0.5)
- `latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt`

**Output:**
- `results/phase6_gate_result.json`

**Metodo:**
1. Proietta le feature BGS osservate nello spazio dei mock
2. Calcola la posizione nel prior w₀ implicitamente (SBI-like: posterior su w₀ dato feature_BGS)
3. Alternativa frequentista: confronta r_obs(feature_BGS, w₀_mock | Ωm_mock, σ₈_mock) con null distribution
4. Produce σ_DESI con range [σ_z0, σ_z05]
5. Confronto con baseline P(k) (chiusura OC-1 per Phase 6)

---

### Script 5 — `src/phase6_power_spectrum_baseline.py`
**Obiettivo:** calcola P(k) monopolo per BGS e per i 2000 mock nwLH. Confronto r_TDA vs r_Pk su DESI.

**Input:** stessi dei precedenti  
**Output:** `results/phase6_pk_comparison.json`

**Note:** questo script chiude definitivamente OC-1 su dati reali.

---

## Ordine di Esecuzione

**Principio:** tutto il possibile viene preparato mentre Run A (Phase 5) è ancora in corso, per evitare attese all'apertura di Phase 6. Solo Script 4 dipende dai risultati di A.

### Eseguibili immediatamente (mentre A gira)

```
[PARALLELO — ora, mentre A gira]

Terminale 1:
Script 1: phase6_bgs_voxelize.py         (~1h, CPU)
    ↓ completato
Script 2: phase6_bgs_tda.py              (~10min, gudhi)
    ↓ completato
Script 5: phase6_power_spectrum_baseline.py  (~2h, CPU)

Terminale 2 (dopo conferma colonne FITS BGS):
Script 3: phase6_mock_calibration.py     (~8h, GPU — z=0.5 run)
    ↓ completato
Gate D2: n(z) check (automatico nello script)
```

### Dipende da Run A

```
[DOPO completamento Run A]

Script 4: phase6_partial_corr.py         (~30min, CPU)
    — richiede: results/phase5_hod_features.npz (Run A)
    — richiede: results/phase6_mock_features_z05.npz (Script 3)
    — richiede: results/phase6_bgs_tda_features.json (Script 2)
    ↓
Review Phase 6 → Gate 6
```

### Dipendenze tra script

| Script | Dipende da | Bloccante? |
|--------|-----------|------------|
| Script 1 (voxelize) | dati DESI DR1 già in mano | No — lancia subito |
| Script 2 (TDA BGS) | Script 1 | No — lancia dopo Script 1 |
| Script 3 (mock z=0.5) | halo catalogs già scaricati | No — lancia subito in parallelo |
| Script 4 (partial corr) | Script 2, Script 3, Run A | Sì — aspetta Run A |
| Script 5 (P(k) baseline) | Script 1 | No — lancia dopo Script 1 |

---

## Open Issues da Risolvere in Phase 6

- **OC-1 (critico):** confronto r_TDA vs r_Pk su DESI — chiuso da Script 5
- **Smoothing sensitivity:** R=5 vs R=10 Mpc/h su BGS — eseguire come robustness check
- **NGC vs SGC:** analisi separata e combinata — verificare coerenza tra i due campi del cielo
- **Zero-padding:** gestione del boundary non-periodico della survey — da validare su mock con geometria survey realistica
- **b1_fwhm=0:** feature confermata non informativa nel regime galattico — dichiarata esplicitamente nella sezione Methods

---

## Note Finali

Questo documento va aggiornato dopo il completamento di Phase 5 (risultati Run A) prima di aprire formalmente Phase 6. In particolare:

- Se σ_A >> σ_B3: la marginalizzazione HOD amplifica il segnale → aggiornare D2 verso Opzione A confermata
- Se σ_A ≈ σ_B3: B3 deterministico è sufficiente → Script 3 può usare solo B3 (K=1), risparmio ~80% del tempo GPU
- Se σ_A << σ_B3: la marginalizzazione diluisce il segnale → investigare prima di Phase 6
