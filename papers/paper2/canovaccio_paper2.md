# Paper 2 — canovaccio rev. 25 agosto 2026 (sera)
## A cosa risponde *N*_H1: geometria, pesatura e cosmologia

> **Sostituisce la revisione del 25 agosto (mattina).** Due motivi.
>
> **(1) Fusione.** Il canovaccio del Paper 5 è assorbito qui come **Componente D**. Il triage aveva
> già stabilito che il test CPL non è fattibile su quella griglia; il suo contenuto residuo — il
> tetto di sensibilità delle statistiche topologiche — è la stessa domanda di cui parlano le
> Componenti A e B, rivolta a un parametro diverso. Due paper probabilmente nulli diventano le due
> metà negative di un enunciato positivo.
>
> **(2) La Fase 1 ha prodotto risultati che cambiano il paper.** Prop. 2 emendata e verificata su
> dati reali, Lemma 3, il gauge di Chebyshev, e quattro scoperte sulla pipeline che diventano
> materiale del manoscritto invece che note interne.

**Titolo di lavoro:** *"What does the loop count respond to? Geometry, weighting and cosmology in
persistent homology of voxelized redshift surveys"*

**Cita:** M26 (MN-26-2100-P) e Paper 1 (MN-26-2388-P).

---

## 1. La domanda, e perché la fusione la rende un paper

M26 stabilisce un deficit; il Paper 1 mostra che non è a un punto e che il 76% è a due punti. Resta
la domanda che nessuno dei due pone: **a cosa risponde questa statistica?**

La risposta che emerge dalla Fase 1 ha una struttura a quattro negazioni e un'affermazione:

| | canale | esito | chiuso da |
|---|---|---|---|
| 1 | ampiezza del campo | invariante | **Prop. 1** (teorema) |
| 2 | dilatazione isotropa / AP isotropo | invariante | **Prop. 2** (teorema) |
| 3 | AP anisotropo | sub-voxel, ≤ 0.60 voxel | misura, Componente A |
| 4 | *w*₀ | *r* = −0.015, *p* = 0.84, risposta piatta | misura, Componente D |
| **5** | **forma dello spettro** | ***r*(*n*_s) = +0.376** | **misura** |

Il paper non è «l'AP non spiega il deficit» più «*w*₀ nemmeno». È: *ecco la funzione di risposta di
N*_H1*, e ha una forma sorprendente* — insensibile all'ampiezza per teorema, insensibile alla
geometria per teorema, insensibile a *w*₀ per misura, e sensibile alla **forma** dello spettro
primordiale. Una statistica così, che segnala un deficit a rango 1/2001, sta rispondendo a qualcosa
che i parametri di ΛCDM non parametrizzano.

Questo è anche l'unico modo onesto di far stare insieme il deficit e l'insensibilità: **non è una
contraddizione, è il contenuto.**

---

## 2. Risultati teorici già in mano

### Proposizione 2 (dimostrata, verificata su dati reali)

> Se il cubo di embedding è il bounding box del catalogo random su griglia *N*³ con padding nullo o
> **moltiplicativo**, e σ_px è fissato in unità di griglia, il diagramma di persistenza è
> **esattamente invariante** sotto dilatazione isotropa *r* → α*r*.

La dimostrazione non usa nulla di topologico: riguarda la **parametrizzazione**, non la statistica, e
vale per qualunque schema di assegnazione, kernel e grado omologico. È complementare e indipendente
dalla Prop. 1, che vincola il codominio del campo invece del suo dominio.

### Proposizione 2′ (residuo dell'implementazione)

Con padding additivo *p* = 5 h⁻¹Mpc costante, la mappa fra coordinate di griglia è l'affinità
*u*(α) = *a*(α)·*u*(1) + *b*(α) con *a* = α(*E*+2*p*)/(α*E*+2*p*) e **punto fisso al centro del
cubo**: una dilatazione residua di ampiezza max |Δ*u*| = *Np*|1−α|/(α*E*+2*p*), **≤ 1.4 × 10⁻²
voxel** su tutta la griglia e in entrambi gli emisferi.

**Verificata per quattro vie indipendenti**, l'ultima su 13.2 milioni di random veri: predice il lato
del cubo dei punti a dilatazione pura a 5 × 10⁻⁵ h⁻¹Mpc (A1: predetto 1942.710437, osservato
1942.7104; A3: 2078.049851 contro 2078.0498), e α_box − α_iso a tre cifre significative.

### Lemma 3

> Per una rimappatura radiale, *F*_AP(*r*) = *f*(*r*)/(*r f*′(*r*)); è costante e pari a *F*₀ **se e
> solo se** *f*(*r*) = *A r*^(1/*F*₀).

Elimina l'ambiguità del *z*_pivot, incastra la Prop. 2 come il caso *F* = 1, e rende immediato il
test di convenzione su `make_dc_tab_ap` (regressione ln *f* su ln *r*).

### Il gauge della decomposizione

La separazione *f* = α_iso·*r* + residuo **non è unica**: α_iso da minimi quadrati è una media pesata
di *f*/*r*, e il residuo varia di un fattore 4.3 sull'insieme degli α ammissibili. Per la Prop. 2 la
parte isotropa è assorbibile a costo zero, quindi il contenuto fisico è il **minimo su α** —
l'approssimazione di Chebyshev. Il fit ai minimi quadrati **sovrastima il segnale AP fino al 26.4%**.

Residuo anisotropo fisico, gauge minimax: **0.541 voxel** al punto peggiore della griglia con Δ*x*
effettivo, contro 0.013 voxel di artefatto di padding. **Rapporto 41×.**

---

## 3. Le quattro componenti

### Componente A — geometria AP *(chiude la limitazione ix)*

Griglia riparametrizzata in (α_iso, *F*_AP), tre blocchi:

- **A1–A3, linea α_iso pura:** test di chiusura ad attesa nota. Solo lato dati.
- **B1–B5, linea *F*_AP pura:** il segnale, campionato a residuo minimax equispaziato in voxel e
  **simmetrico**, il che compra il test se *N*_H1 risponda al segno della distorsione o solo alla sua
  ampiezza.
- **C1–C4, quattro angoli:** **non sono controlli**. La famiglia a due parametri non è completa: al
  peggiore degli angoli lascia 0.082 voxel non modellati, il 14.5% dell'ampiezza e 6× l'artefatto di
  padding. Gli angoli sono l'unico posto dove quel terzo canale è misurabile.

Otto geometrie complete più due run di sola chiusura, contro le dodici del piano originale.

### Componente B — pesatura dei mock, ensemble v2

Il Paper 1 §7.2 ha già eseguito la correzione FKP alla sorgente su 60 coppie appaiate
(Δ*N*_H1 = −78.0 ± 8.0, −9.7σ, −1.09% del deficit, verso i dati). Restano:

- l'ensemble completo a 2000 realizzazioni, ~16 h;
- le predizioni a un punto mai misurate (PDF di δ e ν, v1 contro v2 contro DESI);
- la verifica **per prima** che v2 non sposti il residuo beyond-two-point del Paper 1.

**È il prodotto che serve a tutta la serie**, e la ragione per cui il Paper 2 va eseguito per primo
anche se non è il più interessante: un ensemble sbagliato propagato a tre paper è il difetto più
costoso che questo programma possa commettere.

### Componente C — scala di erosione su v2

Risolve la tensione registrata come F0.4: §8.1 attribuisce il massimo del deficit a *k* = 1 alla
rimozione dei voxel contaminati FKP, §7.2 misura l'effetto della pesatura a −78 loop mentre
l'escursione *k* = 0 → *k* = 1 vale ≈ +1840. Fattore ~24. Riusa la cache di B.

### Componente D — risposta ai parametri cosmologici *(ex Paper 5)*

#### Il meccanismo, che viene prima dei numeri

`carve_cutsky` sottocampiona **ogni** mock a `N_TARGET_BGS = 217614` seguendo l'*n*(*z*) di DESI:
tutti i mock finiscono alla stessa densità numerica. È **corretto e necessario** — è ciò che rende il
confronto like-for-like — ma rimuove l'informazione di ampiezza, che è il canale principale
attraverso cui i parametri cosmologici agiscono su una statistica di struttura. A questo si somma la
Prop. 1: `build_field` applica log(1+δ) → lisciatura → sottrazione della media, e nessuna di queste
operazioni reintroduce ampiezza assoluta.

**L'insensibilità non è un difetto della statistica: è una conseguenza del protocollo, prevedibile a
priori.** Questa è la spiegazione causale, e va enunciata prima delle correlazioni, non dopo.

> *Chiusura numerica gratuita:* `N_TARGET_BGS = 217614` coincide esattamente con `N_data` misurato da
> `data_side('NGC')`. Il bersaglio di sottocampionamento **è** il campione DESI.

#### Le misure

**Già eseguito, dentro M26 R1 §5.5** — la decomposizione della varianza chiude senza residuo:

| termine | valore | quota |
|---|---|---|
| σ(cosmologia) | 261.5 | 69.8% |
| σ(HOD + downsampling) | 128.3 | 16.8% |
| σ(realizzazione) | 114.6 | 13.4% |
| σ_fixed | 172.0 | — |
| σ totale | 313.0 | 100% |

**Da chiudere, e costa minuti:** correlazione parziale di *w*₀ su **tutti i 2000** valori parametrici
(`latin_hypercube_nwLH_params.txt`), non sui 200 etichettati. A *n* = 2000 l'errore su *r* scende a
0.022, quindi anche *r* = 0.05 sarebbe misurabile. Il valore disponibile è *r* = −0.015 con *p* di
permutazione 0.84 a *n* = 200, e la risposta binned è piatta.

Correlazioni **grezze** a *n* = 200 sull'ensemble nwLH, che copre *w*₀ ∈ [−1.30, −0.70], cioè ±0.30
attorno a −1 — un intervallo molto più ampio di qualunque prior credibile:

| parametro | *r* | IC95% |
|---|---|---|
| *w*₀ | **+0.011** | [−0.128, +0.150] |
| Ω_m | +0.150 | [+0.012, +0.283] |
| σ₈ | +0.137 | [−0.002, +0.270] |

Da non confondere con la correlazione **parziale** di M26 R1 §5.5, *r*(β₁, *w*₀ | Ω_m, σ₈) = −0.015
con *p* di permutazione 0.84: sono due quantità diverse e vanno etichettate come tali nel manoscritto.

**La leva, e il numero da titolo.** Dal limite superiore al 95% (*r* < 0.15): pendenza
< 0.15 × 313 / 0.174 ≈ **270 generatori per unità di *w*₀**; su Δ*w*₀ = 0.6 l'escursione è
**< 162 generatori**, cioè **< 0.52 σ**; il vincolo 1σ corrispondente su *w*₀ è circa **±0.6**, contro
i **±0.06** di BAO DESI. **Un ordine di grandezza peggio, nel caso più favorevole consentito dai dati
attuali.** È questo il numero che chiude la questione, non la correlazione.

**Il confronto scatola / cut-sky, con la sua riserva dichiarata.** Dal pilota in scatola a *N* = 3:
dispersione relativa 15.3% (scatola, cosmologia variabile) contro 0.88% (cut-sky, *N* = 2000), cioè
un fattore ~17 di soppressione. **Non è attribuibile al density matching da solo:** le due
configurazioni differiscono anche per volume, geometria, dimensione di cella (7.81 contro 15.60
h⁻¹Mpc), trattamento del bordo e filtrazione mascherata. Il 17 è un **limite superiore** alla
compressione da density matching, non una sua misura, e va scritto così.

**Il risultato positivo:** *n*_s guida a *r* = +0.376; σ₈ è debole, coerentemente con l'invarianza
monotona. E **nessuna cosmologia campionata raggiunge il deficit**, che resta un fattore 4.8 lontano.

**L'invarianza monotona come pregio, non come limite.** La Prop. 1 è normalmente presentata come una
restrizione. È anche una **garanzia di robustezza**: la statistica è immune per teorema agli errori di
calibrazione dell'ampiezza, al bias di luminosità e a qualunque errore moltiplicativo nei pesi. In un
contesto dominato dai sistematici è un vantaggio, e va detto in quei termini.

**Il tetto di sensibilità come risultato metodologico.** Con *n*_r realizzazioni per punto serve
Δ*N*_H1 > 2√2·σ_fixed/√*n*_r per distinguere due punti adiacenti: a *n*_r = 2, **344 generatori**,
contro un'escursione stimata sull'intero intervallo di *w*₀ sotto 162. La griglia non ha la potenza,
con margine ~2.1×. **Questo è il numero che serve a chiunque proponga statistiche topologiche per
vincolare la cosmologia, e nessuno l'ha misurato in modo controllato.** Chiude la limitazione (ii)
come limite, non come misura.

---

## 4. Quattro scoperte sulla pipeline, che vanno nel manoscritto

Non sono note interne: sono la parte del paper che altri riutilizzeranno.

**(a) σ_px è calcolato a runtime come *R*/Δ*x*.** Verificato all'ultimo bit: σ_px × Δ*x* = 5.000000.
La pipeline usa dunque la convenzione in **unità fisiche**, non quella in unità di griglia scelta dal
Paper 1 §8.3. Conseguenza operativa: il cancello 2.2 richiede un **override esplicito** di σ_px,
altrimenti misura il 2.3. Conseguenza sostanziale: lungo la linea *F*_AP pura, dove α_iso = 1 per
costruzione ma il lato del cubo varia dello 0.8%, la regola a runtime inietta una variazione di σ_px
dell'**1.64% picco-picco** proprio sulla linea che porta il segnale. Con la convenzione in unità di
griglia è esattamente zero.

**(b) `set_geometry()` non ri-deriva il box.** Iniettando una tabella *D*_C deformata, *D*_C cambia e
il box resta al valore fiduciale. Va ripassato esplicitamente dopo `derive_box`, e farlo commuta
automaticamente σ_px alla convenzione fisica. Questo è il punto in cui una pipeline può
silenziosamente voxelizzare una geometria su una griglia che non le appartiene.

**(c) La regola di maschera `v1_fullcube`, decodificata.** Soglia = 1% della densità random pesata
media **sul cubo pieno**: 0.01 × Σ*w*_r/128³ = 0.0200129. Riproduce `mask_threshold` a dieci cifre.
La regola concorrente differisce di un fattore ~6.5–6.8 e sposta il conteggio dei voxel di alcuni
punti percentuali.

**(d) Il σ_px fiduciale SGC è 0.336055, sopra il limite pratico 0.333 derivato da NGC.** Applicato
tale e quale, quel limite escluderebbe il fiduciale SGC — cioè un risultato già pubblicato. *d*_med
va ricalcolato per regione e per geometria: **il criterio di esclusione non può essere una soglia
scalare unica**, ed è la correzione più importante che questo paper porta al protocollo di M26.

**Bonus, non nel manoscritto ma nel record:** nel modulo `positions(region, kind)` qualunque `kind`
diverso da `"ran"` cade nel ramo `else` e restituisce **i dati** senza errore. È la stessa classe di
difetto della collisione di path che aveva prodotto la discrepanza 445/313 nel Paper 1. Guardia
inserita.

---

## 5. Le convenzioni da dichiarare — la vera eredità metodologica

M26 §6.2 elenca le practice obbligatorie. Questo paper ne aggiunge **quattro**, e tre non erano
esplicite in nessuno dei due manoscritti precedenti:

1. verificare w̄ per **ogni** geometria fiduciale, non una volta sola;
2. pesare i mock come i dati;
3. **dichiarare la convenzione di σ_px** — unità fisiche o di griglia — perché sotto AP le due non
   sono equivalenti, e la pipeline di default sceglie la prima. **L'ampiezza della scelta dipende dal
   contesto e va data con entrambi i numeri:** 1.64% picco-picco lungo la linea *F*_AP dentro questa
   griglia, ma **40%** fra suite con celle di dimensione diversa, come mostra il pilota in scatola
   (7.81 contro 15.60 h⁻¹Mpc). È l'argomento più forte a favore di questa practice, e viene da fuori
   il Paper 2;
4. **dichiarare il gauge** della decomposizione isotropo/anisotropo, perché il residuo varia di un
   fattore 4.3 con la scelta;
5. **dichiarare la convenzione di *F*_AP**, α_⊥/α_∥ oppure il suo reciproco, con la formula e non
   solo col nome.

---

## 5-bis. Una predizione dichiarata e smentita, da riportare

Prima del pilota in scatola era stata formulata l'aspettativa **«σ(realizzazione) domina, oltre
l'80% della varianza»**. Il pilota l'ha smentita di **due ordini di grandezza**
(σ_fiduciale/σ_nwLH ≈ 0.006 in scatola), e la decomposizione finale assegna alla realizzazione il
13.4%.

Va nel manoscritto, non solo nel record. Il Paper 1 ha già stabilito il precedente riportando
apertamente il fallimento dell'albero decisionale pre-registrato, e in quel caso la trasparenza ha
**aumentato** la credibilità del lavoro. La regola vale solo se le aspettative si dichiarano prima e
non si riscrivono dopo; una predizione smentita e pubblicata è la prova che la regola è stata
applicata davvero.

---

## 6. Struttura del manoscritto

1. Introduzione: la domanda della funzione di risposta; le due limitazioni aperte, (ix) e (ii).
2. **Teoria.** Prop. 2 e Prop. 2′; Lemma 3; il gauge di Chebyshev; posizionamento rispetto a
   M26 §4.1 e Paper 1 §2.3.
3. Il canale isotropo è una convenzione di griglia: misura del suo effetto via σ_px, e le due
   convenzioni messe a confronto sulla linea *F*_AP.
4. Il canale anisotropo: griglia (α_iso, *F*_AP), w̄ per punto, esclusioni dichiarate, il confondente
   di tiling e la sua neutralizzazione, il test di completezza della parametrizzazione a due
   parametri.
5. Risposta AP del deficit: decomposizione a quattro contributi, ranghi empirici.
6. **Risposta ai parametri cosmologici:** decomposizione della varianza, *w*₀ a *n* = 2000, *n*_s
   come parametro guida, il tetto di sensibilità.
7. Ensemble v2: voxelizzazione mock pesata FKP sui 2000; le predizioni a un punto.
8. La scala di erosione su v2 e la risoluzione della tensione §7.2/§8.1.
9. Budget sistematico aggiornato; le righe (ix) e (ii) di Tab. 8 chiuse.
10. Discussione: **la funzione di risposta di *N*_H1**, cosa resta non testato, e la lista di
    priorità per i Paper 3 e 4.

### Figure

- **(F1)** *f*(*r*) − α_iso·*r* in voxel per ogni geometria, banda ±0.1 voxel, con la soglia
  dell'artefatto di padding (0.013) come riferimento inferiore — **figura metodologica principale**.
- **(F2)** Deficit contro *F*_AP a α_iso fissato, con σ_Δ come banda — **figura del risultato**.
- **(F3)** σ_px e w̄ per geometria, con le soglie **per regione**; punti esclusi in grigio.
- **(F4)** Illustrazione della Prop. 2: stesso campo, due dilatazioni, diagrammi identici.
- **(F5)** PDF di δ e ν, mock v1 contro v2 contro DESI.
- **(F6)** Scala di erosione *k* = 0–3, v1 contro v2, due emisferi.
- **(F7)** **La funzione di risposta**: |∂*N*_H1/∂θ| normalizzato per θ ∈ {σ₈, Ω_m, *n*_s, *w*₀,
  α_iso, *F*_AP}, con le due barre a zero-per-teorema marcate diversamente dalle zero-per-misura —
  **la figura che riassume il paper**.
- **(F8)** Molteplicità di tiling e frazione indipendente per geometria, col gradino evidenziato.

---

## 7. Cancelli e regole di decisione

Nessun numero nuovo prima che i cancelli passino. Le regole si fissano prima e non si rinegoziano.

| | cancello | atteso |
|---|---|---|
| 2.1 | chiusura M26/Paper 1 | 28 256 / 15 122; 35 436.7 ± 313.0 e 18 713.0 ± 197.8 |
| 2.2a | dilatazione, padding additivo | \|Δ*N*_H1\| ≤ 5 generatori |
| 2.2b | dilatazione, padding riscalato | **esattamente 0** |
| 2.3 | σ_px | lo scarto rispetto a 2.2 **è** l'intero canale isotropo |
| 2.4 | monotonia di *f*(*r*) | **chiuso**: 12/12 |
| 2.5 | appaiamento dei semi | riproduzione galassia per galassia al fiduciale |

**Regola di decisione della Componente A:** misura di sensibilità se |∂*D*/∂*F*_AP| × escursione
> 3σ_Δ ≈ 750 generatori; altrimenti limite superiore, con la Prop. 2 come risultato principale.

**Regola di decisione della Componente D:** già valutabile e già puntata alla riformulazione. Resta
solo la correlazione a *n* = 2000 per chiudere formalmente il gate.

**Test di completezza della parametrizzazione:** se |*D*_obs − *D*_pred| < σ_Δ ≈ 250 su tutti e
quattro gli angoli, la famiglia a due parametri basta; se fallisce su C1 e C4 ma non su C2 e C3, il
terzo canale è reale e si riporta con la sua ampiezza; se fallisce ovunque, è tiling o
ri-randomizzazione e va chiuso prima di interpretare qualunque derivata.

---

## 8. Rischi

| rischio | probabilità | mitigazione |
|---|---|---|
| Esito nullo su A e D → paper percepito come sottile | **alta** | è esattamente ciò che la fusione risolve: il nucleo positivo è la funzione di risposta, non i due nulli |
| Convenzione σ_px sbagliata sulla linea B | **media** | (a) di §4: dichiarata e forzata prima dei run |
| Uno o più angoli falliscono w̄ | alta | esclusi a priori; se cadono C1 o C4 va **detto** che il terzo canale resta non misurato |
| Il gradino di tiling simula una risposta AP | media | misura per punto + randomizzazione delle repliche su tutti i punti |
| Ensemble v2 sposta il residuo beyond-two-point | bassa | verificato per primo; se si muove, avvisare il Paper 1 subito |
| Il Paper 1 cambia in revisione | media | non sottomettere prima che sia fuori dal secondo giro |
| La Componente D sembra un'aggiunta posticcia | **media** | la figura F7 è ciò che la rende integrale: senza D quella figura ha metà delle barre |

---

## 9. Risorse

Nessun dato nuovo. Componente A: 8 geometrie complete più 2 run di chiusura. Componente B: ~16 h per
l'ensemble v2. Componente C: riusa la cache di B. Componente D: **minuti** — è già quasi tutta
eseguita dentro M26 R1.

Settimane su workstation.

---

## 10. Target

**MNRAS.** Chiude la limitazione (ix), limita la (ii), corregge la pesatura dei mock per tutta la
serie, e consegna cinque convenzioni obbligatorie più la prima misura controllata del tetto di
sensibilità di una statistica topologica in un framework like-for-like.

Se l'esito è nullo su geometria e cosmologia, il paper è corto e va bene così — ma non è più un paper
di soli nulli: è la funzione di risposta di *N*_H1, con due teoremi che spiegano *perché* metà dei
canali sono chiusi per costruzione.
