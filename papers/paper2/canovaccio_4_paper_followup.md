# Canovaccio per quattro paper di approfondimento
## Programma di follow-up del deficit di generatori *H*₁ in DESI BGS (MN-26-2100-P)

> **Revisione 25 agosto 2026 (sera) — sostituisce `canovaccio_6_paper_followup.md`.**
>
> La revisione precedente pianificava sei paper ordinati per **fattibilità**. Questa ne pianifica
> quattro ordinati per **contributo**. Il motivo è un test applicato a ciascun paper:
>
> > *Se domani l'anomalia si dissolvesse del tutto, questo paper resterebbe pubblicabile?*
>
> Tre paper lo passano in pieno, due lo falliscono, uno lo passa a fatica. I due che lo falliscono
> non vengono cancellati: vengono **fusi** con quelli che lo passano, dove il loro contenuto diventa
> sezione di un argomento più grande invece che paper autonomo magro.
>
> **La numerazione 2, 3, 4 è conservata** per allineamento con l'albero `results/paperN/` già
> esistente. Nessuna cartella va rinominata.

---

## 1. Il test, e il suo esito

| paper della rev. precedente | contributo proprio | sopravvive alla dissoluzione? | destino |
|---|---|---|---|
| **2** (AP + pesatura) | Prop. 2, Lemma 3, gauge, degenerazione AP | sì, ma **sottile**: tre teoremi e un nullo | → nucleo del **nuovo Paper 2** |
| **3** (BOSS DR12) | replica su seconda survey | **debole**: con PATCHY l'esito è ambiguo comunque | → **ramo C del Paper 4** |
| **3-bis** (nuvola di punti, *H*₂) | filtrazione senza reticolo su survey reale | **sì, pienamente** | → **Paper 3**, intatto |
| **4** (altMTL, Uchuu) | effetto del forward model sulla PH | **sì, pienamente** | → **rami A e B del Paper 4** |
| **5** (CPL su Abacus) | tetto di sensibilità delle statistiche topologiche | **sì, pienamente** | → **Componente D del Paper 2** |

**Osservazione che vale la pena registrare.** Questo ordinamento è quasi l'**inverso** di quello di
fattibilità con cui la serie era stata pianificata. I paper più eseguibili con risorse da workstation
sono quelli con meno contenuto autonomo; quelli con contenuto autonomo pieno sono i più costosi. La
serie era ordinata per ciò che si poteva fare, non per ciò che valeva fare.

### La regola di fusione applicata

Non «quanti paper», ma: **stessa domanda e stesso pubblico → si fondono; pubblico diverso → si
separano.** Il secondo criterio è quello che salva il Paper 3: chi legge di fiber assignment non è
chi legge di filtrazioni su nuvole di punti, e un manoscritto unico non raggiungerebbe bene nessuno
dei due.

---

## 2. Stato del programma

| | stato | ID |
|---|---|---|
| **M26** (paper base) | R1 sottomessa 23 ago 2026 | MN-26-2100-P.R1 |
| **Paper 1** | sottomesso dopo revisione maggiore | MN-26-2388-P |
| **Paper 2** | Fase 0 chiusa, Fase 1 in corso; **riperimetrato in questa revisione** | — |
| **Paper 3** | canovaccio, non avviato | — |
| **Paper 4** | canovaccio, non avviato | — |

**Vincoli assunti:** nessuna affiliazione (solo dati pubblici, niente NERSC), workstation
multi-core, 32–128 GB RAM, qualche TB di disco, budget ~zero, pipeline CAUCHY congelata.

**Principio guida:** ogni paper riusa il protocollo congelato — cancelli pre-registrati, record
numerici congelati, ranghi empirici invece di *z* gaussiani — e cambia **una** cosa alla volta
rispetto al paper base.

**Catena di citazione:** M26 non cita il Paper 1 (è nato prima). Il Paper 1 cita M26; il Paper 2 cita
M26 e il Paper 1; e così via, solo all'indietro.

---

## 3. Le limitazioni di M26 R1, ricollocate

| | limitazione | stato | chiusa da |
|---|---|---|---|
| (i) | fiber assignment (surrogati) | aperta | **Paper 4**, ramo B |
| (ii) | *w*_a ≠ 0 | aperta | **Paper 2**, Componente D — *come limite, non come misura* |
| (iii) | survey singola | aperta | **Paper 4**, ramo C (BOSS) e ramo A (multi-tracciatore) |
| (iv) | error budget / varianza cosmica | parziale | **Paper 4**, sintesi |
| (v) | HOD su griglia grossolana | aperta | **Paper 4**, ramo B (SHAM + HOD-su-NFW) |
| (vi) | snapshot vs lightcone | bounded 0.2% | **Paper 4**, ramo B |
| (vii) | tiling | **chiusa da M26 R1** | — |
| (viii) | profili satellite / RSD | bounded −0.8% dal Paper 1 | **Paper 4**, ramo B |
| (ix) | cosmologia fiduciale / AP | aperta | **Paper 2**, Componente A |
| (x) | *H*₂ e topologia dei vuoti | nuova | **Paper 3** |
| (xi) | decomposizione in scala | in gran parte chiusa dal Paper 1 §5.2 | **Paper 3** la chiude |

**Ogni paper deve dichiarare esplicitamente quali limitazioni restano aperte dopo di sé.** Con
quattro manoscritti invece di sei il rischio che la lista si sfilacci è minore, ma non nullo.

---

## Paper 1 — *(consuntivo)* Contenuto a due punti del deficit
**Sottomesso: MN-26-2388-P.**
*"Three quarters of the DESI BGS H₁ deficit is reproduced by its power spectrum; one quarter is not"*

Risultati che vincolano tutto il resto:

- **Non è a un punto.** *N*_H1 è esattamente invariante sotto trasformazioni monotone; imporre la PDF
  DESI ai mock lo sposta di +0.29/+0.78%, **nel verso sbagliato**.
- **Il 76.3% è a due punti**, per randomizzazione simmetrica delle fasi ad ampiezze fisse, con
  controllo di idempotenza.
- **Il residuo beyond-two-point è 1710.5 generatori a 6.8σ** contro la dispersione mock-to-mock di
  Δ*N* (σ_Δ = 250.5).
- **Il criterio w̄ ≳ 0.99 è una condizione sui confronti differenziali**, non sui conteggi assoluti;
  residuo ±3.4%.
- **La griglia è imposta dal campionamento** (0.71 galassie per voxel a 128³): il deficit **non
  converge** raffinando (20.3% → 14.2% a 256³).

Le ultime due righe sono la ragione d'esistere del Paper 3.

---

## Paper 2 — A cosa risponde *N*_H1
**(fattibilità: alta — solo riprocessamento; chiude (ix) e limita (ii))**

*Titolo di lavoro:* **"What does the loop count respond to? Geometry, weighting and cosmology in
persistent homology of voxelized redshift surveys"**

Dettaglio operativo in `canovaccio_paper2.md` rev. 25 ago (sera) e `checklist_paper2.md`.

### Perché è un paper e non due nulli

Fondendo l'AP e il test CPL, i due esiti probabilmente nulli smettono di essere due paper magri e
diventano **le due metà negative di un enunciato positivo**: *N*_H1 risponde alla **forma** dello
spettro e non alla sua ampiezza, e i canali geometrici sono chiusi da un teorema. La struttura
diventa: ecco cosa la statistica **non** vede — la dilatazione isotropa per la Prop. 2, l'ampiezza
per la Prop. 1, *w*₀ per misura diretta — ed ecco cosa **vede**: *n*_s a *r* = +0.376.

Una statistica insensibile ai parametri di ΛCDM che segnala un deficit a rango 1/2001 sta rispondendo
a qualcosa che ΛCDM non parametrizza. Restringere quel «qualcosa» vale più di un vincolo debole su
*w*₀.

### Quattro componenti

- **A — geometria AP.** Prop. 2 emendata, Lemma 3, gauge di Chebyshev, griglia (α_iso, *F*_AP),
  confondente di tiling. Chiude (ix).
- **B — pesatura dei mock, ensemble v2.** Voxelizzazione FKP-pesata sui 2000; le predizioni a un
  punto mai misurate.
- **C — scala di erosione su v2.** Risolve la tensione §7.2 ↔ §8.1 del Paper 1.
- **D — risposta ai parametri cosmologici** *(ex Paper 5)*. Decomposizione della varianza già
  eseguita in M26 R1 §5.5 (σ_cos 261.5 / σ_HOD 128.3 / σ_realizz. 114.6 / σ_tot 313.0); correlazione
  parziale di *w*₀ a *n* = 2000 da chiudere; il tetto di sensibilità come risultato metodologico.

### Esito atteso

Nullo su A, piccolo su B, informativo su C e D. **Non è un fallimento:** il paper consegna tre
teoremi, tre convenzioni obbligatorie, un ensemble corretto e la prima misura controllata di cosa una
statistica topologica può e non può vedere in un confronto like-for-like.

**Target:** MNRAS.

---

## Paper 3 — Il deficit è una statistica di reticolo?
**(fattibilità: alta sul dato, incerta sul costo computazionale — chiude (x) e (xi))**

*"Is the H₁ deficit a lattice statistic? A point-cloud persistent-homology test of the DESI BGS
anomaly"*

### Perché è il paper più indipendente della serie

Due affermazioni pubbliche lasciano insieme una porta aperta. Il Paper 1 §8.3: il deficit frazionario
non converge raffinando la griglia, perché il survey campiona a separazione media 17.5 h⁻¹Mpc e la
cella 128³ è già alla scala di campionamento. M26 R1 §6.2: i generatori *H*₂ a 128³ sono artefatti
del reticolo cubico. Messe insieme: **il deficit potrebbe essere una proprietà del reticolo applicato
a un campo sotto-campionato, non del campo.**

È l'unica via di fuga «mondana» che nessun esperimento della serie può toccare, perché tutti vivono
su quella griglia. Una filtrazione senza reticolo — alpha complex, Vietoris–Rips, DTM — si adatta al
campionamento locale e non ha reticolo per costruzione.

### Metodo

1. **Pilota di costo prima di tutto.** Alpha complex su ~2 × 10⁵ punti con `gudhi`: tempo e memoria su
   una realizzazione. Se il costo per mock supera il budget, ripiegare su DTM o su un
   sotto-campionamento dichiarato — **non** ridurre il numero di mock sotto la soglia del rango
   empirico.
2. **Il bordo, che è il vero contenuto.** Il sentinel voxel di M26 non esiste su un alpha complex.
   Due convenzioni da confrontare: scarto dei simplessi che intersecano il complemento della
   maschera, oppure omologia relativa al bordo. La scelta si dichiara prima, l'altra si riporta come
   robustezza.
3. **Like-for-like sulla nuvola.** Selezione radiale, pesi e RSD reimplementati sui punti. I pesi FKP
   su una filtrazione geometrica non hanno l'interpretazione che hanno su un campo di densità: va
   deciso e dichiarato se entrano come pesi di misura (DTM pesata) o non entrano.
4. **Statistica primaria.** *N*_H1 sulla nuvola non è confrontabile in valore assoluto con *N*_H1 sul
   reticolo. Le sole quantità trasferibili sono il **deficit frazionario** e il **rango empirico**.
5. ***H*₂.** Sulla nuvola i generatori *H*₂ non sono artefatti di reticolo: prima misura possibile di
   topologia dei vuoti su questo campo.

### Predizione, da dichiarare prima

Se il deficit fosse puramente di reticolo, la filtrazione su nuvola dovrebbe darlo compatibile con
zero. Se fosse fisico, dovrebbe restare fra il 15% e il 25% con rango 1/(*N*+1). Soglia fissata prima
del run.

### Rischi

Medio-alti, ma di natura diversa dagli altri: il rischio non è l'esito nullo, è che il trattamento
del bordo su un complesso geometrico diventi esso stesso il paper. Il che sarebbe comunque un
contributo — nessuno ha risolto il bordo per la PH su nuvola di punti in una survey cut-sky, e M26
§6.2 lo dichiara come il problema che sopravvive al cambio di filtrazione.

**Target:** MNRAS. Nessun dato nuovo: stessi cataloghi, stessi mock già carvati.

---

## Paper 4 — Il deficit sopravvive a una costruzione realistica?
**(fattibilità: medio-bassa — volumi grandi, formati DESI; chiude (i), (iii), (iv), (v), (vi), (viii))**

*"Does the H₁ deficit survive a realistic forward model? Multi-tracer, fiber assignment and
independent-survey tests"*

È il paper in cui l'anomalia vive o muore. Tre rami, **in quest'ordine**, con un punto di decisione
dopo il primo.

### Ramo A — multi-tracciatore dentro DESI *(il discriminante più forte, e il più economico)*

I cataloghi LRG, ELG e QSO DR1 sono **già sul disco** accanto a BGS. Stessa survey, stessa pipeline
osservativa, stesso codice di analisi; mock e calibrazioni HOD **indipendenti**.

- Se il deficit compare in **tutti** i tracciatori con ampiezza simile → punta alla pipeline dati o a
  qualcosa di fisico.
- Se è **solo in BGS** → punta alla calibrazione dei mock BGS, cioè direttamente alla limitazione (v).

> **La concordanza NGC/SGC non discrimina questo.** 20.26% e 19.19% leggono come robustezza, ma sia
> un segnale fisico sia un disallineamento di pipeline sono comuni ai due emisferi. La consistenza
> fra cap esclude un errore *locale*, non un errore *comune*. Il multi-tracciatore è l'asse che
> manca.

**Complicazione tecnica da non sottovalutare, e da dichiarare nel manoscritto:** LRG, ELG e QSO hanno
densità numerica molto più bassa di BGS. L'occupazione di 0.71 galassie per voxel a 128³ non si
trasferisce, e la griglia va riderivata per tracciatore secondo il criterio del Paper 1. Il confronto
onesto è quindi *«compare un deficit?»* e non *«è lo stesso 20%?»*. Vale comunque: è un confronto fra
regimi di campionamento diversi, e va presentato come tale.

### Ramo B — il forward model ufficiale DESI

Sostituire i surrogati con i prodotti ufficiali: mock DR1 con fiber assignment reale (altMTL) e
veloce (FFA), con varianti *complete* per il nullo; lightcone SHAM Uchuu-BGS, che riproducono
l'evoluzione in *z* del clustering BGS-BRIGHT entro il 5%.

La differenza altMTL − complete **è** l'effetto fibra reale sulla topologia, da confrontare col segno
«sbagliato» trovato dai due surrogati di M26. Aggiungere un ramo esplicito **HOD-su-NFW**, che è più
economico dello SHAM e risponde alla stessa domanda — il Paper 1 lo indica come *"the one small-scale
channel whose amplitude the present experiments do not bound"*.

Attenzione al numero limitato di realizzazioni: il risultato è lo spostamento della **media** mock,
non un nuovo *p*-value fine.

### Ramo C — BOSS DR12, come robustezza e non come tesi

I random CMASS North e South sono già scaricati. Il ramo esiste per chiudere (iii) su una survey con
strumento, targeting e imaging completamente indipendenti — ma **il suo peso probatorio è limitato**
e va dichiarato: i mock MultiDark-PATCHY non sono N-body completi e sbagliano notoriamente le piccole
scale, quindi un deficit su BOSS sarebbe ambiguo quasi quanto quello su BGS. Da qui la retrocessione
da paper autonomo a sezione.

### Punto di decisione, dopo il ramo A

- **Se A dissolve l'anomalia** (deficit assente o molto ridotto negli altri tracciatori), i rami B e C
  si riducono a conferme e il paper si scrive prima, con la conclusione già in mano.
- **Se A la conferma su tre tracciatori**, B e C diventano il corpo del paper e l'anomalia entra nel
  territorio in cui vale la pena cercare un collaboratore affiliato.

**Target:** MNRAS o JCAP.

---

## 4. Cosa è stato ritirato, e perché

Va scritto qui perché non si perda, e perché ogni ritiro va dichiarato nel manoscritto che lo eredita.

| ritirato | motivo |
|---|---|
| **Paper 3 (BOSS) come paper autonomo** | il denominatore PATCHY rende l'esito ambiguo; come sezione del Paper 4 costa poco e dice quanto può dire |
| **Paper 5 come test CPL** | la regola di decisione pre-dichiarata punta già alla riformulazione: *r*(β₁, *w*₀) = −0.015 con *p* = 0.84, risposta binned piatta, e la griglia non ha la potenza (Δ*N* > 344 fra punti adiacenti contro un'escursione totale < 162) |
| **Paper 3-bis come numerazione** | diventa Paper 3; nessun contenuto rimosso |
| **«sei paper»** | due dei sei non passavano il test di sopravvivenza |

---

## 5. Ordine di esecuzione e dipendenze

```
Paper 2  ──────────────────────────────►  settimane
   │  (produce l'ensemble v2, che serve a tutto il resto)
   │
   ├──►  Paper 3   ────────────────────►  mesi, costo computazionale da sondare
   │        (nessun dato nuovo)
   │
   └──►  Paper 4   ────────────────────►  mesi, download pesanti
            ramo A ──► punto di decisione ──► rami B, C
```

**Perché il Paper 2 va per primo, anche se non è il più interessante.** La Componente B produce
l'**ensemble v2**, cioè i mock voxelizzati con la stessa pesatura dei dati. Concettualmente quella
correzione apparterrebbe al Paper 4, ma il Paper 4 ne ha bisogno **già corretto**. Un ensemble
sbagliato propagato a tre paper è il difetto più costoso che questa serie possa commettere.

**Perché il Paper 3 va prima del 4.** Il Paper 3 verifica se l'anomalia esiste sullo stesso cielo con
una pipeline diversa; il Paper 4 se esiste in altri cieli con la stessa pipeline. Sono i due assi
ortogonali della replicazione, ma il 3 non richiede download e il 4 sì. Se i download del ramo B si
rivelano proibitivi, il 3 è già fatto.

---

## 6. Pronostici, dichiarati adesso

Registrati qui perché la regola del progetto vale anche per le aspettative: si dichiarano prima e non
si riscrivono dopo.

**Sull'anomalia complessivamente:**

| esito | probabilità dichiarata |
|---|---|
| si dissolve in larga parte (>50% attribuito a costruzione) | ~60% |
| sopravvive come residuo robusto sopra 5σ con budget onesto | ~15% |
| resta indeterminata: ridotta ma non risolta | ~25% |

Il motivo del 60% è l'ampiezza: 7180 generatori, due ordini di grandezza sopra ogni sistematico
finora caratterizzato (FKP −1.1%, NFW −0.8%, maschera ~1.1 pp). Discrepanze di quella taglia, in
cosmologia, quasi sempre vivono nella catena di costruzione.

**Per paper:**

| | pronostico | fiducia |
|---|---|---|
| Paper 2 | nullo su A, la Prop. 2 regge, il tetto di sensibilità è il risultato citabile | ~85% |
| Paper 3 | varianza massima: o il risultato più interessante della serie, o dissolve tutto | 50/50 |
| Paper 4 | lo spostamento singolo più grande, 20–50% del deficit dal ramo B | media |

---

## 7. Cosa resterà aperto comunque

Anche nello scenario migliore, quattro cose sopravvivono a tutti e quattro i paper:

1. **A cosa risponde *N*_H1 in positivo.** Il Paper 2 misura che risponde alla forma dello spettro
   (*n*_s a +0.376) e non all'ampiezza. *Perché* lo faccia resta senza teoria.
2. **Una seconda suite con HOD indipendente end-to-end.** Uchuu/SHAM aiuta, ma resta un confronto
   Quijote-calibrato ↔ altro-misurato.
3. **La covarianza fra canali sistematici.** Ogni paper limita un canale; nessuno produce la matrice
   di covarianza fra i limiti. È il contenuto naturale di un eventuale paper di sintesi.
4. **La rappresentazione.** Reticolo, nuvola, e i regimi di campionamento intermedi: il Paper 3 apre
   la domanda più di quanto la chiuda.

---

## 8. Un quinto paper, eventuale, e di che tipo

**Non una review.** Una rassegna della propria serie, autore singolo senza affiliazione, con
bibliografia dominata da autocitazioni, si legge come promozionale; e MNRAS non pubblica review non
invitate.

Due forme legittime, in ordine di valore:

**(a) Il paper metodologico.** Prop. 1, Prop. 2, Lemma 3, il criterio w̄ ≥ 0.99, la convenzione di
σ_px, il gauge della decomposizione, il trattamento del tiling, il bordo su nuvola di punti. Serve a
chiunque applichi omologia persistente a una survey mascherata, **non dipende da come finisce
l'anomalia**, e si cita da solo. Venue: **RASTI** o **Open Journal of Astrophysics**. Da valutare
dopo il Paper 3, quando anche il pezzo sul bordo esiste.

**(b) Il paper di sintesi come risultato nuovo.** Non «ecco cosa ho fatto» ma l'analisi congiunta:
budget sistematico completo **con la covarianza fra canali** e il verdetto numerico finale. È prassi
standard nelle serie. Ha senso solo se l'anomalia sopravvive al Paper 4 — cioè nel ramo al ~15%.

**(c) La pre-registrazione prima di DR2**, già in programma, che non è un paper ma va depositata.

---

## 9. Il rischio che non è scientifico

Il prior della comunità su un'anomalia di questo tipo è «sistematico», e non lo si sposta con la
solidità interna. Lo si sposta con tre cose, in ordine di efficacia:

1. una replica su un tracciatore o una survey indipendente — **ramo A del Paper 4**;
2. codice e dati pubblici che un altro possa rilanciare — già in programma, Zenodo;
3. un collaboratore affiliato che metta il proprio nome accanto al tuo — da cercare **dopo** che il
   Paper 3 sia su arXiv, avvicinando chi lavora su statistiche beyond-two-point e TDA in cosmologia,
   non «DESI» genericamente.

Le prime due sono interamente sotto controllo. Quattro paper con contributi netti reggono quel prior;
sette, di cui due magri, no.

---

## 10. Tracciabilità

Sostituisce `canovaccio_6_paper_followup.md` (25 ago, mattina), che sostituiva
`canovaccio_5_paper_followup.md`. Documenti figli da aggiornare di conseguenza:

- `canovaccio_paper2.md` → riscritto in questa stessa revisione
- `checklist_paper2.md` → va esteso con la Componente D (ex Paper 5); le Fasi 0–3 restano valide
- `canovaccio_paper5.md` → **archiviare**, il contenuto vive nella Componente D del Paper 2
- `paper2_stato.md`, `paper2_sottoprodotti.md` → invariati
