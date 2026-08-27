# Stato della major revision — MN-26-2847-P

Aggiornato: luglio 2026. Sostituisce l'ordine operativo di
`piano_risposta_review_01.md` §"Ordine operativo proposto".

Legenda: ✅ chiuso · 🟡 parziale · ⬜ da fare · 🔒 bloccante per altro

---

## 1. I tre punti bloccanti dell'editore

### E1 — Identità della statistica primaria ✅ **CHIUSO, con prova dal codice**

`phase8_cutsky_mocks.compute_tda_features` (righe 344–356):

```
feats[1] = b1_curve[pk]   # picco della curva di Betti-1
feats[4] = len(p1)        # conteggio TOTALE delle coppie H1 finite
```

`beta1_max` in M26 **è** `feats[4]`, cioè il conteggio totale. Quindi:

- la definizione di Paper 1 («conteggio totale delle coppie H1 finite») è **corretta**
- la dicitura di M26 («the finite H1 generator count *at the Betti-curve peak*»)
  è **errata**

Non è una scelta fra convenzioni: è un errore di etichetta in M26, localizzabile in
una riga. Il valore congelato 28 256 e tutti i rank e i deficit che ne discendono
sono corretti in Paper 1.

**Resta da fare:** ⬜ T2 (definizione inequivoca + nota terminologica in Paper 1),
⬜ correzione nella revisione di M26, ⬜ nota all'editore di M26.

### E2 — Disciplina della significatività + discrepanza di dispersione ✅ **CHIUSO**

Documentato in `paper1_sigma_discrepancy_resolution.md`.

**Discrepanza 313 vs 445 — risolta e invertita di direzione.** Il record congelato
`phase8_test2_masked.json` (2026-07-03, N=2000, masked) riporta
σ = 312.9891651683112, riprodotto cifra per cifra da `paper1_remap.py`. Il 445 viene
da `phase9_extract_features.py`, una ricomputazione che per gli indici 0–199 leggeva
cubi sovrascritti da un run successivo a 200 mock con HOD diverso; il suo controllo
di consistenza confrontava la media (drift 0.038, superato) e **mai la deviazione
standard**. Prova diretta: il CSV del pilota coincide con l'npz su 200/200 valori e
con i nostri su 0/200.

**Il referee legge la discrepanza al contrario.** Paper 1 non ha ristretto la σ: usa
quella congelata. È M26 ad avere il numero contaminato.

**Regressione statistica — difesa disponibile.** Il record congelato contiene già
`"N=2000; empirical p-floor ~1/2001. Ranks primary."`: la disciplina dei rank era
designata nel run originale, prima di qualunque rapporto. La regressione sta
nell'aver titolato z = −22.9 nell'abstract, cioè nella presentazione, non nel metodo.

**Correzione a una premessa di R3.7.** Il referee cita «il 94% della varianza è
cosmologica». Misurato a n = 2000: **26.1%** (§3 di
`paper1_variance_decomposition.md`). L'obiezione sui rank resta valida; la
contaminazione da mescolamento di cosmologie è 3.5× minore di quanto assunto.

**Resta da fare:** ⬜ T3 (rank primari in abstract, Tab. 2, conclusioni; z
parentetiche e ribattezzate).

### E3 — Divario fra dimostrato e affermato 🟡 **APERTO — è il punto che decide il paper**

Richiede N1 (vedi §3). Nessun avanzamento su questo asse.

**Ma M1 ha cambiato le probabilità a priori, e in direzione sfavorevole alla tesi
attuale.** La gerarchia misurata dei driver di N_H1 è nₛ (+0.376, t = 19.3), h
(+0.210), σ₈ (+0.182), Ωm (+0.154), Ωb (−0.128): **sono tutti e soli i parametri che
governano la FORMA dello spettro di potenza.** N_H1 è una sonda spettrale, non di
ampiezza — come il lemma di invarianza monotona prevede.

Questo rende l'ipotesi di R3 — che il deficit sia una proprietà a due punti — **più
plausibile**, non meno. Va affrontato di petto in N1, non aggirato.

Con una sfumatura importante che gioca in senso opposto: per spiegare 7181
generatori con la sola forma servirebbe Δnₛ ≈ 7.1, assurdo. Quindi *entro la
famiglia cosmologica* nessuna forma raggiunge il deficit. La domanda di N1 resta
genuinamente aperta: DESI giace sulla relazione P_small–N_H1 dei mock, o ne cade
fuori?

---

## 2. Chiuso oltre il piano

| voce | esito |
|---|---|
| ✅ V3 rank empirico | 1/2001 in entrambi gli emisferi, 0 mock sotto DESI, invariante sotto ogni trattamento; margine sotto il minimo dell'ensemble +2970 (NGC), +1100 (SGC) |
| ✅ Verifica ramo SGC | pulito: maschera congelata effettivamente usata (8.2123%), `k_mocks=200` confermato, σ_px identico; σ = 178 a N = 200 è il 42° percentile di sottocampioni dai nostri 2000 |
| ✅ Taglio in redshift SGC | `ZMIN, ZMAX = 0.1, 0.4` condivisi con NGC: nessuna violazione del like-for-like |
| ✅ M1 risposta cosmologica a n = 2000 | R² = 0.261; gerarchia nₛ > h > σ₈ > Ωm > Ωb > Mν > w0 |
| ✅ Decomposizione della varianza | cosmologia 160 (26.1%) + realizzazione 246 (61.6%) + HOD 110 (12.3%) = 313.4 vs 312.99 misurata. Nessun residuo |
| ✅ **Tetto cosmologico al deficit** | l'angolo più estremo dell'hypercube dà 1233 generatori; il deficit è 7181: **manca di 5.8×** (SGC 4.7×). Argomento nuovo, più forte di qualunque cosa nel manoscritto |
| ✅ Decisione Paper 5 | riformulare: r(N_H1, w0) = +0.055 [+0.012, +0.099], soglia 0.10 non raggiunta |

---

## 3. Ordine di esecuzione

### Passo 0 🔒 — Correzione dei percorsi di uscita *(30 min, BLOCCANTE)*

`phase8_test2_masked.py`: `tbl` e `out_fields` scrivono sempre sugli stessi
percorsi mentre il JSON si dirama su `--hod_json`. **È il bug che ha prodotto
l'intera contaminazione.** Va corretto **prima** di qualunque run che salvi campi o
tabelle per-mock — cioè prima di M2, N6, N7 — altrimenti si ripete.

Nella stessa passata: docstring di `load_nwlh_params()` (dichiara 6 colonne, sono 7)
e propagazione di `--project_root` a `M.ROOT` in `phase8_test2_masked.main()`.

### Passo 1 — Esperimenti gratuiti sui dati già in mano

Tutti dallo stesso ensemble, nessuna nuova pipeline.

| | punto | costo | perché in testa |
|---|---|---|---|
| ⬜ **N1** | R3.1c, E3 | quasi nullo | **decide titolo, abstract e §7.** Va per primo |
| ⬜ **N2** | R1.3 | gratuito | segnalato dall'editore come decisivo; senza il grafico persistenza-taglio l'interpretazione non ha appoggio |
| ⬜ N3 | R3.3 | gratuito | risolve «statistically independent channels» |
| ⬜ N4 | R2.6, R3.min3 | quasi nullo | stabilità P5/P15 |
| ⬜ N5 | R3.6iv, R2.min1 | gratuito | omogeneità delle incertezze |
| ⬜ **Tetto non lineare** | difende §4 | 30 min | aggiungere termini quadratici e incrociati alla regressione e vedere di quanto sale l'escursione massima. R² = 0.26 significa che il fattore 5.8 vale al primo ordine: un referee lo chiederà. Meglio misurarlo che argomentarlo |

### Passo 2 — M2, verifica del termine preso in prestito *(come un run Test 2)*

⬜ Pipeline Test 2 cut-sky sui 2000 cataloghi in
`data/raw/quijote/3D_cubes/fiducial/`. Misura σ(realizzazione+HOD) nella geometria
del paper e **verifica indipendentemente il 110 di M26**, che è l'unico numero della
decomposizione che stiamo ancora prendendo in prestito da un run non controllato.
Chiude le riserve di §3.1 di `paper1_variance_decomposition.md`.

Può girare mentre si scrive.

### Passo 3 — Il bound satelliti, prima del test *(analitico, poche ore)*

⬜ N7a. L'editore chiede «tested **or quantitatively bounded**»: il bound analitico
potrebbe bastare e costa un ordine di grandezza meno del run NFW. Da fare prima di
decidere se serve N7b.

### Passo 4 — Esperimenti con modifica di pipeline

⬜ N6 (pesi FKP, N = 200) · ⬜ N7b (satelliti NFW, N = 200, se il bound non basta) ·
⬜ N8 (maschere sintetiche per il criterio w̄)

### Passo 5 — Condizionali

⬜ N10 (gaussianizzazione / fasi randomizzate): **solo se N1 non chiude la
questione**. ⬜ N9 (convergenza di risoluzione): decisione da prendere insieme dopo
N1, perché se il paper si re-intitola sull'origine spettrale la semantica della
scala cambia peso.

### Passo 6 — Riscrittura, T1–T18

Tutti ⬜. Quattro sono condizionati agli esiti: T4 (definizione di «fase») e il
titolo dipendono da N1; T7 dallo scope di N8; T9 da N7; T11 da N3; T14 da N1/N2.

Il materiale nuovo da inserire, non previsto nel piano: il tetto cosmologico di §4
(entra in §7 e nell'abstract), la decomposizione corretta (sostituisce il rimando a
M26 5.5), la citazione di `"Ranks primary"` dal record congelato (disinnesca
l'accusa di regressione), e «N_H1 è una sonda di forma» che alimenta T14.

### Passo 7 — Comunicazione unica all'editore di M26

⬜ Come concordato, a fine lavoro, così le correzioni vanno in un unico invio.

---

## 4. Correzioni a M26 (`cauchy_mnras.tex`, ancora in review)

| # | dove | correzione |
|---|---|---|
| 1 | Sez. 3.1 e App. A | definizione di β₁^max: **non** «at the Betti-curve peak» ma conteggio totale delle coppie H1 finite. Considerare la ridenominazione del simbolo, che è fuorviante |
| 2 | tabella battery, righe 459/510/636 | σ NGC 445 → **312.99** |
| 3 | riga 735 | frazione stocastica 6% → **12.3%**; e **riscrivere l'attribuzione**: il driver è nₛ, non Ωm. Correlazioni +0.45/+0.29/−0.03 → nₛ +0.376, h +0.210, σ₈ +0.182, Ωm +0.154, Ωb −0.128, Mν −0.048, w0 +0.055 |
| 4 | riga 735 | «the remaining ~94% is cosmological» → decomposizione misurata: cosmologia 26.1%, realizzazione 61.6%, HOD 12.3% |
| 5 | riga 735 | «the single mock below the data is itself the extreme low-Ωm corner (Ωm = 0.10)» → da verificare: il mock 139 (Ωm = 0.1033) ha N_H1 = 34 119, mentre il minimo dell'ensemble è il mock 1666 a 31 226 |
| 6 | Sez. robustezza, riga 675 | SGC: «below *all* 200 mocks (z = −20)» → **rank 1/201, p ≤ 5.0 × 10⁻³**, per coerenza con la disciplina che E2 impone. Nota favorevole: il nostro SGC a N = 2000 dà rank 1/2001, p ≤ 5.0 × 10⁻⁴ — Paper 1 qui **rafforza** M26 di un fattore dieci |
| 7 | figure e appendici | prodotti derivati dall'npz contaminato: istogramma empirico, curva di risposta a w0, `phase9b_majors`. Da rigenerare |

Nota di merito: la correzione **rafforza** M26. La σ corretta è più piccola, quindi
il deficit è più significativo, non meno; e il tetto cosmologico del fattore 5.8 è
un argomento che M26 non aveva.

---

## 5. Impatti sugli altri lavori

**Paper 2 (Alcock–Paczyński).** Nessun impatto strutturale. Erediterà la σ corretta
e la decomposizione; T10 continua a rimandare l'AP a Paper 2 come previsto.

**Paper 3 (replica BOSS DR12) e Paper 4 (altMTL + Uchuu).** Impatto **preventivo**:
entrambi useranno la stessa pipeline con salvataggio di campi e tabelle per-mock. Il
Passo 0 va fatto prima, o la contaminazione da percorsi condivisi si ripresenta su
un ensemble nuovo — e in Paper 3, che è a protocollo pre-registrato, sarebbe molto
più grave.

**Paper 5 (CPL w0–wa).** Riformulato. Tesi nuova, misurata: «N_H1 è una sonda di
forma dello spettro, e il deficit non è raggiungibile da nessuna forma entro
ΛCDM+w0». Resta ⬜ M3 (inventario delle realizzazioni per punto di griglia in
AbacusSummit), non più per decidere ma per **giustificare** la riformulazione nel
testo. Vedi `canovaccio_paper5.md` §5 e
`paper1_variance_decomposition.md` §5.

**Protocollo di pre-registrazione.** R2.min3 e R3.min1 contestano l'aggettivo
«pre-registered» perché nessun protocollo è citato nel manoscritto. Il protocollo
**esiste** (`paper1_preregistration_protocol.md`): basta citarlo e pubblicarlo
(repo + Zenodo, come M26). È l'obiezione più facile del lotto e attualmente non è
sfruttata.

---

## 6. I bivi che decidono la forma finale

1. **N1.** DESI sulla relazione P_small–N_H1 → il paper si re-intitola sull'origine
   spettrale, e «fase» esce da titolo e abstract. DESI fuori dalla relazione → è la
   prova che R3 chiede, più forte di tutto il resto, e «beyond-two-point» diventa
   dimostrato. **M1 ha spostato le probabilità verso il primo esito.**
2. **N2.** Il deficit vive nelle coppie a bassa persistenza → «deficit di
   fluttuazioni a scala di voxel», compatibile con effetti di campionamento, e
   l'interpretazione strutturale cade. Vive nelle coppie persistenti → si rafforza
   molto.
3. **N7.** Se il bound sul profilo dei satelliti non è trascurabile, «genuine
   difference in the connectivity of the cosmic web» esce dall'elenco delle
   spiegazioni, come l'editore chiede in via subordinata.

---

## 7. Rischio principale

I punti chiusi finora sono tutti **verifiche fattuali** su dati esistenti: E1, E2,
V3, SGC, M1. Il punto che decide il paper — E3, via N1 — non è ancora stato
toccato, ed è anche quello con il maggior potenziale di ribaltare titolo e tesi.

La sessione ha prodotto una correzione importante a un paper in review e un
argomento nuovo e forte, ma ha anche consumato tempo su una deviazione (il pilota in
scatola) evitabile. N1 costa quasi nulla e va prima di tutto il resto.
