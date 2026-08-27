# Paper 2 — Item 1.3: la griglia definitiva in (α_iso, *F*_AP)
### 25 agosto 2026 — design, nessun run

> **Sostituisce** il campionamento provvisorio proposto in §4 di `paper2_item12a.md`
> (*F*_AP ∈ {0.961, 0.980, 1.000, 1.013, 1.027}), che era ancorato agli estremi **puntuali** di
> *F*_AP(*z*) e non alla quantità operativa. Motivo della sostituzione in §3.

---

## 1. Il risultato che fissa la parametrizzazione

Nella pipeline la fiducia entra come una singola mappa radiale *r* → *f*(*r*), identica in ogni
direzione. A distanza *r* le separazioni trasverse scalano di *f*(*r*)/*r* e quelle radiali di
*f*′(*r*). Dunque, senza passare per *z*:

> **Lemma 3.** *Per una rimappatura radiale f, il parametro di Alcock–Paczyński locale è*
>
> &nbsp;&nbsp;&nbsp;&nbsp;*F*_AP(*r*) = α_⊥/α_∥ = *f*(*r*) / (*r f*′(*r*)).
>
> *Esso è costante e pari a F₀ su tutto l'intervallo **se e solo se***
>
> &nbsp;&nbsp;&nbsp;&nbsp;*f*(*r*) = *A r*^(1/*F*₀).

*Dimostrazione.* *f*/(*r f*′) = *F*₀ ⟺ *f*′/*f* = 1/(*F*₀*r*) ⟺ d ln *f* = (1/*F*₀) d ln *r*. ∎

Tre conseguenze immediate.

1. ***F*_AP = 1 ⟺ *f* lineare ⟺ Proposizione 2.** Le due proposizioni si incastrano: il canale
   isotropo è esattamente il caso *F*₀ = 1, dove *N*_H1 è invariante. Non serve un argomento
   separato.
2. **La linea *F*_AP pura è una famiglia a un parametro esplicita**, *f* = *A r*^(1/*F*₀), con *A*
   fissato dalla normalizzazione α_iso = 1. Non serve scegliere un *z*_pivot: *F* è costante per
   costruzione, e l'ambiguità del pivot sparisce.
3. **Il test di convenzione su `make_dc_tab_ap` diventa banale.** Chiamarla con
   `alpha_iso=1.0, F_ap=1.03`, prendere la *D*_C(*z*) risultante, e fare una regressione di
   ln *f* su ln *r*:

   | pendenza osservata | convenzione implementata |
   |---|---|
   | 0.9709 = 1/1.03 | *F* = α_⊥/α_∥ (standard, *D*_M *H*/*c*) |
   | 1.03 | *F* = α_∥/α_⊥ (quella della tabella del 25 ago) |
   | nessuna delle due | la funzione non produce *F* costante — da capire prima di 1.3 |

   **Questa è la precondizione dell'item 1.3.** Costa due minuti e decide l'etichetta di ogni punto
   della linea B. *In questo documento uso ovunque la convenzione standard α_⊥/α_∥.*

**Nota di implementazione.** *A* dipende dalle unità di *r*, perché *r*^(1/*F*) non è omogeneo: con
*r* in h⁻¹Mpc e α_iso = 1 si ha *A* = 0.783 a *F* = 0.9648 e *A* = 1.271 a *F* = 1.0372. Se
`make_dc_tab_ap` lavora in altre unità la normalizzazione va ricalcolata, non trasportata.

---

## 2. La griglia

Tre blocchi. Undici punti nominali, di cui il fiduciale è già in mano (ensemble v1).

### Blocco A — linea α_iso pura, *F*_AP = 1 (test di chiusura)

| | α_iso | attesa |
|---|---|---|
| A1 | 0.9725 | Δ*N*_H1 = 0 esatto con `pad = 5.0·α_iso`; ≤ 5 generatori col padding additivo |
| A2 | **1.0000** | fiduciale, già misurato |
| A3 | 1.0406 | come A1 |

Non è una misura: è la Proposizione 2 messa alla prova sulla pipeline reale, agli estremi effettivi
della griglia invece che al valore convenzionale α = 1.05 del cancello 2.2. **Richiede solo il lato
dati** — due run, non due ensemble di mock. Se A1 o A3 danno uno scarto sopra 5 generatori, tutto il
resto si ferma.

### Blocco B — linea *F*_AP pura, α_iso = 1 (il segnale fisico)

Campionata a **residuo anisotropo equispaziato in voxel**, non a *F* equispaziato — vedi §3.

| | *F*_AP | *A* | residuo (h⁻¹Mpc) | voxel NGC | voxel SGC |
|---|---|---|---|---|---|
| B1 | 0.9648 | 0.78348 | 11.55 | **0.740** | 0.776 |
| B2 | 0.9822 | 0.88561 | 5.77 | 0.370 | 0.388 |
| B3 | **1.0000** | 1.00000 | 0.00 | 0.000 | 0.000 |
| B4 | 1.0183 | 1.12799 | 5.77 | 0.370 | 0.388 |
| B5 | 1.0372 | 1.27107 | 11.55 | **0.740** | 0.776 |

Il campionamento è **simmetrico in ampiezza**: B1/B5 e B2/B4 hanno residuo identico in modulo e
segno opposto di (*F*−1). Questo compra un test che non era nel piano:

> *N*_H1 risponde al **segno** della distorsione AP, o solo alla sua **ampiezza**?

Una risposta pari — Δ*N*(B1) ≈ Δ*N*(B5) — significa che la topologia vede il disallineamento
radiale/trasverso come una degradazione, non come una direzione. Una risposta dispari significa che
compressione e stiramento radiale non sono equivalenti. Sono due affermazioni fisiche diverse e il
costo di distinguerle è zero, perché i punti servivano comunque.

L'escursione è ancorata a **0.740 voxel**, il residuo massimo dell'intera griglia (Ω_m, *w*₀) sui due
emisferi. B1 e B5 quindi *bracketano* il caso fisico peggiore invece di interpolarlo.

### Blocco C — quattro angoli di controllo

| | Ω_m | *w*₀ | *F*_eff | residuo tot. (vox NGC) | quota **non** rappresentata dai blocchi A+B |
|---|---|---|---|---|---|
| C1 | 0.25 | −1.2 | 0.97320 | 0.735 | **0.165 vox (22.4%)** |
| C2 | 0.25 | −0.8 | 1.00577 | 0.106 | 0.013 vox (12.2%) |
| C3 | 0.35 | −1.2 | 0.99293 | 0.139 | 0.008 vox (5.8%) |
| C4 | 0.35 | −0.8 | 1.01906 | 0.453 | 0.090 vox (19.8%) |

---

## 3. Il punto che cambia il ruolo del blocco C

**La famiglia a due parametri (α_iso, *F*_AP) non è completa.** Una cosmologia reale ha *F*_AP(*z*)
che varia sull'intervallo: per (0.25, −1.2) va da 0.9611 a 0.9856. La legge di potenza che meglio la
approssima lascia un residuo di **0.165 voxel** — il 22.4% dell'ampiezza anisotropa totale.

Il confronto che conta:

| | ampiezza in voxel |
|---|---|
| residuo anisotropo massimo (segnale fisico) | 0.740 |
| **quota non catturata da (α_iso, *F*_AP)** | **0.165** |
| artefatto di padding additivo (Prop. 2′) | 0.013 |

La quota non modellata è **12.6 volte** l'artefatto di padding: è misurabile, non trascurabile.
Due conseguenze.

1. **Gli angoli non sono un "controllo di consistenza": sono l'unico posto dove vive il terzo
   canale.** Vanno trattati come punti di misura a pieno titolo, con lo stesso numero di mock
   appaiati dei punti B. La formulazione del checklist — *"i quattro angoli della griglia originale
   come controllo di consistenza"* — va aggiornata.
2. **C2 e C3 dicono qualcosa di diverso da C1 e C4.** Per C2 e C3 la quota non modellata (0.008 –
   0.013 voxel) è **allo stesso livello dell'artefatto di padding**: lì la famiglia a due parametri è
   esatta entro il rumore di fondo dell'implementazione. Per C1 e C4 non lo è. Se la predizione
   A+B → C tiene su C2 e C3 e fallisce su C1 e C4, il verdetto è netto e attribuito.

### Il test di completezza, dichiarato prima dei run

Dai blocchi A e B si ricava la superficie di risposta *D*(α_iso, *F*_AP) (con la parte α_iso attesa
piatta). Per ogni angolo *C*_i si predice *D*_pred(*C*_i) interpolando in *F*_eff. Allora:

- **Se |*D*_obs − *D*_pred| < σ_Δ ≈ 250 generatori su tutti e quattro gli angoli**, la
  parametrizzazione a due parametri è sufficiente e il paper riporta una superficie di risposta a due
  variabili, chiusa.
- **Se lo scarto supera σ_Δ su C1 e/o C4 ma non su C2 e C3**, il terzo canale è reale e si riporta
  come tale, con la sua ampiezza in voxel: è un risultato metodologico, non un fallimento.
- **Se lo scarto supera σ_Δ ovunque, compresi C2 e C3**, allora non è il terzo canale — è il tiling,
  o la ri-randomizzazione del carving, e la decomposizione 3.3 deve chiuderlo prima di interpretare
  qualunque derivata.

Soglia dichiarata qui, non rinegoziabile a run in corso.

---

## 4. Perché il campionamento è cambiato rispetto a `paper2_item12a.md` §4

Ieri avevo proposto *F*_AP ∈ {0.961, 0.980, 1.000, 1.013, 1.027}, ancorato agli estremi **puntuali**
di *F*_AP(*z*) sulla griglia. È l'ancoraggio sbagliato per due motivi.

1. Gli estremi puntuali includono la variazione in *z* dentro un singolo punto di griglia. Il *F*
   **costante** che rappresenta meglio l'angolo peggiore è 0.9732, non 0.9611. Campionare a 0.961
   avrebbe piazzato B1 fuori dal range effettivo, con residuo 0.823 voxel invece di 0.740.
2. *F* e residuo non sono in relazione lineare: equispaziare in *F* non equispazia la quantità che la
   pipeline vede. Il campionamento corrente equispazia i voxel — 0, 0.370, 0.740 — che è la variabile
   della figura F1 e quella rispetto a cui si stima ∂*D*/∂*F*_AP.

---

## 5. Costo

| blocco | geometrie nuove | lato dati | lato mock | note |
|---|---|---|---|---|
| A | 2 (A1, A3) | ✓ | — | attesa nota; mock non necessari |
| B | 4 (B1, B2, B4, B5) | ✓ | 100–200 appaiati | il segnale |
| C | 4 | ✓ | 100–200 appaiati | il terzo canale |
| | **10** | 10 run | **8 ensemble** | contro i 12 punti × ensemble del piano originale |

Il piano originale prevedeva 12 geometrie complete. Questo ne prevede **8 complete più 2 run di sola
chiusura**, e in cambio ogni punto risponde a una domanda dichiarata invece di riempire una casella
di una griglia rettangolare.

---

## 6. Cosa 1.3 **non** decide

La regola di decisione — se il Paper 2 sia una misura di sensibilità o un limite superiore — resta
all'item **1.4**, e va scritta prima che parta il primo run del blocco B. Il design qui sopra è
neutrale rispetto all'esito: la stessa griglia produce sia la superficie di risposta sia il limite
superiore, a seconda di cosa esce.

---

## 7. Precondizioni, in ordine

1. **Test di convenzione su `make_dc_tab_ap`** (§1, punto 3). Due minuti, blocca l'etichettatura di
   tutto il blocco B.
2. **Metà geometrica di 1.2a** — serve il Δ*x* effettivo per convertire i residui in voxel e per il
   σ_px di ogni punto.
3. **1.2b** — w̄ per punto; potrebbe escludere qualche angolo, e in tal caso il blocco C perde
   proprio i punti che portano il terzo canale. Se C1 o C4 falliscono w̄, va detto esplicitamente
   nel manoscritto che il terzo canale resta non misurato, invece di far finta che gli angoli
   superstiti bastino.
4. **1.5a** — molteplicità di tiling per punto. Dipende da α_iso, quindi è **costante lungo tutto il
   blocco B** (α_iso = 1) e varia solo lungo A e C. Questo è il beneficio principale della
   riparametrizzazione: il blocco che porta il segnale è quello immune al confondente.

---

## 8. Da aggiornare negli altri documenti

1. **Checklist 1.3** — sostituire "quattro angoli di controllo" con "quattro angoli di misura,
   unici portatori del canale oltre-legge-di-potenza".
2. **Checklist 1.2** / **consegna §5.4** — l'escursione di *F*_AP da citare come intervallo di
   *F* **efficace** (0.973 – 1.019) accanto a quello puntuale (0.961 – 1.027): sono due cose diverse
   e la prima è quella che il design usa.
3. **Canovaccio §7, struttura** — la sezione 4 acquista un terzo contenuto: oltre a griglia, w̄ ed
   esclusioni, il test di completezza della parametrizzazione.
4. **Figura F1** — la banda ±1 voxel proposta è larga rispetto ai residui reali (max 0.78). Meglio
   ±0.1 voxel con la soglia dell'artefatto di padding (0.013) tracciata come riferimento inferiore:
   così la figura mostra insieme il segnale, il terzo canale e il rumore di costruzione.
5. **Lemma 3** — va nel manoscritto §2, subito dopo la Proposizione 2: è tre righe e giustifica la
   parametrizzazione invece di postularla.
