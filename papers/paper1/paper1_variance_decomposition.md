# Decomposizione della varianza e risposta cosmologica di N_H1

**Record congelato** — misura M1, n = 2000, luglio 2026.

Questo documento **sostituisce**:

- `paper1_sigma_discrepancy_resolution.md` §4.1 (decomposizione della varianza:
  l'ipotesi «oltre l'80% è varianza di realizzazione» è quantitativamente errata)
- `canovaccio_paper5.md` §2.1, §3.M1 e la regola di decisione di §4 (ora applicata)

Script: `src/paper1_rev_m1_cosmo_response.py`
Report: `results/paper1/rev_m1_cosmo_report.json`

---

## 1. Validazione preliminare

Tabella dei parametri:
`data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt`,
2000 × 7.

Mappatura delle colonne: `0=Om, 1=Ob, 2=h, 3=ns, 4=s8, 5=Mnu, 6=w0`. Verificata
contro `phase9_likeforlike_arrays.npz` sugli indici 0–199 con
`max|npz − params| = 0.0` su w0, Ωm e σ₈.

**Nota sul codice.** Il docstring di `load_nwlh_params()` in
`phase8_test2_masked.py` dichiara «6 colonne (Om, Ob, h, ns, s8, w0)»; il commento
interno dichiara 7 con Mν in posizione 5 e usa `tab[:,0], tab[:,4], tab[:,6]`. Il
commento e gli indici sono corretti, il docstring è sbagliato. Da correggere.

Disegno sperimentale: massima correlazione fuori diagonale fra i sette parametri
**0.037**. Latin hypercube pulito, quindi correlazioni univariate e coefficienti
multivariati concordano e nessuna degenerazione va districata.

I valori di N_H1 sono quelli corretti di Paper 1
(`results/paper1/per_mock_{NGC,SGC}_R5.jsonl`, 2000 ciascuno), non l'array
contaminato.

## 2. Risposta ai parametri cosmologici

NGC, n = 2000. Correlazioni univariate e coefficienti OLS del modello a sette
parametri (R² = 0.2606, R² aggiustato = 0.2580, σ residua = 269.6):

| parametro | r | IC95% | t (OLS) | coef | escursione sul range |
|---|---|---|---|---|---|
| **nₛ** | **+0.3761** | [+0.338, +0.413] | **+19.34** | +1010.4 | **+403.9** |
| h | +0.2099 | [+0.168, +0.251] | +10.90 | +569.9 | +227.8 |
| σ₈ | +0.1822 | [+0.140, +0.224] | +8.62 | +450.9 | +180.3 |
| Ωm | +0.1541 | [+0.111, +0.197] | +8.43 | +440.7 | +176.2 |
| Ωb | −0.1277 | [−0.171, −0.084] | −6.25 | −3271.1 | −130.8 |
| Mν | −0.0479 | [−0.092, −0.004] | −3.01 | −63.6 | −62.9 |
| w0 | +0.0554 | [+0.012, +0.099] | +2.45 | +85.4 | +51.2 |

SGC riproduce la stessa gerarchia con R² = 0.2773: nₛ +0.394 (t = +20.4), σ₈
+0.233, h +0.194, Ωm +0.137, Ωb −0.123, w0 +0.048, Mν −0.008.

Escludendo i quattro mock patologici le correlazioni si muovono di poco e nₛ
sale (+0.415 NGC): la gerarchia non dipende dalla coda.

### 2.1 Lettura fisica

**N_H1 è una sonda della FORMA dello spettro di potenza, non della sua ampiezza.**

Il lemma di invarianza monotona rende N_H1 cieco a rimappature monotone del campo,
e `build_field` applica log(1+δ) → lisciatura → sottrazione della media: nessuna
operazione reintroduce l'ampiezza assoluta. Di conseguenza σ₈ resta debole, mentre
i parametri che governano la forma — nₛ in primo luogo, poi h, Ωm, Ωb attraverso il
prodotto Γ = Ωm h e la soppressione barionica — dominano. Il segno negativo di Ωb
è quello atteso se lo smorzamento barionico riduce la potenza a piccola scala.

Non è un dettaglio interpretativo: è una **previsione del lemma ora misurata**, e va
enunciata come tale.

### 2.2 Correzione a M26

`cauchy_mnras.tex` riga 735 attribuisce la varianza a Ωm (r = +0.45) e debolmente a
σ₈ (+0.29), «not by w0 (−0.03)». Quei tre valori sono riprodotti esattamente
dall'array contaminato sui 200 indici del pilota (+0.4529, +0.2884, −0.0277).

L'errore non è solo nei numeri: è **nell'attribuzione**. Il driver è nₛ, che in M26
non è nemmeno menzionato.

## 3. La decomposizione, chiusa

NGC, σ totale = 312.989:

| termine | σ | frazione della varianza | fonte |
|---|---|---|---|
| cosmologia (7 parametri) | **160** | **26.1%** | R² × σ², questa misura |
| realizzazione delle CI | **246** | **61.6%** | residuo OLS meno HOD in quadratura |
| HOD / downsampling | **110** | **12.3%** | M26, 50 semi a cosmologia e realizzazione fisse |

Verifica: 160² + 110² + 246² = 313.4², contro 312.989 misurata. Torna allo 0.13%.

**Nessun residuo e nessuna inferenza per esclusione** — che era il vizio da
correggere in M26.

### 3.1 Riserve da dichiarare

- σ(realizzazione) è ottenuta per differenza dal residuo OLS, quindi assorbe
  qualunque dipendenza cosmologica **non lineare** non catturata dal modello.
  È un limite superiore.
- σ(HOD) = 110 viene da M26 su un singolo punto dell'hypercube (indice nwLH 1805).
  La misura M2 del canovaccio — pipeline Test 2 cut-sky sui 2000 cataloghi
  fiduciali — la verificherebbe direttamente e chiuderebbe anche questa riserva.
- Per SGC il termine HOD non è mai stato misurato, quindi la sua decomposizione si
  ferma a σ(cosmologia) = 104 e un residuo di 168.

### 3.2 Perché il pilota in scatola aveva sviato

`paper1_rev_v3b_pilot_box.py` dava σ(fiducial)/σ(nwlh) ≈ 0.006 in scatola, da cui
avevo concluso che la varianza di realizzazione fosse trascurabile. Sbagliato come
inferenza sul cut-sky: **in scatola non esistono né density matching né HOD né
carving**, quindi quel rapporto misura una decomposizione diversa da quella
richiesta. Nel cut-sky la realizzazione è il termine dominante.

Lezione di metodo: la misura corretta era a un file di testo di distanza e ho
costruito una deviazione in scatola per arrivarci. Verificare quali metadati
esistono già **prima** di progettare un esperimento sostitutivo.

## 4. Il limite cosmologico al deficit

Sommando in modulo le escursioni della tabella §2, l'angolo più estremo
dell'hypercube produce l'escursione massima consentita dal modello lineare:

| | escursione cosmologica massima | deficit osservato | rapporto |
|---|---|---|---|
| NGC | 1233 generatori | 7181 | **5.8×** |
| SGC | 763 generatori | 3591 | **4.7×** |

In unità della dispersione cosmologica, il deficit NGC è **45 σ_cosmo**.

L'hypercube copre Ωm ∈ [0.10, 0.50], σ₈ ∈ [0.60, 1.00], nₛ ∈ [0.80, 1.20],
h ∈ [0.50, 0.90], w0 ∈ [−1.30, −0.70]: una prior molto più ampia di qualunque
prior credibile, e indifendibile per chiunque volesse restringerla.

**Nessuna combinazione dei sette parametri, in nessun angolo di quell'iperspazio,
produce il deficit osservato.**

Riserve: il modello è lineare con R² = 0.26, quindi direzioni non lineari o
degeneri potrebbero produrre escursioni maggiori; e l'hypercube non contiene fisica
esotica. L'enunciato corretto è dunque: *entro ΛCDM+w0 come parametrizzato da questi
sette parametri, e al primo ordine, il deficit non è raggiungibile.*

Con questa riserva, è l'argomento più forte della serie contro l'interpretazione
cosmologica del deficit, e non era in nessun canovaccio.

## 5. Decisione su Paper 5

Regola fissata in `canovaccio_paper5.md` §4: procedere come test CPL se
|r(N_H1, w0)| > 0.10 con IC95% che esclude lo zero.

Misurato: **r = +0.0554, IC95% [+0.0116, +0.0990], n = 2000.**

L'IC esclude lo zero ma |r| non raggiunge 0.10. **Regola non soddisfatta.**

Dettaglio, perché l'esito non è «nessuna risposta»:

- pendenza +85.4 ± 34.8 generatori per unità di w0
- escursione su Δw0 = 0.60: **+51 generatori = 0.16 σ**
- limite superiore al 95%: 92 generatori = 0.29 σ
- medie binnate: andamento monotono in **entrambi** gli emisferi, stesso segno
  (NGC +84 su 10 bin con SEM 20; SGC +56 con SEM 13)
- termine quadratico in (w0+1)²: escluso (t = −0.39 NGC, −1.03 SGC), quindi non
  c'è risposta simmetrica attorno a w0 = −1 nascosta dietro un r lineare piccolo
- vincolo 1σ implicato su w0: **±2.0** nel caso più favorevole al 95%, contro
  **±0.06** di BAO DESI

La risposta a w0 è dunque **reale ma trenta volte troppo debole** per essere
competitiva.

### 5.1 Conseguenza

Paper 5 come test CPL su griglia w0–wa **non procede** nella forma prevista. Resta
da verificare M3 (realizzazioni per punto di griglia in AbacusSummit), ma con
σ(realizzazione) = 246 nel cut-sky e una risposta di 51 generatori sull'intero
intervallo di w0, il criterio di §M3 del canovaccio non ha margine: servirebbero
centinaia di realizzazioni per punto di griglia, e AbacusSummit ne offre una o due.

Riformulazione, secondo `canovaccio_paper5.md` §5, ora con una tesi misurata invece
che congetturale:

**«N_H1 è una sonda di forma dello spettro, e il deficit osservato non è
raggiungibile da nessuna forma entro ΛCDM+w0.»**

Contenuto: la gerarchia di §2 come primo risultato, la decomposizione di §3 come
secondo, il limite di §4 come terzo. Nessun vincolo su w0 — e il fatto che non ce ne
sia uno è a sua volta un risultato, perché quantifica il tetto di sensibilità che il
density matching impone a qualunque statistica topologica in un framework
like-for-like.

## 6. Errori corretti da questo documento

- «I parametri cosmologici spiegano ~4% della varianza»: era una stima ottenuta
  sommando r² di tre parametri misurati su n = 200. Il valore è **26%**, e il
  parametro dominante (nₛ) non era nemmeno nella lista considerata.
- «Oltre l'80% è varianza di realizzazione»: è **61.6%**.
- «σ(realizzazione) è trascurabile» (dal pilota in scatola): vale nella scatola,
  non nel cut-sky, dove è il termine dominante. Vedi §3.2.

## 7. Prossimi passi

1. **M2** — pipeline Test 2 cut-sky sui 2000 cataloghi fiduciali di
   `data/raw/quijote/3D_cubes/fiducial/`: verifica diretta di σ(realizzazione+HOD)
   e chiude le riserve di §3.1.
2. **Correzione dei percorsi di uscita** in `phase8_test2_masked.py`: `tbl` e
   `out_fields` vanno diramati sul tag del run come già avviene per il JSON. È il
   bug che ha prodotto l'intera contaminazione.
3. Aggiornare la bozza di response letter con il limite di §4, che è più forte di
   qualunque argomento attualmente nel manoscritto.
4. Aggiornare la nota di correzione per M26: riga 735 va riscritta nell'attribuzione
   (nₛ, non Ωm) oltre che nei numeri.
