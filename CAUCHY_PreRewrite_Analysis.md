# CAUCHY — Pre-Rewrite Analysis
## Registro delle Decisioni e Motivazioni: Transizione v1.9 → v2.0

**Classification:** Decisional Record — Storico  
**Version:** 1.0 — Aprile 2026  
**Status:** Chiuso — Decisioni implementate in v2.0  
**Autore:** PI + Claude (Sessione 1, 2026-04-25)  
**Fonti primarie:** CAUCHY_Execution_Design_v2.md §1.4, §11; CAUCHY_Systematic_Methodology_v2.md intestazione

---

## Scopo del Documento

Questo documento registra le **decisioni architetturali**, le **motivazioni** e le **trade-off valutate** durante la transizione dalla v1.9 (sistema multi-agente agentico) alla v2.0 (sistema PI-driven). Serve tre funzioni:

1. **Memoria storica:** evitare di rivalutare decisioni già prese in sessioni future.
2. **Audit trail scientifico:** un referee che chiede "perché avete abbandonato X?" trova la risposta qui, non nei commit git.
3. **Guard contro regressioni:** se una proposta futura reintroduce un elemento eliminato, questo documento è la prima verifica.

Il documento non è operativo. Non contiene threshold, parametri o gate criteria — quelli vivono in `CAUCHY_Execution_Parameters.md`. Contiene solo ragionamento decisionale.

---

## Parte I — Contesto: Cos'era la v1.9

### I.1 Architettura della v1.9

La v1.9 era un sistema multi-agente autonomo costruito attorno al framework GAME (Goal-Action-Memory-Environment). La struttura comprendeva:

- **21 file di framework** scritti e testati (AgentRegistry, Agent base class, AgentLanguage, Capability hooks, SessionBoundary, ActionContext con dependency injection)
- **97 Fixed Decisions architetturali** sul framework, separate dalle decisioni scientifiche
- **Gerarchia di agenti:** Coordinator → BranchA_Controller + BranchB_Controller → Specialist Pool (CosmologyAgent, EngineeringAgent, StatisticsAgent, LiteratureAgent)
- **RefereeAgent interno:** un agente specializzato nel sistema che simulava la review
- **ScriptedLLM loop:** sessioni agentive con loop automatico di chiamate al modello
- **Concetto di "sessione agentiva":** autonomia non supervisionata per task che duravano più chiamate

**Volume totale del framework:** stimato 3.000–5.000 righe di codice di infrastruttura prima di scrivere una riga di codice scientifico.

### I.2 Cosa Funzionava nella v1.9

Prima di documentare l'eliminazione, è importante registrare cosa della v1.9 era corretto e viene mantenuto:

| Elemento | Perché era corretto | Status in v2.0 |
|----------|---------------------|----------------|
| Prior congelati + Protocollo di Ricalibrzione | Previene p-hacking; difendibile ai referee | **Mantenuto** — D-04/D-05/D-06 |
| Asymmetric Recalibration Test | Unica validazione credibile che la ricalibrzione non sia reverse-engineering | **Mantenuto** — D-05 |
| Schemi JSON canonici (GateResult, FrozenPriorV, RecalibrationReport, SessionArtifact, ReviewerResponse) | Interoperabilità, audit trail, riproducibilità | **Mantenuto** — §6 Execution Design |
| Git tagging dei gate passati | Catena crittografica verificabile per i referee | **Mantenuto** — D-14 |
| N_max = 2 ricalibrazioni per gate | Previene cicli infiniti di ricalibrzione | **Mantenuto** — Methodology §2.4 |
| Document-as-Implementation per i PDFs Tier 1 | Riproducibilità offline | **Mantenuto** — D-07 |
| Vincolo hard sui numeri fisici | Previene allucinazioni numeriche del modello | **Mantenuto** — D-08 |
| Stack scientifico (gudhi, torch, e3nn, pysr, Julia) | Corretto tecnicamente | **Mantenuto** — §8 Execution Design |
| Struttura di Phase e gate criteria | Allineata con il Methodology | **Mantenuto** — §5 Execution Design |
| CHANGELOG a due livelli | Separazione narrativo/macchina | **Mantenuto** — D-13 |

---

## Parte II — Decisioni di Eliminazione

### D-E1: Eliminazione del Framework GAME e dell'Infrastruttura Agentiva

**Cosa è stato eliminato:**
- Framework GAME custom (21 file, 33 test di unità)
- AgentRegistry, Agent base class, AgentLanguage, Capability hooks
- SessionBoundary procedurale, ActionContext con dependency injection
- BranchA_Controller, BranchB_Controller come agenti autonomi
- CosmologyAgent, EngineeringAgent, StatisticsAgent, LiteratureAgent
- ScriptedLLM loop e concetto di sessione agentiva con autonomia

**Motivazione primaria:**
Il framework GAME aggiungeva un progetto di ingegneria del software — parallelo e di dimensioni comparabili — al progetto scientifico. Per un progetto pionieristico in cui ogni decisione metodologica è critica, questo significava che il PI doveva supervisionare *due* sistemi complessi simultaneamente: il codice scientifico (gudhi, torch, e3nn, pysr) e il framework agentivo (21 file, 97 decisioni architetturali).

**Diagnosi del problema strutturale:**
Il framework GAME presupponeva che il valore dell'automazione fosse nell'esecuzione autonoma delle sessioni. Ma l'analisi ha mostrato che per CAUCHY il collo di bottiglia non è l'esecuzione — è la *validazione*. Ogni output scientifico deve essere validato dal PI prima che possa essere usato come input del passo successivo. L'autonomia tra sessioni non era un guadagno: era una fonte di rischio non supervisionato.

**Alternativa adottata (v2.0):**
Il pattern Istruzione-Handback (§3.3 Execution Design): Claude genera l'istruzione eseguibile, il PI lancia, il PI riporta il risultato. L'autonomia è zero — ma la supervisione è totale. La linearità del flusso è garantita dalla struttura del progetto (sessioni dedicate con scopo preciso), non dal codice.

**Trade-off accettati:**
- Perdita: parallelizzazione automatica di alcune operazioni (es. TDA su fiduciali + LHC simultaneamente)
- Guadagno: zero codice di infrastruttura da mantenere; zero modalità di fallimento dell'agente; piena supervisione umana; riproducibilità garantita dalla manualità

**Rischio residuo:** nessuno specifico a questa eliminazione. Il rischio di overhead operativo per il PI è mitigato dalla chiarezza del pattern Istruzione-Handback.

---

### D-E2: Eliminazione del RefereeAgent Interno

**Cosa è stato eliminato:**
- RefereeAgent come agente autonomo interno al sistema v1.9
- System prompt del referee embedded nell'AgentRegistry
- Invocazione automatica del referee alla fine di ogni sessione agentiva

**Motivazione primaria:**
Un referee simulato internamente al sistema che ha prodotto il lavoro non è indipendente. Ha accesso al contesto della sessione, ai ragionamenti intermedi, alle motivazioni delle scelte — esattamente le informazioni che un referee reale *non* ha. Questo lo rendeva strutturalmente incapace di sollevare obiezioni genuinamente esterne.

**Diagnosi del problema epistemico:**
Se il CosmologyAgent produce un'analisi Fisher e il RefereeAgent legge il ragionamento che ha portato a quella analisi, il RefereeAgent non può fare a meno di essere influenzato da quel contesto. Il bias di conferma è architetturalmente inevitabile in un sistema co-localizzato.

**Alternativa adottata (v2.0):**
Claude Reviewer è un'istanza separata di Claude, istanziata in un **progetto Claude distinto**, con system prompt da referee (Nature Astronomy / PRD / JCAP). Il PI sottomette il prompt strutturato — che include solo le informazioni che un referee reale vedrebbe — senza il contesto della sessione di lavoro. L'indipendenza è strutturale, non solo procedurale.

**Trade-off accettati:**
- Perdita: overhead operativo per il PI (sottomissione manuale del prompt al progetto reviewer)
- Guadagno: indipendenza genuina del reviewer; parere scientificamente difendibile; allineamento con la prassi di peer review reale

**Nota:** il system prompt del Reviewer è versionato in `prompts/reviewer_system_prompt.md` (D-16). Il PI può aggiornarlo deliberatamente ma non accidentalmente.

---

### D-E3: Riduzione delle Fixed Decisions da 97 a 17

**Cosa è stato eliminato:**
- 80 delle 97 decisioni architetturali della v1.9, tutte relative al framework GAME e al sistema multi-agente
- Decisioni su: AgentRegistry API, Capability hooks signature, SessionBoundary behavior, ActionContext dependency injection, ScriptedLLM loop parameters, AgentLanguage specification

**Motivazione:**
Le 80 decisioni eliminate non erano decisioni scientifiche o operative — erano decisioni di *ingegneria del framework*. Erano necessarie solo perché il framework esisteva. Eliminando il framework, quelle decisioni cessano di essere rilevanti.

**Cosa è rimasto (17 decisioni):**
Le 17 decisioni rimanenti (D-01–D-17, §9 Execution Design) sono tutte operative o scientificamente motivate: prior congelati, protocollo di ricalibrzione, grounding sulla letteratura, audit trail, sequenza lineare delle Phase, attivazione lazy del Ramo B, CHANGELOG a due livelli, git tagging, system prompt del Reviewer versionato, documenti L2 just-in-time.

---

### D-E4: Eliminazione del Concetto di "Sessione Agentiva"

**Cosa è stato eliminato:**
- Il concetto di sessione che si auto-gestisce attraverso multiple chiamate al modello
- Il loop automatico di generazione-esecuzione-validazione
- La capacità del sistema di lanciare script autonomamente

**Motivazione:**
Il concetto di sessione agentiva presupponeva che Claude potesse operare come agente autonomo su task computazionali lunghi (ore, giorni). Ma per CAUCHY, il momento critico non è l'esecuzione — è la **validazione del risultato prima di procedere**. Un agente che esegue 12 ore di TDA e poi auto-valida il risultato non offre garanzie scientifiche: il PI non ha visto l'output prima che venisse usato come input del passo successivo.

**Alternativa adottata:**
Pattern Istruzione-Handback con sessioni di lavoro tipizzate (sessione di generazione script, sessione di analisi risultati, sessione di review prep, sessione di gate evaluation). Ogni tipo di sessione ha uno scopo preciso e produce un output definito. Il PI è il soggetto attivo in tutte le fasi critiche.

---

## Parte III — Decisioni di Mantenimento con Modifiche

### D-M1: Mantenimento degli Schemi JSON con Versionamento Esplicito

**Cosa è rimasto:** GateResult, FrozenPriorV, RecalibrationReport, SessionArtifact, ReviewerResponse come schemi JSON canonici.

**Modifica rispetto alla v1.9:** in v1.9 gli schemi erano popolati automaticamente dagli agenti. In v2.0 sono popolati dal PI con l'assistenza di Claude, ma il PI verifica ogni campo prima del commit. La struttura degli schemi è identica; il processo di popolamento è supervisionato.

**Motivazione del mantenimento:** gli schemi JSON sono la spina dorsale dell'audit trail. Un referee che chiede il RecalibrationReport del Gate 2 riceve un file strutturato e verificabile, non note in markdown. Questo è indipendente dall'architettura agentiva.

---

### D-M2: Mantenimento del Reviewer con Cambio di Implementazione

**Cosa è rimasto:** il concetto di review esterno prima di ogni gate, con tre esiti possibili (PROCEED / REVISE NON-BLOCKING / REVISE BLOCKING).

**Modifica rispetto alla v1.9:** da RefereeAgent interno (D-E2) a Claude Reviewer in progetto separato. Il system prompt del reviewer è ora esplicitamente versionato e mantenuto in `prompts/reviewer_system_prompt.md`.

**Motivazione del mantenimento:** la review esterna è il meccanismo fondamentale di controllo della qualità scientifica. Eliminarlo avrebbe compromesso la difendibilità dell'analisi ai referee reali.

---

### D-M3: Mantenimento della Struttura di Phase con Rimozione della Parallelizzazione

**Cosa è rimasto:** le 7 Phase (0–6) con i gate criteria come definiti nel Methodology.

**Modifica rispetto alla v1.9:** la v1.9 prevedeva parallelizzazione parziale di alcune Phase (es. avvio della CNN di Phase 2 in parallelo alla verifica finale dei risultati di Phase 1). La v2.0 adotta la **sequenza lineare stretta**: nessuna Phase inizia prima che il gate precedente sia chiuso.

**Motivazione della modifica:** la parallelizzazione richiedeva state management complesso per gestire i casi in cui Phase 1 poteva ancora falsificare assunzioni di Phase 2. La linearità elimina questa complessità e garantisce che ogni Phase sia costruita su risultati verificati.

**Trade-off accettato:** incremento del tempo totale di esecuzione stimato del 10–20% rispetto a un'esecuzione parallelizzata ottimale. Il guadagno in correttezza e semplicità è considerato superiore al costo.

---

## Parte IV — Decisioni Scientifiche Mantenute Invariate

Le seguenti decisioni scientifiche erano già corrette nella v1.9 e vengono trasferite intatte alla v2.0. Non richiedono analisi aggiuntiva — sono riportate per completezza del registro.

| Decisione | Riferimento v2.0 |
|-----------|-----------------|
| Due rami scientifici indipendenti (Ramo A: TDA(δ(x)); Ramo B: TDA(τ(x))) | Methodology §2.3 |
| Supervisione della CNN sulle Betti features, non sui parametri cosmologici | Methodology §2.1 |
| Test T1 di fattorizzazione parametrica (rapporto W₂) come Gate 2 | Methodology §2.3, Exec Design §5.3 |
| Symbolic Regression come strumento interpretativo, non predittivo | Methodology §4.1 |
| Phantom crossing injection test con marginalizzazione HOD a 9 parametri | Methodology §5.1–5.2 |
| HOD AbacusSummit 9 parametri (errore v3.x con HOD fisso documentato) | Methodology §5.2 |
| Test di robustezza HOD obbligatorio (Zheng 2007 vs AbacusSummit) | Methodology §5.2 |
| Confronto obbligatorio σ_CAUCHY vs σ_Pk per Gate 5 | Methodology §5.3 |
| Tre scenari di pubblicazione (A/B/C), tutti pubblicabili | Methodology §1.4 |
| Attivazione lazy del Ramo B: solo dopo Gate 1 passato | Methodology §2.3, D-11 |

---

## Parte V — Lezioni della v3.x (Errore Documentato)

Prima della v2.0, una versione intermedia v3.x aveva tentato di implementare la CNN con supervisione diretta sui parametri cosmologici (Ωm, σ₈) invece che sulle Betti features. Il risultato è stato che la CNN imparava a stimare σ₈ misurando l'ampiezza media del campo — operazione equivalente allo spettro di potenza monopolo — rendendo il Ramo B ridondante rispetto al Ramo A.

**Lezione incorporata in v2.0:**
La scelta di supervisionare la CNN sulle Betti features invece che sui parametri è ora una **decisione fissa non modificabile** senza passare per il Protocollo di Ricalibrzione Formale con review del Reviewer. L'errore v3.x è documentato esplicitamente nel Methodology §2.1 come motivazione negativa (anti-pattern).

**Implicazione per il gate:** il test T1 di fattorizzazione parametrica (Gate 2) è progettato specificamente per rilevare la ricaduta nell'errore v3.x. Se R ≈ 0, la CNN ha di nuovo collassato su σ₈ — il gate blocca e il Ramo B non si attiva.

---

## Parte VI — Domande Aperte al Momento della Riscrittura

Le seguenti questioni erano aperte al momento della transizione v1.9 → v2.0 e rimangono aperte. Vengono documentate qui per evitare che vengano perse tra le sessioni.

| ID | Domanda | Fase rilevante | Stato |
|----|---------|---------------|-------|
| Q-01 | La filtrazione di supralivello su campi di griglia 128³ è ottimale rispetto alla filtrazione α-DTMℓ su cataloghi di punti? | Fase 1 | Aperta — da valutare dopo Gate 1 |
| Q-02 | La proiezione scalare di τ(x) ottimale è la norma del vettore latente |τ(x)| o il primo componente principale? | Fase 3 | Aperta — dipende da D_latent e dalla struttura della CNN |
| Q-03 | L'accesso ai cataloghi DESI DR2 è ottenibile entro il timeline del progetto? | Fase 6 | Aperta — decision point a Gate 5 |
| Q-04 | La distanza di Mahalanobis nello spazio latente è superiore alla distanza euclidea per la definizione di τ(x)? | Fase 2 | Aperta — menzionata dal Claude Reviewer come domanda specifica (Review_and_GATE §Phase 2) |
| Q-05 | L'architettura SE(3)-equivariante è appropriata per campi su griglia cubica (dove le simmetrie del reticolo differiscono da SE(3) continuo)? | Fase 2 | Aperta — menzionata dal Claude Reviewer come domanda specifica |

---

## Parte VII — Stato di Completamento Pre-Esecuzione

Al momento della produzione di questo documento (Sessione 1, 2026-04-25), lo stato pre-esecuzione è:

| Item | Stato |
|------|-------|
| Methodology v2.0 | ✅ Prodotto e congelato |
| Execution Design v2.0 | ✅ Prodotto |
| Review and Gate protocol | ✅ Prodotto |
| CAUCHY_PreRewrite_Analysis (questo documento) | ✅ Prodotto |
| CAUCHY_Open_Issues | ✅ Prodotto (vuoto) |
| CAUCHY_Execution_Parameters v1.1 | ✅ Prodotto con threshold numerici |
| CHANGELOG aggiornato | ✅ Aggiornato a Sessione 1 |
| index.json (9 paper Tier 1) | ✅ Valido e corretto |
| PDF Tier 1 (9 paper) | ✅ In `literature/tier1/` |
| Revisioni .md Tier 1 (8 paper) | ✅ In `literature/tier1/StateOfArt/` |
| prompts/reviewer_system_prompt.md | ⬜ Da produrre (M0) |
| prior/gate0_prior_v1.0.json | ⬜ Da produrre (M0) — i valori sono in CAUCHY_Execution_Parameters |
| environment.yml testato | ⬜ Da verificare in M0 |
| Struttura directory git | ⬜ Da inizializzare in M0 |
| Sessione review di prova (Reviewer) | ⬜ Da completare (exit criterion M0) |

**Prossimo passo:** Milestone M0.

---

*CAUCHY PreRewrite Analysis v1.0*  
*Prodotto: Aprile 2026, Sessione 1*  
*Questo documento è chiuso: le decisioni sono implementate in v2.0 e non riapribili senza esplicita deliberazione del PI con entry CHANGELOG.*
