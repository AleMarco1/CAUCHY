# Record 54 — contenuto

Bozza del contenuto, da avvolgere nello schema del ledger. I numeri sono da
verificare riga per riga prima dell'append: sono tutti derivati dai registri
`onepoint_v1_{NGC,SGC}.jsonl`, `onepoint_v1_DESI_{NGC,SGC}.jsonl` e dal
sommario, via `paper2_letture_1punto.py` (selftest 31/31).

Testo del record in inglese, come gli altri; note e motivazioni in italiano.

---

## 1. Cosa deposita il record

Quattro decisioni prese **prima** che l'ensemble v2 giri, sui valori v1
misurati il 7 settembre 2026, e la loro motivazione.

| | decisione |
|---|---|
| **A** | 4.2b-3 ritirata come falsificazione; *r*_f resta diagnostica senza soglia |
| **B** | soglia di 4.2b-1 riscritta a *n*=2000: 7.2924 (NGC), 16.1314 (SGC) |
| **C** | soglia di 4.2c dichiarata: successo/fallimento a un terzo e due terzi di v1 |
| **D** | risoluzione della mediana di max δ: la riga della consegna §6 è a *n*=100 |

---

## 2. Cancelli superati prima di misurare

| cancello | esito |
|---|---|
| `paper2_cancello_nu.py`, indici 200/500/1000/1805/1999 | **UNICA**: `build_nu(δ)` riproduce i cubi congelati `test2_*.npz` con `max|Δ| = 0.000e+00`; momenti contro `n1b_spectra` a 3.789e-07 |
| `paper2_passata_1punto.py` NGC | 2000 record, **1850 ancore** (50 δ da `n1_spectra` idx 0–49, 1800 ν da `n1b_spectra` idx 200–1999), peggior scarto **2.562e-06** contro tolleranza 1e-5 dichiarata |
| `paper2_passata_1punto.py` SGC | 2000 record, **0 ancore**: nessun cubo ν congelato esiste per SGC; validità ereditata dal cammino verificato in NGC |
| righe di DESI | **28 valori** riscontrati con `paper1_step6_<REG>.json` per emisfero, peggior scarto **0.000e+00**; `p01` è l'unica quantità non ancorata |
| `paper2_letture_1punto.py` | **12 costanti congelate** riprodotte in entrambi gli emisferi entro la quantizzazione della cifra quotata; margine più stretto **1.00** (SGC kurt sd: 4.9827e-05 su 5e-05 ammessi) |

Ancoraggio agli ingressi: ogni record porta `delta_sha256`, riscontrato contro
`cachedelta_manifest_<REG>.jsonl`, 2000 voci per emisfero, zero scarti.

---

## 3. Valori v1 misurati, *n* = 2000

### NGC — 307805 voxel, σ_px 0.320422, soglia patologici 125.47415161132812

| grandezza | DESI | mock | *z* | rango |
|---|---:|---:|---:|---|
| var δ, footprint pieno | 2.916642 | 2844.93429 ± 509.83181 | −5.574 | 0/2000 |
| curtosi ν | −0.438215 | 2.817516 ± 0.458057 | **−7.108** | 3/2000 |
| *r*_f = (p99−p1)/σ | 3.224635 | 5.648966 ± 0.250815 | **−9.666** | 0/2000 |
| max δ | 125.47415 | 3938.70910 ± 2130.46930 | −1.790 | 0/2000 |
| *n* patologici | 0 (per costruzione) | 4048.21 ± 84.66 (SEM 1.893) | — | min 3314, max 4274 |

ν di DESI: p1 −5.137403, p99 3.524586, σ 2.686192.
*R* = ⟨var mock⟩/var DESI: pieno 975.4143; a P10 **3.6462**.

### SGC — 172225 voxel, σ_px 0.336055, soglia patologici 161.6696

| grandezza | DESI | mock | *z* | rango |
|---|---:|---:|---:|---|
| var δ, footprint pieno | 4.815533 | 9886.22733 ± 1587.69743 | −6.224 | 0/2000 |
| curtosi ν | −1.135173 | 1.132737 ± 0.278277 | **−8.150** | 1/2000 |
| *r*_f | 2.999872 | 4.790012 ± 0.151191 | **−11.840** | 0/2000 |
| max δ | 161.66965 | 6968.60580 ± 2972.96715 | −2.290 | 0/2000 |
| *n* patologici | 0 (per costruzione) | 2811.56 ± 71.45 (SEM 1.598) | — | min 2195, max 3004 |

ν di DESI: p1 −4.712914, p99 4.049958, σ 2.921082.
*R*: pieno 2052.9870; a P10 **8.0657**.

---

## 4. Decisione A — 4.2b-3 ritirata come falsificazione

### Il fatto

Curtosi di ν e *r*_f sono collineari sull'ensemble v1, in **entrambi** gli
emisferi, su maschere e geometrie diverse:

| coppia | NGC Pearson | NGC Spearman | SGC Pearson | SGC Spearman |
|---|---:|---:|---:|---:|
| curtosi ↔ *r*_f | **+0.9988** | +0.9976 | **+0.9985** | +0.9978 |
| curtosi ↔ σ(ν) | −0.9880 | −0.9980 | −0.9922 | −0.9980 |
| *r*_f ↔ σ(ν) | −0.9891 | −0.9988 | −0.9932 | −0.9958 |

Residui della relazione curtosi–*r*_f in NGC: sd 0.0122 su un intervallo che va
da 3.6 a 6.0. Non è un accidente dell'ensemble che la ripesatura possa
sciogliere: sono due funzionali di forma dello stesso campo.

Le altre coppie restano distinguibili: var δ ↔ max δ dà +0.8789 (NGC) e +0.8323
(SGC), *r*² ≈ 0.7–0.77. *n* patologici è la grandezza meno legata alle altre,
con *r*² massimo 0.43.

### La decisione

**4.2b-2 resta la regola di falsificazione. 4.2b-3 è ritirata come tale**, e
*r*_f viene riportata come diagnostica, con i suoi valori v1 registrati sopra e
**senza soglia**.

### Il criterio, e cosa il criterio NON è

Due ragioni, entrambe note **prima** che la passata girasse:

1. La soglia di 4.2b-2 era già dichiarata (`|z| < 3` successo, `> 5`
   fallimento). Quella di 4.2b-3 no — la consegna del 7 settembre la dà
   esplicitamente come «NON SCRITTA», perché `p1` non esisteva in nessun
   registro. Scriverla adesso significherebbe fissare una soglia dopo aver
   visto il valore che deve giudicare.
2. La curtosi ha **1800 ancore** in `n1b_spectra_NGC.jsonl`; `p1` non ne ha
   nessuna, ed è l'unica grandezza dell'intera passata che nessun registro
   congelato contiene.

**Va messo a verbale che il criterio non è stato il *z***. Al momento della
scelta era noto che *r*_f dà il segnale più forte: −9.666 e −11.840 contro
−7.108 e −8.150, ranghi 0/2000 in entrambi gli emisferi contro 3/2000 e 1/2000.
Scegliere la statistica più favorevole dopo averle viste entrambe sarebbe
selezione a posteriori, ed è precisamente ciò che questa nota esclude.

---

## 5. Decisione B — soglia di 4.2b-1 a *n* = 2000

| | dichiarata (*n*=200) | **nuova** (*n*=2000) | base v1 a P10 |
|---|---:|---:|---:|
| NGC | 7.3581 | **7.2924** | 3.6462 (era 3.6791) |
| SGC | 16.2032 | **16.1314** | 8.0657 (era 8.1016) |

Regola invariata nella forma: successo se *R*^v2(footprint pieno) + 3σ è sotto
la soglia.

Due ragioni:

- **v2 sarà misurata su 2000 realizzazioni**, non su 200, e la regola già in
  checklist dice che le soglie calibrate a un *n* non si applicano a un altro.
- La revisione va nella direzione **più severa**: 7.2924 < 7.3581 e
  16.1314 < 16.2032, quindi il successo diventa più difficile. Una modifica che
  stringe non ha bisogno di difendersi dal sospetto di essere di comodo.

I valori a *n*=200 restano nel registro come superati, non cancellati.

---

## 6. Decisione C — soglia di 4.2c

| | v1 (media d'ensemble) | successo < | fallimento > |
|---|---:|---:|---:|
| NGC | 4048.21 | **1349.40** | **2698.81** |
| SGC | 2811.56 | **937.19** | **1874.37** |

Sulla media d'ensemble dei 2000, come *P*_mock in 4.3b. Frazioni: un terzo e
due terzi, già dichiarate per 4.3b — non c'è una frazione scelta oggi.

**Condizione di invalidazione**: se su v2 la dispersione per realizzazione
supera un terzo della media v2, la regola smette di decidere. Su v1 quel
rapporto è 2.09% (NGC) e 2.54% (SGC), quindi la condizione non è al limite.

**Scomposizione lato dati / lato mock (principio del §2)**: la soglia dei
patologici è il massimo di δ di DESI — 125.47415161132812 in NGC,
161.6696 in SGC — ed è **lato dati e fissa** sotto ripesatura; il conteggio
viene interamente dal campo mock. Frazione invariante sotto ripesatura: **zero**.
È l'unica delle cinque regole di cui si possa dire, e per questo è anche l'unica
che porta informazione non già contenuta nelle altre.

**Perché non una regola in σ**: la SEM è 1.893 su una media di 4048.21. Qualunque
effetto reale vale migliaia di σ, quindi una soglia in σ non distinguerebbe
successo da fallimento.

---

## 7. Decisione D — la mediana di max δ è a *n* = 100

La consegna del 7 settembre, §6, sotto il blocco intitolato
«Statistiche a un punto, footprint pieno, v1, n=200», riporta:

> Massimo di δ per mock: mediana **3474.58**, minimo **2417.18**, massimo **32244.41**.

La passata su *n*=200 dà mediana 3530.1012 e minimo 2375.2747, con massimo
identico 32244.4102.

**Risoluzione**: quelle tre statistiche sono a *n* = 100, non 200.

| *n* | mediana | minimo | massimo |
|---:|---:|---:|---:|
| **100** | **3474.5798** | **2417.1763** | **32244.4102** |
| 200 | 3530.1012 | 2375.2747 | 32244.4102 |

La mediana 3474.58 vale solo per *n* fra 86 e 102; il minimo 2417.18 vale per
*n* ≤ 192 (l'indice 193 introduce 2375.27); nell'intersezione l'unico numero
tondo è 100.

Nessuno dei due valori è sbagliato. Il difetto è che una riga a *n*=100 sta
sotto un'intestazione che dichiara *n*=200.

---

## 8. Provenienza

| strumento | selftest | cosa ha prodotto |
|---|---|---|
| `paper2_cancello_nu.py` | 26/26 | `cancello_nu_NGC.jsonl` |
| `paper2_passata_1punto.py` | 43/43 | `onepoint_v1_{NGC,SGC}.jsonl` + sommari + righe DESI |
| `paper2_letture_1punto.py` | 31/31 | `letture_1punto_{NGC,SGC}.json` |
| `paper2_contratto_4_2a.py` | 19/19 | verifica: nove nomi accettati, quattro `N_H1_k*` assenti come atteso |

Costo: 0.12 s per mock, 4.1 minuti per emisfero.

---

## 9. Voci nuove di disciplina, per la checklist

Vengono da errori di questa sessione, tutti commessi da me e trovati dai dati:

- **Un flag su un record non è un'etichetta sul numero che contiene.** Avevo
  concluso che 35318 fosse un valore di smoke perché il primo record di
  `fase3_mock.jsonl` che lo porta ha `smoke: true`. È il contrario: 35318 è il
  valore di produzione, registrato come congelato negli amendment 14, 23, 35, 51
  e 52, e 35538 compare in un record di smoke. Lo smoke riproduce i valori di
  produzione — è il suo scopo — quindi la presenza di un numero dentro un record
  di smoke non dice nulla sulla sua provenienza. Per stabilirla vanno guardati
  tutti i record che lo portano.
- **Su una costante quotata la tolleranza è mezza unità dell'ultima cifra, non
  un relativo.** Una soglia relativa a 1e-4 respinge 0.274250 contro 0.2743, che
  è corretto: la quantizzazione di quattro decimali vale 1.8e-4 in relativo.
- **Due regole collineari sono una prova sola.** Vale come conteggio delle
  occasioni di smentita, non solo come ridondanza di calcolo.
- **Un'intestazione di blocco non copre necessariamente tutte le righe sotto.**
  Il caso *n*=100 sotto «n=200».
- **Un record che non è una misura non sta nel registro delle misure.** Il
  sommario senza `idx` ha fatto rifiutare il verificatore del contratto, ed è la
  stessa forma del difetto delle 38 prove di fumo dentro `fase3_mock.jsonl`.
