# CAUCHY — Systematic Methodology v2.0
## Cosmic Anomaly via Unified Cosmological Hyper-fields analYsis

**Classification:** Principal Investigator Document  
**Version:** 2.0 — Aprile 2026  
**Status:** Pre-execution — revised from v1.0  
**Supersedes:** CAUCHY_Systematic_Methodology v1.0

---

## Executive Summary

Questo documento definisce la metodologia completa, lineare e scientificamente robusta per il Progetto CAUCHY. Stabilisce il fondamento scientifico, l'architettura della pipeline, la specifica fase per fase, il protocollo di analisi Fisher e il framework di robustezza. Non contiene codice implementativo: quello è prodotto durante l'esecuzione del progetto e validato dal PI prima di ogni lancio.

**Domanda scientifica centrale:** La topologia tridimensionale del campo di densità galattico — misurata tramite l'intera triade di Betti (β₀, β₁, β₂) applicata a oggetti fisici nuovi e ben definiti — riesce a rilevare deviazioni dall'energia oscura cosmica ΛCDM che sono invisibili alle statistiche compresse (P(k), BAO)? In particolare: esiste un'impronta topologica del phantom crossing w < −1 nei vuoti 3D della struttura cosmica a grande scala?

**Approccio operativo:** Il PI conduce il progetto con Claude come strumento di analisi e generazione di script. Claude analizza i task, produce script Python e Julia, redige analisi scientifiche. Il PI revisiona tutto, lancia gli script sull'hardware locale e cloud, valida i risultati e prende tutte le decisioni sui parametri. Ogni fase è progettata in anticipo tenendo conto dei requisiti delle due fasi successive.

---

## Parte I — Fondamenti Scientifici

### 1.1 Il Contesto: Pressioni sul Modello ΛCDM

Il modello ΛCDM descrive con straordinaria precisione una vasta gamma di osservazioni cosmologiche, dalla struttura a grande scala dell'universo alle anisotropie del fondo cosmico a microonde. Tuttavia, i dati più recenti esercitano pressioni crescenti su questo paradigma lungo due assi distinti.

**Evidenza di energia oscura dinamica da DESI DR2.** Il secondo rilascio di dati del Dark Energy Spectroscopic Instrument (Abdul Karim et al. 2025), basato su misure BAO di oltre 14 milioni di galassie e quasar, mostra una preferenza statisticamente significativa per un'equazione di stato dell'energia oscura dinamica nella parametrizzazione CPL, w(z) = w₀ + wₐz/(1+z). Le significatività variano tra 2.8σ (DESI+CMB+PantheonPlus) e 4.2σ (DESI+CMB+DESY5). I valori best-fit si collocano nel regime w₀ > −1, wₐ < 0, compatibile con uno scenario Quintom-B in cui l'equazione di stato attraversa la phantom divide w = −1 a redshift intermedi. Questo segnale è confermato indipendentemente dall'analisi della foresta Lyman-α (Capozziello et al. 2026), che fornisce ulteriore evidenza per energia oscura dinamica sfruttando sonde del campo di densità ad alto redshift.

**La tensione di Hubble.** La discrepanza tra H₀ misurato localmente tramite la scala delle distanze (SH0ES: 73.17 ± 0.86 km/s/Mpc) e H₀ inferito dalla CMB nell'ambito ΛCDM (Planck 2018: 67.4 ± 0.5 km/s/Mpc) supera i 5σ e non è riconducibile a errori sistematici noti. L'analisi di Dai et al. (2026) mostra che modelli con energia oscura interagente producono un'evoluzione di H₀ con il redshift compatibile con questa tensione, suggerendo che la soluzione potrebbe richiedere fisica al di là del modello standard. Crucialmente, il modello w₀wₐCDM non risolve la tensione di Hubble — anzi, il valore di H₀ inferito in questo modello è inferiore al valore Planck ΛCDM.

**Robustezza dell'evidenza DESI.** È essenziale notare che la robustezza dell'evidenza per energia oscura dinamica da DESI è oggetto di dibattito attivo. Wang & Mota (2025) dimostrano che le combinazioni DESI+CMB+SNe presentano tensioni interne tra i singoli dataset; Efstathiou (2025) identifica una potenziale sistematica di calibrazione nel campione DESY5 a basso redshift che, se corretta, ridurrebbe la significatività del segnale. Chudaykin et al. (2026) mostrano invece che un'analisi full-shape di DESI DR1 con prior basati su simulazioni migliora i vincoli su wₐ rispetto all'analisi ufficiale. Questa ambiguità nella letteratura è precisamente la motivazione per un approccio field-level indipendente che bypasasi le statistiche compresse.

### 1.2 Il Gap Scientifico

La letteratura recente sulle statistiche di ordine superiore e sull'inferenza field-level cosmologica ha prodotto sviluppi significativi, ma lascia aperto un gap preciso che CAUCHY intende colmare.

**Yip, Biagetti et al. (JCAP 2024)** presentano la prima previsione Fisher sistematica per l'omologia persistente applicata ai cataloghi di aloni di materia oscura dalle simulazioni Quijote. Dimostrano che la persistent homology supera la combinazione spettro di potenza + bispettro per 8 su 10 parametri cosmologici, con guadagni del 13–50%. La combinazione delle due statistiche riduce ulteriormente i vincoli del 12–33% grazie a direzioni di degenerazione complementari nello spazio dei parametri. Tuttavia: il lavoro opera su **aloni di materia oscura**, non su galassie osservabili; non testa l'equazione di stato dinamica w₀/wₐ come parametro primario; non applica l'analisi al campo di densità galattico 3D in spazio di redshift.

**Prat et al. — DES Y3 (MNRAS 2025)** applicano l'omologia persistente sferica alle mappe di convergenza del lensing gravitazionale debole di DES Anno 3, ottenendo S₈ = 0.821 ± 0.018 e Ωm = 0.304 ± 0.037 nel modello wCDM con un miglioramento del 70% nel figure of merit rispetto alle statistiche a due punti. Tuttavia: il metodo opera su **mappe 2D di convergenza**; il numero di Betti β₂ — che descrive i vuoti 3D chiusi — è **inaccessibile a qualsiasi proiezione 2D** e non è incluso nell'analisi; il test di phantom crossing w < −1 non è l'obiettivo primario.

**Hahn et al. — SimBIG (Nature Astronomy 2024)** realizzano il primo framework SBI per il clustering galattico non-gaussiano e non-lineare, estraendo vincoli da CNN, trasformate wavelet scattering e bispettro applicate al campo galattico 3D di BOSS. Dimostrano miglioramenti sostanziali su Ωm, σ₈, H₀ rispetto alle analisi PT standard. Tuttavia: il framework usa **statistiche summary** (CNN, WST, B₀), non TDA; w₀/wₐ non è il parametro di interesse primario; l'informazione topologica del campo non è sfruttata.

**Leclercq (SciPost 2025)** fornisce il framework teorico completo per l'inferenza a livello di campo in cosmologia, dall'HMC al BORG fino agli emulatori neurali. Il campo di applicazione più avanzato — BORG — ricostruisce le condizioni iniziali dell'Universo dai cataloghi galattici, ma non integra statistiche topologiche e non testa w(z) dinamico.

**Il gap è quindi questo:** nessun lavoro esistente applica la persistent homology 3D al campo galattico tridimensionale in spazio di redshift per vincolare direttamente l'equazione di stato dinamica dell'energia oscura, e in particolare per rilevare il phantom crossing w < −1 attraverso la topologia dei vuoti cosmici 3D. CAUCHY colma questo gap con due contributi distinti e scientificamente indipendenti.

### 1.3 Il Contributo Originale di CAUCHY

CAUCHY porta due contributi che non hanno precedenti in letteratura:

**Contributo A — TDA 3D su δ(x) per w₀/wₐ (Ramo A).** L'applicazione sistematica della triade di Betti (β₀, β₁, β₂) al campo di densità galattico 3D in spazio di redshift per derivare vincoli Fisher su (Ωm, σ₈, w₀). Questo estende Yip & Biagetti 2024 al settore dell'energia oscura dinamica e al campo galattico osservabile, e produce il risultato di baseline confrontabile con la letteratura.

**Contributo B — TDA 3D su τ(x) per phantom crossing (Ramo B).** La topologia non viene applicata al campo di densità grezzo δ(x), ma al campo di tensione τ(x) — definito come il residuo, nello spazio latente di una CNN equivariante, tra la rappresentazione dell'osservazione e quella attesa sotto ΛCDM. La TDA di τ(x) misura la topologia dell'anomalia strutturata rispetto al modello nullo. Questo oggetto non ha precedenti in letteratura e porta informazione su deviazioni da ΛCDM che è invisibile sia alla TDA di δ(x) sia alle statistiche compresse convenzionali.

β₂ — il numero di Betti che descrive le cavità 3D chiuse (vuoti cosmici) — è il segnale primario per il phantom crossing. Con w < −1, i vuoti si espandono più rapidamente e diventano più sferici, lasciando un'impronta topologica nelle strutture a tre dimensioni che è completamente inaccessibile a qualsiasi analisi 2D o a statistiche di compressione scalare.

### 1.4 Architettura Epistemologica

**Il risultato nullo è architetturalmente primario, non un fallback.**

CAUCHY è strutturato come un test di ipotesi formale con tre possibili esiti, tutti pubblicabili:

| Scenario | Descrizione | Venue target |
|----------|-------------|--------------|
| **A** | Phantom crossing rilevato ≥ 2σ, degeneracy breaking significativo | Nature Astronomy / PRL |
| **B** | Vincoli competitivi, complementari a BAO+P(k) | Physical Review D |
| **C** | Pipeline validata, risultato nullo documentato, prima applicazione field-level topologica al campo 3D | JCAP |

La pipeline è progettata per essere **falsificabile a ogni stadio**. Ogni gate di validazione ha criteri espliciti per procedere o documentare un risultato negativo. I gate threshold sono prior congelati, modificabili solo attraverso il protocollo di ricalibrzione formale (§2.4).

### 1.5 Letteratura Obbligatoria

#### Tier 1 — Lettura obbligatoria prima dell'esecuzione

| Paper | Perché obbligatorio |
|-------|---------------------|
| Abedi et al. — RSD su 3D PH (IJGMM 2025) | Le RSD modificano sistematicamente β₁ — quantificazione obbligatoria |
| Karim et al. — DESI DR2 BAO (Phys. Rev. D 2025) | Contesto fisico target e benchmark principale |
| Yip, Biagetti et al. — Fisher PH (JCAP 2024) | Valida la triade di Betti come statistica cosmologica; fornisce stime Fisher di riferimento per la ricalibrzione dei gate |
| Prat et al. — DES Y3 PH (MNRAS 2025) | Concorrente diretto — differenziazione esplicita richiesta (2D vs 3D, β₂ inaccessibile) |
| Hahn et al. — SimBIG (Nature Astronomy 2024) | Architettura del modello forward da replicare per DESI; riferimento per HOD a 9 parametri |
| Leclercq — Field-level inference (SciPost 2025) | Fondamento teorico per l'analisi a livello di campo non compresso |


#### Tier 2 — Lettura prima della Fase 3

| Paper | Perché importante |
|-------|-------------------|
| Capozziello et al. — Lyman-α DDE (A&A 2026) | Caso di test critico per energia oscura dinamica — 4.2σ dalla foresta Lyman-α |
| Dai et al. — IDE Hubble Evolution (Phys. Rev. D 2026) | Motivazione per l'approccio field-level indipendente dalla tensione di Hubble |
| Li & Wang — HDE (MNRAS 2026) | Framework teorico alternativo per la tensione di Hubble |
| Pinon et al. — Fiber assignment (JCAP 2025) | Bias correlato con il campo di densità — vulnerabilità sistematica primaria |
| Maus et al. — σ₈ da DESI Y1 (JCAP 2025) | La tensione σ₈ è parzialmente dipendente dal tracciatore |
| Artola, Lazkoz & Salzano — IDE+CPL (arXiv 2026) | Gerarchia di modelli IDE con kernel $Q=3H(\delta+\eta a)\rho_{\rm de}$: confronto frequentista vs. bayesiano |
| Neumann, Videla & Araya — IDE+CPL (arXiv 2026) | Soluzioni analitiche esatte in termini di funzioni gamma: transizione fantasma→quintessenza e accelerazione cosmica transitoria |
| Wang & Wang — CIT (arXiv 2026) | Cosmological intercept tension |
| Gavela — Dark coupling (JCAP 2009) | Dark matter and Dark energy interaction |


---

## Parte II — Architettura della Pipeline

### 2.1 Correzioni Strutturali dalla v3.x

Il Methodology v2.0 eredita tre correzioni architetturali già introdotte nella v1.0 e qui confermate:

**Correzione 1 — TDA prima della CNN.** Nella v3.x la CNN era addestrata prima che la baseline topologica fosse stabilita. Questo rende impossibile rispondere alla domanda del referee "quanto aggiunge la CNN rispetto alla TDA pura?" e rischia che la CNN impari la varianza gaussiana (σ₈ come ampiezza) invece della struttura geometrica non-lineare. La correzione è che la Fase 1 (TDA su δ(x)) è completata e documentata prima che la CNN della Fase 2 venga addestrata. Le Betti curve features della Fase 1 diventano il target di supervisione della CNN.

**Correzione 2 — Curve di Betti invece dello scalare W₂.** Nella v3.x l'output della TDA era il secondo momento di Wasserstein W₂(β₁) — un singolo scalare che collassa tutta la distribuzione di persistenza in un numero. Questo è equivalente a fare fotometria bolometrica invece di spettroscopia: si perde l'intera struttura spettrale. La correzione è l'uso delle **Betti curve** β_k(t) campionate a N_thresh soglie (50–100), da cui si estraggono feature fisicamente motivate: posizione del picco (sensibile a w(z)), altezza del picco (sensibile a σ₈), larghezza, integrale, persistenza alta. Questo è supportato dalla letteratura: Yip et al. 2024 usano istogrammi del diagramma di persistenza; la posizione del picco di β₁ è identificata come la feature più sensibile a w.

**Correzione 3 — Baseline ΛCDM formale.** Nella v3.x non esisteva una baseline documentata delle capacità della TDA pura prima del ML. La correzione è che il Gate 1 certifica questa baseline in modo rigoroso, con la matrice di Fisher calcolata sulla TDA di δ(x) su tutti i dataset rilevanti. Questo è il riferimento contro cui tutte le fasi successive misurano il proprio miglioramento.

### 2.2 I Due Oggetti Fisici Primari

**δ(x) — il campo di densità galattico.** È l'oggetto di input della pipeline. Viene prodotto dalla Fase 0 (preprocessing standardizzato sui campi Quijote) ed è l'oggetto su cui opera il Ramo A (TDA baseline). È un campo fisico direttamente osservabile, confrontabile con la letteratura esistente.

**τ(x) — il campo di tensione.** È l'oggetto originale di CAUCHY e il cuore del Ramo B. È definito come:

τ(x) = CNN_encoder(δ_obs(x)) − E_{p_ΛCDM}[CNN_encoder(δ_ΛCDM(x))]

dove CNN_encoder è la rappresentazione latente prodotta dalla CNN equivariante di Fase 2, e l'aspettazione è calcolata sui campi fiduciali ΛCDM. τ(x) non è un campo fisico in senso stretto, ma un campo di anomalia strutturata: misura la distanza nello spazio latente tra ciò che la CNN vede nell'osservazione e ciò che si aspetterebbe vedere sotto ΛCDM. La TDA applicata a τ(x) misura la **topologia di questa anomalia** — le strutture connesse, i loops e i vuoti in τ(x) sono le regioni dove l'osservazione e il modello nullo divergono in modo strutturato e persistente.

L'ordine operativo per la costruzione di τ(x) è il seguente e deve essere rispettato rigorosamente:

1. La CNN è addestrata sui campi LHC con supervisione sulle Betti curve features di δ(x) calcolate in Fase 1.
2. La CNN, una volta conversa, è applicata ai campi fiduciali ΛCDM (prime 2000 delle 15000 disponibili localmente) per calcolare la distribuzione delle rappresentazioni latenti sotto ΛCDM.
3. L'aspettazione E_{p_ΛCDM}[CNN_encoder(δ_ΛCDM(x))] è calcolata come media su questi 2000 campi fiduciali.
4. Per ogni campo osservato (LHC o nwLH), τ(x) è calcolato sottraendo questa media.
5. Solo a questo punto τ(x) è definito e può essere dato in input alla TDA del Ramo B (Fase 3).

### 2.3 I Due Rami e il Loro Rapporto

**Ramo A — TDA(δ(x)):** stabilisce cosa la topologia del campo grezzo può fare. Produce la baseline scientifica confrontabile con la letteratura (Yip 2024, Prat 2025). Eseguito in Fase 1, completato prima che la CNN della Fase 2 inizi.

**Ramo B — CNN(δ(x)) → τ(x) → TDA(τ(x)) → GNN → SR:** il contributo originale. La CNN costruisce la rappresentazione latente, τ(x) è il campo di anomalia, la TDA di τ(x) caratterizza la topologia di quel residuo, il GNN estrae feature geometriche non-locali dal grafo topologico di τ(x), la SR scopre la legge funzionale.

**Separazione scientifica dei rami.** Il Ramo A e il Ramo B sono scientificamente indipendenti per costruzione: il Ramo A usa TDA(δ(x)), il Ramo B usa TDA(τ(x)). I due oggetti sono distinti. Un referee non può obiettare che la separazione è solo parziale.

**Indipendenza dei risultati.** Il Ramo A può produrre un risultato pubblicabile anche se il Gate 2 fallisce e il Ramo B non viene mai attivato. Il Gate 2 (test T1 di fattorizzazione parametrica) certifica se la CNN ha appreso struttura geometricamente significativa o solo varianza gaussiana. Se T1 fallisce: solo il Ramo A è valido e il paper documenta perché le CNN locali non generalizzano per field-level inference cosmologica — questo è anch'esso un contributo metodologico originale.

### 2.4 Protocollo di Ricalibrzione

Un threshold di gate può essere revisionato se e solo se:

1. La revisione è motivata da un'analisi diagnostica scritta che identifica una differenza strutturale specifica tra il contesto di derivazione del prior e il contesto di esecuzione corrente.
2. La revisione è quantificata tramite un argomento di scaling esplicito, non fitting al valore osservato. Esempio: σ(Ωm)_scalato = σ_letteratura × √(V_letteratura/V_CAUCHY).
3. L'analisi è rivista dal PI prima di procedere.
4. Il numero di ricalibrzioni per gate è limitato a N_max = 2. Una terza richiesta di ricalibrzione chiude il gate in Scenario C.

I gate threshold numerici non sono specificati in questo documento: sono fissati nel documento di parametri di esecuzione (CAUCHY_Execution_Parameters), derivati dalla letteratura e calibrati per il volume e il dataset Quijote.

### 2.5 Architettura Sequenziale

```
Fase 0: Preparazione e Validazione dei Dati
    ↓ [GATE 0: integrità dati verificata, pipeline di preprocessing version-locked]
Fase 1: TDA Baseline — Ramo A
    ↓ [GATE 1a: Fisher su (Ωm, σ₈) dal dataset LHC documentato]
    ↓ [GATE 1b: correlazione con w₀ dal dataset nwLH documentata]
Fase 2: CNN con Supervisione Topologica → τ(x)
    ↓ [GATE 2: test T1 di fattorizzazione parametrica superato]
Fase 3: GNN su TDA(τ(x)) — Ramo B
    ↓ [GATE 3: breaking della degenerazione Ωm–σ₈ dimostrato]
Fase 4: Symbolic Regression
    ↓ [GATE 4: espressione simbolica stabile su ≥ 10/20 run]
Fase 5: Phantom Crossing Injection Test
    ↓ [GATE 5: significatività statistica documentata → determina venue]
Fase 5bis: Test di Degenerazione IDE/CPL (analisi numerica, no nuove simulazioni)
    ↓ [GATE 5bis: degenerazione documentata, framing del paper deliberato]
Fase 6: Applicazione a DESI DR2 (o submission Quijote)
    ↓ [GATE 6: sistematiche validate, triplo confronto baseline DESI eseguito]
Fase 7: Paper
```

**Principio di linearità:** nessuna fase inizia prima che il gate precedente sia superato. Nessuna dipendenza circolare. Ogni gate produce un file di risultato documentato e versionato.

**Nota su Fase 5bis (introdotta nell'addendum 2026-05-05):** Fase 5bis è una sotto-fase consecutiva a Fase 5, istituita in risposta alla letteratura aprile 2026 (Neumann 2026, Artola 2026, Wang & Wang 2026; vedi `CAUCHY_Literature_April2026_Update.md`). Il suo scopo è documentare la degenerazione di background tra phantom crossing CPL e cosmologie IDE quintessenza non interagenti, prerequisito non negoziabile dell'apertura di Fase 6. Phase 5bis non richiede nuove simulazioni N-body ed è puramente analitica/perturbativa lineare; il budget computazionale è quasi nullo.

---

## Parte III — Specifica Fase per Fase

### Fase 0 — Preparazione e Validazione dei Dati

**Durata stimata:** 2–3 giorni  
**Responsabilità:** PI (validazione scientifica), Claude (generazione script di integrità e manifest)

#### 0.1 Inventario dei Dataset

Il progetto opera su tre dataset Quijote disponibili localmente:

- **Fiduciali PCS 128³:** 15.000 campi disponibili localmente. Si usano le prime 2.000 per la Fase 0 e Fase 1; le restanti 13.000 costituiscono la riserva per studi di robustezza e bootstrap. Parametri fiduciali: Ωm = 0.3175, σ₈ = 0.834, w₀ = −1.0, h = 0.6711.
- **LHC PCS 128³:** 2.000 campi con parametri campionati da un Latin Hypercube. Coprono Ωm ∈ [0.10, 0.50], σ₈ ∈ [0.60, 1.00]. Usati per le Fasi 1 (Gate 1a), 2, 3, 4. Dimensione su disco: ~16 GB.
- **nwLH PCS 128³:** 2.000 campi con w₀ variato in [−1.30, −0.70], gli altri parametri al fiduciale. Cruciali per il Gate 1b (sensibilità TDA a w₀) e per la Fase 5 (phantom crossing injection test). Dimensione su disco: ~105 GB.

Dataset secondari (download on demand):
- **AbacusSummit:** 60+ cosmologie, z = 0.1–2.5. Usato per il modello HOD realistico nella Fase 5.
- **DESI DR2 Galaxy Catalogs:** BGS, LRG, ELG, QSO. Accesso pendente; usato in Fase 6 se disponibile.
- **BOSS DR12 CMASS:** ~700k galassie. Cross-validazione indipendente.

#### 0.2 Controlli di Integrità

Prima di qualsiasi processing, ogni campo deve superare i seguenti controlli:

- Dimensioni: tutti i campi devono essere 128×128×128 voxel.
- Assenza di valori NaN o Inf.
- Copertura dei parametri LHC: Ωm ∈ [0.10, 0.50], σ₈ ∈ [0.60, 1.00].
- Copertura nwLH: w₀ ∈ [−1.30, −0.70].
- Statistica di campo: media del contrasto di densità δ = 0 (normalizzazione CIC verificata).
- Checksum SHA-256 per ogni file, registrato nel data manifest.

#### 0.3 Pipeline di Preprocessing Standardizzata

Tutti i campi vengono processati con una pipeline identica — nessuna eccezione, nessun aggiustamento per campo specifico. La pipeline è:

1. **Verifica normalizzazione CIC:** ⟨δ⟩ = 0 a precisione numerica.
2. **Smoothing PCS a scala fissa:** scala di smoothing in unità di Mpc/h da definire nel documento di parametri di esecuzione. La scelta è motivata dal trade-off tra preservazione dell'informazione topologica a piccola scala e soppressione del rumore di discretizzazione della griglia.
3. **Normalizzazione a livello di cosmologia:** normalizzazione dell'ampiezza calcolata sui campi fiduciali e applicata uniformemente. Critica: la normalizzazione per-campo distruggerebbe l'informazione di ampiezza (σ₈ come altezza del picco di β₁). La varianza fiduciale è il riferimento.

La versione della pipeline, i parametri di smoothing e il seed globale (GLOBAL_SEED = 42) sono registrati nel file di output del Gate 0 come prerequisito di riproducibilità.

**GATE 0:** tutti i campi superano i controlli di integrità. La pipeline è applicata e version-locked. Output: `results/phase0_data_manifest.json` con checksum di tutti i campi di input e `results/phase0_preprocessing_lock.json` con la specifica completa della pipeline.

---

### Fase 1 — TDA Baseline: il Ramo A

**Durata stimata:** 3–5 giorni (inclusi i tempi di calcolo)  
**Responsabilità:** PI (analisi scientifica, interpretazione Fisher), Claude (generazione script parallelizzati)  
**Perché questa fase è prima:** stabilisce la ground truth di cosa la topologia del campo cosmico sa, indipendentemente da qualsiasi ML. È la baseline che ogni referee chiederà e il riferimento contro cui tutte le fasi successive devono dimostrare un miglioramento.

#### 1.1 Calcolo della Triade di Betti Completa

La TDA viene applicata tramite filtrazione di supralivello (superlevel filtration) sul campo di densità δ(x) su griglia cubica 128³. La scelta della filtrazione di supralivello è motivata fisicamente: inizia dalle regioni a massima densità (cluster) e abbassa la soglia progressivamente, costruendo la topologia della struttura cosmica nel modo in cui si forma (dense first, voids last).

Si usano N_thresh soglie campionate uniformemente tra il massimo e il minimo del campo. Per ogni soglia t, si calcolano i tre numeri di Betti:

- **β₀(t):** numero di componenti connesse al livello t. Descrive la frammentazione della struttura in cluster distinti. Sensibile a Ωm (numero di aloni).
- **β₁(t):** numero di loops indipendenti (anelli, filamenti). Il suo picco descrive la scala di massima connettività filamentaria del web cosmico. La posizione del picco è sensibile a w(z); l'altezza è sensibile a σ₈.
- **β₂(t):** numero di cavità 3D chiuse (vuoti cosmici). Questo è il segnale primario per il phantom crossing: con w < −1, i vuoti si espandono più rapidamente, aumentano in numero e diventano più sferici, lasciando un'impronta topologica che è **inaccessibile a qualsiasi analisi 2D** e non è catturata da P(k) o BAO.

Implementazione: CubicalComplex di gudhi v3.9, applicato direttamente al campo 128³ negato (per convertire la filtrazione di supralivello nella filtrazione di sottolivel standard di gudhi). La parallelizzazione è eseguita a livello di campo: ogni campo è processato indipendentemente e i risultati sono aggregati.

#### 1.2 Estrazione di Feature Fisicamente Motivate

Le curve di Betti β_k(t) non sono usate direttamente come vettore di dati per l'analisi Fisher (la dimensionalità sarebbe 3 × N_thresh, con problemi di convergenza della matrice di covarianza documentati da Ouellette & Holder 2025). Si estraggono invece feature fisicamente interpretabili:

**Feature di β₁ (più cosmologicamente informative):**
- Altezza del picco: sensibile a σ₈ e Ωm.
- Posizione del picco (in unità di soglia di densità): sensibile a w(z) e σ₈.
- Larghezza a metà altezza: sensibile a σ₈.
- Integrale: connettività filamentaria totale.
- Integrale ad alta persistenza (percentile 75): filamenti cosmologicamente significativi vs rumore topologico.

**Feature di β₂ (geometria dei vuoti — segnale phantom crossing):**
- Numero massimo di vuoti chiusi.
- Persistenza media: tempo di vita medio dei vuoti nella filtrazione.
- Integrale ad alta persistenza: vuoti cosmologicamente significativi.

**Feature di β₀ (statistica dei cluster):**
- Valore al livello di densità media: numero di cluster a soglia fiduciale.

Il diagramma di persistenza completo (birth, death) per β₁ e β₂ è salvato per ogni campo e disponibile per il GNN in Fase 3. La compressione in feature scalari è utilizzata esclusivamente per l'analisi Fisher della baseline.

#### 1.3 Analisi Fisher — Gate 1a (dataset LHC)

L'analisi Fisher per il Gate 1a usa i 2.000 campi LHC per derivare vincoli su (Ωm, σ₈). Il calcolo rigoroso procede in tre passi:

**Passo 1 — Matrice di covarianza del rumore.** La varianza di misurazione di ogni feature topologica è stimata dalla dispersione tra i campi fiduciali ΛCDM (stessa cosmologia, realizzazioni diverse). Questo è il rumore di campionamento cosmico per un singolo volume (1 Gpc/h)³, non la varianza tra cosmologie diverse.

**Passo 2 — Derivate delle feature rispetto ai parametri.** Per ogni feature topologica e per ogni parametro cosmologico, si calcola la derivata numerica usando una regressione lineare locale intorno al valore fiduciale, sui campi LHC. La regione locale è definita da |θ − θ_fid| < tolleranza, dove la tolleranza è scelta per bilanciare accuratezza della linearizzazione e numero sufficiente di campi.

**Passo 3 — Matrice Fisher e vincoli marginalizzati.** La matrice Fisher è calcolata dalla formula standard F_ij = (∂O/∂θ_i)^T × Cov_noise⁻¹ × (∂O/∂θ_j), applicando il fattore di correzione di Hartlap per la stima non distorta della matrice di covarianza inversa. I vincoli marginalizzati σ(Ωm) e σ(σ₈) sono ricavati dalla diagonale della matrice di covarianza dei parametri C = F⁻¹.

Il confronto con la previsione Fisher di Yip et al. 2024 (σ(w) ~ ±0.06 su (1 Gpc/h)³ con omologia persistente su aloni) fornisce un benchmark di riferimento per la calibrazione del gate. La ricalibrzione del gate è attesa e prevista per differenze di volume, tracciatori (galassie vs aloni), e spazio di redshift.

**Degeneracy breaking:** si calcola esplicitamente la correlazione ρ(Ωm, σ₈) nella matrice di covarianza dei parametri di CAUCHY e si confronta con ρ ≈ −0.95 tipica di P(k). Una correlazione diversa implica che CAUCHY+DESI romperà questa degenerazione — questo è un risultato pubblicabile indipendente dalla significatività del segnale phantom crossing.

#### 1.4 Analisi Fisher — Gate 1b (dataset nwLH)

L'analisi per il Gate 1b usa i 2.000 campi nwLH (w₀ variato in [−1.30, −0.70], altri parametri al fiduciale) per derivare la sensibilità topologica a w₀.

Il risultato chiave è la correlazione di Pearson |r(feature_k, w₀)| per ogni feature topologica, calcolata sull'intero dataset nwLH. Questo non è un Fisher completo (che richiederebbe la varianza dei parametri e non solo la correlazione lineare), ma fornisce un indicatore robusto di quali feature portano informazione su w₀.

La feature attesa più sensibile è la posizione del picco di β₁(t): la fisica è che w₀ controlla la storia dell'espansione, che regola la scala di turnover dalla formazione lineare di strutture alla non-linearità, il che si manifesta nella posizione del picco di connettività filamentaria. Con w₀ < −1 (phantom), l'espansione più rapida sopprime la formazione di strutture a scale intermedie, spostando il picco.

La correlazione con β₂ — la persistenza media e il numero di vuoti — è il segnale più diretto per il phantom crossing e motiva l'intera architettura del Ramo B.

**GATE 1 (bipartito):**
- **Gate 1a:** Fisher su (Ωm, σ₈) dal dataset LHC calcolato e documentato. σ(Ωm) e σ(σ₈) registrati in `results/phase1_tda_baseline.json`. La correlazione ρ(Ωm, σ₈) calcolata e confrontata con P(k).
- **Gate 1b:** |r(b1_peak_position, w₀)| e |r(b2_mean_persistence, w₀)| calcolati dal dataset nwLH e documentati nello stesso file. I threshold numerici sono specificati nel documento di parametri di esecuzione.

Il Gate 1 è superato solo quando entrambe le condizioni sono soddisfatte.

---

### Fase 2 — CNN con Supervisione Topologica e Costruzione di τ(x)

**Durata stimata:** 1–2 settimane (incluso il training)  
**Responsabilità:** PI (validazione architetturale, lancio training, interpretazione T1), Claude (specifica architetturale, script di training)  
**Hardware:** A100 o equivalente su cloud. Costo stimato: $100–200.

#### 2.1 Principio Architetturale

La CNN di Fase 2 non è addestrata a predire direttamente i parametri cosmologici (Ωm, σ₈, w₀). È addestrata a predire le **Betti curve features** calcolate in Fase 1. Questa scelta di supervisione è l'elemento architetturale più importante:

- Se la CNN fosse addestrata sui parametri, potrebbe imparare a stimare σ₈ semplicemente misurando l'ampiezza media del campo — un'operazione equivalente allo spettro di potenza monopolo. Questo è l'errore della v3.x.
- Con la supervisione sulle Betti features, la CNN è costretta a imparare la struttura geometrica multi-scala del campo — loops, connettività, cavità — che è l'informazione topologica. Il test T1 (Gate 2) verifica che questo sia effettivamente avvenuto.

L'architettura prescritta è una CNN SE(3)-equivariante basata su e3nn, con blocchi convoluzionali equivarianti e message passing k-NN. L'equivarianza rispetto al gruppo SE(3) (rotazioni + traslazioni) è fisicamente motivata: la topologia del campo cosmico è invariante per rotazioni e traslazioni nell'approssimazione di uniformità e isotropia statistica. L'equivarianza garantisce che la rete non sprechi capacità imparando questa simmetria dai dati.

Input: campo di densità δ(x) campionato su una griglia di punti (o sul reticolo cubico 128³).  
Output: mappa di feature latenti τ-layer di dimensione [N_punti, D_latent].  
Target di supervisione: vettore di Betti features dalla Fase 1 per lo stesso campo.

#### 2.2 Costruzione di τ(x)

Una volta che la CNN ha convergito, si procede alla costruzione del campo di tensione seguendo rigorosamente la sequenza descritta in §2.2:

La CNN è applicata ai 2.000 campi fiduciali ΛCDM. Si calcola il valore medio della rappresentazione latente su questo ensemble: μ_ΛCDM = (1/2000) Σ CNN_encoder(δ_fiduciale_i). Per ogni campo target (LHC o nwLH), τ(x) è definito come:

τ(x) = CNN_encoder(δ_target(x)) − μ_ΛCDM

τ(x) è quindi un campo definito sugli stessi punti di δ(x), con dimensionalità D_latent per punto. Rappresenta la deviazione, nello spazio latente della CNN, tra il campo osservato e il campo atteso sotto ΛCDM.

#### 2.3 Test di Validazione — Gate 2

Il Gate 2 certifica che la CNN ha imparato struttura geometricamente significativa e non soltanto varianza gaussiana. Il test primario è il **test T1 di fattorizzazione parametrica**:

Si dividono i 2.000 campi LHC in quattro quadranti del piano (σ₈, Ωm): alto-σ₈/alto-Ωm, alto-σ₈/basso-Ωm, basso-σ₈/alto-Ωm, basso-σ₈/basso-Ωm. Si calcolano le distribuzioni dei feature τ per ogni quadrante.

Il test chiave è: la distanza di Wasserstein W₂ tra i quadranti con stesso σ₈ ma Ωm diverso è significativamente positiva? Se W₂(stesso-σ₈, Ωm-diverso) ≈ 0, la CNN legge solo la varianza del campo (σ₈ come ampiezza) e le distribuzioni di τ collassano su σ₈ — la CNN ha fallito il suo scopo. Se W₂(stesso-σ₈, Ωm-diverso) >> 0, la CNN cattura struttura non-lineare sensibile a Ωm indipendentemente da σ₈.

Il criterio quantitativo è il rapporto R = W₂(stesso-σ₈, Ωm-diverso) / W₂(stesso-Ωm, σ₈-diverso). Il threshold numerico è specificato nel documento di parametri di esecuzione con motivazione dal contesto fisico.

Se il Gate 2 fallisce: il Ramo B non viene attivato. Il paper documenta il Ramo A (Gate 1) come risultato principale e il fallimento del T1 come contributo metodologico — le CNN convoluzionali locali non generalizzano per catturare l'informazione topologica non-locale nel campo galattico 3D. Si esplora un'architettura alternativa (ViT 3D o architettura graph-first) come possibile Scenario B.

**GATE 2:** test T1 superato. R > threshold. τ(x) costruito per tutti i campi LHC e nwLH. Output: `results/phase2_cnn_diagnostic.json` con i valori di W₂ per tutti i quadranti e il path del checkpoint del modello.

---

### Fase 3 — GNN su TDA(τ(x)): il Cuore del Ramo B

**Durata stimata:** 1–2 settimane  
**Responsabilità:** PI (validazione del grafo, interpretazione fisica), Claude (architettura GNN, script di training)  
**Hardware:** A100 o equivalente. Costo stimato: $150–300.

#### 3.1 Dalla TDA(τ(x)) al Grafo

In questa fase la TDA **non** viene applicata a δ(x), ma a τ(x). Questo è la scelta architetturale centrale del Ramo B (discussa in §2.3 del documento di analisi pre-riscrittura): il GNN lavora sulla topologia dell'anomalia, non sulla topologia del campo fisico. Questo garantisce che i due rami siano genuinamente indipendenti e che il Ramo B risponda a una domanda scientificamente distinta.

La filtrazione di supralivello è applicata al campo τ(x) (o, più precisamente, a una sua proiezione scalare, tipicamente la norma del vettore latente |τ(x)|, oppure al primo componente principale se D_latent > 1). Si calcolano i diagrammi di persistenza β₁(τ) e β₂(τ).

Da questi diagrammi si costruisce un grafo in cui:

- **Nodi:** le feature topologiche di alta persistenza di τ(x) — loops (β₁) e vuoti (β₂) — filtrate da una soglia di persistenza minima. Solo le feature con persistenza sopra questo threshold sono "cosmologicamente reali" e non rumore topologico. La soglia è derivata dalla distribuzione di persistenza nei campi fiduciali.
- **Feature dei nodi:** (birth, death, persistence, tipo_0_o_1) per la feature topologica, più i valori di τ(x) nella posizione spaziale corrispondente alla feature.
- **Archi:** connessioni k-NN nello spazio (birth, death) del diagramma di persistenza. I archi connettono features topologiche vicine nella scala di filtrazione, catturando la struttura gerarchica del campo τ.

#### 3.2 Addestramento del GNN

Il GNN equivariante (e3nn, torch-geometric) viene addestrato sul dataset LHC: per ogni campo, il grafo di τ(x) è l'input e i parametri cosmologici (Ωm, σ₈, w₀) sono il target.

L'obiettivo scientifico del training è identificare le combinazioni di feature topologiche di τ(x) — le componenti del "vettore GNN" — che massimizzano la correlazione con i parametri cosmologici. Analogamente a come SimBIG/Hahn 2023 identifica le dimensioni latenti della CNN più correlate con H₀, CAUCHY identifica le dimensioni latenti del GNN più correlate con w₀.

La separazione dei dataset segue la prassi standard: 80% per il training, 20% per la valutazione al Gate 3.

#### 3.3 Analisi Fisher — Gate 3

Per ogni componente j del vettore di output del GNN, si calcola la correlazione |r(GNN_j, Ωm)| e |r(GNN_j, σ₈)| sul test set (20% del LHC). Si identificano le componenti più informative (GNN_j*) e si dimostra che spiegano varianza non catturata dalla baseline TDA del Ramo A — questo è il requisito formale di miglioramento.

Si calcola anche |r(GNN_j*, w₀)| sul dataset nwLH. Questa correlazione è il precursore diretto del phantom crossing test della Fase 5.

**GATE 3:** |r(GNN_j*, Ωm)| e |r(GNN_j*, σ₈)| superano i threshold sul test set. Il GNN dimostra un miglioramento sulla baseline TDA (la varianza spiegata aggiuntiva è documentata). Output: `results/phase3_gnn_correlations.json`.

---

### Fase 4 — Symbolic Regression

**Durata stimata:** 2–3 giorni  
**Responsabilità:** PI (interpretazione fisica delle espressioni), Claude (configurazione PySR, analisi di stabilità)  
**Hardware:** locale. Nessun costo cloud.

#### 4.1 Scopo Scientifico

La symbolic regression (SR) cerca espressioni analitiche che descrivono la relazione funzionale tra le feature topologiche — di Ramo A e Ramo B — e i parametri cosmologici. Il suo valore non è principalmente predittivo (il GNN è già più preciso), ma **interpretativo**: se la SR trova un'espressione stabile del tipo b2_mean_persistence ∝ (1+w₀)^α × σ₈^β, questa relazione ha un significato fisico diretto che può essere confrontato con previsioni perturbative e giustificato dall'evoluzione lineare e non-lineare della struttura cosmica.

#### 4.2 Configurazione

Si usa PySR (Julia backend, versione 0.18) con 20 run indipendenti (seed distinti, stessa inizializzazione). Le variabili di input sono le feature topologiche di Fase 1 e le componenti GNN più informative di Fase 3. Il target è w₀ (o una combinazione dei parametri cosmologici).

La metrica di selezione del modello usa penalizzazione AIC/BIC sulla complessità dell'espressione, non solo l'MSE sul training set. Questo previene l'overfitting a espressioni polinomiali arbitrariamente complesse.

#### 4.3 Criteri di Stabilità

Un'espressione è considerata fisicamente significativa solo se appare in ≥ 10 delle 20 run indipendenti. Questa soglia di stabilità del 50% è il filtro principale contro l'overfitting e la dipendenza dall'inizializzazione. Il R² è valutato sul test set held-out (non sul training set).

**GATE 4:** espressione stabile trovata in ≥ 10/20 run con R² sul test set > threshold. L'espressione è fisicamente interpretabile (no polinomi arbitrari senza motivazione). Se R² è insufficiente dopo 20 run: il segnale è troppo debole per la SR — risultato documentato e pubblicabile come Scenario C (il campo topologico ha struttura utile per l'inferenza statistica, ma non ha forma analitica semplice alla sensibilità attuale). Output: `results/phase4_sr_expressions.json` con istogramma di frequenza delle espressioni e metriche per tutte le 20 run.

---

### Fase 5 — Phantom Crossing Injection Test

**Durata stimata:** 1–2 settimane  
**Responsabilità:** PI (interpretazione statistica, scelta delle injection values), Claude (script di test, analisi di permutazione)  
**Hardware:** A100 o equivalente per il retraining. Costo stimato: $300–500.  
**Questa è la fase scientificamente più importante.** Il suo risultato determina la venue del paper.

#### 5.1 Disegno del Test

Il test risponde alla domanda: la pipeline CAUCHY (Ramo A e/o Ramo B) riesce a rilevare la differenza tra ΛCDM (w₀ = −1) e modelli con phantom crossing, dopo aver marginalizzato su Ωm e σ₈?

I campi nwLH (2.000 campi, w₀ ∈ [−1.30, −0.70]) sono il dataset del test. Si usano valori di injection specifici corrispondenti alle regioni best-fit di DESI DR2 e ai modelli teorici rilevanti:
- w₀ = −0.7, wₐ = −0.8 (regime preferito da DESI DR1, Quintom-B moderato)
- w₀ = −1.3, wₐ = +0.5 (phantom forte)
- w₀ = −0.9, wₐ = −0.3 (lieve quintessenza)

Per ogni valore di injection, si misura la correlazione parziale r(pipeline_output, w₀ | Ωm, σ₈) — cioè la correlazione con w₀ dopo aver rimosso la variazione dovuta a Ωm e σ₈ tramite regressione. La significatività è calcolata via **permutation test** con N = 1.000 shuffles delle label w₀: σ = (|r_obs| − mean(r_null)) / std(r_null).

#### 5.2 Modello HOD e Marginalizzazione

Questo è il punto più critico del test — l'errore che ha invalidato la v3.x. Un HOD fisso assorbe il segnale dipendente da w attraverso i suoi parametri liberi: se l'HOD non può variare, la struttura galattica a piccola scala non porta informazione su w₀ e r ≈ 0 per costruzione.

La specifica prescritta è:
- **Modello HOD:** AbacusSummit HOD a 9 parametri (stesso framework usato da SimBIG/Hahn 2023). I 9 parametri includono la distribuzione standard di centrali e satelliti di Zheng 2007, più estensioni per assembly bias (dipendenza dalla concentrazione e dall'epoca di formazione dell'alone), velocità e concentrazione dei satelliti. Questa flessibilità è necessaria per descrivere correttamente la connessione galassia-alone a scale non-lineari dove il segnale da w è più forte.
- **Strategia:** marginalizzazione via campionamento MCMC sui 9 parametri HOD con prior flat entro i range fisici. I vincoli su w₀ sono derivati dopo aver integrato sulla distribuzione dei parametri HOD.
- **Test di robustezza HOD (obbligatorio):** ripetere l'analisi phantom crossing con il modello Zheng 2007 a 5 parametri e verificare che il segnale su w₀ non cambi di più di 1σ. Se cambia di più, la dipendenza dall'HOD è dominante — questo è documentato e pubblicato come risultato sistematico.

#### 5.3 Confronto con la Baseline P(k)

Per completezza scientifica e difendibilità, lo stesso test di permutazione è eseguito sulla baseline P(k) con gli stessi campi nwLH. Questo permette di confrontare direttamente: r_CAUCHY vs r_Pk. Se r_CAUCHY > r_Pk con significatività statistica, CAUCHY porta informazione aggiuntiva su w₀ rispetto alla statistica standard. Questo confronto è essenziale per l'Objection 3 dei referee (vedi Parte V).

**GATE 5 (determina la venue del paper):**
- σ ≥ 2.0: phantom crossing rilevato → Nature Astronomy / PRL
- 1.0 ≤ σ < 2.0: evidenza marginale → Physical Review D
- σ < 1.0: non-rilevazione → documentare l'upper bound → JCAP

Output: `results/phase5_phantom_test.json` — il file di risultato chiave dell'intero progetto.

---

### Fase 5bis — Test di Degenerazione IDE/CPL

**Durata stimata:** 3–5 giorni
**Responsabilità:** PI (deliberazione framing del paper), Claude (script analitici di degenerazione)
**Hardware:** CPU locale; nessuna GPU richiesta. Costo computazionale: ~$0.
**Status:** Istituita nell'addendum di letteratura del 5 Maggio 2026. Vedi `CAUCHY_Literature_April2026_Update.md` per la motivazione completa.

#### 5bis.1 Motivazione

Tre paper apparsi su arXiv tra il 24 e il 30 aprile 2026 — Neumann, Videla & Araya 2026 (arXiv:2604.22970), Artola, Lazkoz & Salzano 2026 (arXiv:2604.25373), Wang & Wang 2026 (arXiv:2604.28013) — convergono su un argomento epistemologico unitario: la "preferenza per energia oscura dinamica" da DESI DR2 è (i) degenere a livello di background con cosmologie IDE quintessenza non interagenti (Neumann; Petri 2026), (ii) frequentista ma non bayesiana (Artola; Ong 2026), (iii) parzialmente guidata da sistematiche di calibrazione delle SNe (Wang & Wang).

La conseguenza per CAUCHY è che il segnale topologico misurato in Phase 5 — che dipende da H(z) e D(z) — è in linea di principio degenere con una famiglia di modelli IDE a livello di background. Questa limitazione, non visibile al momento del freeze del Methodology v2.0, deve essere documentata e quantificata prima della submission del paper. Phase 5bis è la risposta minimale che permette di mantenere il claim della rilevazione topologica senza abbandonare la robustezza scientifica.

#### 5bis.2 Disegno del Test

Phase 5bis non richiede nuove simulazioni N-body. È un'analisi numerica sui campi nwLH già usati in Phase 5, articolata in cinque output (O5b-1 ÷ O5b-5):

- **O5b-1: Quantificare la degenerazione H(z).** Per ogni campo nwLH, calcolare H(z) da z = 0 a z = 3 e costruire la matrice di degenerazione "H(z)-equivalente" entro tolleranza 0.5%. Output: `results/phase5bis_Hz_degeneracy.json`.

- **O5b-2: Mappa IDE-equivalente.** Per ogni cosmologia nwLH (w₀ ∈ [−1.30, −0.70]), derivare i parametri (β, w₀_de) di un modello IDE Q = β H ρ_de con quintessenza non-fantasma che riproduce la stessa H(z), usando le formule analitiche di Neumann, Videla & Araya 2026 §2.2 (funzioni gamma incomplete). Output: `results/phase5bis_IDE_mapping.json`.

- **O5b-3: Documentazione paper.** Sezione "Background degeneracy" del paper, citante Petri 2026, Neumann 2026, Artola 2026.

- **O5b-4: Differenza perturbativa.** Calcolare D(z) per i modelli IDE-equivalenti usando le equazioni di crescita lineare modificate di Gavela et al. 2009. Quantificare ΔD(z)/D(z) rispetto al CPL nominale. Output: `results/phase5bis_growth_factor.json`.

- **O5b-5: Riformulazione del claim.** Deliberazione formale tra Opzione conservativa (titolo: "Topological field-level constraints on background expansion histories of the dark sector") e Opzione aggressiva (titolo: "Topological detection of dynamical dark energy via field-level persistent homology", riservata a venue Nature Astronomy/PRL e solo se ΔD/D > 1%). Output: `results/phase5bis_framing.md`.

#### 5bis.3 Scope ridotto per Scenario C di Phase 5

Se Phase 5 chiude con σ < 1.0 (non-rilevazione), Phase 5bis può essere ridotta agli output O5b-1, O5b-3, O5b-5 (con motivazione documentata). O5b-2 e O5b-4 diventano opzionali.

#### 5bis.4 Gate 5bis

Il Gate 5bis è di tipo *documentativo*: non richiede una soglia di significatività statistica, ma richiede che tutti gli output O5b-1 ÷ O5b-5 siano stati prodotti e archiviati. Esiti possibili:

- **Gate 5bis PASS_CONSERVATIVE:** tutti gli artefatti prodotti, framing conservativo deliberato. Phase 6 autorizzata.
- **Gate 5bis PASS_AGGRESSIVE:** tutti gli artefatti prodotti, ΔD/D > 1% in O5b-4, framing aggressivo motivato. Phase 6 autorizzata.
- **Gate 5bis FAIL_INCOMPLETE:** uno o più artefatti mancanti, oppure Reviewer BLOCKING. Phase 6 non autorizzata fino a chiusura.

Output: `results/phase5bis_gate_result.json`, `prior/gate5bis_prior_v1_0.json`, `results/phase5bis_review.json`. Per la specifica completa di Phase 5bis vedi `CAUCHY_Literature_April2026_Update.md` §3.

---

### Fase 6 — Applicazione a DESI DR2 (o Submission Quijote)

**Durata stimata:** 1–2 mesi (se DESI accessibile) / immediata (submission Quijote)  
**Responsabilità:** PI (decisione strategica, coordinamento accesso dati)

#### 6.1 Albero Decisionale

Al momento del completamento della Fase 5, il PI valuta la disponibilità di accesso ai dati DESI DR2:

Se DESI DR2 è accessibile: si costruisce un modello forward completo per i cataloghi DESI, includendo maschera angolare, funzione di selezione in redshift separata per BGS, LRG, ELG, QSO, correzione per fiber assignment bias (PIP weighting), e validazione contro BOSS CMASS come cross-check indipendente. La pipeline CAUCHY è applicata ai campi riconstruiti dai cataloghi DESI.

Se DESI DR2 non è accessibile: si sottomette il paper con i risultati Quijote. Il framing è "prima validazione sistematica dell'inferenza topologica field-level su simulazioni N-body con phantom crossing injection test". La Fase 6 DESI è citata come "in preparazione".

#### 6.2 Analisi delle Vulnerabilità Sistematiche per DESI

| Sistematica | Impatto su CAUCHY | Mitigazione |
|------------|-------------------|-------------|
| Fiber assignment bias | Correlato con il campo di densità → contamina τ(x) | PIP weighting; test: τ(x) cambia con la mappa di completezza delle fibre? |
| Sistematiche di imaging ELG | Funzione di selezione angolare modifica la topologia | Correzione Obiwan; cross-check con analisi LRG-only |
| σ₈ dipendente dal tracciatore | Tracciatori diversi danno σ₈ diversi (Maus et al. 2025) | Test di sensibilità al tracciatore: ripetere per BGS/LRG/ELG separatamente |
| RSD (Abedi et al. 2025) | Modificano sistematicamente le curve β₁ | Il modello forward deve includere RSD; test: topologia in spazio reale vs redshift |
| Incompletezza fotometrica | Il campionamento sparso crea artefatti topologici | Jackknife resampling della topologia su regioni del cielo |
| Baseline DDE da calibrazione SNe (Wang & Wang 2026, Ong 2026) | La preferenza DDE su DESI dipende dalla calibrazione SNe (DES-SN5YR vs DES-Dovekie); il "segnale" che CAUCHY cerca su DESI può essere parzialmente sistematica di calibrazione | Eseguire il triplo confronto baseline: (A) Karim 2025 ufficiale w₀≈−0.4, wₐ≈−1.7; (B) DES-Dovekie corretta (Ong 2026, ln B≈−0.01); (C) IDE-degenerate (Petri 2026, Neumann 2026). Il paper finale riporta la robustezza ai tre |

**GATE 6:** tutti i test sistematici superati. Il segnale topologico non cambia significativamente (< 1σ) quando le sistematiche sono variate entro le loro incertezze. Triplo confronto baseline DESI eseguito e documentato. Output: `results/phase6_systematics.json`.

---

### Fase 7 — Paper

**Target:** determinato dal Gate 5.  
**Titolo suggerito:** "Topological Field-Level Inference of Dynamical Dark Energy: Phantom Crossing Detection via 3D Persistent Homology and Equivariant Neural Networks"

Il paper presenta entrambi i rami: il Ramo A come validazione e confronto con la letteratura (Yip 2024, Prat 2025), il Ramo B come contributo principale. La struttura è falsificabile a ogni stadio e tutti i file di risultato sono pubblici con il codice.

---

## Parte IV — Analisi Fisher: Specifica Completa

### 4.1 Il Calcolo Centrale

L'analisi Fisher è eseguita alla fine di ogni fase. Risponde alla domanda: quali parametri cosmologici vincola CAUCHY, con quale precisione, e come migliora fase per fase?

**Osservabili utilizzati:** le feature topologiche si accumulano fase per fase. Dopo la Fase 1: (b1_peak_height, b1_peak_position, b1_width_half, b1_integral, b1_high_persistence, b2_max, b2_mean_persistence, b2_high_persistence, b0_at_mean_density). Dopo la Fase 3: le precedenti più le componenti GNN più informative (GNN_j*, j = 1, ..., K).

**Parametri di interesse:** (Ωm, σ₈, w₀). L'analisi è eseguita separatamente con dataset LHC (per Ωm, σ₈) e dataset nwLH (per w₀), dato che i due dataset coprono regioni diverse dello spazio dei parametri.

**Struttura del calcolo:**
1. Stima della matrice di covarianza del rumore dai campi fiduciali (varianza intra-cosmologia, non inter-cosmologia).
2. Stima delle derivate delle osservabili rispetto ai parametri dal dataset LHC/nwLH tramite regressione locale al fiduciale.
3. Calcolo della matrice Fisher F_ij = (∂O/∂θ_i)^T C_noise⁻¹ (∂O/∂θ_j) con regolarizzazione della matrice di covarianza.
4. Correzione di Hartlap per stima non distorta dell'inversa.
5. Vincoli marginalizzati dalla diagonale di F⁻¹.

**Confronto con benchmark:**
- DESI DR2 BAO: σ(Ωm) ~ 0.009, σ(w₀) ~ 0.08 (su survey completo, non singolo volume)
- SimBIG BOSS: σ(Ωm) ~ 0.030, σ(σ₈) ~ 0.035 (su ~10% del volume BOSS)
- Yip & Biagetti 2024: σ(w) ~ 0.06 su singolo volume (1 Gpc/h)³ con omologia persistente su aloni

CAUCHY opera su un singolo volume (1 Gpc/h)³ con galassie (non aloni): i vincoli attesi sono competitivi con Yip 2024 e complementari a DESI DR2 (statistiche diverse, correlazioni diverse).

**Degeneracy breaking:** il confronto tra la correlazione ρ(Ωm, σ₈) di CAUCHY e quella di P(k) è uno dei risultati più importanti anche in caso di non-rilevazione del phantom crossing. Se CAUCHY ha una diversa orientazione della degenerazione nello spazio dei parametri, la combinazione CAUCHY+DESI romperà la degenerazione e migliorerà i vincoli congiunti — questo è Scenario B.

---

## Parte V — Robustezza e Difendibilità Scientifica

### 5.1 Obiezioni Anticipate dei Referee e Risposte Strutturali

**Obiezione 1: "I risultati potrebbero riflettere sistematiche della pipeline DESI."**

Risposta strutturale: tutti i risultati principali sono mostrati prima su simulazioni N-body con verità nota. La sensibilità alle sistematiche DESI è analizzata nella tabella della §6.2 con un test quantitativo per ciascuna. La cross-validazione con BOSS DR12 è eseguita indipendentemente. La correlazione tra τ(x) e la mappa di completezza delle fibre è calcolata e riportata esplicitamente — se la correlazione è significativa, viene sottratta prima di procedere.

**Obiezione 2: "La CNN potrebbe stare imparando solo la varianza gaussiana (σ₈ come ampiezza)."**

Risposta strutturale: il test T1 di fattorizzazione parametrica è eseguito e riportato come Appendice A con risultati numerici completi. W₂(stesso σ₈, Ωm diverso) >> 0 è dimostrato quantitativamente. Le mappe di feature τ(x) mostrano correlazione con l'hessiano di δ(x) (struttura locale non-lineare) e non con |δ(x)| (ampiezza). Il Gate 2 deve essere superato prima che il Ramo B prosegua.

**Obiezione 3: "Perché non usare SimBIG direttamente? Cosa aggiunge la TDA?"**

Risposta strutturale: la Fase 1 documenta i vincoli Fisher dalla TDA pura. La Fase 2-3 documenta i vincoli CNN+GNN. Il miglioramento esplicito (CNN+GNN+TDA vs TDA-only) è riportato. La motivazione fisica è che la TDA cattura struttura topologica non-locale (connettività dei filamenti, geometria dei vuoti) che è inaccessibile alle operazioni convoluzionali locali di SimBIG. β₂ — inaccessibile a qualsiasi statistica 2D e di difficile interpretazione per P(k) — è la firma distintiva di CAUCHY.

**Obiezione 4: "La symbolic regression non è stabile tra i run."**

Risposta strutturale: 20 run indipendenti sono riportati con l'istogramma di frequenza delle espressioni. Solo le espressioni che appaiono in ≥ 10/20 run sono interpretate fisicamente. Il R² è valutato sul test set held-out. Se nessuna espressione stabile è trovata: è esplicitamente riportato come risultato negativo.

**Obiezione 5: "Il phantom crossing test usa dati simulati — potrebbe non applicarsi alle osservazioni reali."**

Risposta strutturale: AbacusSummit HOD a 9 parametri è usato (il più realistico disponibile). La marginalizzazione sui parametri HOD è eseguita (non HOD fisso). Il confronto tra injection test e dati DESI DR2 è eseguito se l'accesso è disponibile. Il modello forward è validato contro lo spettro di potenza osservato (deve riprodurlo entro gli errori).

**Obiezione 6 (canonica del referee post-aprile 2026): "Il segnale topologico è degenere con cosmologie IDE quintessenza non interagenti — Neumann 2026, Petri 2026, Artola 2026 dimostrano che esiste una famiglia di modelli IDE che riproduce la stessa H(z) di un CPL con phantom crossing. Come distinguete il phantom crossing fondamentale da IDE degenere?"**

Risposta strutturale: il segnale topologico di CAUCHY, analogamente alle statistiche compresse BAO+SNe, è in linea di principio degenere con cosmologie IDE-equivalenti a livello di background. Questo limite è strutturale e condiviso con qualsiasi probe basato sulla storia di espansione. Phase 5bis (vedi §3 della Fase 5bis e `CAUCHY_Literature_April2026_Update.md`) introduce due elementi di mitigazione documentati: (i) costruzione esplicita della mappa IDE-equivalente (β, w₀_de) per ogni cosmologia nwLH (output `phase5bis_IDE_mapping.json`); (ii) calcolo della differenza perturbativa ΔD(z)/D(z) tra modelli CPL e IDE-equivalenti usando le equazioni di crescita modificate di Gavela et al. 2009 (output `phase5bis_growth_factor.json`). Se ΔD/D > 1%, il segnale topologico — sensibile al collasso non-lineare e quindi a D(z) — è in linea di principio capace di disambiguare il meccanismo fisico. Il paper riporta esplicitamente questa limitazione come future work, indicando l'esecuzione di simulazioni N-body specifiche per cosmologie IDE come prossimo passo.

### 5.2 Controlli di Consistenza Interna

| Controllo | Test | Criterio di superamento |
|-----------|------|------------------------|
| Riproducibilità TDA | Stesso campo, due run | \|β_k(t)_1 − β_k(t)_2\| < 0.1% |
| Determinismo CNN | Seed fisso, due training | AUC difference < 0.002 |
| Stabilità Fisher | Jackknife sul 10% dei campi LHC | σ(Ωm) varia < 20% |
| Stabilità SR | 20 run indipendenti | Espressione migliore appare ≥ 10/20 |
| Indipendenza dal tracciatore | Ripetere con LRG-only, poi ELG-only | Rank correlation dei segnali > 0.7 |
| Robustezza HOD | Zheng 2007 vs AbacusSummit | Segnale w₀ cambia < 1σ |

---

## Parte VI — Versionamento e Riproducibilità

### 6.1 Struttura del Repository

```
cauchy/
├── README.md
├── CHANGELOG.md              ← ogni decisione metodologica documentata
├── environment.yml           ← versioni esatte dei pacchetti (conda)
├── data/
│   ├── manifest.json         ← checksum di tutti i dati di input
│   └── README.md             ← provenienza dei dati
├── src/                      ← script prodotti durante l'esecuzione
│   ├── phase0_data_prep.py
│   ├── phase1_tda_baseline.py
│   ├── phase2_cnn.py
│   ├── phase3_gnn.py
│   ├── phase4_sr.jl
│   ├── phase5_phantom.py
│   ├── phase6_desi.py
│   └── fisher_analysis.py
├── results/
│   ├── phase0_data_manifest.json
│   ├── phase0_preprocessing_lock.json
│   ├── phase1_tda_baseline.json     ← GATE 1 output
│   ├── phase2_cnn_diagnostic.json   ← GATE 2 output
│   ├── phase3_gnn_correlations.json
│   ├── phase4_sr_expressions.json
│   ├── phase5_phantom_test.json     ← RISULTATO CHIAVE
│   ├── phase6_systematics.json
│   └── fisher_all_phases.json
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_tda_visualization.ipynb
│   ├── 03_model_diagnostics.ipynb
│   └── 04_results_figures.ipynb
└── paper/
    ├── main.tex
    └── figures/
```

### 6.2 Protocollo di Logging Obbligatorio

Ogni file di risultato deve contenere:

```json
{
  "metadata": {
    "timestamp": "ISO8601",
    "git_commit": "hash del commit",
    "python_version": "3.11.x",
    "torch_version": "2.x",
    "numpy_seed": 42,
    "phase": 1,
    "gate_passed": true,
    "gate_version": "v1.0",
    "deviations_from_protocol": "note esplicite su qualsiasi deviazione"
  },
  "results": { }
}
```

Il campo `deviations_from_protocol` non è mai lasciato vuoto senza ragione: se non ci sono deviazioni, si scrive esplicitamente "none".

### 6.3 Stack Software

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

### 6.4 Budget Computazionale Stimato

| Fase | Operazione | Tempo locale | Tempo cloud (se necessario) | Costo stimato |
|------|-----------|--------------|----------------------------|---------------|
| 0 | Controlli integrità + manifest | 30 min | — | — |
| 1 | TDA su 500 campi fiduciali | ~3 ore | — | — |
| 1 | TDA su 2000 campi LHC + 2000 nwLH | ~12 ore | $20 (A100) | $20 |
| 2 | CNN training (2000 LHC) | 1–3 giorni | $100–200 (A100) | $150 |
| 3 | GNN training (2000 campi) | 2–4 giorni | $150–300 (A100) | $225 |
| 4 | SR (20 run, Julia) | ~8 ore | — | — |
| 5 | Phantom test (retraining+eval) | 1 settimana | $300–500 (A100) | $400 |
| 6 | Forward model DESI (se accessibile) | 2–4 settimane | $500–1000 (A100) | $750 |

**Costo cloud totale stimato (senza Fase 6): ~$795**  
**Con Fase 6 DESI: ~$1.300–$2.000**

---

## Appendice A — Dataset Quijote: Riferimento Rapido

| Dataset | N campi locali | Dimensione | Parametri variati | Uso primario |
|---------|---------------|------------|-------------------|--------------|
| Fiduciali PCS | 15.000 (2.000 usati) | ~10 GB | Nessuno (cosmologia fissa) | Matrice di covarianza del rumore; costruzione di μ_ΛCDM per τ(x) |
| LHC PCS | 2.000 | ~16 GB | Ωm, σ₈ (Latin Hypercube) | Gate 1a, training Fasi 2-4 |
| nwLH PCS | 2.000 | ~105 GB | w₀ ∈ [−1.30, −0.70] | Gate 1b, Fase 5 phantom crossing |

---

*CAUCHY Systematic Methodology v2.0*  
*Supersedes v1.0 — Aprile 2026*  
*Prossima revisione: dopo il superamento del Gate 1*
