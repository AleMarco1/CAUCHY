
# Record consolidato finale — revisione MN-26-2847-P

Luglio 2026. **Sostituisce** tutte le versioni precedenti, in particolare
`paper1_record_consolidato.md`, `paper1_variance_decomposition.md` e
`paper1_sigma_discrepancy_resolution.md`, che restano solo come tracce di
lavoro. Tutti gli esperimenti sono chiusi.

---

## 1. Titolo e tesi

> **Three quarters of the DESI BGS H1 deficit is reproduced by its power
> spectrum; one quarter is not**

La tesi originale — «origine di fase» — non era sostenuta, e i tre referee
l'hanno contestata all'unisono. La tesi nuova è misurata, con un residuo a 42σ
e un controllo di imparzialità a supporto, e viene dal test che Referee 3 ha
indicato lui stesso. «Fase» esce da titolo e abstract.

---

## 2. Il risultato primario

| | valore |
|---|---|
| DESI N_H1 (NGC, R5, filtrazione mascherata) | **28 256** |
| mock nwLH, N = 2000 congelati | **35 436.686 ± 312.989** |
| deficit | **20.3%** |
| rank empirico | **1/2001**, 0 mock sotto DESI |
| margine sotto il minimo dell'ensemble | +2970 (NGC), +1100 (SGC) |

### 2.1 Decomposizione fasi / spettro (N10)

Randomizzazione delle fasi a spettro fissato, applicata **simmetricamente** a
DESI e ai mock (n = 50 / 100):

| | N_H1 |
|---|---|
| DESI originale | 28 256 |
| DESI a fasi randomizzate | 33 719.4 ± 22.2 |
| mock originali | 35 458.9 ± 25.8 |
| mock a fasi randomizzate | 39 211.8 ± 34.0 |

- deficit originale **7202.9** → dopo randomizzazione **5492.4 ± 40.6**
- **frazione spettrale 76.3%**
- **residuo oltre-due-punti 23.7% = 1710.5 ± 40.6 generatori, 42σ**

Controllo di imparzialità (N10b): una seconda randomizzazione su campi già a
fasi casuali non sposta N_H1 — DESI −20 ± 65 (0.3σ), mock +150 ± 200 (0.7σ).
La trasformazione è idempotente sui campi gaussiani, quindi la salita alla
prima applicazione è contenuto di fase reale e non artefatto della maschera.
Verificato anche che ν è **esattamente** nullo fuori maschera.

### 2.2 Significatività rispetto a un modello (M2a)

Referee 2 §1: *«la dispersione al denominatore mescola 2000 cosmologie diverse:
la z non è significatività rispetto al modello, è distanza dalla famiglia»*.

Ensemble a **cosmologia fissa** (fiduciale Quijote, 200 realizzazioni,
geometria cut-sky del paper):

| | mock | DESI | rank | z |
|---|---|---|---|---|
| cosmologia fissa | 35 501.7 ± 172.0 | 28 256 | **1/201** | **−42.13** |
| famiglia nwLH | 35 436.7 ± 313.0 | 28 256 | 1/2001 | −22.94 |

Il referee ha ragione sulla semantica, e **la scelta del paper è conservativa
di quasi un fattore due**. Vanno riportate entrambe, etichettate per quello che
sono. Lo scarto fra le medie è +65.0 (0.18%): la cosmologia fiduciale sta
essenzialmente al centro dell'hypercube.

---

## 3. Dove vive il deficit in persistenza (N2, 1800 mock)

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
rank resta 1/1801 fino a ν = 0.8 (~75° percentile). Si chiude a ν ≈ 1.1; sopra
c'è un eccesso lieve e non significativo (+0.7σ, +0.9σ).

La versione autonormalizzata (per R_f = p99 − p1) dà il pareggio a 0.433 e un
apparente eccesso a z = +9.4. **È un artefatto**: R_f vale 8.66 per DESI e
≈ 11.7 per i mock, quindi autonormalizzare taglia i mock al 34% in più di
persistenza assoluta — e R_f dei mock è maggiore *proprio a causa* delle code
da shot noise che stiamo misurando. Entrambe vanno in figura, con la
spiegazione della divergenza.

---

## 4. Quanto predicono P(k) e la PDF (N1)

Regressione di N_H1 su 16 bande logaritmiche di P(k), 1800 mock:

- R² in campione 0.711, **R² validato 5-fold 0.700**
- aggiungendo σ, asimmetria e curtosi del campo: **R² validato 0.754**

Questa è la risposta a R3.4: un quarto della varianza di N_H1 fra i mock non è
riducibile a P(k) e PDF.

DESI vive **fuori** dallo spazio campionato: Mahalanobis **34.3** nello spazio a
16 bande, contro ~4 di un mock tipico. La predizione per DESI è quindi
un'estrapolazione, e sbaglia:

| metodo | N_H1 previsto per «fasi tipiche + spettro di DESI» |
|---|---|
| N1c, regressione estrapolata | 33 538 |
| N10, misura diretta (33 719.4 − 3752.9) | **29 966.5** |
| osservato | 28 256 |

La differenza fra misura diretta e osservato, 1710.5, **è** il residuo di fase
di N10 a meno di un decimale: i due metodi si riconciliano esattamente. La
regressione sovrastimava di **3572 generatori, metà del deficit**.

È un risultato metodologico riusabile: quantifica il rischio dell'attribuzione
per regressione quando il dato vive fuori dall'intervallo di calibrazione.

---

## 5. A cosa risponde N_H1, e la decomposizione della varianza

### 5.1 Risposta ai parametri cosmologici (M1, n = 2000)

Mappatura delle colonne validata contro l'npz sugli indici 0–199 con
max|diff| = 0.0.

| parametro | r | t (OLS) | escursione |
|---|---|---|---|
| **nₛ** | **+0.376** | **+19.3** | +404 |
| h | +0.210 | +10.9 | +228 |
| σ₈ | +0.182 | +8.6 | +180 |
| Ωm | +0.154 | +8.4 | +176 |
| Ωb | −0.128 | −6.3 | −131 |
| Mν | −0.048 | −3.0 | −63 |
| w0 | +0.055 | +2.5 | +51 |

**N_H1 è una sonda della FORMA dello spettro, non dell'ampiezza.** Il lemma di
invarianza monotona lo prevede: σ₈ resta debole mentre nₛ, h, Ωm e Ωb — i
parametri che governano la forma — dominano. Ωb esce negativo, come deve essere
se lo smorzamento barionico riduce la potenza a piccola scala.

### 5.2 Decomposizione della varianza — CORRETTA da M2a

σ a cosmologia fissa **misurata direttamente** nella geometria del paper:
**171.996 ± 8.62** (200 realizzazioni fiduciali). Il valore ottenuto per
sottrazione dal modello lineare era 269.6: **scarto di 11.3σ**.

Il residuo OLS assorbiva dipendenza cosmologica **non lineare** — coerente col
fatto che quadratici e incrociati alzano R² da 0.253 a 0.357.

| termine | σ | frazione | fonte |
|---|---|---|---|
| **cosmologia** | **261.5** | **69.8%** | √(313.0² − 172.0²) |
| HOD / downsampling | **128.3** | **16.8%** | M2b, 4 indici × 40 semi |
| realizzazione delle CI | **114.6** | **13.4%** | √(172.0² − 128.3²) |

Verifica: 261.5² + 128.3² + 114.6² = 313.0². Nessun residuo.

**Conseguenza da dichiarare: M26 aveva ragione nella sostanza** — la varianza
dell'ensemble è dominata dalla cosmologia — pur avendo sbagliato i numeri (6%
stocastico) e l'attribuzione (Ωm invece di nₛ). L'errore sulla ripartizione era
**nostro**, nell'aver attribuito l'intero residuo lineare alla realizzazione.

σ_HOD è stato verificato indipendentemente su quattro indici nwLH
(1805, 1173, 1795, 900): 124.9, 135.4, 137.3, 115.5, con χ² = 1.56 su 3 gradi —
compatibile con un valore unico. M26 riportava 110 da 50 semi su un solo indice,
che sta a 3.6σ dalla nostra media.

### 5.3 Il tetto cosmologico al deficit

Modello con 7 lineari + 7 quadratici + 21 incrociati: R² validato **0.357**
contro 0.253 del lineare, quindi i termini non lineari catturano struttura vera.
Escursione massima sulle 2000 cosmologie campionate: **1501 generatori**, contro
un deficit di 7181.

> **Nessuna combinazione dei sette parametri, in un iperspazio che copre
> Ωm ∈ [0.10, 0.50], σ₈ ∈ [0.60, 1.00], nₛ ∈ [0.80, 1.20],
> w0 ∈ [−1.30, −0.70], raggiunge il deficit: manca di un fattore 4.8.**

Riserva: il modello cattura il 35.7% della varianza, quindi il tetto vale entro
la parametrizzazione adottata. E la §5.2 mostra che una parte sostanziale della
dipendenza cosmologica resta non catturata anche dal modello quadratico — quindi
il tetto è una stima, non un limite rigoroso.

---

## 6. Sistematici delimitati

### 6.1 Profilo radiale dei satelliti (N7)

I mock distribuiscono i satelliti **uniformemente** nel raggio viriale
(`r = r_vir · u^(1/3)`) invece che secondo NFW. Test appaiato, 40 coppie, stesso
catalogo e stesso seme, sola mappa radiale cambiata:

| | valore |
|---|---|
| bound analitico | 93 generatori (1.30% del deficit) |
| **misura appaiata** | **−56.5 ± 23.5** (2.4σ) |
| frazione del deficit | **−0.79%** |

L'appaiamento cancella il 47% della varianza. NFW dà **meno** loop
dell'uniforme, quindi correggere ridurrebbe il deficit dello 0.8%. L'editore
chiedeva «tested **or** quantitatively bounded»: ci sono entrambi e concordano.

Limite da dichiarare: il test isola il profilo a **HOD fisso**; una
ricalibrazione dell'HOD su NFW potrebbe compensare in parte.

### 6.2 Pesatura FKP (N6)

Asimmetria verificata nel codice: i random sono pesati `WEIGHT_FKP`, i dati
`WEIGHT × WEIGHT_FKP`, i mock `np.ones()`. Correzione con w_FKP(z) estratto dal
catalogo dei random (w medio 0.309), 60 coppie appaiate:

**−78.0 ± 8.0 generatori (−9.7σ), cioè −1.09% del deficit.** I mock si spostano
*verso* i dati. L'appaiamento cancella il 77% della varianza.

M26 Tabella 1 riporta +622 «in allontanamento», ma **non è lo stesso test**:
parte da una baseline di 35 838 (che non è l'ensemble congelato) e usa *«an
FKP-like positional weight»* invece del w_FKP radiale che dati e random
portano. In entrambi i casi il sistematico resta entro l'1–2%, e la conclusione
qualitativa di M26 — β₁ᵐᵃˣ insensibile alla pesatura — ne esce rafforzata.

Nota per il testo: il referee chiede N = 200 non appaiati; 60 coppie appaiate
danno precisione superiore. Va spiegato, non mascherato.

### 6.3 Somma dei sistematici

| canale | effetto sul deficit |
|---|---|
| profilo satelliti | −0.79% |
| pesatura FKP | −1.09% |
| **somma** | **−1.9%** |

Il residuo oltre-due-punti passa da 23.7% a ~23.3%: invariato alla precisione
quotata.

---

## 7. Geometria e scala

### 7.1 Erosione, con k = 1 (R2.6)

Riga 229 di `paper1_step6_onepoint_betti.py`: `out.append((f"erosione {k}
voxel", dist > k))`. **k = 1 non era escluso da nulla: mancava dalla lista.**

Cancello superato: il rerun riproduce `R5_er0`, `er2`, `er3` dell'SGC cifra per
cifra (18693.595, 12560.18, 8160.075).

| livello | voxel NGC | w̄ NGC | D_frac NGC | D_frac SGC |
|---|---|---|---|---|
| er0 | 100% | 0.99800 | 0.2023 | 0.1911 |
| **er1** | **84.6%** | **0.99999** | **0.2540** | **0.2711** |
| er2 | 68.1% | 1.000 | 0.2059 | 0.1999 |
| er3 | 48.7% | 1.000 | 0.1862 | 0.1727 |

**k = 1 dà il deficit frazionario massimo in entrambi gli emisferi**, e
l'escursione della tabella passa da **2.0 → 6.8 pp (NGC)** e **2.7 → 9.8 pp
(SGC)**. La colonna «Excursion» valeva 2.0 e 2.7 pp *perché k = 1 mancava*.

Interpretazione coerente col resto: a er0 w̄ è 0.998, a er1 diventa 0.99999.
Rimuovere il primo strato di bordo elimina i voxel contaminati dall'artefatto
FKP — gli stessi che in N4b ribaltano l'asimmetria da z = −7.91 a +0.60 — e il
deficit **cresce**. Ai livelli successivi cala perché si perde volume vero.

Sostanza favorevole (pulendo bene il deficit è maggiore), affermazione di
stabilità da riscrivere (escursione triplicata).

`sign_stability`: R5 e R10 STABILE in entrambi gli emisferi; R17 INSTABILE
(NGC), R15 e R20 INSTABILE (SGC). L'instabilità compare **solo sopra la soglia
w̄**, quindi il criterio predice *dove* la statistica cessa di essere
affidabile — argomento che il manoscritto non usa. Ma NGC dà R15 STABILE e SGC
INSTABILE: seconda evidenza contro la trasferibilità.

### 7.2 Il criterio w̄ ≥ 0.99 (N8, N8b)

**N8 — bias assoluto, 240 configurazioni su 128³, cinque topologie**
(lastra, guscio, tubo, cuneo, lastra forata):

| variabile | dispersione residua | riduzione |
|---|---|---|
| **w̄** | 0.1592 | **16.2%** |
| profondità mediana | 0.1859 | 2.2% |
| superficie/volume | 0.1761 | 7.4% |

Bias a w̄ = 0.99: da **−0.212** (guscio) a **−0.411** (cuneo). L'escursione fra
forme (0.199) è **maggiore** della dispersione residua che w̄ lascia. A w̄
fissata la forma governa il bias più di w̄. Il cuneo — la forma più vicina al
footprint reale — è il caso peggiore.

**N8b — bias differenziale**, due campi con lo stesso rumore bianco e pendenze
−1.5 e −2.3 (differenza vera 36.9%), regime w̄ ≥ 0.99, 58 configurazioni:

| | assoluto | differenziale |
|---|---|---|
| bias medio | −19.5% | **−3.4% ± 2.8%** |
| escursione fra forme | 0.158 | **0.019** |

La dipendenza dalla forma crolla di un fattore otto. La maschera **comprime il
contrasto**: su una differenza vera del 36.9% ne misura il 33.5%, cioè −9.3%
relativo. Se il fattore si trasferisce, il deficit misurato del 20.3%
sottostima uno vero di circa il 22% — ennesimo sistematico nella direzione
sfavorevole a una spiegazione banale.

Formulazione: il criterio **non** collassa il bias assoluto attraverso
topologie, quindi «survey-independent» e «transferable» sono ritirati; nel
confronto differenziale, che è l'uso effettivo, la dipendenza dalla forma si
riduce di un ordine di grandezza e resta un residuo del 3.4% da propagare come
sistematico. Il criterio va riformulato come condizione **sul confronto**, non
sui conteggi assoluti.

Limite: il differenziale è misurato fra campi gaussiani con spettri diversi;
DESI e mock differiscono anche in non-gaussianità (curtosi +0.20 contro +3.90),
canale non coperto.

### 7.3 Risoluzione e semantica della scala (N9)

| | 128³ | 256³ |
|---|---|---|
| cella | 15.6044 | 7.8022 |
| σ_px | 0.32042 | 0.64084 |
| FWHM del kernel | 0.75 celle | 1.51 celle |
| FWHM in Mpc/h | 11.77 | 11.77 |
| peso nel voxel centrale | **0.685** | 0.180 |
| mock | 35 447.1 ± 276.7 | 111 493.4 ± 2013.4 |
| DESI | 28 256 | 95 722 |
| **deficit** | **20.29%** | **14.15%** |
| dispersione relativa | 0.78% | 1.81% |
| z | −25.99 | −7.83 |
| rank | 1/51 | **1/51** |

Cancello superato: l'iniezione dei globali riproduce DESI = 28 256 e il mock
200 = 35 257, esatti.

Il deficit **non converge**: −6.14% ± 0.28%, cioè 22σ. Ma la ragione è
calcolabile. Il volume in maschera è 1.17 × 10⁹ (Mpc/h)³ con 217 614 galassie,
quindi la separazione media è **17.5 Mpc/h**, e le galassie per voxel sono
**0.71 a 128³** e **0.088 a 256³**.

> **La cella a 128³ è già alla scala di campionamento della survey. La griglia
> non è raffinabile: a 256³ nove voxel su dieci sono vuoti e la topologia misura
> rumore di Poisson.**

Non è una scelta arbitraria, è imposta dai dati — e spiega perché la dispersione
relativa raddoppi e la z crolli. Il deficit resta (rank 1/51 anche a 256³): si
degrada il rapporto segnale/rumore, non il segno.

L'etichetta «5 Mpc/h» resta però sbagliata: la scala onesta è quella di
campionamento, ~16–18 Mpc/h. La riformulazione richiesta da R1.5 va fatta, ora
con una giustificazione fisica invece che con un'ammissione.

### 7.4 Tabella 3 e i clean voxels (N4b)

Definizione, letta in `paper1_step6_onepoint_betti.py` righe 220–233:
`thr = percentile(field_r[mask], p)`, selezione `mask & (field_r > thr)`.
Il percentile è **dentro** la maschera; le selezioni tengono esattamente
95.00%, 90.00%, 85.00%.

Cancello superato — Tabella 3 riprodotta a 200 mock:

| momento | manoscritto | N4b | rank pubbl. | rank N4b |
|---|---|---|---|---|
| varianza | +6.2 | **+6.15** | 198/200 | 198/200 |
| asimmetria | +5.6 | **+5.57** | 198/200 | 198/200 |
| curtosi | −5.1 | **−5.06** | 1/200 | 1/200 |
| mediana | +13.8 | **+13.82** | 200/200 | 200/200 |

**Stabilità fra P5, P10 e P15**: nessun momento cambia segno; escursioni
0.54 (varianza), 1.04 (asimmetria), 1.05 (curtosi), 2.52 (mediana) su valori di
5–15. R2.6 si chiude in modo favorevole.

Ma esiste un salto fra **nessun taglio e taglio**: l'asimmetria passa da
z = −7.91 (footprint pieno) a +4.53 (P5), undici unità su un taglio che rimuove
il 5% dei voxel. **Non è fragilità: è la dimostrazione che quel 5% è
patologico**, ed è la ragione per cui il paper calcola i momenti sui clean
voxel. La verifica conferma la scelta invece di minarla.

Sotto erosione l'asimmetria diventa compatibile con zero (z = 0.60–0.91, rank
158–183/200) mentre a P10 resta +5.57: i due tagli non sono equivalenti
sull'asimmetria, e va detto quale sostiene l'affermazione.

---

## 8. Il fatto fisico coerente su cinque diagnostici

| diagnostico | mock | DESI |
|---|---|---|
| curtosi dentro maschera | +3.90 | +0.20 |
| p99 − p1 in unità di σ | 5.6σ | 3.22σ |
| voxel duplicati | 0.21–0.27% | **1.65%** |
| molteplicità massima | 3–4 | **52** |
| potenza a piccola scala | minore a ogni k | maggiore, spettro più rosso |

Cinque misure indipendenti della stessa proprietà: **i mock hanno picchi da
shot noise che DESI non ha.** N7 lo attacca direttamente e lo delimita allo
0.8%.

---

## 9. La discrepanza 313 / 445, risolta

`phase8_test2_masked.json` (2026-07-03, N = 2000, mascherata) riporta
σ = **312.9891651683112**, riprodotto cifra per cifra da `paper1_remap.py`. Il
445 viene da `phase9_likeforlike_arrays.npz`, prodotto da
`phase9_extract_features.py`, che per gli indici 0–199 leggeva cubi
**sovrascritti da un run successivo a 200 mock con HOD diverso**.

Meccanismo: in `phase8_test2_masked.py` il JSON di sintesi si diramava su
`--hod_json`, la tabella per-mock e i campi no.

Prova diretta: il CSV del pilota coincide con l'npz su **200/200** valori e con
la catena definitiva su **0/200**; per ranghi dentro maschera la Spearman fra i
due cache vale 0.9996 sui controlli e 0.60–0.67 sul blocco.

Perché nessuno se n'era accorto: il controllo di consistenza confronta la media
e **mai** la deviazione standard —
`drift = |35424.784 − 35436.7| / 313.0 = 0.038 < 0.5` → `[ok]`.

**Corretto** (`paper1_rev_fix_phase8_paths.py`, applicata): tabella e campi si
diramano sul tag del run, con guardia sulla sovrascrittura e controllo che
RES_DIR stia sotto `--project_root`.

**313 è il valore congelato, 445 l'artefatto.** Paper 1 non ha ristretto nulla.

---

## 10. Correzioni a M26 (`cauchy_mnras.tex`, in review)

| # | dove | correzione |
|---|---|---|
| 1 | definizione di β₁ᵐᵃˣ | **non** «at the Betti-curve peak»: `feats[4] = len(p1)` è il conteggio totale delle coppie H1 finite; il picco è `feats[1]`. Considerare la ridenominazione |
| 2 | battery, righe 459/510/636 | σ NGC 445 → **312.99** |
| 3 | riga 735 | frazione stocastica 6% → **16.8%**; attribuzione: il driver è **nₛ**, non Ωm |
| 4 | riga 735 | correlazioni +0.45/+0.29/−0.03 → nₛ +0.376, h +0.210, σ₈ +0.182, Ωm +0.154, Ωb −0.128, Mν −0.048, w0 +0.055 |
| 5 | riga 735 | «~94% cosmologico»: **qualitativamente confermato** (69.8%), numeri da sostituire con 69.8 / 16.8 / 13.4 |
| 6 | riga 735 | «the single mock below the data is the extreme low-Ωm corner (Ωm = 0.10)»: il mock 139 (Ωm = 0.1033) ha N_H1 = 34 119, il minimo è il mock 1666 a 31 226 |
| 7 | riga 675 | SGC: «below *all* 200 mocks (z = −20)» → **rank 1/201, p ≤ 5.0 × 10⁻³** |
| 8 | Tabella 1 | «FKP-like weights on mocks 35838 → 36460»: baseline non riconciliabile con l'ensemble congelato; il test corretto dà −78 ± 8 |
| 9 | figure e appendici | prodotti derivati dall'npz contaminato: istogramma empirico, curva di risposta a w0, `phase9b_majors` |

Nel merito la correzione **rafforza** M26: la σ corretta è più piccola, quindi
il deficit è più significativo; il tetto cosmologico è un argomento che M26 non
aveva; e la sua tesi qualitativa sulla dominanza cosmologica sopravvive.

---

## 11. Cosa cambia nel manoscritto

**Titolo e abstract.** Nuovo titolo. Rank primario (1/2001, p ≤ 5.0 × 10⁻⁴), z
parentetica, decomposizione 76.3 / 23.7, e la z a cosmologia fissa (−42.1)
accanto a quella di famiglia (−22.9).

**Sezione 4.2.** «Statistically independent channels» va rimossa: i momenti
correlano con N_H1 a −0.792 (σ) e +0.779 (curtosi) su 1800 mock. Aggiungere che
`N_H1` e `n_pers_top10` correlano a 0.99996 (sono la stessa quantità) e
`b1_integral` con `mean_pers1` a 0.994: le otto feature non sono otto misure
indipendenti.

**Tabella 3.** Confermata e riprodotta. Aggiungere la stabilità P5/P10/P15 e il
salto fra nessun taglio e taglio come *giustificazione* della scelta.

**Tabella erosione.** Aggiungere k = 1 a R5 su entrambi gli emisferi, e
**correggere l'escursione a 6.8 e 9.8 pp**.

**Sezione w̄.** Ritirare «survey-independent» e «transferable»; riformulare come
criterio sul confronto; propagare il 3.4% residuo nella banda sistematica.

**Sezione risoluzione.** Aggiungere il test a 256³ e l'argomento del
campionamento: la cella è alla separazione media fra galassie, la griglia non è
raffinabile, «5 Mpc/h» è nominale.

**Figura 1.** Distinguere il picco della curva dal valore a densità media: DESI
picca a 8457 con ν = +1.337, i mock rimappati a 13 321 con ν ≈ +1.02, mentre i
7162 ± 183 del testo sono il valore a ν = 0. E `peak_nu` non è robusto (da +0.89
a R10 a −2.37 a R12): non usarlo come diagnostico.

**Sezione 7.** Sostituire la speculazione con il tetto cosmologico e la
decomposizione.

**Incertezze.** Etichettare ovunque sd o SEM. R3.6(iv) si risolve a favore: la
dispersione fra i 50 bersagli del mirror è 0.258%, tre volte e mezzo minore di
quella dell'ensemble (0.883%), quindi SEM = 9.95 a n = 50 contro 7.00 a n = 2000.

**Due tensioni da dichiarare noi.** I due stimatori corretti danno 20.5% e
23.2% con incertezze interne di ±0.03: 2.7 punti di discordanza sistematica
(Referee 3 l'ha letta come conferma). E `g₁ₚ` **diverge** dove D attraversa lo
zero fra R15 e R17: i valori +4.79 e −1.21 non sono misure, e il riassunto
«14.87 ± 8.26%» media sette numeri di cui quattro instabili — va sostituito
dalla tabella per scala, limitata a R5, R10, R12.

**Conservatività, da rivendicare.** σ_HOD = 128.3 è rumore di nostra
costruzione e sta dentro la σ = 313 usata al denominatore. Togliendolo la z
passerebbe da −22.94 a −25.15. La scelta di tenerlo è conservativa e va
dichiarata come tale — utile rispondendo a un referee che ci accusa di aver
gonfiato una significatività restringendo una σ.

**Pre-registrazione.** Citare e pubblicare `paper1_preregistration_protocol.md`
(repo + Zenodo). È l'obiezione più facile del lotto e oggi non è sfruttata.

---

## 12. Paper 5 — riformulato

r(N_H1, w0) = **+0.0554**, IC95% [+0.0116, +0.0990], n = 2000. La soglia
|r| > 0.10 non è raggiunta. La risposta a w0 esiste (monotona in entrambi gli
emisferi, quadratico escluso) ma vale 51 generatori su tutto l'intervallo, cioè
0.16σ; vincolo implicato ±2.0 contro ±0.06 di BAO DESI.

Tesi nuova: **«N_H1 è una sonda di forma dello spettro, e il deficit non è
raggiungibile da nessuna forma entro ΛCDM+w0.»**

---

## 13. Punti aperti

Nessun esperimento. Restano:

- le diciotto voci testuali T1–T18 e la riscrittura
- la nota di correzione per M26 e la comunicazione all'editore, in un unico invio
- la response letter
- l'incoerenza fra `--k 2000` e `n_mocks: 200` in `paper1_mask_erosion.py`: da
  chiarire prima di quotare n in `tab:erosion`
- `sign_stability` a R15 discorde fra emisferi (NGC STABILE, SGC INSTABILE): da
  citare come seconda evidenza contro la trasferibilità

---

## 14. Errori commessi durante la revisione, e corretti

Elencati perché i report JSON conservano tracce di ciascuno.

1. **Test di provenienza su timestamp**: privo di valore diagnostico, vero per
   costruzione in ogni run sequenziale.
2. **Criterio di esclusione su cosmologia NaN**: costruito su un artefatto
   (1800 mock su 2000 sono NaN). Ritirato.
3. **Correlazioni presentate come su 2000 punti**: erano su 200.
4. **«La cosmologia spiega ~4% della varianza»**: è 26% col modello lineare, e
   **69.8%** con la misura diretta a cosmologia fissa.
5. **«Oltre l'80% è varianza di realizzazione»**: è **13.4%**. L'errore era
   attribuire l'intero residuo lineare alla realizzazione, ignorando la
   dipendenza cosmologica non lineare.
6. **Pilota in scatola**: misurava una decomposizione diversa da quella
   richiesta (niente density matching, niente HOD).
7. **`violazioni_monotonia_frac` e `fuori_maschera_spearman` in v2h**: prive di
   significato ai valori di N in gioco.
8. **N1 prima versione**: correlava lo spettro dei δ dei mock con quello del ν
   di DESI. Ha prodotto numeri completi e formattati — frazione −57%, residuo
   −46σ — tutti privi di senso. L'ha rivelato solo `sigma_in_mask`, inclusa
   quasi per caso.
9. **N2 letto su 20 mock e nella normalizzazione autonormalizzata**: mi aveva
   portato a concludere che il deficit fosse rumore diagonale e che il paper ne
   uscisse indebolito. Con 782 mock e la normalizzazione assoluta si ribalta.
10. **Autocontrollo P10 in N4**: testava l'ipotesi sbagliata (che la maschera
    congelata fosse il taglio «clean voxels»).
11. **N4**: percentile su `field_r[field_r > 0]` invece di `field_r[mask]`; le
    selezioni tenevano 98.9/93.7/88.5% invece di 95/90/85%. **L'inversione di
    segno dell'asimmetria fra P5 e P10 è ritirata** — N4b mostra che non esiste.
12. **`key` convertito con `int()` dentro `try/except`**: ripiego silenzioso
    sulla posizione. Ha funzionato, ma per caso; verificato a posteriori.
13. **Previsioni sbagliate, dichiarate prima**: frazione di deficit spiegata
    dallo spettro «sopra la metà» (era 23.6% con N1c, 76.3% con N10 — sbagliata
    in entrambe le direzioni); σ(realizzazione) dominante; deficit frazionario
    crescente a 256³; dispersione relativa minore a 256³.

**La lezione operativa**, ricorrente: l'unica difesa affidabile è mettere
nell'output una quantità che *deve* avere un valore noto. Ha funzionato con
N_H1 = 28 256, `pers_mean` = 0.7245888380122361, `f_half` = 0.680, la mappatura
delle colonne a max|diff| = 0.0, i quattro z di Tabella 3, e i tre valori SGC
dell'erosione. È esattamente ciò che il controllo di
`phase9_extract_features.py` non faceva quando ha lasciato passare σ da 313 a
445.

---

## 15. Tracciabilità

| script | esito |
|---|---|
| `paper1_rev_v2v3.py` → `v2i_close.py` | diagnosi completa della discrepanza 313/445 |
| `paper1_rev_v3a_sgc_fiducial.py` | ramo SGC pulito; σ = 178 al 42° percentile |
| `paper1_rev_v3b_pilot_box.py` | pilota in scatola (fuorviante, §14.6) |
| `paper1_rev_m1_cosmo_response.py` | risposta cosmologica, n = 2000 |
| `paper1_rev_n1_spectral.py` | **invalido**, §14.8 |
| `paper1_rev_n1b_spectral.py` | piano (f_half, N_H1), 1800 mock |
| `paper1_rev_n1c_bandpower.py` | spettro binnato, PCA, Mahalanobis |
| `paper1_rev_n2_persistence.py` | decomposizione in persistenza, 1800 mock |
| `paper1_rev_n10_phases.py` | randomizzazione delle fasi, 50/100 |
| `paper1_rev_n10b_control.py` | controllo di idempotenza |
| `paper1_rev_par_bundle.py` | R3.3, R3.6iii, tetto non lineare, pareggi |
| `paper1_rev_n4n5.py` | **ritirato**, §14.11 |
| `paper1_rev_n4b_clean.py` | Tabella 3 riprodotta; stabilità del taglio |
| `paper1_rev_n6_fkp.py` | pesatura FKP, 60 coppie |
| `paper1_rev_n7_nfw.py` | profilo satelliti, bound + 40 coppie |
| `paper1_rev_n8_masks.py` | trasferibilità di w̄, 240 configurazioni |
| `paper1_rev_n8b_differential.py` | bias differenziale |
| `paper1_rev_n9_resolution.py` | convergenza a 256³ |
| `paper1_rev_m2_fiducial.py` | σ a cosmologia fissa, 200 realizzazioni |
| `paper1_rev_m2b_hodscatter.py` | σ_HOD su 4 indici |
| `paper1_rev_fix_phase8_paths.py` | correzione dei percorsi di uscita |
| `paper1_mask_erosion.py` | rerun con k = 1, R5, entrambi gli emisferi |

Report JSON in `results/paper1/`.
