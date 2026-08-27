# Record consolidato — revisione MN-26-2847-P

Luglio 2026. **Sostituisce** `paper1_sigma_discrepancy_resolution.md`,
`paper1_variance_decomposition.md` e `stato_revisione_paper1.md`, che restano
come tracce di lavoro ma non vanno più citati come autorevoli.

---

## 1. Titolo e tesi

> **Three quarters of the DESI BGS H1 deficit is reproduced by its power
> spectrum; one quarter is not**

La tesi originale — «origine di fase» — non era sostenuta e i tre referee
l'hanno contestata all'unisono. La tesi nuova è **misurata**, con un residuo a
42σ e un controllo di imparzialità a supporto, e viene dal test che Referee 3
ha indicato lui stesso.

«Fase» esce da titolo e abstract. Entra la decomposizione.

---

## 2. Risultati

### 2.1 Il deficit e la sua decomposizione

| quantità | valore |
|---|---|
| DESI N_H1 (NGC, R5, filtrazione mascherata) | **28 256** |
| mock, N = 2000 congelati | **35 436.686 ± 312.989** |
| deficit | **20.3%** |
| rank empirico | **1/2001**, 0 mock sotto DESI |
| margine sotto il minimo dell'ensemble | +2970 (NGC), +1100 (SGC) |

Randomizzazione delle fasi a spettro fissato, applicata **simmetricamente** a
DESI e ai mock (n = 50 / 100):

| | N_H1 |
|---|---|
| DESI originale | 28 256 |
| DESI a fasi randomizzate | 33 719.4 ± 22.2 |
| mock originali | 35 458.9 ± 25.8 |
| mock a fasi randomizzate | 39 211.8 ± 34.0 |

- deficit originale **7202.9**, dopo randomizzazione **5492.4 ± 40.6**
- **frazione spettrale 76.3%**
- **residuo oltre-due-punti 23.7% = 1710.5 ± 40.6 generatori, 42σ**

Controllo di imparzialità (N10b): una seconda randomizzazione, su campi già a
fasi casuali, non sposta N_H1 — DESI −20 ± 65 (0.3σ), mock +150 ± 200 (0.7σ).
La trasformazione è idempotente sui campi gaussiani, quindi la salita alla
prima applicazione è contenuto di fase reale e non artefatto della maschera.
Verificato anche che ν è **esattamente** nullo fuori maschera (potenza dentro
maschera = 1.000000000000000).

### 2.2 Dove vive il deficit in persistenza (N2, 1800 mock)

Taglio in unità assolute di ν — la scelta corretta, perché ν è su scala comune
per costruzione grazie al density matching:

| ε | deficit | sopravvivenza | rank |
|---|---|---|---|
| 0 | 20.3% | 100% | 1/1801 |
| 0.075 | 26.6% | **116.3%** | 1/1801 |
| 0.10 | **27.0%** | 113.4% | 1/1801 |
| 0.40 | 23.1% | 59.5% | 1/1801 |
| 0.80 | 13.6% | 17.7% | 1/1801 |
| 1.50 | −9.3% | −3.8% | 1556/1801 |

**Il deficit non è rumore vicino alla diagonale**: cresce in termini frazionari
fino a ν ≈ 0.1, resta sopra il 23% alla mediana di persistenza (0.404), e il
rank resta 1/1801 fino a ν = 0.8, circa il 75° percentile. Si chiude a ν ≈ 1.1;
sopra c'è un eccesso lieve e non significativo (+0.7σ, +0.9σ).

La versione autonormalizzata (per R_f = p99 − p1 di ciascun campo) dà il
pareggio a 0.433 e un apparente eccesso a z = +9.4. **È un artefatto**: R_f vale
8.66 per DESI e ≈ 11.7 per i mock, quindi autonormalizzare taglia i mock al 34%
in più di persistenza assoluta. E R_f dei mock è maggiore *proprio a causa*
delle code da shot noise che stiamo misurando: normalizzare per esso normalizza
via l'effetto. Entrambe vanno in figura, con la spiegazione della divergenza.

### 2.3 Quanto predicono P(k) e la PDF (N1)

Sui mock (1800), regressione di N_H1 su 16 bande logaritmiche di P(k):

- R² in campione 0.711, **R² validato 5-fold 0.700**
- aggiungendo σ, asimmetria e curtosi del campo: **R² validato 0.754**

Questa è la risposta a R3.4 («valore aggiunto rispetto a P(k)+PDF»): un quarto
della varianza di N_H1 fra i mock non è riducibile a P(k) e PDF.

DESI però vive **fuori** dallo spazio campionato: distanza di Mahalanobis
**34.3** nello spazio a 16 bande, contro ~4 di un mock tipico. La predizione per
DESI è quindi un'estrapolazione, e infatti sbaglia:

| metodo | N_H1 previsto per «fasi tipiche + spettro di DESI» |
|---|---|
| N1c, regressione estrapolata | 33 538 |
| N10, misura diretta (33 719.4 − 3752.9) | **29 966.5** |
| osservato | 28 256 |

La differenza fra la misura diretta e l'osservato, 1710.5, **è** il residuo di
fase di N10, a meno di un decimale: i due metodi si riconciliano esattamente.
La regressione sovrastimava di **3572 generatori, metà del deficit**.

È un risultato metodologico riusabile: quantifica il rischio dell'attribuzione
per regressione quando il dato vive fuori dall'intervallo di calibrazione.

### 2.4 A cosa risponde N_H1 (M1, n = 2000)

Regressione sui sette parametri nwLH, mappatura delle colonne validata contro
l'npz sugli indici 0–199 con max|diff| = 0.0:

| parametro | r | t (OLS) | escursione |
|---|---|---|---|
| **nₛ** | **+0.376** | **+19.3** | +404 |
| h | +0.210 | +10.9 | +228 |
| σ₈ | +0.182 | +8.6 | +180 |
| Ωm | +0.154 | +8.4 | +176 |
| Ωb | −0.128 | −6.3 | −131 |
| Mν | −0.048 | −3.0 | −63 |
| w0 | +0.055 | +2.5 | +51 |

**N_H1 è una sonda della FORMA dello spettro, non dell'ampiezza.** È una
previsione del lemma di invarianza monotona, ora misurata: σ₈ resta debole
mentre nₛ, h, Ωm e Ωb — i parametri che governano la forma — dominano. Ωb esce
negativo, come deve essere se lo smorzamento barionico riduce la potenza a
piccola scala.

Decomposizione della varianza, senza residui:

| termine | σ | frazione |
|---|---|---|
| cosmologia (7 parametri) | 160 | 26.1% |
| realizzazione delle CI | 246 | 61.6% |
| HOD / downsampling | 110 | 12.3% |

Verifica: 160² + 110² + 246² = 313.4², contro 312.99 misurata (0.13%).

**Tetto cosmologico al deficit.** Modello con 7 lineari + 7 quadratici + 21
incrociati: R² validato **0.357** contro 0.253 del lineare, quindi i termini non
lineari catturano struttura vera e non overfitting. Escursione massima sulle
2000 cosmologie campionate: **1501 generatori**, contro un deficit di 7181.

> **Nessuna combinazione dei sette parametri, in un iperspazio che copre
> Ωm ∈ [0.10, 0.50], σ₈ ∈ [0.60, 1.00], nₛ ∈ [0.80, 1.20], w0 ∈ [−1.30, −0.70],
> raggiunge il deficit: manca di un fattore 4.8.**

---

## 3. La discrepanza 313 / 445, risolta

`phase8_test2_masked.json` (2026-07-03, N = 2000, filtrazione mascherata)
riporta σ = **312.9891651683112**, riprodotto cifra per cifra da
`paper1_remap.py`. Il 445 viene da `phase9_likeforlike_arrays.npz`, prodotto da
`phase9_extract_features.py`, che per gli indici 0–199 leggeva cubi
**sovrascritti da un run successivo a 200 mock con HOD diverso**.

Meccanismo: in `phase8_test2_masked.py` il JSON di sintesi si diramava su
`--hod_json`, la tabella per-mock e la directory dei campi no. Il run con HOD
fittato ha deviato il proprio JSON ma sovrascritto gli artefatti condivisi.

Prova diretta: il CSV del pilota coincide con l'npz su **200/200** valori e con
la catena definitiva su **0/200**; per ranghi dentro maschera la Spearman fra i
due cache vale 0.9996 sui controlli e 0.60–0.67 sul blocco.

Perché non se n'è accorto nessuno: il controllo di consistenza confronta la
media e **mai** la deviazione standard —
`drift = |35424.784 − 35436.7| / 313.0 = 0.038 < 0.5` → `[ok]`.

**Corretto** (`paper1_rev_fix_phase8_paths.py`): tabella e campi ora si diramano
sul tag del run, con guardia sulla sovrascrittura e controllo che RES_DIR stia
sotto `--project_root`.

Il referee legge la discrepanza al contrario: **313 è il valore congelato,
445 l'artefatto.** Paper 1 non ha ristretto nulla.

---

## 4. Correzioni a M26 (`cauchy_mnras.tex`, ancora in review)

| # | dove | correzione |
|---|---|---|
| 1 | definizione di β₁^max | **non** «at the Betti-curve peak»: `feats[4] = len(p1)` è il conteggio totale delle coppie H1 finite; il picco è `feats[1]`. Considerare la ridenominazione del simbolo |
| 2 | tabella battery, righe 459/510/636 | σ NGC 445 → **312.99** |
| 3 | riga 735 | frazione stocastica 6% → **12.3%**; e **riscrivere l'attribuzione**: il driver è nₛ, non Ωm |
| 4 | riga 735 | correlazioni +0.45/+0.29/−0.03 → nₛ +0.376, h +0.210, σ₈ +0.182, Ωm +0.154, Ωb −0.128, Mν −0.048, w0 +0.055 |
| 5 | riga 735 | «the remaining ~94% is cosmological» → decomposizione misurata: 26.1 / 61.6 / 12.3 |
| 6 | riga 735 | «the single mock below the data is the extreme low-Ωm corner (Ωm = 0.10)»: il mock 139 (Ωm = 0.1033) ha N_H1 = 34 119, mentre il minimo dell'ensemble è il mock 1666 a 31 226 |
| 7 | riga 675 | SGC: «below *all* 200 mocks (z = −20)» → **rank 1/201, p ≤ 5.0 × 10⁻³**. Paper 1 a N = 2000 dà 1/2001, p ≤ 5.0 × 10⁻⁴: **rafforza** M26 di un fattore dieci |
| 8 | figure e appendici | prodotti derivati dall'npz contaminato: istogramma empirico, curva di risposta a w0, `phase9b_majors` |

Nel merito la correzione **rafforza** M26: la σ corretta è più piccola, quindi
il deficit è più significativo, e il tetto cosmologico del fattore 4.8 è un
argomento che M26 non aveva.

---

## 5. Cosa cambia nel manoscritto

**Titolo e abstract.** Nuovo titolo. Abstract con rank primario
(1/2001, p ≤ 5.0 × 10⁻⁴), z parentetica, e la decomposizione 76.3 / 23.7.

**Sezione 4.2.** «Statistically independent channels» va rimossa: i momenti
correlano con N_H1 a −0.792 (σ) e +0.779 (curtosi) su 1800 mock. Sostituire con
la formulazione che il referee propone in subordine — coesistono, e il primo non
spiega il secondo. Aggiungere che `N_H1` e `n_pers_top10` correlano a 0.99996
(sono la stessa quantità) e che `b1_integral` e `mean_pers1` a 0.994: le otto
feature non sono otto misure indipendenti.

**Tabella 3.** L'asimmetria **inverte il segno** fra P5 (z = −4.58) e P10
(z = +7.69): qualunque affermazione su di essa va ritirata o riqualificata come
dipendente dalla soglia. Deviazione standard (z ≈ +6.8 stabile) e curtosi
(z ≈ −6, mock +3.90 contro DESI +0.20) reggono.

**Figura 1.** Distinguere il picco della curva dal valore a densità media: DESI
picca a 8457 con ν = +1.337, i mock rimappati a 13 321 con ν ≈ +1.02, mentre i
7162 ± 183 del testo sono il valore a ν = 0. E `peak_nu` non è robusto — salta
da +0.89 (R10) a −2.37 (R12) — quindi non va usato come diagnostico.

**Sezione 7.** Sostituire la speculazione con il tetto cosmologico e la
decomposizione.

**Incertezze.** Etichettare ovunque sd dell'ensemble o SEM. L'obiezione R3.6(iv)
si risolve a favore: la dispersione fra i 50 bersagli del mirror è lo 0.258%,
tre volte e mezzo minore di quella dell'ensemble (0.883%), quindi SEM = 9.95 a
n = 50 contro 7.00 a n = 2000 — comparabili.

**Due tensioni da dichiarare noi.** I due stimatori corretti danno 20.5% e
23.2%, con incertezze interne di ±0.03: 2.7 punti di discordanza sistematica
(Referee 3 l'ha letta come conferma). E `g₁ₚ` **diverge** dove D attraversa lo
zero, fra R15 e R17: i valori +4.79 e −1.21 non sono misure. Il riassunto
«14.87 ± 8.26%» media sette numeri di cui quattro instabili per costruzione: va
sostituito dalla tabella per scala, limitata a R5, R10, R12.

**Pre-registrazione.** Citare e pubblicare `paper1_preregistration_protocol.md`
(repo + Zenodo). È l'obiezione più facile del lotto e oggi non è sfruttata.

---

## 6. Un fatto fisico coerente su cinque diagnostici

I mock hanno picchi da shot noise che DESI non ha:

| diagnostico | mock | DESI |
|---|---|---|
| curtosi dentro maschera | +3.90 | +0.20 |
| p99 − p1 in unità di σ | 5.6σ | 3.22σ |
| voxel duplicati | 0.21–0.27% | **1.65%** |
| molteplicità massima | 3–4 | **52** |
| potenza a piccola scala | minore a ogni k | maggiore, spettro più rosso |

Cinque misure indipendenti della stessa proprietà. Non è dimostrato che sia la
causa del deficit, ma è il candidato meccanico più concreto, e cade dove N2
colloca la maggior parte del deficit. **N7** (satelliti NFW invece che uniformi
nel raggio viriale) è il test che lo attacca direttamente.

---

## 7. Paper 5 — riformulato

r(N_H1, w0) = **+0.0554**, IC95% [+0.0116, +0.0990], n = 2000. La soglia
|r| > 0.10 fissata in `canovaccio_paper5.md` §4 non è raggiunta. La risposta a
w0 esiste (andamento monotono in entrambi gli emisferi, quadratico escluso) ma
vale 51 generatori su tutto l'intervallo, cioè 0.16σ; vincolo implicato ±2.0
contro ±0.06 di BAO DESI.

Tesi nuova: **«N_H1 è una sonda di forma dello spettro, e il deficit non è
raggiungibile da nessuna forma entro ΛCDM+w0.»**

---

## 8. Punti aperti

| | |
|---|---|
| **N7** satelliti NFW | bound analitico, poi test a N = 200 se serve |
| **N6** pesi FKP | N = 200 |
| **N8** maschere sintetiche | unica via al margine del 3% su w̄ ≥ 0.99 |
| **N9** convergenza di risoluzione | decisione |
| **M2** σ(realizzazione) cut-sky | verifica il 110 preso in prestito da M26 |
| definizione del taglio «clean voxels» | la maschera congelata ha 307 805 voxel, più di quanti ne dia P5: è un oggetto diverso, da identificare nel sorgente prima di rispondere a R2.6 |
| erosione k = 1 | perché manca fra i livelli (T7) |
| T1–T18 | riscrittura |
| comunicazione all'editore di M26 | a fine lavoro, in un unico invio |

---

## 9. Errori commessi durante la revisione, e corretti

Elencati perché i report JSON conservano tracce di ciascuno.

1. **Test di provenienza su timestamp**: privo di valore diagnostico, vero per
   costruzione in ogni run sequenziale.
2. **Criterio di esclusione su cosmologia NaN**: costruito su un artefatto
   (1800 mock su 2000 sono NaN). Ritirato.
3. **Correlazioni presentate come su 2000 punti**: erano su 200.
4. **«La cosmologia spiega ~4% della varianza»**: è 26%, e il parametro
   dominante (nₛ) non era nella lista considerata.
5. **«Oltre l'80% è varianza di realizzazione»**: è 61.6%.
6. **Pilota in scatola**: misurava una decomposizione diversa da quella
   richiesta (niente density matching, niente HOD). La misura corretta era a un
   file di testo di distanza.
7. **`violazioni_monotonia_frac` e `fuori_maschera_spearman` in v2h**: prive di
   significato ai valori di N in gioco.
8. **N1 prima versione**: correlava lo spettro dei δ dei mock con quello del ν
   di DESI. Ha prodotto numeri completi e formattati — frazione di deficit
   −57%, residuo −46σ — tutti privi di senso. L'unica cosa che l'ha rivelato è
   stata `sigma_in_mask`, inclusa quasi per caso.
9. **N2 letto su 20 mock e nella normalizzazione sbagliata**: mi aveva portato a
   concludere che il deficit fosse rumore diagonale e che il paper ne uscisse
   indebolito. Con 782 mock e la normalizzazione assoluta la conclusione si
   ribalta.
10. **Autocontrollo P10 in N4**: testava l'ipotesi sbagliata (che la maschera
    congelata fosse il taglio «clean voxels»).
11. **`key` convertito con `int()` dentro `try/except`**: ripiego silenzioso
    sulla posizione. Ha funzionato — verificato a posteriori — ma per caso.

**La lezione operativa**, ricorrente: l'unica difesa affidabile è mettere
nell'output una quantità che *deve* avere un valore noto. Ha funzionato con
N_H1 = 28 256, con `pers_mean` = 0.7245888380122361, con `f_half` = 0.680, con
la mappatura delle colonne a max|diff| = 0.0. È esattamente ciò che il controllo
di `phase9_extract_features.py` non faceva quando ha lasciato passare σ da 313
a 445.

---

## 10. Tracciabilità

| script | esito |
|---|---|
| `paper1_rev_v2v3.py` → `v2i_close.py` | diagnosi completa della discrepanza 313/445 |
| `paper1_rev_v3a_sgc_fiducial.py` | ramo SGC pulito; bootstrap: σ = 178 al 42° percentile |
| `paper1_rev_v3b_pilot_box.py` | pilota in scatola (fuorviante, vedi §9.6) |
| `paper1_rev_m1_cosmo_response.py` | risposta cosmologica, n = 2000 |
| `paper1_rev_n1_spectral.py` | **invalido**, vedi §9.8 |
| `paper1_rev_n1b_spectral.py` | piano (f_half, N_H1), 1800 mock |
| `paper1_rev_n1c_bandpower.py` | spettro binnato, PCA, Mahalanobis |
| `paper1_rev_n2_persistence.py` | decomposizione in persistenza, 1800 mock |
| `paper1_rev_n10_phases.py` | randomizzazione delle fasi, 50/100 |
| `paper1_rev_n10b_control.py` | controllo di idempotenza |
| `paper1_rev_par_bundle.py` | R3.3, R3.6iii, tetto non lineare, pareggi |
| `paper1_rev_n4n5.py` | stabilità P5/P15, incertezze omogenee |
| `paper1_rev_fix_phase8_paths.py` | correzione dei percorsi di uscita |

Report JSON in `results/paper1/`.
