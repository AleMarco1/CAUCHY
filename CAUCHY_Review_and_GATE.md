Ecco le sezioni da inserire come patch.

---

## Struttura Generale del Protocollo di Review

Ogni fase, prima della valutazione del gate, attraversa un ciclo di review condotto da un secondo Claude istanziato in un progetto separato con un system prompt che lo istruisce a comportarsi come un referee scientifico esigente. Il review non è opzionale e non può essere saltato: il gate non si chiude senza il parere del reviewer.

### Il Prompt di Review

Per ogni fase, il PI costruisce un prompt strutturato da sottomettere al reviewer. Il prompt segue sempre questo schema:

```
CAUCHY PROJECT — PHASE [N] REVIEW REQUEST

CONTESTO DEL PROGETTO:
[Breve descrizione dell'obiettivo scientifico di CAUCHY e della posizione
di questa fase nella pipeline. Massimo un paragrafo.]

INPUT DI QUESTA FASE:
[Lista dei file e artefatti in ingresso, con riferimento ai gate superati
nelle fasi precedenti. Include i valori numerici rilevanti prodotti dai
gate precedenti.]

METODI APPLICATI:
[Descrizione dei metodi scientifici usati in questa fase, con riferimento
alle scelte metodologiche del Methodology §X.X. Deve includere le scelte
non ovvie e la loro giustificazione.]

OUTPUT PRODOTTI:
[Lista dei file di risultato con i valori numerici chiave. Deve essere
possibile per il reviewer valutare i risultati senza accedere ai file
direttamente.]

GATE CRITERIA APPLICATI:
[Riproduzione verbatim dei criteri del gate da CAUCHY_Execution_Parameters,
con i valori osservati per ogni criterio.]

CONSIDERAZIONI SPECIFICHE:
[Eventuali anomalie osservate, deviazioni dal protocollo, valori
inattesi, ricalibrzioni applicate (con il loro audit trail), o aspetti
su cui si richiede particolare attenzione del reviewer.]

RICHIESTA:
Il reviewer è invitato a valutare se i risultati di questa fase sono
scientificamente solidi e se il progetto può procedere alla fase
successiva. Si chiede di identificare eventuali problemi metodologici,
deviazioni dalla letteratura, o vulnerabilità non affrontate.
```

### Esiti Possibili del Review

Il reviewer restituisce uno dei tre esiti:

**PROCEED:** il reviewer non ha obiezioni bloccanti. La fase è chiusa, il gate si chiude, la fase successiva può iniziare.

**REVISE — NON-BLOCKING:** il reviewer identifica problemi metodologici o lacune che non invalidano il risultato corrente ma devono essere affrontati prima della sottomissione del paper. Per ogni revisione non-bloccante, il PI deve scegliere una delle tre opzioni e documentarla nel CHANGELOG:
- *Risolto:* la revisione è stata implementata, con descrizione della soluzione.
- *Giustificato:* la revisione non è stata implementata, con motivazione scientifica esplicita di perché il problema non compromette la validità del risultato.
- *Rimandato con motivazione:* la revisione sarà affrontata in una fase successiva specifica, con motivazione del perché è appropriato rimandare.

Le revisioni non-bloccanti non impediscono la chiusura del gate, ma devono essere tutte assegnate a una delle tre opzioni prima che la fase successiva inizi. Non è consentito ignorarle.

**REVISE — BLOCKING:** il reviewer identifica un problema che invalida il risultato o impedisce la corretta interpretazione scientifica. Il gate non si chiude. Il PI deve affrontare il problema, rieseguire l'analisi se necessario, e sottomettere un nuovo ciclo di review. Ogni revisione bloccante consuma uno dei N_max = 2 cicli di ricalibrzione disponibili per quel gate (§2.4). Alla terza revisione bloccante, il gate chiude in Scenario C.

---

## Review e Gate Rivisti per Ogni Fase

---

### Review e Gate — Fase 0

**Review di Fase 0**

Al completamento dei controlli di integrità e della pipeline di preprocessing, il PI sottomette al reviewer il seguente contenuto:

*Input dichiarati:* i path locali dei tre dataset (fiduciali, LHC, nwLH) con numero di campi effettivamente verificati e statistiche aggregate (media, deviazione standard, min, max del contrasto di densità per dataset).

*Metodi applicati:* i controlli di integrità eseguiti (dimensioni, NaN/Inf, copertura parametrica, normalizzazione CIC), la pipeline di preprocessing applicata (scala di smoothing, normalizzazione), e il metodo di generazione del data manifest con checksum.

*Output prodotti:* `phase0_data_manifest.json` con numero di campi per dataset e tasso di superamento dei controlli; `phase0_preprocessing_lock.json` con la specifica completa della pipeline.

*Considerazioni specifiche:* qualsiasi campo rigettato dai controlli con la motivazione del rigetto; qualsiasi deviazione dalla pipeline standard applicata a specifici campi.

*Domande specifiche al reviewer:* la scala di smoothing scelta è coerente con la letteratura di riferimento (Yip 2024, Prat 2025) per l'omologia persistente su campi di questa risoluzione e volume? La normalizzazione per-cosmologia (non per-campo) è l'approccio corretto per preservare il segnale di ampiezza necessario per β₁?

**GATE 0 — Rivisto:**

Criteri tecnici:
- Tutti i campi passano i controlli di integrità (o i campi rigettati sono documentati e il loro numero non supera la soglia specificata in CAUCHY_Execution_Parameters).
- La pipeline è applicata uniformemente e version-locked.
- Il data manifest è generato con checksum per tutti i campi.

Criterio di review:
- Il reviewer ha restituito esito PROCEED, oppure REVISE NON-BLOCKING con tutte le revisioni assegnate.

Il gate non si chiude con un esito REVISE BLOCKING aperto.

---

### Review e Gate — Fase 1

**Review di Fase 1**

Al completamento dell'analisi Fisher su LHC e nwLH, il PI sottomette al reviewer:

*Input dichiarati:* i risultati del Gate 0 (pipeline version-locked), i parametri di calcolo TDA (N_thresh, range di filtrazione, implementazione gudhi usata), il numero di campi processati per dataset.

*Metodi applicati:* la scelta della filtrazione di supralivello con motivazione fisica; la scelta delle N feature estratte dalle curve di Betti con la loro motivazione fisica; la procedura di stima della matrice di covarianza del rumore (numero di fiduciali usati, regolarizzazione applicata); la procedura di stima delle derivate (metodo di regressione locale, range di linearizzazione); il fattore di correzione di Hartlap applicato.

*Output prodotti:* la matrice di Fisher completa su (Ωm, σ₈) con i vincoli marginalizzati σ(Ωm) e σ(σ₈); la correlazione ρ(Ωm, σ₈) confrontata con il valore P(k) di riferimento; le correlazioni |r(feature_k, w₀)| per le feature più sensibili sul dataset nwLH; le curve di Betti medie per il dataset fiduciale come sanity check visivo.

*Considerazioni specifiche:* se σ(Ωm) si discosta significativamente dalla previsione di Yip 2024 scalata per volume, documentare la diagnosi (differenza aloni/galassie, spazio reale/redshift, range di persistenza). Se il tasso di convergenza della matrice Fisher è insoddisfacente (meno di 2 direzioni ben convergenti con 2.000 realizzazioni, come osservato da Ouellette & Holder 2025), documentarlo.

*Domande specifiche al reviewer:* le feature estratte sono fisicamente motivate e coerenti con la letteratura? La scelta del range di filtrazione cattura le scale cosmologicamente rilevanti? La correlazione |r(b1_peak_position, w₀)| è al livello atteso dalla fisica del phantom crossing? Le derivate numeriche mostrano segni di non-linearità che richiederebbero un approccio non-lineare per l'analisi Fisher?

**GATE 1 — Rivisto:**

Criteri tecnici (Gate 1a — dataset LHC):
- Matrice di Fisher su (Ωm, σ₈) calcolata e documentata con vincoli marginalizzati.
- Correlazione ρ(Ωm, σ₈) calcolata e confrontata con P(k).
- Valori numerici registrati in `results/phase1_tda_baseline.json`.
- I threshold numerici specifici sono in CAUCHY_Execution_Parameters.

Criteri tecnici (Gate 1b — dataset nwLH):
- Correlazioni |r(feature_k, w₀)| calcolate per tutte le feature di Fase 1.
- Le feature più sensibili a w₀ identificate e documentate.
- Valori numerici registrati nello stesso file.

Criterio di review:
- Il reviewer ha restituito esito PROCEED, oppure REVISE NON-BLOCKING con tutte le revisioni assegnate.

Il Gate 1 è superato solo quando entrambe le condizioni 1a e 1b sono soddisfatte e il criterio di review è soddisfatto. Il gate non si chiude con un esito REVISE BLOCKING aperto.

---

### Review e Gate — Fase 2

**Review di Fase 2**

Al completamento del training della CNN e della costruzione di τ(x), il PI sottomette al reviewer:

*Input dichiarati:* i risultati del Gate 1 (feature TDA di Fase 1 usate come target di supervisione, con i loro valori medi e varianze); la specifica dell'architettura CNN (numero di layer equivarianti, dimensione dello spazio latente D_latent, k del k-NN graph, numero di parametri totali); i parametri di training (learning rate, batch size, numero di epoche, scheduler, seed).

*Metodi applicati:* la funzione di loss di supervisione topologica con la sua motivazione (perché non supervisionare direttamente sui parametri cosmologici); la procedura di calcolo di μ_ΛCDM sui 2.000 fiduciali; la definizione operativa di τ(x); il test T1 di fattorizzazione parametrica con la definizione dei quadranti e il calcolo della distanza di Wasserstein.

*Output prodotti:* la loss di training e validazione in funzione delle epoche; il valore di R su cui si basa il Gate 2 (rapporto W₂ same-σ₈/W₂ same-Ωm); le mappe di τ(x) per un campione rappresentativo di campi (sanity check visivo — τ deve mostrare struttura correlata con le deviazioni locali dal campo medio, non rumore uniforme); la correlazione tra |τ(x)| e l'hessiano locale di δ(x) (verifica che τ cattura struttura non-lineare e non solo ampiezza).

*Considerazioni specifiche:* se il training non converge o mostra instabilità, documentare le ipotesi diagnostiche; se il valore di R è vicino al threshold, documentare la sensibilità alle scelte architetturali.

*Domande specifiche al reviewer:* la supervisione sulle Betti features è sufficiente a forzare la CNN verso rappresentazioni topologicamente significative, o ci sono modalità di collasso verso soluzioni degeneri? La definizione di τ(x) come differenza dalla media fiduciale è la scelta più difendibile scientificamente, o si dovrebbe usare una distanza diversa nello spazio latente (es. Mahalanobis)? L'architettura SE(3)-equivariante è la scelta giusta per campi su griglia cubica, dove le simmetrie del reticolo differiscono dal gruppo continuo SE(3)?

**GATE 2 — Rivisto:**

Criteri tecnici:
- Test T1 superato: R > threshold specificato in CAUCHY_Execution_Parameters.
- τ(x) costruito per tutti i campi LHC e nwLH con la procedura version-locked.
- Checkpoint del modello salvato e checksum registrato.
- Valori numerici in `results/phase2_cnn_diagnostic.json`.

Criterio di review:
- Il reviewer ha restituito esito PROCEED, oppure REVISE NON-BLOCKING con tutte le revisioni assegnate.

Se il Gate 2 fallisce per il test T1 (R < threshold dopo N_max ricalibrzioni): il Ramo B non viene attivato. Il PI documenta il fallimento come contributo metodologico, il paper procede con solo Ramo A.

Il gate non si chiude con un esito REVISE BLOCKING aperto.

---

### Review e Gate — Fase 3

**Review di Fase 3**

Al completamento del training del GNN su TDA(τ(x)), il PI sottomette al reviewer:

*Input dichiarati:* i risultati del Gate 2 (τ(x) costruito per tutti i campi); la specifica della filtrazione di τ(x) (proiezione scalare usata, range di filtrazione, threshold di persistenza minima per la selezione dei nodi); la specifica del grafo (k per k-NN in spazio (birth, death), feature dei nodi); la specifica del GNN (architettura, loss, iperparametri di training).

*Metodi applicati:* la motivazione della filtrazione di supralivello su |τ(x)| (o sulla proiezione scelta); la procedura di costruzione del grafo topologico con i diagrammi β₁(τ) e β₂(τ); la procedura di identificazione delle componenti GNN più informative; il calcolo delle correlazioni parziali su LHC e nwLH.

*Output prodotti:* le correlazioni |r(GNN_j*, Ωm)| e |r(GNN_j*, σ₈)| sul test set; la varianza spiegata aggiuntiva rispetto alla baseline TDA del Gate 1 (il miglioramento deve essere documentato quantitativamente); la correlazione |r(GNN_j*, w₀)| sul dataset nwLH come indicatore per la Fase 5.

*Considerazioni specifiche:* il numero di nodi per grafo (se troppo basso per campi ΛCDM, τ ≈ 0 e il grafo degenera — questo deve essere verificato); la distribuzione delle persistenze nei diagrammi β₁(τ) e β₂(τ) vs i diagrammi analoghi su δ(x) (sanity check che τ abbia struttura topologica non banale).

*Domande specifiche al reviewer:* la costruzione del grafo in spazio (birth, death) cattura le relazioni strutturali rilevanti tra le feature topologiche di τ(x)? Il miglioramento sulla baseline TDA è statisticamente robusto o compatibile con fluttuazioni di campionamento? La correlazione |r(GNN_j*, w₀)| sul nwLH è al livello atteso per motivare il phantom crossing test?

**GATE 3 — Rivisto:**

Criteri tecnici:
- |r(GNN_j*, Ωm)| e |r(GNN_j*, σ₈)| sul test set superano i threshold in CAUCHY_Execution_Parameters.
- Il miglioramento sulla baseline TDA (Gate 1) è documentato quantitativamente.
- Valori numerici in `results/phase3_gnn_correlations.json`.

Criterio di review:
- Il reviewer ha restituito esito PROCEED, oppure REVISE NON-BLOCKING con tutte le revisioni assegnate.

Il gate non si chiude con un esito REVISE BLOCKING aperto.

---

### Review e Gate — Fase 4

**Review di Fase 4**

Al completamento dei 20 run di symbolic regression, il PI sottomette al reviewer:

*Input dichiarati:* le feature topologiche usate come variabili di input (da Fase 1 e componenti GNN da Fase 3); il target (w₀ o combinazione di parametri); la configurazione PySR (operatori binari e unari permessi, parsimony coefficient, maxsize, numero di iterazioni); i 20 seed usati.

*Metodi applicati:* la procedura di selezione del modello (AIC/BIC, non MSE puro); la procedura di valutazione sul test set held-out; la costruzione dell'istogramma di frequenza delle espressioni tra i 20 run.

*Output prodotti:* l'istogramma di frequenza delle espressioni; l'espressione più frequente con la sua forma algebrica, R² sul test set e frequenza; l'interpretazione fisica proposta dell'espressione (se stabile); i valori di R² per tutte le 20 run.

*Considerazioni specifiche:* se nessuna espressione raggiunge il threshold di stabilità del 50%, documentare la distribuzione delle espressioni e l'ipotesi diagnostica (segnale non abbastanza forte, relazione non algebricamente semplice, feature input non ottimali).

*Domande specifiche al reviewer:* l'espressione trovata (se stabile) è fisicamente plausibile — è compatibile con le previsioni della teoria perturbativa o della letteratura sulla dipendenza topologica da w? Il parsimony coefficient è calibrato correttamente per prevenire overfitting senza penalizzare eccessivamente le espressioni fisicamente motivate? Il test set held-out è sufficientemente rappresentativo dello spazio dei parametri?

**GATE 4 — Rivisto:**

Criteri tecnici:
- Espressione stabile trovata in ≥ 10/20 run con R² sul test set > threshold in CAUCHY_Execution_Parameters, oppure risultato negativo documentato (nessuna espressione stabile — Scenario C parziale).
- Istogramma di frequenza registrato in `results/phase4_sr_expressions.json`.

Criterio di review:
- Il reviewer ha restituito esito PROCEED, oppure REVISE NON-BLOCKING con tutte le revisioni assegnate.

Il gate non si chiude con un esito REVISE BLOCKING aperto.

---

### Review e Gate — Fase 5

**Review di Fase 5**

Questa è la review più importante del progetto: il suo esito determina la venue. Il PI sottomette al reviewer un report completo:

*Input dichiarati:* i risultati del Gate 3 e Gate 4; la specifica dei valori di injection testati con la loro motivazione (perché questi valori di w₀ e wₐ, collegamento con DESI DR2 best-fit); il modello HOD usato (AbacusSummit a 9 parametri) con i prior sui parametri HOD; il numero di passi MCMC per la marginalizzazione HOD e le diagnostiche di convergenza della catena.

*Metodi applicati:* il calcolo della correlazione parziale r(pipeline_output, w₀ | Ωm, σ₈) con la procedura di residualizzazione; il permutation test con N = 1.000 shuffle e il calcolo della significatività σ; il test di robustezza HOD (Zheng 2007 vs AbacusSummit) con i risultati numerici; il confronto con la baseline P(k) sugli stessi campi nwLH.

*Output prodotti:* la significatività σ per ogni valore di injection testato (Ramo A e Ramo B separatamente); il confronto σ_CAUCHY vs σ_Pk; i risultati del test di robustezza HOD; la distribuzione delle correlazioni null dal permutation test (sanity check che la distribuzione null sia centrata su zero).

*Considerazioni specifiche:* qualsiasi indicazione che la marginalizzazione HOD non sia conversa; qualsiasi segnale che la significatività sia dipendente dalla scelta dei campi fiduciali di riferimento; la differenza di significatività tra Ramo A e Ramo B (se il Ramo B non migliora su Ramo A, questo è un risultato metodologico importante).

*Domande specifiche al reviewer:* la procedura di residualizzazione per Ωm e σ₈ è corretta e non introduce bias nella stima di r(pipeline, w₀)? La marginalizzazione HOD è sufficientemente flessibile da non assorbire il segnale da w₀, o ci sono parametri HOD che rimangono correlati con w₀ anche dopo la marginalizzazione? Il confronto con la baseline P(k) è equo (stesse simulazioni, stesso numero di campi, stessa procedura di test)?

**GATE 5 — Rivisto:**

Criteri tecnici:
- Significatività σ documentata per tutti i valori di injection.
- Test di robustezza HOD eseguito e documentato.
- Confronto con baseline P(k) documentato.
- Venue determinata: σ ≥ 2.0 → Nature Astronomy; 1.0 ≤ σ < 2.0 → PRD; σ < 1.0 → JCAP.
- Valori in `results/phase5_phantom_test.json`.

Criterio di review:
- Il reviewer ha restituito esito PROCEED, oppure REVISE NON-BLOCKING con tutte le revisioni assegnate.

Nota: per la Fase 5 il reviewer può emettere un REVISE NON-BLOCKING anche con σ ≥ 2.0 se identifica problemi metodologici che non invalidano il risultato ma devono essere affrontati nel paper. In quel caso il gate si chiude sulla venue determinata dalla σ, ma le revisioni non-bloccanti devono essere risolte, giustificate o rimandate con motivazione prima della sottomissione del preprint.

Il gate non si chiude con un esito REVISE BLOCKING aperto.

---

### Review e Gate — Fase 6

**Review di Fase 6**

*Input dichiarati:* i risultati del Gate 5; la specifica del modello forward DESI (maschera angolare, funzione di selezione, correzione fiber assignment, tracciatori usati); i risultati della cross-validazione con BOSS DR12.

*Metodi applicati:* l'analisi delle vulnerabilità sistematiche della tabella §6.2, con i valori numerici di ogni test; la procedura di validazione del modello forward contro lo spettro di potenza osservato; il test di sensibilità al tracciatore (BGS/LRG/ELG).

*Output prodotti:* per ogni sistematica nella tabella §6.2, il valore numerico della variazione del segnale topologico quando la sistematica è variata entro le sue incertezze; il confronto del segnale CAUCHY su DESI vs il segnale su Quijote (consistenza).

*Considerazioni specifiche:* qualsiasi sistematica che produce una variazione > 1σ del segnale è riportata come risultato primario, non come problema da correggere.

*Domande specifiche al reviewer:* il modello forward per DESI è sufficientemente realistico da produrre cataloghi statisticamente indistinguibili dalle osservazioni per le statistiche topologiche? Le correzioni per fiber assignment sono adeguate per l'omologia persistente (le fiber collisions possono creare connessioni artificiali tra galassie a piccola scala che modificano β₀ e β₁)?

**GATE 6 — Rivisto:**

Criteri tecnici:
- Tutti i test sistematici della tabella §6.2 eseguiti e documentati.
- Variazioni < 1σ per le sistematiche non dominanti, oppure sistematiche dominanti identificate e documentate come risultato.
- Valori in `results/phase6_systematics.json`.

Criterio di review:
- Il reviewer ha restituito esito PROCEED, oppure REVISE NON-BLOCKING con tutte le revisioni assegnate.

Il gate non si chiude con un esito REVISE BLOCKING aperto.

---

### Note Operative sul Processo di Review

**Istanziazione del reviewer.** Il reviewer è un secondo Claude istanziato in un progetto separato su Claude.ai con un system prompt dedicato che lo istruisce a comportarsi come un referee di Nature Astronomy / Physical Review D / JCAP con esperienza specifica in TDA cosmologica, field-level inference e analisi statistica di survey. Il system prompt specifica che il reviewer non ha accesso ai precedenti cicli di review della stessa fase (ogni ciclo è indipendente) e che il suo ruolo è identificare problemi, non suggerire soluzioni.

**Registro delle review.** Ogni ciclo di review è registrato nel CHANGELOG con: data, fase, esito, lista delle revisioni emesse (bloccanti e non-bloccanti), e la risposta del PI per ogni revisione non-bloccante. Il CHANGELOG è il documento legale del processo scientifico.

**Limitazione dei cicli bloccanti.** Come specificato in §2.4, ogni revisione bloccante consuma uno dei N_max = 2 cicli di ricalibrzione disponibili per quel gate. Alla terza revisione bloccante, il progetto entra in Scenario C per quel gate, indipendentemente dalla causa della revisione.