# Paper 2 — sensibilità alla cosmologia fiduciale (Alcock–Paczyński)

**In preparazione.** Misura di come il deficit di generatori *H*₁ nella DESI BGS risponda alla
scelta della cosmologia fiduciale. Il manoscritto non esiste ancora: quando esisterà andrà in
`papers/paper2/MNRAS/`, escluso via `.gitignore` finché non è pubblicato.

Tutto il resto è qui, ed è il punto: **la pianificazione e la pre-registrazione sono versionate
prima dei risultati**, non dopo.

## Il documento che conta

**`paper2_prereg_v1.md`** — protocollo pre-registrato, v1.0 del 27 agosto 2026, in inglese. Nove
sezioni: cosa il documento impegna e cosa no, la regola di decisione con le sue soglie, la griglia
di misura, il budget d'errore, la procedura obbligatoria.

Il **§1 è la sezione di trasparenza, in testa e non in coda**: elenca cosa era già in mano alla data
del deposito — la Componente D interamente eseguita, le Fasi 0–2 eseguite, quattro predizioni
smentite (P1, Q1–Q4, il cancello 2.2a, il *padladder*) — e chiude dichiarando cosa era genuinamente
ignoto. Il documento pre-registra la **Fase 3 in poi**, non le fasi già eseguite, e lo dice in
apertura.

## Pianificazione

| file | contenuto |
|---|---|
| `checklist_paper2.md` | la checklist operativa, rev. 3.5. Ogni voce porta il proprio cancello, la propria predizione e l'esito |
| `canovaccio_paper2.md` | impostazione del lavoro |
| `canovaccio_paper3.md`, `canovaccio_paper4.md`, `canovaccio_4_paper_followup.md` | serie di follow-up |
| `paper2_stato.md` | glossario dei nomi, nato da collisioni terminologiche reali |
| `paper2_item*.md` | verbali dei singoli item: proposizioni, gauge, griglia, regola di decisione |
| `paper2_v1_freeze_declaration.md`, `paper2_item01_closed.md` | dichiarazione e chiusura del freeze v1 |
| `paper2_fase0_chiusura.md` | chiusura della Fase 0 |

## Metodo

- **Cancelli prima delle misure.** Ogni script riproduce almeno un valore di riferimento congelato
  prima di riportare qualcosa di nuovo. Regole di decisione e predizioni dichiarate prima di vedere
  i risultati.
- **Ranghi empirici**, non z gaussiani, come statistica di significatività primaria.
- **I risultati nulli sono pubblicabili.** La dissoluzione dell'anomalia è un esito riportabile.
- **Le predizioni smentite restano smentite**, registrate con la ragione per cui la soglia era mal
  posta. Non si riscrivono per farle tornare.
- **Emendamenti append-only** in `src/paper2_v1_amendments.jsonl`; il reference congelato non si
  modifica mai.

## Fasi 0–2, eseguite

Dieci cancelli chiusi. Gli esiti sono in `results/paper2/`: `gate21.jsonl` (chiusura verso il
Paper 1, riproducibilità della maschera, chiusura del runner), `fase2.jsonl` (dilatazione, σ_px, le
due scale), `gate25.jsonl` (appaiamento dei semi).

Due risultati che il manoscritto dovrà riportare:

**Il canale isotropo è isolato per costruzione.** I cancelli 2.3 e 2.2a condividono geometria e
maschera; cambia solo il raggio di smoothing, quindi la differenza **è** il canale: +357 generatori
in NGC e +248 in SGC. L'elasticità a σ_px è −0.267 contro −0.346: SGC risponde il 30% di più,
coerentemente con la sua occupazione minore (0.4786 contro 0.7070 galassie per voxel).

***N*_H1 segue il conteggio dei voxel di maschera**, non la risoluzione, con pendenza
0.1009 ± 0.0016 (NGC) e 0.0945 ± 0.0036 (SGC) ed elasticità **1.08**, cioè leggermente
super-lineare: i voxel aggiunti al bordo portano più anelli della media. È una funzione nota e si
**sottrae**, non si somma in quadratura. Il pavimento irriducibile che resta, nel gauge a cubo
costante, vale **0.03–0.065 σ** dell'ensemble.

## Stato

Fase 2 completa. Restano il deposito della pre-registrazione su Zenodo e, sul Paper 1, l'esito della
revisione in corso. Nessun run di Fase 3 prima che il DOI di versione sia citato nel §9 della
pre-registrazione.
