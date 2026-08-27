# Paper 2 — Item 1.4 e 1.4a: regola di decisione e convenzione di σ_px
### 26 agosto 2026 — **dichiarati prima di qualunque run di Fase 3**

> Questo documento fissa cosa si misura, con quale rumore, e quali soglie separano i possibili
> esiti. Confluisce integralmente nella pre-registrazione (item 0.6). **Nessuna soglia qui è
> rinegoziabile a run in corso.** Se un esito cade in una zona non prevista, si riporta come tale e
> si dichiara che la regola era incompleta — non la si estende a posteriori.

---

## 1.4a — La convenzione di σ_px: la domanda si è dissolta

L'item 1.4a chiedeva di scegliere fra due convenzioni, perché lungo la vecchia linea B σ_px variava
dell'**1.64% picco-picco** (0.3178 → 0.3230) e la scelta cambiava il risultato.

**Nel gauge a cubo costante la domanda non esiste più.** Con *L* fisso, Δ*x* è fisso, quindi:

| | valore, su tutti e nove i punti | escursione misurata |
|---|---|---|
| NGC | σ_px = 0.32042249039652254 | 1.9 × 10⁻¹⁴ (rel 5.9 × 10⁻¹⁴) |
| SGC | σ_px = 0.33605500065144590 | 1.2 × 10⁻¹⁴ (rel 3.7 × 10⁻¹⁴) |

La regola a runtime della pipeline (*R*/Δ*x*, unità fisiche) e la convenzione in unità di griglia del
Paper 1 §8.3 **danno lo stesso numero**, perché Δ*x* non cambia. Non è una scelta risolta: è una
scelta resa vuota dal gauge.

**Dichiarazione.** Il Paper 2 adotta σ_px costante sulla griglia AP, al valore fiduciale della
regione, e riporta nel manoscritto che nel gauge scelto le due convenzioni coincidono. La practice 3
di §5.4 resta obbligatoria per chi lavori in un gauge diverso, con i due numeri che ne quantificano
la posta: **1.64%** dentro una griglia AP, **40%** fra suite con celle di dimensione diversa.

**Dove la questione sopravvive:** nei cancelli **2.2** e **2.3**, che dilatano deliberatamente e
quindi cambiano Δ*x*. Lì l'override è necessario, ed è una riga —
`build_nu(delta, mask, sigma_px)` prende σ_px come argomento (item 0.5 Q4).

---

## 1.4 — La regola di decisione

### 1. Cosa si misura, e cosa no

Il deficit a una geometria *g* è

&nbsp;&nbsp;&nbsp;&nbsp;*D*(*g*) = ⟨*N*_H1⟩_mock(*g*) − *N*_H1^DESI(*g*).

**Il lato dati è deterministico**: nessun rumore di realizzazione, quindi le differenze di
*N*_H1^DESI fra punti della griglia sono esatte. Il rumore sta tutto nel lato mock.

> **Il punto che decide tutto: l'AP agisce su entrambi i lati.** Se dati e mock rispondono allo
> stesso modo, la risposta **si cancella in *D***. È il principio like-for-like. La quantità di
> interesse è quindi la risposta **differenziale** ∂*D*/∂*F*_AP, non ∂*N*_H1/∂*F*_AP, che può essere
> grande — è un effetto geometrico reale — senza che *D* si muova di un generatore.
>
> **Entrambe vanno riportate**, e separatamente. Confonderle è l'errore più facile di questo paper.

**Statistica primaria:** *N*_H1 a erosione ***k* = 1** (item 1.2b), entrambi gli emisferi, con rango
empirico nell'ensemble. *k* = 0 riportato in parallelo per l'aggancio ai numeri v1.

**Griglia:** i nove punti di 1.3 rev. 2, gauge a cubo costante. Linea B simmetrica in residuo
minimax (0, ±0.2844, ±0.5687 voxel NGC; ±0.2982, ±0.5965 SGC), quattro angoli ri-gaugiati.

### 2. Le due soglie, e perché ne servono due

**Rilevabilità.** Con semi appaiati la dispersione per realizzazione di Δ*N*_H1 è σ_Δ = 250.5
(Paper 1). Con *N* coppie l'errore sulla media è σ_Δ/√*N*:

| *N* coppie | errore sulla media | soglia 3σ |
|---|---|---|
| 100 | 25.1 | 75 generatori |
| **200** | **17.7** | **53 generatori** |
| 500 | 11.2 | 34 generatori |

**Dichiarato: *N* = 200 coppie per punto, soglia di rilevabilità 53 generatori.**

**Rilevanza.** Un effetto rilevabile può essere irrilevante. L'ancoraggio è il **più grande
sistematico già caratterizzato**, l'ambiguità della regola di maschera, che vale ~1.1 pp di deficit:

| | 1.1 pp | in % del deficit |
|---|---|---|
| NGC | **390 generatori** | 5.4% |
| SGC | **206 generatori** | 5.7% |

**Dichiarato: soglia di rilevanza 390 (NGC) e 206 (SGC) generatori.**

*Nota: la soglia «3σ_Δ ≈ 750» della rev. 1 del checklist era la 3σ per singola realizzazione, non
sull'errore della media. Era conservativa di un fattore √200 ≈ 14, e va ritirata.*

### 3. I quattro esiti, dichiarati adesso

Sia Δ*D*_max l'escursione di *D* sulla linea B, fra B1 e B5.

| | condizione | conclusione, e cosa si scrive |
|---|---|---|
| **E1** | Δ*D*_max < 53 | **Limite superiore.** Si riporta il limite 3σ su ∂*D*/∂*F*_AP. La Prop. 2 è il risultato principale; la limitazione (ix) si chiude con un bound. |
| **E2** | 53 ≤ Δ*D*_max < 390 (206) | **Misura di sensibilità, sotto-dominante.** L'AP entra nel budget come termine minore, con il suo numero. (ix) chiusa con una misura. |
| **E3** | Δ*D*_max ≥ 390 (206) | **Sistematico di primo piano.** Il valore centrale del deficit va ri-quotato con l'incertezza di cosmologia fiduciale, e M26 §5 va aggiornato. |
| **E4** | E3 **e** l'estrapolazione azzera *D* dentro il range fisico | **L'AP potrebbe spiegare il deficit.** Da verificare direttamente al *F* richiesto, non per estrapolazione. |

### 4. La quantità che decide E4, dichiarata come derivata

> ***F*_AP richiesto**: il valore che azzererebbe il deficit sotto estrapolazione lineare della
> risposta misurata.

**Regola di lettura, dichiarata prima:** l'escursione fisicamente ammessa dalla griglia
(Ω_m, *w*₀) è |*F* − 1| ≤ **0.027** (item 1.2a, convenzione α_⊥/α_∥). Quindi:

- **|*F*_richiesto − 1| > 0.027 → l'AP non può spiegare il deficit**, qualunque sia l'ampiezza della
  risposta. È una falsificazione pulita e va enunciata come tale.
- **|*F*_richiesto − 1| ≤ 0.027 →** si esegue il punto a *F*_richiesto e si **misura**, invece di
  estrapolare.

La linea B copre |*F* − 1| fino a **0.0301**, quindi bracket a il range fisico con un margine dell'11%.

### 5. Il test di simmetria, che la linea simmetrica compra gratis

Fit su cinque punti: *D*(*F*) = *D*₀ + *a*(*F*−1) + *b*(*F*−1)².

- **|*a*| > 3σ(*a*) e |*b*| < 3σ(*b*)** → risposta **dispari**: compressione e stiramento radiale non
  sono equivalenti; la topologia vede una **direzione**.
- **|*b*| > 3σ(*b*) e |*a*| < 3σ(*a*)** → risposta **pari**: la topologia vede il disallineamento
  radiale/trasverso come una **degradazione**, non come una direzione.
- entrambi → si riportano entrambi.

Sono affermazioni fisiche diverse, e il costo di distinguerle è zero.

### 6. Il test di completezza sugli angoli

Dalla linea B si predice *D*(*C*_i) interpolando in *F* efficace. Con la stessa soglia di
rilevabilità (53 generatori, *N* = 200):

- **|*D*_obs − *D*_pred| < 53 su tutti e quattro** → la famiglia (α_iso, *F*_AP) è sufficiente; si
  riporta una superficie di risposta a due variabili, chiusa.
- **fallisce su C1 e/o C4 ma non su C2 e C3** → il **terzo canale** è reale. Atteso, se lo è:
  0.082 voxel a C1 e 0.047 a C4, contro 0.006 e 0.005 a C2 e C3 — cioè al livello dell'artefatto di
  padding negli angoli intermedi. **La predizione ha già la sua firma: deve fallire dove il canale è
  grande e non dove è piccolo.**
- **fallisce ovunque, C2 e C3 compresi** → non è il terzo canale. È tiling o ri-randomizzazione del
  carving, e la decomposizione 3.3 deve chiuderlo **prima** di interpretare qualunque derivata.

### 7. Cosa NON è una regola di decisione

Il gauge a cubo costante ha reso costanti, per costruzione e non per correzione, tre quantità che
altrimenti avrebbero potuto imitare una risposta AP: **repliche di tiling** (15 in NGC, 10 in SGC su
tutti e nove i punti), **σ_px**, e **frazione di voxel con *w* < 0.99** (0.0776–0.0781 in NGC,
0.1778–0.1787 in SGC). Nessuna delle tre entra più nel budget come sistematico da sottrarre.

Restano da misurare in Fase 3, e non sono coperti da questa regola:
**(a)** la ri-randomizzazione del carving a geometria fissa (cancello 2.5 + sottrazione in
quadratura, item 3.3); **(b)** il numero di galassie che cambiano stato di selezione per punto
(rottura (ii) di 1.1b, item 3.2).

---

## Riepilogo delle costanti dichiarate

| | simbolo | valore |
|---|---|---|
| mock per punto, semi appaiati | *N* | **200** |
| dispersione per realizzazione | σ_Δ | 250.5 |
| soglia di rilevabilità | 3σ_Δ/√*N* | **53 generatori** |
| soglia di rilevanza NGC | 1.1 pp | **390 generatori** |
| soglia di rilevanza SGC | 1.1 pp | **206 generatori** |
| range fisico di *F*_AP | \|*F*−1\| | **0.027** |
| copertura della linea B | \|*F*−1\| | 0.0301 |
| erosione primaria | *k* | **1** |
| σ_px NGC | | 0.32042249039652254 |
| σ_px SGC | | 0.33605500065144590 |

---

## Cosa manca prima della Fase 3

1. **Fase 2** — cancelli 2.1, 2.2a/b, 2.3, 2.5. Il 2.2 richiede l'override di σ_px, che ora sappiamo
   dove va.
2. **Pre-registrazione (0.6)** — questo documento più la sezione di trasparenza di 0.10.
3. **Ensemble v2 (4.2a)** — non blocca la Fase 3 sulla Componente A, ma blocca i Paper 3 e 4.
