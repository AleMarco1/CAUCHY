# CAUCHY — Execution Design
## Cosmic Anomaly via Unified Cosmological Hyper-fields analYsis

**Classification:** Operational Blueprint  
**Version:** 2.0 — Aprile 2026  
**Status:** Pronto per l'esecuzione — Phase 0  
**Supersedes:** CAUCHY_Agentic_Execution_Design v1.9  

---

## Table of Contents

1. [Executive Summary & Scope](#1--executive-summary--scope)
2. [Principi Operativi](#2--principi-operativi)
3. [Modello di Esecuzione](#3--modello-di-esecuzione)
4. [Meccanismi Fondamentali](#4--meccanismi-fondamentali)
5. [Phase → Session Map](#5--phase--session-map)
6. [Schemi JSON Canonici](#6--schemi-json-canonici)
7. [Repository Layout](#7--repository-layout)
8. [Stack Tecnologico](#8--stack-tecnologico)
9. [Decisioni Fisse](#9--decisioni-fisse)
10. [Implementation Roadmap](#10--implementation-roadmap)
11. [Changelog](#11--changelog)

---

## 1 — Executive Summary & Scope

### 1.1 Cos'è questo documento

Questo documento definisce l'**architettura operativa** del Progetto CAUCHY. È il blueprint che governa come il protocollo scientifico specificato in `CAUCHY_Systematic_Methodology_v2.md` viene operazionalizzato attraverso sessioni di lavoro tra il PI e Claude.

Il documento è strutturato in livelli: **L1 (Blueprint)** fissa architettura, principi e decisioni. Le sezioni vengono approfondite a **L2 (Blueprint + Interfacce)** just-in-time quando si avvicina ogni Phase. Questo evita di scrivere specifiche dettagliate per la Phase 5 mentre la Phase 2 potrebbe ancora falsificare assunzioni upstream.

### 1.2 Cosa NON è questo documento

- **Non** è un duplicato del Methodology. Il Methodology risponde a *cosa* fare scientificamente; questo risponde a *come* eseguirlo operativamente.
- **Non** è congelato. È un documento vivo con un CHANGELOG, aggiornato quando le decisioni cambiano o si raggiungono nuove Phase.

### 1.3 Relazione con il Methodology

| Aspetto | `CAUCHY_Systematic_Methodology_v2.md` | `CAUCHY_Execution_Design.md` (questo) |
|---------|---------------------------------------|---------------------------------------|
| Risponde a | Cosa fare, perché, gate criteria | Come eseguire, con quali strumenti, in quale sequenza |
| Audience primaria | Referee, collaboratori scientifici | PI durante l'esecuzione |
| Cadenza di cambiamento | Lenta — revisioni metodologiche | Più rapida — refinement operativi |
| Autoritativo su | Correttezza scientifica | Correttezza operativa |
| Risoluzione conflitti | **Methodology vince** sulle questioni scientifiche | Questo vince sui dettagli operativi |

### 1.4 Cambio di approccio rispetto alla v1.9

La v1.9 era costruita attorno a un sistema multi-agente autonomo: Coordinator, BranchA/B Controller, Specialist Pool, framework GAME custom, 97 decisioni architetturali, 21 file di framework scritti e testati. Era un progetto di ingegneria del software parallelo al progetto scientifico.

**La v2.0 adotta un approccio radicalmente più semplice e più umano:**

- Il **PI** è il soggetto esecutivo. Prende tutte le decisioni, lancia tutti gli script, valida tutti i risultati.
- **Claude** (Sonnet 4.6 per task analitici e di generazione script; Opus 4.x per analisi scientifiche complesse e review) è lo strumento di analisi e generazione. Produce script Python/Julia, analisi scientifiche, prompt per il reviewer.
- **Claude Reviewer** è un secondo Claude istanziato in un progetto separato con system prompt da referee, consultato prima di ogni gate.
- **Ogni output** va in revisione umana. Nessuna autonomia non supervisionata.
- **La sequenza è lineare**: ogni phase progettata tenendo conto dei requisiti delle due phase successive.

Questo elimina: il framework GAME custom, l'AgentRegistry, il sistema multi-agente gerarchico, il SessionBoundary procedurale, l'ActionContext con dependency injection, e le 97 decisioni architetturali sul framework. Il codice scientifico (gudhi, torch, pysr) rimane. La struttura di audit e gate rimane. Il reviewer rimane, ora come Claude esterno invece che come RefereeAgent interno.

---

## 2 — Principi Operativi

Questi principi sono **vincoli vincolanti** su ogni decisione operativa downstream.

### 2.1 Trasparenza sull'Autonomia

Il valore di Claude non è quante azioni esegue autonomamente, ma quanto chiaramente espone ogni decisione tecnica al giudizio umano. Ogni risposta di Claude deve portare il suo ragionamento in forma leggibile, non solo le conclusioni.

### 2.2 Autorità Esecutiva del PI

Il PI mantiene l'autorità esecutiva su tutte le azioni:
- **Costose** (compute cloud, A100)
- **Irreversibili** (write ai cataloghi condivisi, submission paper)
- **Long-running** (training job da ore a giorni)

Claude non lancia mai queste azioni autonomamente. Genera le istruzioni per lanciarle, il PI revisiona, il PI lancia, il PI riporta il risultato. Questo è il **pattern Istruzione-Handback** (§3.3).

### 2.3 Falsificabilità a Ogni Stadio

Ogni Phase produce un artefatto ispezionabile, riproducibile e falsificabile. Nessuna Phase è "completa" finché il suo gate criterion è soddisfatto e il suo file di risultato è conforme allo schema canonico. I risultati nulli sono output pubblicabili, non fallimenti.

### 2.4 Prior Congelati + Ricalibrzione Formale

I threshold dei gate sono prior congelati, versionati come artefatti immutabili. Possono essere revisionati solo attraverso il Protocollo di Ricalibrzione Formale (§4.2) con argomenti di scaling espliciti, review del Claude Reviewer, e conta di ricalibrzione limitata (N_max = 2 per gate).

### 2.5 Il Repository è Canonico

Lo stato del progetto vive nel filesystem come artefatti versionati. La memoria della sessione Claude è effimera. Il repository è il record scientifico.

---

## 3 — Modello di Esecuzione

### 3.1 I Tre Soggetti

**PI (Principal Investigator)**
- Prende tutte le decisioni scientifiche e operative
- Lancia tutti gli script sul proprio hardware / cloud
- Valida tutti i risultati prima di procedere
- Sottomette i prompt al Claude Reviewer prima di ogni gate
- Chiude o riapre i gate sulla base dell'esito del review

**Claude (strumento di lavoro — Sonnet 4.6 default, Opus 4.x per analisi complesse)**
- Analizza i dati e i risultati quando il PI li porta in sessione
- Genera script Python e Julia per ogni task computazionale
- Produce analisi scientifiche e interpretazioni
- Costruisce i prompt strutturati per il Claude Reviewer
- Suggerisce ma non decide

**Claude Reviewer (istanza separata — Opus 4.x)**
- Istanziato in un progetto Claude separato
- System prompt: referee scientifico esigente (Nature Astronomy / PRD / JCAP)
- Chiamato dal PI prima di ogni gate con il prompt strutturato prodotto da Claude
- Restituisce: PROCEED, REVISE NON-BLOCKING, o REVISE BLOCKING
- Il suo parere è parte del gate criterion (vedi Methodology §Review e Gate)

### 3.2 Routing del Modello

| Task | Modello | Ragione |
|------|---------|---------|
| Generazione script Python/Julia | Claude Sonnet 4.6 | Output strutturato affidabile, costo contenuto |
| Analisi scientifica, interpretazione Fisher | Claude Opus 4.x | Correttezza scientifica primaria |
| Review pre-gate | Claude Reviewer (Opus 4.x) | Ragionamento da referee è il deliverable |
| Interpretazione espressioni SR | Claude Opus 4.x | Giudizio fisico richiede modello più capace |
| Controlli integrità dati, sanity check | Claude Sonnet 4.6 | Task meccanico, frequente |

Il PI sceglie il modello appropriato in base al task. Il default è Sonnet 4.6.

### 3.3 Pattern Istruzione-Handback

Per ogni task computazionale long-running o costoso:

```
SESSIONE N — Preparazione (PI + Claude)
────────────────────────────────────────
Claude genera: script + istruzioni di lancio + output atteso
PI revisiona: lo script è corretto? i parametri sono quelli decisi?
PI lancia: script sul proprio hardware / cloud

PI attende (minuti / ore / giorni)
PI raccoglie: output in artifacts_in/session_N+1/

SESSIONE N+1 — Analisi e Gate (PI + Claude)
─────────────────────────────────────────────
PI porta: report di output in sessione
Claude analizza: schema-valida, interpreta scientificamente
Claude produce: prompt per Claude Reviewer
PI sottomette a Claude Reviewer
Claude Reviewer risponde
PI valuta gate: criteri tecnici + parere reviewer
```

**Proprietà critica:** Claude non ha stato tra le sessioni. Lo stato vive nel filesystem come artefatti versionati. Ogni sessione legge lo stato da disco all'inizio.

### 3.4 Sessioni di Lavoro Tipiche

Una sessione di lavoro è un'interazione PI-Claude in un singolo thread di conversazione Claude. Le sessioni hanno tipicamente uno scopo preciso:

- **Sessione di generazione script:** Claude produce lo script per un task specifico. Output: file Python o Julia pronto per il lancio.
- **Sessione di analisi risultati:** PI porta i risultati, Claude li analizza e interpreta. Output: interpretazione scientifica, tabelle, grafici.
- **Sessione di review prep:** Claude costruisce il prompt strutturato per il Claude Reviewer. Output: prompt da sottomettere al progetto review.
- **Sessione di gate evaluation:** PI porta il parere del reviewer, Claude aiuta a valutare i gate criteria. Output: decisione di gate documentata.

Ogni sessione produce un file di output documentato in `sessions/`.

### 3.5 Multi-Session Planning

Prima di ogni sessione, Claude e il PI definiscono:

**(a) Design completo — sessione corrente.** Rigoroso, completo, eseguibile. Include tutti i parametri dello script, i path di input/output, e i criteri di successo che permettono alla sessione di chiudersi.

**(b) Contratto di output — sessione successiva.** Solo gli schemi degli artefatti che la sessione corrente produrrà e la sessione successiva consumerà. Forza la sessione corrente a produrre output consumabili.

**(c) Horizon di pianificazione — due sessioni successive.** Indicativo, non eseguibile. Identifica le dipendenze che la sessione corrente non deve chiudere in modo tale da bloccare le successive.

---

## 4 — Meccanismi Fondamentali

### 4.1 Gate Transaction

Ogni gate è una transazione atomica documentata nel repository. La transazione:

1. Legge il frozen prior dalla versione corrente (`prior/gate<N>_prior_v<K>.json`)
2. Valuta ogni criterio tecnico sul risultato osservato
3. Il PI sottomette il prompt al Claude Reviewer e riporta il parere
4. Se tutti i criteri tecnici sono soddisfatti E il reviewer ha dato PROCEED o NON-BLOCKING: gate PASS → git commit + tag `gate_N_passed_v<K>`
5. Se un criterio tecnico fallisce O il reviewer ha dato BLOCKING: gate FAIL → Protocollo di Ricalibrzione

**Atomicità:** ogni artefatto è scritto via tempfile + rename (POSIX-atomic per-file). Il git commit + tag `gate_N_passed_v<K>` è il contratto finale. Un file sentinel `.gate_N_commit_in_progress` protegge dal crash recovery.

**Invariante:** `gate_passed = true` è compatibile con parere NON-BLOCKING (le revisioni sono assegnate e documentate). `gate_passed = true` è incompatibile con parere BLOCKING.

### 4.2 Protocollo di Ricalibrzione Formale

Quando un criterio tecnico di gate fallisce, prima di qualsiasi modifica al threshold:

**Step 1 — Diagnosi:** Claude identifica le cause candidate del fallimento. La diagnosi deve essere strutturata: per ogni causa candidata, quantificazione, supporto all'osservato, confidenza.

**Step 2 — Scaling argument:** se la causa è una differenza di contesto rispetto alla letteratura (diverso volume, diverso tracciatore, diverso range di redshift), si calcola il threshold ricalibrto con un argomento di scaling esplicito. Non è fitting al valore osservato.

**Step 3 — Asymmetric Recalibration Test:** Claude verifica che la ricalibrzione superi il test di asimmetria: se il volume fosse 2× più grande, il threshold scalato nella direzione opposta? Se la risposta è sì e il nuovo threshold è fisicamente plausibile, la ricalibrzione è difendibile. Se il test fallisce, la ricalibrzione è p-hacking.

**Step 4 — Review del Reviewer:** il PI sottomette la ricalibrzione proposta al Claude Reviewer con il RecalibrationReport completo. Il Reviewer deve esplicitamente approvare la ricalibrzione.

**Step 5 — Nuovo prior:** se il Reviewer approva, si scrive il nuovo prior `prior/gate<N>_prior_v<K+1>.json`. Il vecchio prior è mantenuto — non si sovrascrive mai.

**Limite:** N_max = 2 ricalibrzioni per gate. Alla terza richiesta bloccante, il gate chiude in Scenario C — si scrive un `GateExhaustionArtifact` e si documenta come risultato scientifico.

**Ogni RecalibrationReport è scritto** sia in caso di approvazione che di rigetto. I tentativi rigettati fanno parte del record scientifico.

### 4.3 Grounding sulla Letteratura

**Tier 1 — PDFs pre-caricati (fonte primaria).** I paper obbligatori del Methodology §1.3 sono in `literature/tier1/` come artefatti PDF con metadati indicizzati in `literature/index.json`. Claude legge da questi artefatti quando risponde a domande scientifiche specifiche — non dalla propria memoria di training.

**Tier 2 — ADS/arXiv live (discovery + novelty check).** Il PI può portare in sessione paper recenti non in Tier 1. Quando Claude identifica un paper rilevante non in Tier 1, lo segnala esplicitamente con `[LITERATURE_NOTICE]`. Il PI valuta → aggiorna `literature/tier1/` se appropriato → aggiorna `literature/index.json`.

**Vincolo hard sui numeri fisici:** qualsiasi numero fisico nell'analisi di Claude deve tracciare a (a) una citazione alla literature index o (b) un calcolo sui dati CAUCHY. Affermazioni numeriche non citate sono segnalate esplicitamente come "valore non verificato — da controllare".

### 4.4 Progress Tracking e Audit Trail

Ogni sessione produce un `SessionArtifact` in `sessions/session_<N>_output.json` che registra: timestamp, input artifacts con checksum, output artifacts con checksum, azione successiva attesa, note su deviazioni dal protocollo.

L'audit trail è parte del materiale supplementare del paper. Un referee che chiede "come è stato ottenuto questo risultato?" riceve una catena verificabile di sessioni, ciascuna con git commit.

**Checksum:** ogni artefatto di input viene verificato contro il checksum dell'artefatto di output della sessione precedente. Mismatch = interruzione e investigazione del PI.

### 4.5 CHANGELOG

Il CHANGELOG ha due livelli:
- `CHANGELOG.md`: narrativo, curato manualmente dal PI per ogni gate passato e ogni decisione metodologica significativa.
- `changelog_events.jsonl`: append automatico di eventi strutturati a ogni gate transaction (machine-parseable).

---

## 5 — Phase → Session Map

Ogni Phase è specificata con input, output, controller (chi fa cosa), stima di sessioni, gate criteria, note. I dettagli di tool signature e prompt template sono approfonditi a L2 just-in-time quando si avvicina la Phase.

### 5.1 Phase 0 — Preparazione e Validazione dei Dati

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Phase 0 |
| Durata (umana) | 2–3 giorni |
| Durata (macchina) | 30 min (controlli integrità) |
| Sessioni stimate | ~2 |
| Input | Path locali dataset Quijote (fiduciali, LHC, nwLH) |
| Output | `results/phase0_data_manifest.json` + `results/phase0_preprocessing_lock.json` + `results/phase0_review.json` |
| Handback richiesto? | No (abbastanza veloce da stare in-session) |

**Sessione 1:** Claude genera lo script di controllo integrità + manifest generator. PI lancia. PI riporta il manifest.

**Sessione 2:** Claude analizza il manifest, valida le scelte di preprocessing contro il Methodology §0.3, costruisce il prompt per il Claude Reviewer. PI sottomette al Reviewer. PI riporta il parere. Claude aiuta a valutare il Gate 0.

**REVIEW 0:** al completamento dei controlli di integrità e della pipeline di preprocessing, il PI sottomette al Claude Reviewer un prompt con: numero di campi verificati per dataset, tasso di superamento dei controlli, scala di smoothing applicata, motivazione della normalizzazione per-cosmologia, e lista di eventuali campi rigettati con causa. Il Reviewer valuta la coerenza della pipeline con la letteratura TDA di riferimento. Le revisioni non-bloccanti devono essere risolte, giustificate o rimandate con motivazione documentata nel CHANGELOG. Le revisioni bloccanti riaprono la Phase; alla terza il gate chiude in Scenario C.

**GATE 0:** tutti i campi superano i controlli di integrità. La pipeline è applicata e version-locked. Il Reviewer ha restituito PROCEED o NON-BLOCKING con tutte le revisioni assegnate. Output: `results/phase0_data_manifest.json` con checksum di tutti i campi di input, `results/phase0_preprocessing_lock.json` con la specifica completa della pipeline,`phase0_gate_result.json`, `gate0_prior_v1.0.json`, `results/phase0_review.json` con parere positivo.

---

### 5.2 Phase 1 — TDA Baseline (Ramo A)

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Phase 1 |
| Durata (umana) | 3–5 giorni |
| Durata (macchina) | 3–12 ore (TDA parallelizzata) |
| Sessioni stimate | ~3–4 |
| Input | `results/phase0_*.json` + dataset fiduciali, LHC, nwLH |
| Output | `results/phase1_tda_baseline.json` + `results/phase1_review.json` |
| Handback richiesto? | **Sì** — TDA su 2000 campi richiede ore |
| Ricalibrzione attesa? | **Sì** — volume scaling rispetto a Yip & Biagetti 2024 probabile |

**Sessione 1:** Claude genera lo script TDA (gudhi, superlevel CubicalComplex) per i 500 campi fiduciali. PI lancia. PI riporta le Betti curves.

**Sessione 2:** Claude valida la forma delle Betti curves (sanity check). Claude genera lo script TDA completo su LHC + nwLH. PI lancia. PI riporta i feature estratti.

**Sessione 3:** Claude calcola la matrice Fisher (Gate 1a) e le correlazioni con w₀ (Gate 1b). Claude costruisce il prompt per il Claude Reviewer.

**Sessione 4 (se necessaria):** Ricalibrzione formale se un gate criterion fallisce.

**REVIEW 1:** al completamento dell'analisi Fisher, il PI sottomette al Claude Reviewer un prompt con: σ(Ωm) e σ(σ₈) dal dataset LHC, correlazione ρ(Ωm, σ₈) confrontata con P(k), correlazioni |r(feature_k, w₀)| dal dataset nwLH, motivazione delle feature estratte, diagnostiche di convergenza della matrice Fisher. Il Reviewer valuta la solidità statistica, la coerenza con Yip 2024 scalato per volume, e la significatività fisica delle correlazioni con w₀. Le revisioni non-bloccanti devono essere risolte, giustificate o rimandate. Le revisioni bloccanti riaprono la Phase; alla terza il gate chiude in Scenario C.

**GATE 1 (bipartito):** matrice Fisher su (Ωm, σ₈) dal dataset LHC calcolata e documentata (Gate 1a). Correlazioni |r(feature_k, w₀)| dal dataset nwLH calcolate e documentate (Gate 1b). Il gate è superato solo quando entrambe le condizioni sono soddisfatte. Il Reviewer ha restituito PROCEED o NON-BLOCKING con tutte le revisioni assegnate. Output: `results/phase1_tda_baseline.json`, `phase1_gate_result.json`, `gate1_prior_v1.0.json`,`results/phase1_review.json` con parere positivo.

---

### 5.3 Phase 2 — CNN con Supervisione Topologica e Costruzione di τ(x)

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Phase 2 |
| Durata (umana) | 1–2 settimane |
| Durata (macchina) | 1–3 giorni (training A100) |
| Sessioni stimate | ~4–5 |
| Input | `results/phase1_tda_baseline.json` + dataset LHC (training) + fiduciali (μ_ΛCDM) |
| Output | `results/phase2_cnn_diagnostic.json` + model checkpoint + `results/phase2_review.json` |
| Handback richiesto? | **Sì — training multi-giorno su A100** |
| Budget | ~$100–200 |
| Ricalibrzione possibile? | Sì — T1 test potrebbe richiedere revisione threshold |

**Nota critica sull'attivazione del Ramo B:** la Phase 2 si attiva solo dopo il superamento del Gate 1. Se il Gate 1 chiude in Scenario C, il Ramo B non viene mai avviato.

**Sessione 1:** Claude specifica l'architettura CNN (SE(3)-equivariante, e3nn) e la loss di supervisione topologica. Claude genera lo script di training. PI revisiona l'architettura. PI autorizza il costo cloud. PI lancia.

**Sessione 2:** PI riporta il training report. Claude analizza convergenza. Claude genera lo script per il T1 test di fattorizzazione parametrica. PI lancia il T1. PI riporta i risultati.

**Sessione 3:** Claude valuta il T1 (rapporto R). Se pass: Claude genera lo script per la costruzione di τ(x) su tutti i campi. Se fail: diagnosi e eventuale ricalibrzione.

**Sessione 4:** Claude costruisce il prompt per il Claude Reviewer.

**REVIEW 2:** al completamento del training CNN e della costruzione di τ(x), il PI sottomette al Claude Reviewer un prompt con: specifica dell'architettura e della loss, valore di R dal T1 con i valori W₂ per tutti i quadranti, correlazione tra |τ(x)| e l'hessiano locale di δ(x), curve di loss. Il Reviewer valuta se la supervisione topologica evita il collasso verso soluzioni gaussiane e se τ(x) cattura struttura geometrica non-lineare. Le revisioni non-bloccanti devono essere risolte, giustificate o rimandate. Le revisioni bloccanti riaprono la Phase; alla terza il gate chiude con attivazione del solo Ramo A.

**GATE 2:** test T1 superato con R > threshold. τ(x) costruito per tutti i campi LHC e nwLH con procedura version-locked. Il Reviewer ha restituito PROCEED o NON-BLOCKING con tutte le revisioni assegnate. Output: `results/phase2_cnn_diagnostic.json`, `phase2_gate_result.json`, `gate2_prior_v1.0.json`, `results/phase2_review.json` con parere positivo.

---

### 5.4 Phase 3 — GNN su TDA(τ(x))

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Phase 3 |
| Durata (umana) | 1–2 settimane |
| Durata (macchina) | 2–4 giorni (training A100) |
| Sessioni stimate | ~4–5 |
| Input | τ(x) per tutti i campi + diagrammi di persistenza β₁(τ), β₂(τ) |
| Output | `results/phase3_gnn_correlations.json` + `results/phase3_review.json` |
| Handback richiesto? | **Sì** |
| Budget | ~$150–300 |


**Input effettivi da Phase 2 (Gate 2 PASS, 2026-04-29)**

τ(x) è disponibile per 4.000 campi (2.000 LHC + 2.000 nwLH), prodotto dalla CNN SE(3)-equivariante (checkpoint SHA-256: 302771fc..., val_loss=0.0817, epoca 186). Ogni campo è rappresentato come point cloud `[8192, 35]` — 8.192 punti campionati con peso |δ(x)|, coordinate fisiche (3) + vettore latente D_latent=32. μ_ΛCDM norm=2.893.

**Prerequisiti da soddisfare all'apertura di Phase 3 prima di qualsiasi codice** (impegni R2-3 e R2-4 del Review 2, obbligatori e potenzialmente bloccanti):

*R2-3 — Test KS su struttura topologica di τ:* calcolare i diagrammi di persistenza β₁(τ) e β₂(τ) su un campione di 50 campi fiduciali. Confrontare le distribuzioni di persistenza con quelle di campi GRF sintetici con stessa varianza (test Kolmogorov-Smirnov). Se le distribuzioni sono indistinguibili (p>0.05), τ(x) non porta struttura topologica genuina rispetto a un campo gaussiano — il Ramo B è bloccato e Phase 3 non può procedere.

*R2-4 — Varianza spaziale di |τ(x)|:* su 50 campi campione, verificare che la varianza spaziale media di |τ(x)| superi il 5% della varianza inter-campo della norma media. Se |τ(x)| è sostanzialmente piatto per campo, la TDA su τ produce segnale nullo indipendentemente dalla cosmologia.

**Proiezione scalare e filtrazione**

La TDA viene applicata alla norma del vettore latente |τ(x)| come campo scalare su point cloud `[8192, 3]` — le coordinate fisiche con i pesi |τ| come funzione di filtrazione. La filtrazione di superlevel su |τ(x)| cattura le strutture di alta anomalia: regioni dove il campo di densità devia fortemente dalla media ΛCDM. I diagrammi di persistenza β₁(τ) (loops di anomalia — filamenti anomali) e β₂(τ) (vuoti di anomalia — regioni chiuse di alta deviazione) sono i target del GNN.

La soglia di persistenza minima per la selezione dei nodi del grafo è derivata dalla distribuzione di persistenza nei campi fiduciali (per definizione τ≈0 nei fiduciali → persistenze brevi = rumore topologico). Formalmente: threshold = percentile 90° della distribuzione di persistenza sui 2.000 campi fiduciali.

**Costruzione del grafo topologico**

Nodi: feature topologiche di β₁(τ) e β₂(τ) con persistenza sopra threshold. Feature dei nodi: (birth_ν, death_ν, persistence, dim) + valore di |τ̄| nella regione corrispondente. Il numero atteso di nodi per campo LHC è tra 20 e 200 sulla base delle statistiche β₁ e β₂ da Phase 1 scalate a τ — da verificare empiricamente su 50 campi all'apertura.

Archi: k-NN nello spazio (birth, death) del diagramma di persistenza, k da determinare in Sessione 1 sulla base della densità di nodi osservata (range atteso k=5–15).

**Architettura GNN**

Il GNN lavora sui grafi topologici di τ(x), non su δ(x) — questo è il punto di separazione architetturale dal Ramo A. L'architettura specifica (numero di layer, dimensione hidden, pooling globale) viene definita in Sessione 1 dopo la verifica degli impegni R2-3/R2-4 e la stima della dimensione media dei grafi.

Target di supervisione: (Ωm, σ₈) sul training set LHC (80/20 split, seed=42 per coerenza con Phase 2). La componente nwLH è usata esclusivamente per la correlazione con w₀ — non entra nel training.

**Gate 3 — Threshold**

| Criterio | Threshold | Autorità |
|---|---|---|
| \|r(GNN_j\*, Ωm)\| sul test set LHC | ≥ 0.20 | CAUCHY_Execution_Parameters §5.2 |
| \|r(GNN_j\*, σ₈)\| sul test set LHC | ≥ 0.20 | CAUCHY_Execution_Parameters §5.2 |
| Varianza spiegata aggiuntiva vs Ramo A | ≥ 5% | CAUCHY_Execution_Parameters §5.2 |
| \|r(GNN_j\*, w₀)\| su nwLH | documentare (soft) | CAUCHY_Execution_Parameters §5.3 |
| Quantificazione empirica variabilità T1 | ≥10 run stesso checkpoint | Riserva Reviewer Phase 2, 2026-04-29 |

Il criterio di miglioramento ≥5% rispetto al Ramo A è calcolato come: varianza di (Ωm, σ₈) spiegata dal GNN su τ(x) meno varianza spiegata dalle 8 feature TDA di Phase 1 sullo stesso test set, normalizzata per la varianza totale. Il confronto usa lo stesso 20% di test set (seed=42) per entrambi i rami.

**Sessioni**

*Sessione 1:* verifica impegni R2-3 e R2-4. Se entrambi PASS: analisi esplorativa su 100 campi (distribuzione numero di nodi, persistenze, densità del grafo). Definizione architettura GNN e iperparametri. Generazione `src/phase3_gnn.py` con assert sui parametri frozen di `gate2_prior_v1.0.json` all'avvio.

*Sessione 2:* report training GNN. Analisi convergenza. Calcolo correlazioni sul test set.

*Sessione 3:* analisi correlazione con w₀ su nwLH. Confronto con baseline Ramo A. Costruzione prompt Review 3.

*Sessione 4–5:* gestione concern Review 3 e chiusura Gate 3.

**REVIEW 3:** al completamento del training GNN, il PI sottomette al Claude Reviewer un prompt con: specifica della filtrazione di τ(x) e della costruzione del grafo topologico, correlazioni |r(GNN_j*, Ωm)| e |r(GNN_j*, σ₈)| sul test set, varianza spiegata aggiuntiva rispetto alla baseline TDA del Gate 1, correlazione |r(GNN_j*, w₀)| sul dataset nwLH. Il Reviewer valuta se il miglioramento sulla baseline è statisticamente robusto e se la correlazione con w₀ motiva il phantom crossing test. Le revisioni non-bloccanti devono essere risolte, giustificate o rimandate. Le revisioni bloccanti riaprono la Phase; alla terza il gate chiude in Scenario C.

**GATE 3:** correlazioni |r(GNN_j*, Ωm)| e |r(GNN_j*, σ₈)| sul test set superano i threshold. Miglioramento sulla baseline TDA documentato quantitativamente. Il Reviewer ha restituito PROCEED o NON-BLOCKING. Output: `results/phase3_gnn_correlations.json`, `phase3_gate_result.json`, `gate3_prior_v1.0.json`,`results/phase3_review.json` con parere positivo.

---

### 5.5 Phase 4 — Symbolic Regression

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Phase 4 |
| Durata (umana) | 2–3 giorni |
| Durata (macchina) | ~8 ore (20 run, Julia backend) |
| Sessioni stimate | ~2–3 |
| Input | Feature topologiche Phase 1 + componenti GNN Phase 3 |
| Output | `results/phase4_sr_expressions.json` + `results/phase4_review.json` |
| Handback richiesto? | Sì (multi-ora) |
| Budget | Locale — nessun costo cloud |

#### Input effettivi da Gate 3

| Dato | Path | Formato |
|---|---|---|
| Embedding j* LHC (1600 train + 400 test) | estratto da `results/checkpoints/phase3_gnn_best.pt` | [2000, 32] float32 |
| Embedding j* nwLH (2000 campi) | idem | [2000, 32] float32 |
| Feature TDA Ramo A (LHC) | `results/phase1_fiducial_cache.npz` → `fvecs_lhc` | [2000, 8] float64 |
| Cosmologie LHC | `results/phase1_fiducial_cache.npz` → `cosmo_lhc` | [2000, 2] — (Ωm, σ₈) |
| Cosmologie nwLH | `results/phase1_fiducial_cache.npz` → `cosmo_nwlh` | [2000, 1] — (w₀) |
| Prior frozen | `prior/gate3_prior_v1.0.json` | — |

Split: stesso seed=42 di Phase 3 — 1600 train / 400 test per LHC. nwLH usato solo per valutazione finale su w₀, mai nel training SR.

#### Prerequisiti obbligatori all'apertura di Phase 4

Prima di eseguire qualsiasi run SR, devono essere completati i seguenti impegni aperti da Gate 3:

**R3-1 + R3-2 (priorità alta, ~10 min):** calcolo di r(ŷ_Ωm, Ωm_true) e r(ŷ_σ₈, σ₈_true) sul test set (correlazione del predetto vs vero — statistica corretta che sostituisce max|r| su 32 componenti). Ricalcolo varianza aggiuntiva vs Ramo A su base equivalente: stesso test set, stessa statistica, Ramo A valutato con regressore Ridge sulle 8 feature TDA. Script standalone, usa il checkpoint GNN senza retraining. Output: `results/phase4_opening_stats.json`.

**R3-3 (priorità critica, ~30 min GPU):** test MMD (Maximum Mean Discrepancy) tra distribuzione di j* per w₀<−1.0 vs w₀>−1.0 sui 2000 campi nwLH, usando il checkpoint GNN esistente. Prerequisito obbligatorio per apertura Phase 6. Se MMD non è significativamente diverso da zero, documentare come risultato scientifico negativo prima di procedere. Output: `results/phase4_mmd_w0.json`.

Se R3-1/R3-2/R3-3 producono risultati anomali (r(ŷ, y_true) << 0.80, MMD=0), comunicare al PI prima di avviare i run SR.

#### Variabili di input per la Symbolic Regression

Il target primario di Phase 4 è w₀ — il parametro di dark energy, obiettivo finale di CAUCHY. Il training SR usa il dataset nwLH (w₀∈[−1.30,−0.70], altri parametri al fiduciale).

**Feature pool di input (due Rami combinati):**

Ramo A — 8 feature TDA scalari da Phase 1:
`b1_peak_pos`, `b1_peak_height`, `b1_fwhm`, `b1_integral`, `b2_max_count`, `b2_mean_persistence`, `b2_high_persist`, `b0_at_mean`

Ramo B — componenti di j* [32] da Phase 3. Non tutte le 32 componenti sono ugualmente informative. Prima del SR: selezione delle top-K componenti per |r(j*_k, w₀)| sui 2000 campi nwLH. K determinato empiricamente: include le componenti con |r|>0.05 o, in alternativa, le prime K che spiegano il 90% della varianza di w₀ predetta dal GNN (PCA su j* in direzione w₀).

**Nota:** con |r(j*, w₀)|=0.031 osservato in Gate 3 (correlazione lineare per-campo), le componenti di j* più correlate con w₀ potrebbero avere segnale debole. Il SR non è vincolato alla correlazione lineare — può trovare relazioni non-lineari. Se dopo la selezione nessuna componente di j* ha |r|>0.05 con w₀, procedere con le sole feature Ramo A più le top-3 componenti di j* per |r|.

#### Configurazione PySR

| Parametro | Valore | Autorità |
|---|---|---|
| Backend | Julia 1.10, PySR 0.18 | environment.yml, Methodology §4.2 |
| N run indipendenti | 20 | Methodology §4.2 |
| Seed per run i | base_seed + i×100 (base_seed=42) | coerenza con pipeline |
| Target primario | w₀ (nwLH) | Methodology §4.1 |
| Target secondario | (Ωm, σ₈) su LHC | confronto cross-ramo |
| Metrica di selezione modello | AIC/BIC | Methodology §4.2 — previene overfitting |
| Operatori binari | +, −, ×, ÷, ^2, ^3 | Methodology §4.2 |
| Operatori unari | sqrt, log, exp, abs | Methodology §4.2 |
| maxsize | 20 nodi | limite complessità — interpretabilità fisica |
| parsimony_coefficient | da calibrare in Sessione 1 (range 0.001–0.01) | Methodology §4.2 |
| Iterazioni per run | 1000 | bilanciamento qualità/tempo |
| Test set held-out | 20% nwLH (seed=42) | coerenza con Phase 3 |

Il parsimony_coefficient controlla il trade-off complessità/accuratezza. Un valore troppo basso produce espressioni sovra-adattate non generalizzabili; troppo alto produce espressioni banali (es. costanti). Calibrazione: eseguire 3 run pilota con parsimony∈{0.001, 0.005, 0.01} e scegliere il valore che produce la complessità media più bassa compatibile con R²≥0.50 sul test set.

#### Analisi di stabilità e selezione espressione

Per ogni run SR si registra: l'espressione simbolica ottimale (forma algebrica normalizzata), il suo R² sul test set held-out, la complessità (numero di nodi dell'albero), il valore AIC/BIC.

**Normalizzazione delle espressioni:** due espressioni algebricamente equivalenti (es. a×b vs b×a) devono essere considerate identiche. Usare forma canonica: ordinamento lessicografico dei termini commutativi, espansione delle potenze.

**Istogramma di frequenza:** costruito sulla forma canonica delle espressioni — mostra quante delle 20 run convergono alla stessa espressione. Un'espressione "stabile" appare in ≥10/20 run (50%).

**Selezione finale:** l'espressione con maggiore frequenza e R²≥0.50 sul test set. Se più espressioni hanno la stessa frequenza, selezionare quella con AIC/BIC inferiore.

#### Gate 4 — Threshold e criteri

Autorità: `CAUCHY_Execution_Parameters.md §6`, Methodology §4.3.

| Criterio | Threshold | Note |
|---|---|---|
| Stabilità espressione | ≥ 10/20 run (50%) | Threshold verbatim da Methodology §4.3 |
| R² sul test set held-out (soglia minima) | ≥ 0.50 | Relazione parziale documentabile |
| R² sul test set held-out (soglia forte) | ≥ 0.70 | Espressione fisicamente interpretabile e pubblicabile |
| Risultato negativo | documentato esplicitamente | se nessuna espressione raggiunge stabilità ≥50% o R²≥0.50 |

Il gate si chiude positivamente con R²≥0.50 e stabilità≥50%, o negativamente con documentazione esplicita del risultato negativo. Entrambi gli esiti sono scientificamente validi.

**Scenario risultato negativo:** se dopo 20 run nessuna espressione è stabile, documentare: (a) distribuzione delle espressioni trovate; (b) ipotesi diagnostica (segnale w₀ insufficiente per SR, relazione non algebricamente semplice, feature input non ottimali); (c) implicazioni per Phase 5-6. Il Reviewer di Phase 4 deve valutare il risultato negativo con lo stesso rigore del positivo.

#### Mappa sessioni Phase 4

**Sessione 1 (apertura):**
- Chiusura impegni R3-1, R3-2, R3-3 (script `src/phase4_opening.py`)
- Selezione feature input per SR (analisi |r(j*_k, w₀)| su nwLH)
- Calibrazione parsimony_coefficient con 3 run pilota
- Configurazione PySR e verifica Julia backend

**Sessione 2 (esecuzione):**
- 20 run SR completi su target w₀ (nwLH)
- 20 run SR su target (Ωm, σ₈) (LHC) — confronto cross-ramo
- Costruzione istogramma di frequenza e analisi stabilità
- Selezione espressione candidata

**Sessione 3 (analisi e chiusura):**
- Interpretazione fisica dell'espressione stabile (o documentazione risultato negativo)
- Costruzione prompt Review 4
- Gestione concern Reviewer e chiusura Gate 4

**REVIEW 4:** al completamento dei 20 run SR, il PI sottomette al Claude Reviewer un prompt con: variabili di input e target, configurazione PySR, istogramma di frequenza delle espressioni tra i 20 run, espressione più frequente con R² sul test set held-out, interpretazione fisica proposta. Il Reviewer valuta stabilità, plausibilità fisica, e adeguatezza della penalizzazione della complessità. Le revisioni non-bloccanti devono essere risolte, giustificate o rimandate. Le revisioni bloccanti riaprono la Phase; alla terza il gate chiude in Scenario C con risultato negativo documentato.

**GATE 4:** espressione stabile in ≥ 10/20 run con R² > threshold, oppure risultato negativo documentato esplicitamente. Il Reviewer ha restituito PROCEED o NON-BLOCKING. Output: `results/phase4_sr_expressions.json`, `phase4_gate_result.json`, `gate4_prior_v1.0.json`, `results/phase4_review.json` con parere positivo.

---

### 5.6 Phase 5 — Phantom Crossing Injection Test

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Phase 5 |
| Durata (umana) | 1–2 settimane |
| Durata (macchina) | ~1 settimana (retraining + eval) |
| Sessioni stimate | ~5–6 |
| Input | Campi nwLH + HOD AbacusSummit 9 parametri |
| Output | `results/phase5_phantom_test.json` + `results/phase5_review.json` |
| Handback richiesto? | **Sì — questo è il test scientifico centrale** |
| Budget | ~$300–500 |
| Vincolo hard | HOD deve essere AbacusSummit 9 parametri con marginalizzazione MCMC |

#### Specifica L2 — Phase 5: Phantom Crossing Injection Test

Questa è la fase scientificamente più importante del progetto. Il suo risultato determina la venue del paper e costituisce il claim principale di CAUCHY: la pipeline riesce a rilevare il phantom crossing (w₀ ≠ −1) nei campi di densità della materia dopo marginalizzazione su Ωm, σ₈ e parametri HOD?

##### Input effettivi da Gate 4

| Dato | Path | Formato |
|---|---|---|
| Campi nwLH preprocessati | `data/processed/phase0_fields/nwlh/{i}/df_m_128_PCS_z=0.npy` | [128,128,128] float64 |
| Cosmologie nwLH | `latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt` col.6 | w₀ ∈ [−1.30, −0.70] |
| Feature TDA Ramo A (nwLH) | `results/phase1_fiducial_cache.npz` → `fvecs_nwlh` | [2000, 8] float64 |
| Checkpoint GNN (Ramo B) | `results/checkpoints/phase3_gnn_best.pt` | frozen — best epoch 171 |
| Prior frozen | `prior/gate4_prior_v1_0.json` + `prior/gate3_prior_v1_0.json` | — |

##### Disegno del test (Methodology §5.1)

La domanda scientifica è: r(pipeline_output, w₀ | Ωm, σ₈) — la correlazione parziale con w₀ dopo aver rimosso la variazione dovuta a Ωm e σ₈ — è significativamente diversa da zero?

**Valori di injection** (Methodology §5.1, corrispondenti a regime DESI DR2):
- w₀ = −0.7 (quintessenza moderata, regime preferito DESI DR1)
- w₀ = −1.0 (ΛCDM, null injection)
- w₀ = −1.3 (phantom forte)

La significatività è calcolata via permutation test con N=1000 shuffles delle label w₀:
σ = (|r_obs| − mean(r_null)) / std(r_null)

Il test è eseguito separatamente per **Ramo A** (feature TDA scalari) e **Ramo B** (embedding j* dal GNN).

##### Modello HOD e marginalizzazione (Methodology §5.2) — VINCOLO HARD

Questa è la lezione centrale dell'errore v3.x: un HOD fisso assorbe il segnale dipendente da w attraverso i suoi parametri liberi. La specifica è non negoziabile:

- **Modello HOD:** AbacusSummit a 9 parametri (framework SimBIG/Hahn 2023). Include parametri standard Zheng 2007 (centrali + satelliti) più estensioni per assembly bias (dipendenza da concentrazione e epoca di formazione dell'alone), velocità e concentrazione dei satelliti.
- **Marginalizzazione:** MCMC sui 9 parametri HOD con prior flat entro i range fisici. I vincoli su w₀ sono derivati dopo aver integrato sulla distribuzione HOD.
- **Diagnostiche di convergenza obbligatorie:** R̂ Gelman-Rubin < 1.01 per tutti i parametri; ESS > 200 per catena; trace plots loggati nel JSON di output.
- **Test di robustezza HOD (obbligatorio per Gate 5):** ripetere con Zheng 2007 a 5 parametri. Se il segnale su w₀ cambia > 1σ, la dipendenza dall'HOD è documentata come sistematica dominante — risultato pubblicabile ma riduce la venue target.

##### Confronto con baseline P(k) (Methodology §5.3)

Obbligatorio per Gate 5 e per OC-1 (impegno pre-submission elevato a CRITICO in Phase 4). Stesso permutation test eseguito su P(k) degli stessi 2000 campi nwLH. Output: r_CAUCHY vs r_Pk con significatività per entrambi. Se r_CAUCHY > r_Pk statisticamente, CAUCHY porta informazione aggiuntiva. Questo confronto risolve anche OC-1.

##### Prerequisiti obbligatori all'apertura di Phase 5

Prima di qualsiasi sviluppo di script, il PI deve confermare:

**P5-1 — Dataset HOD disponibile:** i campi nwLH con popolazioni galattiche HOD AbacusSummit sono disponibili localmente, o devono essere generati? Se devono essere generati, pianificare il tempo di calcolo (~$300–500 stimati in Execution Design) prima di procedere.

**P5-2 — Verifica MCMC toolchain:** emcee o equivalente installato nell'ambiente cauchy. Verificare: `python -c "import emcee; print(emcee.__version__)"`. Se assente: `pip install emcee`.

**P5-3 — Verifica prior frozen:** gli assert sui prior Gate 3 e Gate 4 devono passare all'avvio di ogni script Phase 5.

**P5-4 — Strategia Ramo B:** il checkpoint GNN (best epoch 171) è addestrato su materia oscura pura a z=0. Se i campi nwLH per il phantom test includono tracciatori galattici (HOD), j* estratto da campi di materia oscura non è applicabile direttamente ai campi galattici. Il PI deve decidere:
  - Opzione A: Ramo B sul campo di materia oscura sottostante (dark matter only), Ramo A sulle galassie HOD.
  - Opzione B: retraining GNN sui campi galattici HOD (~3–5h GPU). Garantisce adattamento. Attiva il monitoring R3-4 nel loop di training.
  Il PI decide in Sessione 1 dopo analisi preliminare.

##### Piano di sessioni Phase 5 (stima ~5–6 sessioni)

**Sessione 1:**
1. PI conferma P5-1 (disponibilità dataset HOD) e P5-4 (strategia Ramo B).
2. Claude genera `src/phase5_sanity_check.py` — verifica integrità campi HOD, correlazione parziale preliminare r(feature_TDA, w₀ | Ωm, σ₈) su campione di 100 campi nwLH (no HOD, dark matter only) come lower bound del segnale atteso.
3. Concordare prior MCMC per i 9 parametri HOD (range fisici AbacusSummit).

**Sessione 2:**
Implementazione `src/phase5_hod_mcmc.py`. Marginalizzazione MCMC sui 9 parametri HOD. Diagnostiche di convergenza. Stima tempo run completo su RTX 5060 Ti.

**Sessione 3:**
Run MCMC completo su 2000 campi nwLH. PI riporta catene e diagnostiche.
Claude analizza convergenza e calcola r_parziale per Ramo A.

**Sessione 4:**
Ramo B: estrazione j* (dark matter o retraining HOD, dipende da P5-4).
Calcolo r_parziale per Ramo B.
Permutation test (N=1000) per entrambi i rami.

**Sessione 5:**
Test robustezza HOD (Zheng 2007 vs AbacusSummit).
Confronto r_CAUCHY vs r_Pk (baseline P(k)).
Costruzione prompt Review 5.

**Sessione 6 (se necessario):**
Gestione concern Review 5. Chiusura Gate 5.
Generazione `phase5_gate_result.json`, `gate5_prior_v1_0.json`.

##### Gate 5 — Threshold e venue (Methodology §P3, Execution Parameters §7)

| Criterio | Condizione | Venue target |
|---|---|---|
| σ ≥ 2.0 (Ramo A o B) | phantom crossing rilevato | Nature Astronomy / PRL |
| 1.0 ≤ σ < 2.0 | evidenza marginale | Physical Review D |
| σ < 1.0 | non-rilevazione | JCAP (upper bound documentato) |
| Test robustezza HOD | eseguito e documentato | obbligatorio per qualsiasi venue |
| Confronto σ_CAUCHY vs σ_Pk | eseguito e documentato | obbligatorio per qualsiasi venue |
| Reviewer verdict | PROCEED o NON-BLOCKING | obbligatorio per qualsiasi venue |

Tutti e tre gli scenari di Gate 5 sono pubblicabili (Methodology §1.4, Scenario A/B/C).

##### Open issues rilevanti da fasi precedenti

- **OC-1 CRITICO (da Phase 4):** il confronto r_CAUCHY vs r_Pk in Phase 5 risolve OC-1. Priorità critica — da completare in Phase 5, non rimandare.
- **R4-2:** narrativa Ramo B prospettica — il risultato di Phase 5 su Ramo B è il dato definitivo per questa dichiarazione.
- **R3-5:** ablation β₁ vs β₁+β₂ — eseguibile come sotto-analisi in Phase 5 senza costo aggiuntivo (stessi campi, stessa pipeline).
- **R²(σ₈)=0.987 Ramo A:** verificare se persiste quando si restringe il range LHC a σ₈ ∈ [0.70, 0.90] come sanity check (sollevato dal Reviewer Phase 4).

**REVIEW 5:** al completamento del phantom crossing injection test, il PI sottomette al Claude Reviewer un prompt con: significatività σ per ogni valore di injection (Ramo A e Ramo B separatamente), risultati del test di robustezza HOD (Zheng 2007 vs AbacusSummit), confronto σ_CAUCHY vs σ_Pk, diagnostiche di convergenza MCMC, distribuzione delle correlazioni null dal permutation test. Il Reviewer valuta la correttezza della residualizzazione, l'adeguatezza della marginalizzazione HOD, e l'equità del confronto con la baseline. Le revisioni non-bloccanti devono essere risolte, giustificate o rimandate prima della submission del preprint. Le revisioni bloccanti riaprono la Phase; alla terza il gate chiude in Scenario C.

**GATE 5 (determina la venue):** significatività σ documentata per tutti i valori di injection. Test robustezza HOD eseguito. Confronto con baseline P(k) documentato. Venue: σ ≥ 2.0 → Nature Astronomy; 1.0 ≤ σ < 2.0 → PRD; σ < 1.0 → JCAP. Il Reviewer ha restituito PROCEED o NON-BLOCKING con tutte le revisioni assegnate. Output: `results/phase5_phantom_test.json`, `phase5_gate_result.json`, `gate5_prior_v1.0.json`, `results/phase5_review.json` con parere positivo.

---

### 5.6bis Phase 5bis — Test di Degenerazione IDE/CPL

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Fase 5bis |
| Source addendum | `CAUCHY_Literature_April2026_Update.md` §3 |
| Durata (umana) | 3–5 giorni |
| Durata (macchina) | < 1 giorno |
| Sessioni stimate | 2–3 |
| Input | Cosmologie nwLH (`latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt`) + valori di significatività σ da Gate 5 |
| Output | `results/phase5bis_Hz_degeneracy.json`, `results/phase5bis_IDE_mapping.json`, `results/phase5bis_growth_factor.json`, `results/phase5bis_framing.md` + `results/phase5bis_review.json` |
| Handback richiesto? | Sì — Reviewer deve approvare la deliberazione O5b-5 |
| Budget | $0 (CPU locale) |
| Vincolo hard | Phase 6 non si apre fino a Gate 5bis chiuso (PASS_CONSERVATIVE o PASS_AGGRESSIVE) |

#### Specifica L2 — Phase 5bis: Test di Degenerazione IDE/CPL

Phase 5bis è un'analisi numerica/perturbativa lineare che documenta la degenerazione di background tra phantom crossing CPL e cosmologie IDE quintessenza non interagenti, in risposta alla letteratura aprile 2026 (Neumann, Videla & Araya 2026; Artola, Lazkoz & Salzano 2026; Wang & Wang 2026; Petri et al. 2026; Ong et al. 2026). Non richiede nuove simulazioni N-body. La motivazione completa, i prerequisiti e la specifica scientifica sono in `CAUCHY_Literature_April2026_Update.md` §3; questa sezione è la specifica L2 operativa.

##### Input effettivi da Gate 5

| Dato | Path | Formato |
|---|---|---|
| Cosmologie nwLH | `latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt` | 2.000 righe × 7 colonne (Ωm, Ωb, h, n_s, σ₈, M_ν, w₀) |
| Significatività Phase 5 | `results/phase5_phantom_test.json` | σ_RamoA, σ_RamoB, σ_Pk |
| Prior frozen | `prior/gate5_prior_v1_0.json` | — |

##### Output e specifiche

**O5b-1 — Mappa degenerazione H(z).** Script `src/phase5bis_hz_degeneracy.py`. Calcolo di H(z) per z ∈ [0, 3] su griglia di 200 punti per ciascuna delle 2.000 cosmologie nwLH. Costruzione della matrice 2.000×2.000 di scostamento massimo |ΔH/H|_max. Identificazione delle coppie con scostamento ≤ 0.5% (default; configurabile). Output: `results/phase5bis_Hz_degeneracy.json` con schema:

```json
{
  "schema_version": "1.0",
  "tolerance": 0.005,
  "n_cosmologies": 2000,
  "z_grid": [0.0, ..., 3.0],
  "degenerate_pairs": [
    {"i": 17, "j": 423, "max_DH_over_H": 0.0034, "w0_i": -1.27, "w0_j": -0.93}
  ],
  "metadata": {"git_commit": "...", "timestamp": "..."}
}
```

**O5b-2 — Mappa IDE-equivalente.** Script `src/phase5bis_ide_mapping.py`. Per ogni cosmologia nwLH con w₀ ≠ −1, ricerca dei parametri (β, w₀_de) con w₀_de > −1 (vincolo non-fantasma) di un modello IDE Q = β H ρ_de che riproduce la stessa H(z) entro la tolleranza di O5b-1. Implementazione delle formule analitiche di Neumann, Videla & Araya 2026 §2.2 con `scipy.special.gammainc`/`gammaincc`. Verifica nei casi limite (β = 0, wₐ = 0, w₀ = −1) prima dell'esecuzione completa. Output: `results/phase5bis_IDE_mapping.json` con schema:

```json
{
  "schema_version": "1.0",
  "n_cosmologies_mapped": 1834,
  "n_cosmologies_unmappable": 166,
  "mapping": [
    {"cosmology_i": 17, "w0_CPL": -1.27, "wa_CPL": 0.0,
     "beta_IDE": 0.123, "w0_de_IDE": -0.94, "max_DH_over_H_residual": 0.0021}
  ],
  "metadata": {"reference": "Neumann, Videla, Araya 2026 §2.2"}
}
```

**O5b-3 — Sezione "Background degeneracy" del paper.** Drafting di paragrafo per la discussion del paper finale, citante Petri 2026, Neumann 2026, Artola 2026. Output: `results/phase5bis_paper_section.md` (paragrafo da inserire in §5 della discussion).

**O5b-4 — Differenza perturbativa ΔD/D.** Script `src/phase5bis_growth_factor.py`. Integrazione numerica delle equazioni di crescita lineare modificate (Gavela et al. 2009) per i modelli IDE-equivalenti di O5b-2. Calcolo di D(z) da z = 0 a z = 3. Confronto con D(z) del CPL nominale per ciascuna coppia. Output: `results/phase5bis_growth_factor.json` con schema:

```json
{
  "schema_version": "1.0",
  "n_cosmologies": 1834,
  "z_grid": [0.0, ..., 3.0],
  "delta_D_over_D": [
    {"cosmology_i": 17, "z": 0.5, "delta_D_over_D": 0.0087}
  ],
  "summary": {
    "max_delta_D_over_D": 0.012,
    "median_delta_D_over_D_at_z0p5": 0.0034,
    "fraction_with_delta_D_above_1pct": 0.18
  }
}
```

**O5b-5 — Deliberazione framing del paper.** Documento `results/phase5bis_framing.md` con motivazione esplicita della scelta tra:

- **Opzione conservativa:** *"Topological field-level constraints on background expansion histories of the dark sector"* — venue PRD/JCAP. Sempre disponibile.
- **Opzione aggressiva:** *"Topological detection of dynamical dark energy via field-level persistent homology"* — venue Nature Astronomy/PRL. Disponibile solo se max(ΔD/D) > 1% in O5b-4 *e* significatività Phase 5 σ ≥ 2.0.

La deliberazione include: (a) valore numerico di max(ΔD/D); (b) σ raggiunto in Phase 5; (c) scelta motivata; (d) bozza di abstract di una pagina coerente con la scelta; (e) lista delle limitazioni da dichiarare nel paper.

##### Prerequisiti obbligatori all'apertura di Phase 5bis

**P5b-1 — Phase 5 chiusa.** `results/phase5_gate_result.json` esiste con `status` ∈ {`PASS`, `FAIL_NEGATIVE`}. Il valore di significatività σ è input per la decisione di scope di Methodology §5bis.3.

**P5b-2 — Codice analitico per IDE+CPL testato.** Implementazione delle formule di Neumann, Videla & Araya 2026 §2.2 in `src/phase5bis_ide_analytics.py`, con test unitari sui casi limite:
- `test_beta_zero_recovers_CPL()` — β = 0 → soluzione CPL pura
- `test_wa_zero_recovers_constant_w()` — wₐ = 0 → IDE con w costante
- `test_LCDM_with_beta()` — w₀ = −1, wₐ = 0, β ≠ 0 → IDE+ΛCDM modificato

I test devono passare prima dell'esecuzione di O5b-2.

**P5b-3 — Equazioni di crescita modificate testate.** Implementazione in `src/phase5bis_growth_factor.py` delle equazioni di Gavela et al. 2009 con test:
- `test_no_interaction_recovers_LCDM_growth()` — β = 0 → D(z) standard ΛCDM
- `test_continuity_at_today()` — D(z=0) = 1 per normalizzazione

##### Piano di sessioni Phase 5bis (stima 2–3 sessioni)

**Sessione 1:**
1. PI conferma chiusura Gate 5 e fornisce valori σ_RamoA, σ_RamoB, σ_Pk.
2. Decisione su scope: full vs ridotto (Methodology §5bis.3) sulla base di σ.
3. Claude genera `src/phase5bis_ide_analytics.py` con test unitari P5b-2.
4. Claude genera `src/phase5bis_hz_degeneracy.py` (O5b-1).
5. PI esegue O5b-1 in locale (~1 ora CPU).

**Sessione 2:**
1. Analisi dei risultati O5b-1.
2. Claude genera `src/phase5bis_ide_mapping.py` (O5b-2) e `src/phase5bis_growth_factor.py` (O5b-4) con test P5b-3.
3. PI esegue O5b-2 e O5b-4 in locale (~3–5 ore CPU complessive).

**Sessione 3:**
1. Analisi dei risultati O5b-2 e O5b-4.
2. PI delibera Opzione conservativa vs aggressiva sulla base di max(ΔD/D) e σ Phase 5.
3. Claude genera bozza di O5b-3 (paragrafo paper) e di O5b-5 (motivazione framing).
4. PI revisiona, finalizza, archivia.
5. Costruzione prompt Review 5bis e sottomissione al Claude Reviewer.

##### Gate 5bis — Threshold

Il Gate 5bis è documentativo. Esiti:

| Criterio | Condizione | Esito |
|---|---|---|
| O5b-1 archiviato | `phase5bis_Hz_degeneracy.json` esiste con schema valido | Necessario |
| O5b-2 archiviato (full scope) | `phase5bis_IDE_mapping.json` esiste; opzionale se Scenario C | Condizionale |
| O5b-3 prodotto | `phase5bis_paper_section.md` esiste, cita Neumann/Petri/Artola | Necessario |
| O5b-4 archiviato (full scope) | `phase5bis_growth_factor.json` esiste; opzionale se Scenario C | Condizionale |
| O5b-5 deliberato | `phase5bis_framing.md` esiste con scelta motivata | Necessario |
| Reviewer verdict | PROCEED o NON-BLOCKING | Necessario |

Esiti finali:
- **PASS_CONSERVATIVE:** Phase 6 autorizzata, paper con framing conservativo.
- **PASS_AGGRESSIVE:** Phase 6 autorizzata, paper con framing aggressivo (max(ΔD/D) > 1% E σ_Phase5 ≥ 2.0).
- **FAIL_INCOMPLETE:** Phase 6 non autorizzata.

**REVIEW 5bis:** al completamento di Phase 5bis, il PI sottomette al Claude Reviewer un prompt con: (1) tabella riassuntiva dei 4 output O5b-1/2/4 con valori numerici principali (frazione di coppie degeneri, frazione mappabili in IDE non-fantasma, distribuzione di max(ΔD/D)); (2) il documento di deliberazione O5b-5 con motivazione; (3) la bozza di paragrafo O5b-3. Il Reviewer valuta: (a) correttezza dell'implementazione delle formule analitiche di Neumann; (b) appropriatezza dello scope (full vs ridotto) data la significatività di Phase 5; (c) coerenza interna tra O5b-4 e la scelta di framing in O5b-5; (d) adeguatezza della bozza di paragrafo paper rispetto alle citazioni richieste.

**GATE 5bis:** tutti gli output O5b-1 ÷ O5b-5 prodotti (con scope condizionale per Scenario C). Reviewer verdict PROCEED o NON-BLOCKING. Output: `results/phase5bis_gate_result.json`, `prior/gate5bis_prior_v1_0.json`, `results/phase5bis_review.json`. Apertura Phase 6 autorizzata.

##### Open Issues consolidate da addendum 2026-05-05

- **OC-2 (Pre-submission):** documentazione esplicita della sensibilità del segnale topologico a H(z)/D(z) anziché alla natura fondamentale dell'EoS. **Risolto** dall'esecuzione di O5b-3 e O5b-5.
- **OC-3 (Pre-submission, nuovo):** revisione `.md` di Wang & Wang 2026 da archiviare in `literature/tier2/StateOfArt/`. Lavoro autonomo eseguibile in parallelo a Phase 5bis.
- **OC-4 (Pre-submission, nuovo):** in Phase 6 (se DESI reale) eseguire triplo confronto baseline (Karim 2025 / DES-Dovekie / IDE-degenerate Petri 2026). Registrato nella tabella sistematiche §6.2 del Methodology.

---

### 5.7 Phase 6 — Applicazione a DESI DR2 o Submission Quijote

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §P3, Phase 6 |
| Durata (umana) | 1–2 mesi (DESI) o immediata (Quijote) |
| Decision point | Accesso DESI DR2 disponibile? Branch sulla risposta |
| Handback richiesto? | Sì (forward model training è costoso) |

**Stato di accesso:** DESI DR2 disponibile. Il branch "DESI reale" è attivo.
Gate 5bis chiuso PASS_CONSERVATIVE (2026-05-07); Phase 6 formalmente autorizzata.

##### Lavoro preparatorio già eseguito (pre-Phase 6 formale)

Prima dell'apertura ufficiale di Phase 6, cinque script di preparazione sono stati
prodotti e validati. I risultati sono canonici e tracciabili.

**Script 1 — `src/phase6_bgs_voxelize.py`**
Converte i cataloghi FITS DESI BGS DR1 in campi di densità 128³ su griglia cartesiana
comovente (pesatura FKP, assegnazione CIC, smoothing Gaussiano R=5 Mpc/h, σ=0.32 px).
Cosmologia fiduciale Planck 2018. Risultati canonici:

| Regione | Galassie | Randoms | Box (Mpc/h) | Fill survey | δ_std |
|---|---|---|---|---|---|
| NGC | 217,614 | 13.2M | 1997.4 Mpc/h | 14.7% | 1.653 |
| SGC | 82,429 | 5.4M | 1904.5 Mpc/h | 8.2% | 2.078 |

Nota: σ_smooth=0.32 px per NGC (sub-pixel). Il sensitivity check R=5 vs R=10 Mpc/h
deferred da Phase 1 rimane aperto e va eseguito in Phase 6 (O6-4).

**Script 2 — `src/phase6_bgs_tda.py`**
Estrae le 8 feature TDA dai campi BGS voxelizzati con la convenzione birth/death v3
(ν_birth=−col0, ν_death=−col1) e bootstrap jackknife su 20 patch spaziali.
Feature primaria b2_mean_persistence: NGC=0.459±0.005 (1.1%), SGC=0.491.

**Script 3 — `src/phase6_mock_calibration.py`**
Calcola le feature TDA su 2000 campi nwLH a z=0.5 (snapnum=3, R_smooth=5 Mpc/h),
con n_gal_target=186,022 (densità target DESI BGS NGC). Distribuzione mock di
riferimento: b2_mean_persistence mean=0.292, std=0.028, range=[0.122, 0.340].

**Script 4 — `src/phase6_partial_corr.py`**
Confronto DESI vs distribuzione mock combinata (z=0 + z=0.5). Risultato principale:

| Metrica | Valore | Note |
|---|---|---|
| b2_DESI NGC | 0.459 ± 0.005 | Feature primaria |
| Mock z=0 mean | 0.239 | range [0.207, 0.316] |
| Mock z=0.5 mean | 0.292 | range [0.247, 0.332] |
| Discrepanza vs z=0 | +92% | — |
| Discrepanza vs z=0.5 | +57% | — |
| Percentile DESI nel mock combined | 100% | fuori range |
| **z-score vs combined mock** | **+5.40σ** | **citabile** |
| Residuo dopo controllo n_gal | +20.20σ | lower bound qualitativo non citabile |

Il valore +5.40σ è il risultato citabile. Il residuo +20.20σ post-controllo n_gal è
sovrastimato perché il controllo usa n_valid_voxels (308K) invece di n_gal reale (217K),
con estrapolazione fuori dal range mock (n_gal~900K); va trattato come lower bound
qualitativo finché non viene eseguito O6-2.

**Script 5 — `src/phase6_power_spectrum_baseline.py`**
Chiusura formale OC-1: confronto TDA vs P(k) su 2000 mock + DESI NGC.

| Metrica | σ |
|---|---|
| TDA b2_mean_persistence (singola feature) | 3.69σ |
| P(k) combinazione 8 feature | 3.37σ |
| TDA combinazione OLS 6 feature | 4.12σ (adattivo, qualificato) |
| TDA conservativo (controllo n_gal) | 3.08σ |
| Guadagno TDA vs P(k) singola feature | +9% |
| Guadagno TDA vs P(k) combinazione | +22% (adattivo) |

OC-1 parzialmente chiuso (+9% su feature singola citabile). Chiusura formale richiede
confronto con regressore P(k) addestrato (R5-3, pre-submission).

##### Specifica operativa L2 — output rimanenti di Phase 6

I seguenti output non sono ancora stati prodotti e costituiscono il corpo di Phase 6:

**O6-1 — Sistematiche tabella §6.2:** per ogni voce della tabella sistematiche del
Methodology (smoothing sensitivity R=5 vs R=10, sensitivity al tracer, cross-validazione
BOSS DR12, forward model vs P(k) osservato), variazione del segnale b2_mean_persistence
documentata in `results/phase6_systematics.json`. Threshold: variazioni < 1σ per
sistematiche non dominanti.

**O6-2 — Controllo n_gal corretto:** ricalcolo del residuo dopo partial correlation
usando n_gal=217,614 (galassie reali) come variabile di controllo invece di
n_valid_voxels. Questo sostituisce il risultato provvisorio +20.20σ con un valore
difendibile. Candidato a diventare la stima σ_DESI definitiva.

**O6-3 — Confronto triplo baseline (OC-4):** confronto b2_mean_persistence DESI contro
le previsioni di tre modelli: (a) ΛCDM Quijote fiduciale, (b) best-fit DESI DR2 CPL
(Karim et al. 2025), (c) best-fit DES-Dovekie CPL. Output: `results/phase6_triple_baseline.json`.

**O6-4 — Smoothing sensitivity (deferred da Phase 1):** ricalcolo b2_mean_persistence
con R=10 Mpc/h (σ=1.28 px) su campi DESI e mock. Confronto con risultato R=5 Mpc/h.
Threshold: variazione < 0.5σ per non-dominanza.

**O6-5 — Regressore P(k) addestrato (R5-3):** addestramento di un regressore lineare
su feature P(k) con la stessa procedura di Ramo A. Confronto formale con b2_mean_persistence.
Chiusura definitiva OC-1.

##### Input effettivi

| Dato | Path | Formato |
|---|---|---|
| Catalogo DESI BGS NGC | FITS DR1 | Galassie + randoms |
| Catalogo DESI BGS SGC | FITS DR1 | Galassie + randoms |
| Campi voxelizzati | `results/phase6_bgs_fields_{NGC,SGC}.npy` | float64 128³ |
| Feature TDA DESI | `results/phase6_bgs_features.json` | 8 feature, 2 regioni |
| Feature TDA mock z=0.5 | `results/phase6_mock_features_z0p5.json` | 2000 campi × 8 feature |
| Feature P(k) mock | `results/phase6_pk_features.json` | 2000 mock × 8 feature |
| Prior frozen | `prior/gate5bis_prior_v1_0.json` | σ_primary=3.69, framing=CONSERVATIVE |

##### Impegni pre-submission bloccanti attivi

R5-1÷R5-5, R4-2_inherited (da fasi precedenti), C5bis-1 (documentare grid β IDE e
confermare residuo 0.51% come minimo globale per phantom w₀<−1.05).

**REVIEW 6:** al completamento dell'analisi sistematica su DESI DR2, il PI sottomette al Claude Reviewer un prompt con: variazioni numeriche del segnale topologico per ogni sistematica della tabella Methodology §6.2, risultati cross-validazione con BOSS DR12, test di sensibilità al tracciatore, validazione del modello forward contro lo spettro di potenza osservato. Il Reviewer valuta se le sistematiche sono controllate da non compromettere l'interpretazione fisica. Le revisioni non-bloccanti devono essere risolte, giustificate o rimandate. Le revisioni bloccanti riaprono la Phase; alla terza il gate chiude e il paper viene sottomesso con soli risultati Quijote.

**GATE 6:** tutti i test sistematici della tabella §6.2 eseguiti e documentati. Variazioni < 1σ per le sistematiche non dominanti, oppure dominanti identificate e trattate come risultato. Il Reviewer ha restituito PROCEED o NON-BLOCKING. Output: `results/phase6_systematics.json`, `phase6_gate_result.json`, `gate6_prior_v1.0.json`, `results/phase6_review.json` con parere positivo.

---

### 5.8 Phase 7 — Paper

| Aspetto | Valore |
|---------|--------|
| Methodology ref | §Part V, §5.3 |
| Output | `paper/main.tex`, pacchetto di submission |
| Venue target | Determinata dal Gate 5 |

Claude produce bozze di sezioni scientifiche. Il PI revisiona e finalizza. Il Claude Reviewer simula il referee formale prima della submission.

### 5.9 Fisher Analysis Cross-Phase

Eseguita alla fine di ogni Phase (specifica completa in Methodology §4.1). I risultati sono aggregati in `results/fisher_all_phases.json`. Il Claude Reviewer esamina i miglioramenti Fisher Phase-per-Phase.

---

## 6 — Schemi JSON Canonici

### 6.1 GateResult

File principale di ogni gate. Scritto in `results/phase<N>_gate_result.json`.

```json
{
  "schema_version": "2.0",
  "metadata": {
    "timestamp": "ISO8601",
    "git_commit": "sha1 (7–40 hex chars)",
    "python_version": "3.11.x",
    "numpy_seed": 42,
    "phase": "<int 0–7>",
    "gate_id": "GATE_<N>",
    "gate_passed": "<bool>",
    "frozen_prior_version": "v1.0 | v1.1 | v1.2",
    "deviations_from_protocol": "none | note esplicite"
  },
  "results": {},
  "gate_evaluation": {
    "criteria": [
      {"name": "<str>", "threshold": "<float|str>", "observed": "<float|str>", "passed": "<bool>"}
    ],
    "overall_passed": "<bool>"
  },
  "reviewer_verdict": {
    "verdict": "PROCEED | NON-BLOCKING | BLOCKING",
    "non_blocking_items": [
      {
        "concern": "<str>",
        "resolution": "resolved | justified | deferred",
        "resolution_note": "<str>"
      }
    ],
    "review_artifact_path": "results/phase<N>_review.json"
  },
  "notes": "deviazioni dal protocollo (Methodology §6.2)"
}
```

**Invarianti obbligatori:**

1. `gate_evaluation.overall_passed == AND(criteria[*].passed)` — validato prima della scrittura.
2. `gate_passed = true` è compatibile con `reviewer_verdict.verdict == "NON-BLOCKING"` solo se tutti gli item NON-BLOCKING hanno un campo `resolution` assegnato.
3. `gate_passed = true` è incompatibile con `reviewer_verdict.verdict == "BLOCKING"`.

### 6.2 FrozenPriorV{N} — one per gate, immutabile

Scritto in `prior/gate<N>_prior_v<K>.json`. Tracciato in git, mai modificato in-place.

```json
{
  "schema_version": "2.0",
  "gate_id": "GATE_<N>",
  "version": "v1.0 | v1.1 | v1.2",
  "frozen_at": "ISO8601",
  "frozen_by": "CAUCHY_Methodology v2.0 | Recalibration v1.1 | ...",
  "criteria": [
    {
      "name": "<str>",
      "expression": "<str>",
      "source": "<citation>",
      "source_artifact": "literature/tier1/<filename>.pdf",
      "source_page": "<int>"
    }
  ],
  "supersedes": "null | v1.0 | v1.1"
}
```

**Invarianti:**
1. `version == "v1.0"` iff `supersedes is null`.
2. `criteria` non-vuoto.

### 6.3 RecalibrationReport

Scritto in `results/recalibration_reports/gate<N>_recalibration_<K>.json` per ogni tentativo (K = 1 o 2). Scritto sia per esiti approvati che rigettati.

```json
{
  "schema_version": "2.0",
  "gate_id": "GATE_<N>",
  "prior_version_from": "v1.0",
  "prior_version_to": "v1.1",
  "recalibration_count_for_this_gate": "<int 1|2>",
  "observed_value": "<float>",
  "original_threshold": "<float>",
  "failure_magnitude": "<float ≥ 0>",
  "failure_gap_signed": "<float>",
  "diagnosis": {
    "candidate_causes": [
      {
        "cause": "<str>",
        "quantification": "<str>",
        "supports_observed": "<bool>",
        "confidence": "high | medium | low"
      }
    ],
    "selected_cause": "<str>"
  },
  "new_threshold": "<float>",
  "new_threshold_justification": "<str>",
  "asymmetric_recalibration_test": {
    "tested_in_other_regime": "<str>",
    "passes_test": "<bool>",
    "reviewer_verdict": "PROCEED | NON-BLOCKING | BLOCKING"
  },
  "reviewer_review_path": "results/gate<N>_recalibration_reviewer.json"
}
```

**Invariante:** `recalibration_count_for_this_gate ∈ {1, 2}`. Un terzo tentativo non può costruire un RecalibrationReport valido. Il PI deve documentare Scenario C.

### 6.4 SessionArtifact

Output terminale di ogni sessione. Scritto in `sessions/session_<N>_output.json`.

```json
{
  "schema_version": "2.0",
  "session_id": "session_<N>",
  "opened_at": "ISO8601",
  "closed_at": "ISO8601",
  "phase_context": "<int 0–7>",
  "session_purpose": "script_generation | result_analysis | review_prep | gate_evaluation",
  "input_artifacts": [
    {"path": "<str>", "checksum": "<SHA256 hex>", "purpose": "<str>"}
  ],
  "output_artifacts": [
    {"path": "<str>", "checksum": "<SHA256 hex>", "purpose": "<str>"}
  ],
  "next_action": "HUMAN_EXECUTION | REVIEW_SUBMISSION | GATE_EVALUATION | PHASE_COMPLETE",
  "next_artifact_expected": "null | <path>",
  "next_session_id": "null | session_<N+1>",
  "literature_notices": [
    {"arxiv_id": "<str>", "title": "<str>", "relevance": "<str>"}
  ],
  "progress_notes": "<str>"
}
```

### 6.5 ReviewerResponse

Output del Claude Reviewer. Scritto in `results/phase<N>_review.json` dal PI dopo la sessione di review.

```json
{
  "schema_version": "2.0",
  "phase": "<int 0–7>",
  "review_timestamp": "ISO8601",
  "prompt_submitted": "<path del prompt sottomesso al Reviewer>",
  "verdict": "PROCEED | NON-BLOCKING | BLOCKING",
  "concerns": [
    {
      "severity": "blocking | major | minor | info",
      "concern": "<str>",
      "suggested_remediation": "<str>"
    }
  ],
  "reasoning_summary": "<testo del ragionamento del Reviewer, ≥100 parole>",
  "canonical_objections_applied": [
    {
      "objection_id": "<str>",
      "applicability": "high | medium | low | n/a",
      "finding": "<str>"
    }
  ]
}
```

**Invariante:** `reasoning_summary` non-vuoto. Un review senza ragionamento non è accettabile.

---

## 7 — Repository Layout

```
cauchy/
├── README.md
├── CHANGELOG.md                    ← narrativo, curato dal PI
├── changelog_events.jsonl          ← eventi automatici di gate
├── environment.yml                 ← stack scientifico completo
├── pyproject.toml
├── CAUCHY_Execution_Parameters.md
├── CAUCHY_PreRewrite_Analysis.md
├── CAUCHY_Review_and_GATE.md
├── CAUCHY_Systematic_Methodology_v2.md
├── CAUCHY_Execution_Design_v2.md
│
├── literature/
│   ├── tier1/
│   │   ├── Abedi2025_RSD_PersistentHomology.pdf
│   │   ├── Capozziello2026_DESI_LymanAlpha_DDE.pdf
│   │   ├── Dai2026_IDE_HubbleEvolution.pdf
│   │   ├── Hahn2023_SIMBIG_Cosmology.pdf
│   │   ├── Karim2025_DESI_DR2_BAO.pdf
│   │   ├── Leclercq2025_FieldLevel_Inference.pdf
│   │   ├── Li2026_Holographic_DarkEnergy.pdf
│   │   ├── Prat2025_DESY3_PersistentHomology.pdf
│   │   └── Yip2024_PersistentHomology_Fisher.pdf
│   ├── tier2/
│   │   └── (read-on-demand)
│   └── index.json
│
├── prior/
│   ├── gate0_prior_v1.0.json
│   ├── gate1_prior_v1.0.json
│   ├── gate2_prior_v1.0.json
│   ├── gate3_prior_v1.0.json
│   ├── gate4_prior_v1.0.json
│   ├── gate5_prior_v1.0.json
│   └── gate6_prior_v1.0.json
│
├── data/
│   └── raw/
│       ├── boss_dr12
│       ├── desi_dr1
│       └── quijote
│
├── src/
│   ├── phase0_data_prep.py
│   ├── phase1_tda_baseline.py
│   ├── phase1_patch_cache.py ← aggiunge fvecs_lhc, fvecs_nwlh, lhc_cosmologies, nwlh_cosmologies alla cache e al baseline di Phase 1, prerequisiti di phase2_cnn.py
│   ├── phase2_cnn.py
│   ├── phase3_prerequisites.py ← Verifica obbligatoria degli impegni R2-3 e R2-4 prima di Gate 3
│   ├── phase3_gnn.py
│   ├── phase4_sr.jl
│   ├── phase5_phantom.py
│   ├── phase6_desi.py
│   └── fisher_analysis.py
│
├── prompts/
│   ├── reviewer_system_prompt.md   ← template system prompt per il Claude Reviewer
│   ├── phase0_development_prompt.md  ← system prompt per inizio sessione Claude di sviluppo fase
│   ├── phase0_review_answer.md ← Claude Reviewer answers
│   ├── phase0_review_prompt.md ← system prompt per il Claude Reviewer di fase
│   ├── phase1_development_prompt.md
│   ├── phase1_review_answer.md
│   ├── phase1_review_prompt.md
│   ├── phase1_development_prompt.md
│   ├── phase2_review_answer.md
│   ├── phase2_review_prompt.md
│   └── ...
│
├── results/
│   ├── phase0_data_manifest.json
│   ├── phase0_preprocessing_lock.json
│   ├── phase0_gate_result.json
│   ├── phase0_review.json
│   ├── phase1_fiducial_cache.npz
│   ├── phase1_tda_baseline.json
│   ├── phase1_gate_result.json
│   ├── phase1_review.json
│   ├── phase2_cnn_diagnostic.json
│   ├── phase2_gate_result.json
│   ├── phase2_review.json
│   ├── ...
│   ├── phase5_phantom_test.json    ← RISULTATO CHIAVE
│   ├── phase5_gate_result.json
│   ├── phase5_review.json
│   ├── fisher_all_phases.json
│   └── recalibration_reports/
│       ├── gate1_recalibration_1.json
│       └── ...
│
├── sessions/
│   ├── session_01_output.json
│   ├── session_02_output.json
│   └── ...
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_tda_visualization.ipynb
│   ├── 03_model_diagnostics.ipynb
│   └── 04_results_figures.ipynb
│
└── paper/
    ├── main.tex
    └── figures/
```

**Git workflow:**
- Ogni gate passato genera un commit + tag: `gate_N_passed_v<K>`
- Ogni ricalibrzione genera un branch: `recalibration/gate_N_attempt_K`
- I file di risultato sono in `.gitignore` (artefatti runtime); i git tag sono il record canonico
- I prior JSON sono tracciati in git (immutabili — non si sovrascrivono mai)

---

## 8 — Stack Tecnologico

### 8.1 Stack Scientifico

Identico alla specifica del Methodology Appendice A. Conda environment lockato in `environment.yml`.

```yaml
name: cauchy
channels: [conda-forge, pytorch]
dependencies:
  - python=3.11
  - pytorch=2.2
  - torch-geometric=2.5
  - e3nn=0.5
  - gudhi=3.9
  - ripser=0.6
  - pysr=0.18
  - numpy=1.26
  - scipy=1.12
  - matplotlib=3.8
  - jupyter=1.0
  - julia=1.10
```

### 8.2 Modelli Claude

| Uso | Modello |
|-----|---------|
| Generazione script, task meccanici | claude-sonnet-4-6 |
| Analisi scientifica complessa, Fisher, SR | claude-opus-4-x |
| Claude Reviewer (progetto separato) | claude-opus-4-x |

### 8.3 Letteratura

- PDFs Tier 1: ~8 paper, ~80 MB, tracciati in git-lfs
- `literature/index.json`: git regolare, aggiornato quando si aggiungono PDFs
- Ricerca PDF locale: pdfminer o pdfplumber
- Ricerca arXiv: `arxiv` Python package (no auth)
- ADS: `ads` Python package (richiede ADS API key in `.env`, non tracciato in git)

### 8.4 Compute

| Phase | Hardware | Costo stimato |
|-------|----------|---------------|
| 0 | Locale | — |
| 1 | Locale + A100 cloud | ~$20 |
| 2 | A100 cloud | ~$150 |
| 3 | A100 cloud | ~$225 |
| 4 | Locale (Julia) | — |
| 5 | A100 cloud | ~$400 |
| 5bis | Locale (CPU) | — (analisi numerica pura, no simulazioni) |
| 6 (DESI) | A100 cloud | ~$750 |

**Costo cloud totale stimato (senza Phase 6):** ~$795  
**Con Phase 6 DESI:** ~$1.300–$2.000

---

## 9 — Decisioni Fisse

Questo è il **registro delle decisioni architetturali operative**. Le decisioni scientifiche sono nel Methodology.

| ID | Decisione | Alternative rigettate | Razionale | Fonte |
|----|-----------|-----------------------|-----------|-------|
| D-01 | PI come soggetto esecutivo, Claude come strumento | Sistema multi-agente autonomo (v1.9) | Il progetto scientifico è responsabilità del PI; l'autonomia agentiva aggiungeva complessità senza valore per un problema pioneristico | Revisione architetturale Aprile 2026 |
| D-02 | Claude Reviewer come istanza separata in progetto Claude dedicato | RefereeAgent interno al framework (v1.9) | Il reviewer esterno è più indipendente e più facile da istanziare; il progetto separato mantiene la separazione dei contesti | Revisione architetturale Aprile 2026 |
| D-03 | Sonnet 4.6 default, Opus 4.x per analisi complesse | Opus 4.x per tutto | Routing per costo: le analisi scientifiche critiche meritano il modello più capace; la generazione di script è meccanica | §3.2 |
| D-04 | Prior congelati + Ricalibrzione Formale (N_max = 2) | Threshold flessibili; singola ricalibrzione senza limite | Guard strutturale anti-p-hacking; loop limitato previene tuning ad-hoc | §2.4, §4.2 |
| D-05 | Asymmetric Recalibration Test obbligatorio | Auto-ricalibrzione senza test di asimmetria | Unica validazione credibile che la ricalibrzione non sia reverse-engineered sul valore osservato | §4.2 |
| D-06 | Il Reviewer deve approvare ogni ricalibrzione | PI può auto-approvare con motivazione | La ricalibrzione è il punto di maggiore vulnerabilità epistemica; reviewer esterno è il guard | §4.2 |
| D-07 | Document-as-Implementation per i PDFs Tier 1 | Solo ADS/arXiv on-demand | Riproducibilità offline; robustezza a outage di servizi esterni; disponibilità garantita dei paper | §4.3 |
| D-08 | Numeri fisici devono tracciare a citazione o calcolo CAUCHY | Affermazioni numeriche dal training LLM | I modelli LLM possono allucinare numeri specifici; il grounding è la guard | §4.3 |
| D-09 | Ogni RecalibrationReport scritto per ogni tentativo (approvato o rigettato) | Solo in caso di approvazione | I tentativi rigettati sono materiale di audit — il referee del paper può chiederli | §6.3 |
| D-10 | Sequenza lineare — nessuna Phase inizia prima del gate precedente | Parallelizzazione delle Phase | Coerente con il Methodology; evita dipendenze circolari; più semplice da supervisionare | Methodology §2.3 |
| D-11 | Il Ramo B si attiva solo dopo Gate 1 passato | Attivazione parallela con Ramo A | Coerente con Methodology "lazy activation"; evita costi computazionali se il Ramo A fallisce | Methodology §2.3 |
| D-12 | Ogni sessione produce un SessionArtifact con checksum degli input | Solo progress notes | Catena di custodia verificabile; il referee può ricostruire il processo | §4.4 |
| D-13 | Il CHANGELOG è a due livelli: narrativo (MD) + eventi strutturati (JSONL) | Solo CHANGELOG.md | Separazione umano/macchina; nessun parsing fragile di markdown per gli eventi automatici | §4.5 |
| D-14 | Git tag come record canonico dei gate passati | Solo filesystem | Catena crittografica verificabile; `git checkout gate_1_passed_v1` da un referee | §7 |
| D-15 | Prior JSON tracciati in git, mai sovrascritti in-place | Sovrascrittura del file corrente | L'immutabilità dei prior è la garanzia fondamentale di non-p-hacking | §6.2 |
| D-16 | System prompt del Reviewer separato, mantenuto in `prompts/reviewer_system_prompt.md` | Prompt inline nella sessione | Versioning del comportamento del Reviewer; il PI può aggiornarlo deliberatamente ma non accidentalmente | §7 |
| D-17 | Documenti di design L2 per ogni Phase, just-in-time | L2 upfront per tutte le Phase | Evita di specificare Phase 5 mentre Phase 2 potrebbe ancora falsificare assunzioni upstream | §1.1 |
| D-18 | Phase 5bis è prerequisito non negoziabile dell'apertura di Phase 6 | Saltare Phase 5bis e documentare la degenerazione IDE/CPL solo nel paper | Senza output numerici (O5b-1, O5b-2, O5b-4), la documentazione di degenerazione è opinabile in revisione; con gli output, è verificabile | `CAUCHY_Literature_April2026_Update.md` §3 |
| D-19 | Il framing del paper (titolo + abstract) è oggetto di deliberazione formale al Gate 5bis sulla base di max(ΔD/D) e σ_Phase5 | Pre-committere a un framing fisso al freeze del Methodology | La letteratura aprile 2026 ha reso esposto il framing originale; deliberazione informata da dati post-Phase 5bis è più difendibile | `CAUCHY_Literature_April2026_Update.md` §3.2 (O5b-5) |

---

## 10 — Implementation Roadmap

### Milestone M0 — Setup repository e primer scientifico

**Goal:** repository inizializzato con struttura, environment, prior gate 0 scritto, PDFs Tier 1 indicizzati, system prompt Reviewer finalizzato.

Deliverables:
- [ ] `environment.yml` completo e testato
- [ ] `literature/tier1/` popolato con tutti i paper obbligatori
- [ ] `literature/index.json` costruito
- [ ] `prompts/reviewer_system_prompt.md` finalizzato e testato su un review di prova
- [ ] `prior/gate0_prior_v1.0.json` scritto con i threshold motivati
- [ ] Struttura di directory completa

**Exit criterion:** una sessione di review di prova completa — PI sottomette un prompt fittizio al Claude Reviewer, il Reviewer risponde con un parere strutturato completo.

---

### Milestone M1 — Phase 0 completata

**Goal:** Gate 0 passato su dati Quijote reali.

Deliverables:
- [ ] Script `src/phase0_data_prep.py` generato e validato
- [ ] Integrità di tutti i campi Quijote verificata
- [ ] Pipeline di preprocessing lockati
- [ ] `results/phase0_data_manifest.json` prodotto
- [ ] Review 0 completato e `results/phase0_review.json` prodotto
- [ ] Gate 0 valutato

**Exit criterion:** `results/phase0_data_manifest.json` prodotto, Gate 0 passato, review positivo, git tag `gate_0_passed_v1_0`.

---

### Milestone M2 — Phase 1 completata (Gate 1)

**Goal:** Ramo A baseline completo, Gate 1 valutato.

Deliverables:
- [ ] Script `src/phase1_tda_baseline.py` generato e validato
- [ ] TDA su fiduciali, LHC, nwLH completata
- [ ] Fisher Matrix calcolata (Gate 1a)
- [ ] Correlazioni con w₀ calcolate (Gate 1b)
- [ ] Prior Gate 1 scritto (con eventuale v1.1 dopo ricalibrzione)
- [ ] Review 1 completato
- [ ] Gate 1 valutato

**Exit criterion:** `results/phase1_tda_baseline.json` prodotto, Gate 1 passato (o chiusura Scenario C documentata), git tag `gate_1_passed_v1` o `gate_1_scenario_c`.

---

### Milestone M3 — Phase 2 completata (Gate 2)

**Goal:** CNN addestrata, τ(x) costruito, Gate 2 valutato.

**Prerequisito:** Gate 1 passato.

Exit criterion: `results/phase2_cnn_diagnostic.json` prodotto, T1 superato, τ(x) disponibile per tutti i campi, git tag `gate_2_passed_v1`.

---

### Milestone M4 — Phase 3 completata (Gate 3)

**Goal:** GNN addestrato su TDA(τ(x)), miglioramento sulla baseline documentato.

**Prerequisito:** Gate 2 passato.

---

### Milestone M5 — Phase 4 completata (Gate 4)

**Goal:** Symbolic Regression completata, espressione stabile (o risultato negativo) documentato.

**Prerequisito:** Gate 3 passato.

---

### Milestone M6 — Phase 5 completata (Gate 5) — Venue determinata

**Goal:** Phantom crossing injection test completato con HOD marginalizzato. Venue del paper determinata.

**Prerequisito:** Gate 4 passato.

Exit criterion: `results/phase5_phantom_test.json` prodotto, gate 5 valutato, venue documentata, git tag `gate_5_passed_vX`.

---

### Milestone M6bis — Phase 5bis completata (Gate 5bis) — Framing del paper deliberato

**Goal:** Test di degenerazione IDE/CPL completato; framing del paper (conservativo vs aggressivo) deliberato e archiviato; OC-2 risolto.

**Prerequisito:** Gate 5 passato (PASS o FAIL_NEGATIVE documentato).

**Source documenti:** `CAUCHY_Literature_April2026_Update.md`; Methodology v2 §3 Fase 5bis; Execution Design §5.6bis.

Deliverables:
- [ ] `src/phase5bis_ide_analytics.py` con test unitari P5b-2 passanti
- [ ] `src/phase5bis_growth_factor.py` con test unitari P5b-3 passanti
- [ ] `results/phase5bis_Hz_degeneracy.json` (O5b-1)
- [ ] `results/phase5bis_IDE_mapping.json` (O5b-2; opzionale per Scenario C)
- [ ] `results/phase5bis_paper_section.md` (O5b-3) con citazioni a Neumann 2026, Petri 2026, Artola 2026
- [ ] `results/phase5bis_growth_factor.json` (O5b-4; opzionale per Scenario C)
- [ ] `results/phase5bis_framing.md` (O5b-5) con deliberazione motivata
- [ ] `results/phase5bis_review.json` con verdict Reviewer
- [ ] `results/phase5bis_gate_result.json` (PASS_CONSERVATIVE / PASS_AGGRESSIVE / FAIL_INCOMPLETE)
- [ ] `prior/gate5bis_prior_v1_0.json` frozen

Exit criterion: Gate 5bis chiuso con esito PASS_CONSERVATIVE o PASS_AGGRESSIVE; OC-2 chiuso (riferimento `phase5bis_paper_section.md`); git tag `gate_5bis_passed_vX`. Apertura Phase 6 autorizzata.

**Stima:** 2–3 sessioni Claude, 3–5 giorni di calendario PI, $0 di budget cloud.

---

### Milestone M7 — Phase 6 + Paper

**Goal:** Applicazione a DESI DR2 (se accessibile) o submission Quijote. Paper scritto e sottomesso.

---

## 11 — Changelog

### v2.0 — Aprile 2026

**Riscrittura completa dalla v1.9 (agentic) alla v2.0 (PI-driven).**

Motivazione: il sistema multi-agente autonomo della v1.9 — pur architetturalmente corretto — aggiungeva complessità di ingegneria del software sproporzionata rispetto al valore per un progetto pioneristico in cui il fattore umano deve essere centrale. La v2.0 adotta un approccio in cui il PI è il soggetto esecutivo e Claude è lo strumento.

**Eliminato dalla v1.9:**
- Framework GAME custom (21 file, 33 test)
- AgentRegistry, Agent base class, AgentLanguage, Capability hooks
- SessionBoundary procedurale, ActionContext + dependency injection
- BranchA_Controller, BranchB_Controller, CosmologyAgent, EngineeringAgent come agenti autonomi
- RefereeAgent interno (sostituito da Claude Reviewer esterno)
- 97 Fixed Decisions architetturali sul framework
- Concetto di "sessione agentiva" con ScriptedLLM e loop automatico
- Tutti i riferimenti al corso AI Agents Engineering

**Mantenuto dalla v1.9:**
- Prior congelati + Protocollo di Ricalibrzione Formale (D-09, ora D-04)
- Asymmetric Recalibration Test (D-10, ora D-05)
- Document-as-Implementation per i PDFs Tier 1 (D-11, ora D-07)
- Vincolo hard su numeri fisici (D-13, ora D-08)
- GateResult, FrozenPriorV, RecalibrationReport, SessionArtifact, ReviewerResponse come schemi JSON (§6)
- Stack scientifico identico (gudhi, torch, e3nn, pysr, Julia)
- Struttura di Phase e gate criteria (allineata al Methodology v2.0)
- Git tagging dei gate passati
- CHANGELOG a due livelli
- N_max = 2 ricalibrzioni per gate

**Aggiunto in v2.0:**
- Sezione §3 Modello di Esecuzione con i tre soggetti (PI, Claude, Claude Reviewer)
- Pattern Istruzione-Handback come prassi operativa, non come architettura agentiva
- Review e Gate per ogni Phase (allineati al Methodology v2.0 e al documento CAUCHY_Review_and_Gate)
- §9 Decisioni Fisse ridotte a 17 decisioni operative rilevanti (da 97 architetturali)
- Milestone riviste per riflettere il nuovo approccio operativo

---

*CAUCHY Execution Design v2.0*  
*Supersedes v1.9 — Aprile 2026*  
*Prossima revisione: dopo Gate 0 passato (Milestone M1)*
