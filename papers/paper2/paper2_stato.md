# Paper 2 — stato consolidato
### Indice unico di tutto ciò che è aperto e chiuso — aggiornato 25 agosto 2026

> **Perché questo file esiste.** Le voci sono state etichettate due volte con lo stesso schema di
> lettere in contesti diversi (le "ambiguità" A–E del riepilogo di Fase 0 contro le sezioni A/B/C/E
> della sonda di provenienza), e due voci sono uscite dal discorso per collisione di nomi. Da qui in
> avanti ogni voce ha un prefisso che ne dichiara la famiglia, e questo file è l'unico indice.

**Famiglie:** `F` fase della checklist · `P` provenienza · `G` geometria/codice · `S` sottoprodotto
scientifico · `R` rilascio

---

## Chiusi

| id | voce | esito |
|---|---|---|
| **F0.1** | congelamento ensemble v1 | 5 tier, 34 836 file, 26.771 GiB, digest riprodotti dopo il commit |
| **F0.2** | dipendenza dal Paper 1 | registrata: vincola la sottomissione, non l'esecuzione |
| **F0.3** | ri-perimetrazione Componente B | canovaccio rev. 25 ago; ritirata la formulazione «caratterizzare non è correggere» |
| **F0.4** | tensione erosione ↔ FKP | registrata; provenienza chiarita da P-B |
| **F0.5** | ispezione del codice | Q1 derivato/hard-coded/sovrascrivibile · Q2 derivato · Q3 ricostruita con controllo |
| **F0.7** | numerazione limitazioni | M26 R1 va da (i) a (xi); il Paper 2 chiude la (ix) |
| **P-A** | due CSV byte-identici | entrambi refit HOD (35 304.56 ± 1033.00, min 27 766) → **nome sbagliato, dato integro** |
| **P-B** | record erosione `_bak` | stato pre-correzione: raggi ritirati ai livelli {0,2,3}, **senza *k*=1** |
| **P-C** | otto `*_manifest.json` identici | registri di completamento `{indice:"done"}`: 30 890 B = 2000 voci esatte → **benigno per costruzione** |
| **P-A1** | CSV mal etichettato | il pilota canonico non e' mai arrivato in git: ogni versione committata e' il refit HOD. Rimosso; `phase8_w0_exclusion.py` fallisce rumorosamente su sorgente mancante |
| **P-D** | dove vive l'ensemble canonico | `per_mock_{NGC,SGC}_R5.jsonl` → **`base.N_H1`**: 35 436.686 ± 312.989 e 18 712.968 ± 197.787. Bersagli del cancello 2.1 |
| **G2** | `set_geometry()` atomica | inserita in `phase8_cutsky_mocks.py:192`; **9 blocchi di test verdi**, no-op bit-esatto al fiduciale |
| **G3** | lato dati parametrizzato | `paper2_data_geometry.py`; NGC **10/10**, SGC **6/6** contro i record congelati |

---

## Aperti — azioni immediate

| id | voce | costo |
|---|---|---|
| **P-A1** | rimuovere o rinominare `phase8_test2_permock.csv`; ricostruire il manifest `records` **da zero** (append-only: `--force` lascerebbe la voce stantia). Il digest `e905d7fd…` cambierà. **Prima:** `grep` per verificare che nessuno script legga quel percorso. | minuti |
| **P-D** | confermare che `per_mock_NGC_R5.jsonl` → `base.N_H1` dia 35 436.7 ± 313.0 e rango 1/2001. È il campo che il **cancello 2.1** deve interrogare. | secondi |

**Non si fa più:** `P-A2` (il sottoinsieme etichettato di M26 §5.5 ha la firma del refit HOD anziché
del baseline). M26 è troppo avanti per correggerlo. Resta **registrato** qui perché il Paper 2 non
deve ripetere l'ambiguità: quando citerà la risposta cosmologica, dirà **quale HOD** ha prodotto i
mock etichettati.

---

## Aperti — prerequisiti della Fase 3, prima di qualunque run

Ex «ambiguità D ed E», riclassificati: non sono problemi di provenienza, sono ingegneria.

### G1 — Nove costanti geometriche, non quattro

| # | costante | riga | dipende da | override SGC |
|---|---|---|---|---|
| 1 | `OMM = 0.3175` | 112 | cosmologia fiduciale | ❌ |
| 2 | `OML = 1.0 - OMM` | 113 | ← 1, all'import | ❌ |
| 3 | `_DC_TAB = comoving_distance(_Z_TAB)` | 152 | ← 1,2, all'import | ❌ |
| 4 | `D_C_ZMIN = 292.535950750378` | 104 | ← 3 | ❌ |
| 5 | `D_C_ZMAX = 1080.7298534541035` | 105 | ← 3 | ❌ |
| 6 | `BOX_MIN` (3 comp., 16 cifre) | 101 | random + cosmologia | ✅ 104 |
| 7 | `BOX_SIZE = 1997.3629167166155` | 102 | random + cosmologia | ✅ 105 |
| 8 | `CELL = BOX_SIZE / NGRID` | 103 | ← 7, all'import | ✅ 106 |
| 9 | `SIGMA_PX = R_SMOOTH / CELL` | 109 | ← 8, all'import | ✅ 107 |

Le voci 4 e 5 sono *D*_C(0.1) e *D*_C(0.4) fiduciali, verificate a nove cifre. Se restano ferme
mentre le posizioni cambiano, la finestra di selezione radiale taglia il campione fino a **3.5 voxel**
fuori posto al bordo esterno: cinque volte il segnale AP anisotropo, e con la stessa dipendenza dalla
fiducia. Sarebbe indistinguibile da una risposta fisica.

### G2 — `set_geometry()` atomica — ✅ CHIUSO

Inserita a `phase8_cutsky_mocks.py:192`, con `make_dc_tab_ap()` a seguire. Nove blocchi di test
verdi (`results/paper2/g2_equivalence.json`, `failures: []`):

| test | esito |
|---|---|
| T1 no-op al fiduciale | scarto **esatto zero** su 7 costanti + `_DC_TAB` + `_Z_TAB` + `BOX_MIN` |
| T2 geometria SGC | σ_px derivata **0.336055** contro **0.3361** pubblicato |
| T3 α_iso puro | max\|dc/dc0 − α\| = 1.1×10⁻¹⁶ su 4000 punti |
| T4 *F*_AP puro | pivot fermo, monotonia preservata |
| T5 monotonia **e atomicità** | tabella respinta *e* stato ripristinato interamente |
| T6 `omm`/`dc_tab` esclusivi | respinti insieme |
| T8 tabella iniettata | `comoving_distance` la segue, scarto 0 |
| T9 ritorno al fiduciale | forma analitica ripristinata, costanti esatte |

**Tre difetti trovati dai test, nessuno visibile a runtime:**

1. `np.power(..., where=)` senza `out=` lasciava memoria non inizializzata nelle celle escluse.
2. `comoving_distance` non ridiretta sull'iniezione: i mock sarebbero stati carvati con la
   mappatura nuova e i dati convertiti con quella vecchia — **2.77 voxel** di disallineamento a
   α_iso = 1.04, quasi quattro volte il segnale AP fisico.
3. **Non atomica sul fallimento**: la tabella veniva assegnata *prima* del controllo di monotonia,
   quindi un input respinto lasciava il modulo corrotto. Il chiamante vedeva un `ValueError` e
   credeva che nulla fosse cambiato.

Il terzo è il più istruttivo: respingere un input non basta, e una funzione che promette atomicità
deve garantirla anche sull'errore. Ora `set_geometry()` fa snapshot, delega a
`_set_geometry_unchecked()` e ripristina su qualunque eccezione.

**Adozione in `phase9_sgc_likeforlike.py`** (facoltativa, quando conviene): le sei assegnazioni
inline delle righe 104–109 diventano `M.set_geometry(box_min=box_min, box_size=box_size)` più le
due righe di percorsi. Le quattro geometriche si muovono insieme o non si muovono.

### G3 — Lato dati parametrizzato — ✅ CHIUSO

`paper2_data_geometry.py` riproduce la logica di `phase6_bgs_voxelize.py` senza toccarlo, e la
riproduzione è validata contro i record congelati: **NGC 10/10** (box, cella, σ_px, α, *N*_data,
*N*_rand, voxel, `box_min`×3) e **SGC 6/6** (via `phase9_sgc_likeforlike.json`, che conserva la
geometria SGC perduta dal record di phase6).

Fornisce `positions()` — conversione senza CIC — che risolve il problema dell'uovo e della gallina:
i loader di phase8 convertono e voxelizzano insieme usando `BOX_MIN`/`BOX_SIZE`, ma per derivare il
box servono le posizioni. L'ordine obbligato della Fase 3 è documentato in testa al file.

**Due misure nuove uscite da qui:**

*Regola della maschera.* Nella pipeline convivono `0.01 * field_r.mean()` (phase6, che ha prodotto
v1) e `0.01 * field_r[field_r>0].mean()` (phase9, ramo di ricostruzione). Il rapporto delle soglie è
**6.547**, come previsto da 1/fill — ma il conteggio dei voxel cambia solo del **−3.27%** (307 805 →
297 731), perché il campo random cade ripidamente al bordo e pochi voxel stanno nella fascia dove la
soglia decide. Calibrando sull'erosione *k*=1 del Paper 1 (−15.4% voxel → +5.2 pp), vale **~1.1 pp**,
cioè il 5.4% in relativo e il 18% della banda sistematica 17–29%.

> Correzione a una stima precedente: avevo previsto ~9 pp estrapolando dal rapporto delle soglie
> senza conoscere la distribuzione del campo random al bordo. Sbagliata di un ordine di grandezza.
> Il motivo per correggere la regola resta strutturale — è un cambio di *definizione* che si applica
> a ogni punto non fiduciale e non al fiduciale, quindi un sistematico differenziale che si somma al
> segnale invece di essere comune modo — ma non è dominante.

*Il record di phase6 descrive un run a R = 14.8.* Confermato: `R_smooth_mpc_h: 14.8` sia al livello
alto sia nel blocco NGC. Quarto caso di **S5**. Tutto il resto del record è indipendente da *R* — box,
cella, α, conteggi, e **la maschera**, che si calcola prima dello smoothing — quindi resta
confrontabile. Conseguenza inerte ma da sapere: `data/processed/phase6_fields/bgs_ngc_delta_128.npy`
su disco è smussato a *R* = 14.8, sotto un nome che non lo dice. È innocuo solo perché
`phase8_cutsky_mocks.py:535-539` dichiara esplicitamente di non usarlo e ricalcola il riferimento
DESI da sé.

### G4 — Il punto d'iniezione, e perché la riparametrizzazione era la scelta giusta

Il codice **non ha un parametro *w*₀** (`OML = 1 - OMM`, ΛCDM piatto). La griglia (Ω_m, *w*₀) del
canovaccio originale avrebbe richiesto di riscrivere `comoving_distance`. Ma tutto passa per
l'interpolazione `_Z_TAB` → `_DC_TAB`: **sostituendo `_DC_TAB` si inietta una rimappatura radiale
arbitraria**, inclusi *w*₀ ≠ −1, α_iso puro e *F*_AP puro. La parametrizzazione (α_iso, *F*_AP),
scelta nella Fase 1 per ragioni teoriche, si innesta sull'architettura esistente meglio della griglia
cosmologica — e senza toccare la funzione delle distanze.

---

## Aperti — rilascio

| id | voce |
|---|---|
| **R1** | tag `v2.0-m26-r1` e `v2.1-paper1` (retroattivi, da dichiarare come tali), push, rilascio Zenodo sotto il concept DOI |
| **R2** | `REPRODUCIBILITY.md` alla radice: mappa manoscritto → tag → DOI di versione → digest congelati. **Bloccato da P-A1**, che cambia il digest `records` |
| **R3** | tarball del tier `features` (24 MB) nel deposito Zenodo, accanto al repository: sono le misure per-mock, e servono a ricontrollare 35 436.7 ± 313.0 senza rigenerare 15 GiB |
| **R4** | `git gc` per consolidare i 13 packfile (cosmetico) |

---

## Sottoprodotti scientifici

Vedi `paper2_sottoprodotti.md`. In sintesi: **S1** zero duplicati in 34 611 artefatti (chiude per
esclusione le realizzazioni duplicate come sorgente di dispersione deflazionata); **S2** l'escursione
ritirata 2.0/2.7 era la scala priva di *k*=1; **S3** tre correzioni appaiate riprodotte dai soli
record archiviati; **S4** note di provenienza minori (due valori di σ_px fiduciale, tre precisioni
del lato del box).

---

## Ordine di esecuzione

```
P-A1, P-D            (minuti)          ->  Fase 0 chiusa
   |
G2, G3               (mezza giornata)  ->  la Fase 3 diventa sicura
   |
F1.1  Prop. 2 emendata
F1.2a/b  tabella AP col box effettivo, w̄ per punto
F1.5a  molteplicità di tiling per punto
   |
F2.1 -> F2.2a/2.2b -> F2.3            <-- PUNTO DI DECISIONE
   |
F1.4 regola di decisione -> F0.6 pre-registrazione
   |
Fase 3 / Fase 4
```

**R1–R4** possono correre in parallelo, purché **R2 aspetti P-A1**.
