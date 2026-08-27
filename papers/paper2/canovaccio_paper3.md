# Paper 3 — canovaccio, rev. 25 agosto 2026
## Il deficit è una statistica di reticolo?

> **Origine.** Eredita per intero la sezione «Paper 3-bis» di `canovaccio_6_paper_followup.md`
> (25 ago, mattina), promossa a Paper 3 nella ristrutturazione a quattro paper. Nessun contenuto
> rimosso. La numerazione cambia; le cartelle `results/paper3/` sono nuove e non collidono con nulla.

**Titolo di lavoro:** *"Is the H₁ deficit a lattice statistic? A point-cloud persistent-homology test
of the DESI BGS anomaly"*

**Cita:** M26, Paper 1, Paper 2.

---

## 1. Perché questo paper esiste

Due affermazioni, entrambe già pubbliche, lasciano insieme una porta aperta.

- **Paper 1 §8.3.** Il deficit frazionario **non converge** raffinando la griglia: 20.3% a 128³,
  14.2% a 256³. Il survey campiona a separazione media 17.5 h⁻¹Mpc e la cella 128³ è già alla scala
  di campionamento. Conclusione adottata: *"the statistic is defined on the grid."*
- **M26 R1 §6.2.** I generatori *H*₂ a 128³ sono artefatti del reticolo cubico, e raffinare non li
  recupera, perché la risorsa limitante è il campionamento del tracciante e non la discretizzazione.

Messe insieme: **il deficit potrebbe essere una proprietà del reticolo cubico applicato a un campo
sotto-campionato, non del campo.**

È l'unica via di fuga «mondana» che nessun esperimento della serie può toccare, perché tutti gli
esperimenti vivono su quella griglia. Una filtrazione **senza reticolo** — alpha complex,
Vietoris–Rips, o distance-to-measure sulla nuvola di punti — si adatta al campionamento locale e non
ha reticolo per costruzione.

- Se il deficit **sopravvive**, la via si chiude in modo definitivo e l'anomalia diventa
  sostanzialmente indipendente dalla rappresentazione.
- Se **sparisce**, l'anomalia è spiegata — ed è un risultato pubblicabile esattamente nella linea del
  paper base.

M26 R1 fornisce il vincolo metodologico gratis: *i requisiti like-for-like sono proprietà del
confronto, non della filtrazione, e solo la loro implementazione cambierebbe.*

---

## 2. Perché è il paper più indipendente della serie

Passa il test di sopravvivenza in pieno: **anche se l'anomalia si dissolvesse domani**, resterebbe
il primo trattamento del bordo per omologia persistente su nuvola di punti in una survey cut-sky, più
la prima misura di *H*₂ su questo campo. Il pubblico è diverso da quello degli altri tre paper — è la
comunità TDA prima ancora di quella cosmologica — e questo è il motivo per cui non va fuso con
nessuno.

---

## 3. Fase 0 — prerequisiti

- [ ] **0.1 — Ensemble v2.** I mock devono essere quelli corretti dal Paper 2, non v1. Se il
      Paper 3 partisse su v1 erediterebbe una pesatura che il Paper 2 ha già dichiarato sbagliata.
- [ ] **0.2 — Pilota di costo, prima di qualunque altra cosa.** Alpha complex su ~2 × 10⁵ punti con
      `gudhi`: tempo di parete e memoria di picco su **una** realizzazione. È il cancello che decide
      se il paper è fattibile.
- [ ] **0.3 — Statistica primaria dichiarata.** *N*_H1 sulla nuvola **non** è confrontabile in valore
      assoluto con *N*_H1 sul reticolo. Le sole quantità trasferibili fra filtrazioni sono il
      **deficit frazionario** e il **rango empirico**. Dichiararlo prima toglie ogni tentazione
      successiva.
- [ ] **0.4 — Pre-registrazione** su Zenodo/OSF con la predizione di §6 e la convenzione di bordo di
      §5 già scelte.

**Se 0.2 fallisce**, ripiegare su DTM o su un sotto-campionamento **dichiarato** — mai ridurre il
numero di mock sotto la soglia che serve per un rango empirico. Un rango 1/2001 vale più di una
filtrazione elegante su 50 realizzazioni.

---

## 4. Fase 1 — la scelta della filtrazione

Tre candidate, in ordine di preferenza dichiarata:

| filtrazione | pro | contro |
|---|---|---|
| **alpha complex** | esatta, dimensione controllata, `gudhi` maturo | costo in 3D su 2 × 10⁵ punti da misurare |
| **DTM** (distance-to-measure) | robusta al rumore di Poisson, pesabile | introduce un parametro *m* da dichiarare |
| **Vietoris–Rips** | semplice | esplode in memoria in 3D, ultima scelta |

La scelta primaria si dichiara **prima** del run; le altre entrano come robustezza, non come
alternative a posteriori.

**Nota sul parametro di DTM.** Se si usa DTM, *m* è una scala di lisciatura implicita e va appaiata
fra dati e mock esattamente come σ_px. Vale la stessa practice del Paper 2: dichiarare se
l'appaiamento è in unità fisiche o in unità di densità locale.

---

## 5. Fase 2 — il bordo, che è il vero contenuto del paper

Il sentinel voxel di M26 non esiste su un alpha complex. Servono, e vanno confrontate, almeno due
convenzioni:

- **(a) Scarto dei simplessi** che intersecano il complemento della maschera.
- **(b) Omologia relativa al bordo**, ℋ(*X*, ∂*X*).

La scelta primaria si dichiara prima; l'altra si riporta come robustezza. **Nessuno ha risolto il
bordo per la PH su nuvola di punti in una survey cut-sky**, e M26 §6.2 lo dichiara esplicitamente
come il problema che sopravvive al cambio di filtrazione.

**Il rischio, ed è il rischio caratteristico di questo paper:** che il trattamento del bordo si
riveli difficile abbastanza da diventare **esso stesso** il paper. Il che sarebbe comunque un
contributo, e va accettato in anticipo invece che subito come deviazione.

**Analogo del criterio w̄.** Il Paper 1 ha stabilito che l'omologia persistente su maschera è
affidabile solo dove il peso del kernel in-maschera supera 0.99. Su nuvola di punti il criterio non
si trasferisce alla lettera, ma la **domanda** sì: qual è la frazione di generatori la cui vita
dipende da simplessi che toccano il bordo? Va misurata e usata come criterio di ammissibilità,
altrimenti si ripete a un livello diverso l'errore che aveva prodotto le scale ritirate del Paper 1.

---

## 6. Fase 3 — like-for-like sulla nuvola

Tutto ciò che nel reticolo era ovvio va reimplementato:

- [ ] **3.1** Selezione radiale *n*(*z*), pesi e RSD applicati ai **punti**, non al campo.
- [ ] **3.2** **I pesi FKP su una filtrazione geometrica non hanno l'interpretazione che hanno su un
      campo di densità.** Va deciso e dichiarato se entrano come pesi di misura (DTM pesata) o non
      entrano affatto. Non c'è una risposta ovvia, ed è un punto che un referee troverà.
- [ ] **3.3** Stesso carving, stessi semi, stessa tassellazione dei mock del Paper 2, così che la
      differenza fra i due paper sia **solo** la filtrazione.
- [ ] **3.4** Rango empirico di DESI nell'ensemble: la statistica primaria.
- [ ] **3.5** ***H*₂.** Sulla nuvola i generatori *H*₂ non sono artefatti di reticolo. È la prima
      misura possibile di topologia dei vuoti su questo campo, e chiude la limitazione (x).

### La predizione, dichiarata prima del run

Il Paper 1 misura che il deficit **cala** raffinando (20.3% → 14.2%) mentre la dispersione relativa
raddoppia.

- Se il deficit fosse **puramente di reticolo**, la filtrazione su nuvola dovrebbe darlo compatibile
  con zero.
- Se fosse **fisico**, dovrebbe restare fra il **15% e il 25%** con rango 1/(*N*+1).
- **Zona grigia dichiarata:** un deficit fra il 5% e il 15% non decide, e va riportato come tale
  invece di essere spinto da una parte. In quel caso la conclusione è che la rappresentazione
  contribuisce ma non esaurisce, con l'ampiezza del contributo come risultato.

Soglie fissate qui, non rinegoziabili a run in corso.

---

## 7. Struttura del manoscritto

1. Introduzione: le due affermazioni di M26 R1 §6.2 e Paper 1 §8.3, e la porta che lasciano aperta.
2. Filtrazioni senza reticolo: alpha complex, DTM, e perché si adattano al campionamento locale.
3. **Il bordo:** le due convenzioni, la scelta dichiarata, il criterio di ammissibilità.
4. Like-for-like sulla nuvola: cosa si trasferisce e cosa va reimplementato; il problema dei pesi FKP.
5. Risultato: deficit frazionario e rango empirico, contro la predizione pre-registrata.
6. *H*₂ e topologia dei vuoti: prima misura, chiusura della limitazione (x).
7. Discussione: reticolo, nuvola, e i regimi di campionamento intermedi.

### Figure

- **(F1)** Lo stesso campo nelle due rappresentazioni, con i generatori sovrapposti — **la figura
  che spiega il paper in un colpo d'occhio**.
- **(F2)** Deficit frazionario contro filtrazione (reticolo 128³, reticolo 256³, alpha, DTM), con la
  banda della predizione pre-registrata.
- **(F3)** Le due convenzioni di bordo a confronto, con la frazione di generatori sensibili al bordo.
- **(F4)** Diagramma di persistenza *H*₂ su nuvola, DESI contro banda dei mock — prima misura.
- **(F5)** Costo computazionale contro numero di punti, per la riproducibilità del pilota.

---

## 8. Rischi

| rischio | probabilità | mitigazione |
|---|---|---|
| Il costo computazionale rende infattibile l'ensemble completo | **alta** | 0.2 lo misura prima; ripiego su DTM o sotto-campionamento dichiarato |
| Il bordo diventa il paper | media | accettato in anticipo: è comunque un contributo |
| I pesi FKP non hanno una collocazione difendibile | media | dichiarare entrambe le scelte e riportare la differenza |
| Esito in zona grigia | media | dichiarata come esito ammissibile in §6, non come fallimento |
| L'ensemble v2 non è pronto | bassa | dipendenza esplicita in 0.1 |

---

## 9. Risorse

**Nessun dato nuovo.** Stessi cataloghi DESI, stessi mock già carvati, stesso ensemble v2 del
Paper 2. Il costo è interamente computazionale e va sondato prima. `gudhi` ha già alpha complex,
Rips e DTM.

Mesi, con il grosso del rischio concentrato nel pilota di costo delle prime ore.

---

## 10. Target

**MNRAS.** Chiude le limitazioni (x) e (xi), e la via di fuga più seria rimasta.

**Nota di trasparenza da riportare nel Paper 2.** L'ordine dei *next steps* è già pubblico in M26 §7
e nel Paper 1 §9.4. La promozione di questo paper — da «3-bis» a terzo della serie, davanti ai test
sui sistematici DESI — va dichiarata nel Paper 2 come riformulazione motivata dai risultati di
risoluzione del Paper 1, non introdotta silenziosamente.
