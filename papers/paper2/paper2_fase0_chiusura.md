# Fase 0 — chiusura
### Paper 2 — item 0.1 · 0.2 · 0.3 · 0.4 · 0.5 · 0.7 — 25 agosto 2026
### (0.6, pre-registrazione, è rinviato per costruzione: vedi §6)

---

## 0.5 — Ispezione del codice: le tre risposte

### Q1 — Il cubo di embedding e Δ*x* sono derivati o hard-coded?

**Risposta a tre livelli.**

**Lato dati: derivato.** `phase6_bgs_voxelize.py:166–168`

```python
box_min  = pos_r.min(axis=0) - 5.0
box_max  = pos_r.max(axis=0) + 5.0
box_size = float((box_max - box_min).max())   # box cubico
cell_size = box_size / NGRID
```

Il box è il bounding box del **catalogo random**, con 5 h⁻¹Mpc di padding additivo per lato.

**Modulo mock: hard-coded.** `phase8_cutsky_mocks.py:101–103`

```python
BOX_MIN  = np.array([-1085.5836039835003, -1059.3513403117618, -194.44091723978792])
BOX_SIZE = 1997.3629167166155
CELL     = BOX_SIZE / NGRID
```

Sedici cifre significative: valore calcolato una volta sul lato dati e incollato. È il
*"box minimum and side taken verbatim from the data voxelization"* di M26 App. C0.0.3, alla lettera.

**Ma completamente sovrascrivibile a runtime, e già esercitato.** `phase9_sgc_likeforlike.py:94–107`
deriva il box SGC dai random SGC e riscrive i globali del modulo:

```python
M.BOX_MIN = box_min ; M.BOX_SIZE = box_size ; M.CELL = cell ; M.SIGMA_PX = sigma_px
```

I due punti d'uso dei globali sono coperti: `phase8:458` (assegnazione ai voxel, usa `BOX_MIN` e
`CELL`) e `phase8:503` (smoothing, usa `SIGMA_PX`). `cic_3d` (righe 264–265) riceve la geometria per
argomento ed è già parametrizzata. **Nessun difetto.**

### Q2 — σ_px è calcolato o congelato?

**Calcolato**, `phase8:109`: `SIGMA_PX = R_SMOOTH / CELL`. Ma all'import, e da un `CELL` che discende
dal `BOX_SIZE` letterale. La catena è **letterale → derivato → derivato**; la SGC la spezza alla
radice.

### Q3 — La maschera è ricostruita o caricata?

**Ricostruita, dietro un controllo di consistenza già implementato.**
`phase9_sgc_likeforlike.py:121–137`

```
mask = None
  ... "frozen SGC mask: fill ..."
  ... "-> using frozen SGC mask (geometry consistent)."
  ... "-> frozen SGC mask INCONSISTENT with recomputed box; rebuilding."
if mask is None:
    mask = field_r > 0.01 * ref
```

Carica la maschera congelata, verifica la compatibilità col box ricalcolato, e se non è compatibile
la ricostruisce dai random con la soglia dell'1%. È il comportamento sicuro. Non va scritto: va
riusato.

---

## Proposizione 2, emendata

> **Proposizione 2 (versione corretta).** Sia il cubo di embedding il bounding box del catalogo
> random su griglia *N*³, con padding *p* per lato, e sia σ_px fissato **in unità di griglia**.
> Sotto una dilatazione isotropa *r* → α*r* delle coordinate comoventi:
>
> **(a)** se il padding è **nullo o moltiplicativo**, gli indici di voxel di ogni galassia sono
> immutati e *N*_H1 è **esattamente invariante**;
>
> **(b)** se il padding è **additivo**, come nell'implementazione (*p* = 5 h⁻¹Mpc), il box scala come
> α·(estensione) + 2*p* invece di α·(estensione + 2*p*), e l'invarianza si rompe di
> **δ = 2p(1−α)/L** in unità relative, cioè **Nδ voxel** al bordo esterno.

Quantificato sulla griglia AP effettiva (*L* = 1997.3629, cella 15.6044, *p* = 5, *N* = 128):

| α_iso | box nuovo | α·box | scarto (h⁻¹Mpc) | voxel al bordo |
|---|---|---|---|---|
| 0.9725 | 1942.710 | 1942.435 | +0.275 | 0.018 |
| 0.9900 | 1977.489 | 1977.389 | +0.100 | 0.007 |
| **1.0000** | **1997.363** | **1997.363** | **0** | **0** |
| 1.0100 | 2017.237 | 2017.337 | −0.100 | 0.006 |
| 1.0406 | 2078.050 | 2078.456 | −0.406 | **0.025** |

**0.025 voxel al massimo**, contro un residuo anisotropo fisico di **0.73 voxel**: fattore 29. La
conclusione non cambia — la componente isotropa dell'AP resta degenere con la convenzione di griglia
— ma nel manoscritto va scritto *"invariante a 2.5 × 10⁻² voxel"*, non *"esattamente invariante"*.
Un referee che ricontrolla e trova uno scarto non nullo dove è scritto "zero" ha ragione lui.

### Conseguenza sul cancello 2.2: due varianti, non una

- **2.2a — padding additivo (implementazione attuale).** Dilatare coordinate e box di α = 1.05.
  Atteso: scarto ≤ 1 generatore. Misura l'implementazione.
- **2.2b — padding riscalato o azzerato.** Stessa dilatazione con `box_min = pos_r.min()·α − 5.0·α`.
  Atteso: **esattamente zero, all'unità.** Misura la proposizione.

La coppia separa la verità del teorema dall'artefatto del codice. Una sola delle due non lo fa.

---

## Il punto d'iniezione della Fase 3 — nove costanti, non quattro

**Correzione a una valutazione precedente.** `phase9_sgc_likeforlike.py` era stato indicato come
template completo per la Fase 3. Lo è **solo per metà**: la SGC ha cambiato *geometria a cosmologia
fissa* e ha sovrascritto quattro costanti. Il Paper 2 cambia *cosmologia*, che ne tocca nove.

| # | costante | riga | dipende da | override SGC |
|---|---|---|---|---|
| 1 | `OMM = 0.3175` | 112 | cosmologia fiduciale | ❌ |
| 2 | `OML = 1.0 - OMM` | 113 | ← 1, all'import | ❌ |
| 3 | `_DC_TAB = comoving_distance(_Z_TAB)` | 152 | ← 1,2, all'import | ❌ |
| 4 | `D_C_ZMIN = 292.535950750378` | 104 | ← 3 | ❌ |
| 5 | `D_C_ZMAX = 1080.7298534541035` | 105 | ← 3 | ❌ |
| 6 | `BOX_MIN` (3 componenti, 16 cifre) | 101 | random + cosmologia | ✅ riga 104 |
| 7 | `BOX_SIZE = 1997.3629167166155` | 102 | random + cosmologia | ✅ riga 105 |
| 8 | `CELL = BOX_SIZE / NGRID` | 103 | ← 7, all'import | ✅ riga 106 |
| 9 | `SIGMA_PX = R_SMOOTH / CELL` | 109 | ← 8, all'import | ✅ riga 107 |

Le voci 4 e 5 sono verificate come *D*_C(0.1) e *D*_C(0.4) nella fiduciale, a nove cifre.

**Perché le cinque scoperte sono critiche.** Definiscono la finestra di selezione radiale. Se
restano ai valori fiduciali mentre le posizioni sono calcolate in un'altra cosmologia, il campione
viene tagliato nel posto sbagliato:

| Ω_m | *w*₀ | scarto su *D*_C(0.4) | in voxel |
|---|---|---|---|
| 0.25 | −1.2 | +55.26 | **3.54** |
| 0.35 | −0.8 | −36.82 | **2.36** |
| 0.35 | −1.2 | +16.47 | 1.06 |
| 0.25 | −0.8 | −13.30 | 0.85 |

Fino a **3.5 voxel** al bordo esterno: cinque volte il segnale AP anisotropo che vogliamo misurare, e
con la stessa dipendenza dalla fiducia. Sarebbe indistinguibile da una risposta fisica.

### Il rovescio elegante

Il codice **non ha un parametro *w*₀**: `OML = 1 - OMM` è ΛCDM piatto e basta. La griglia
(Ω_m, *w*₀) del canovaccio originale avrebbe richiesto di riscrivere `comoving_distance`.

Ma tutto passa per l'interpolazione `_Z_TAB` → `_DC_TAB`. **Sostituendo `_DC_TAB` con una qualunque
tabella monotona si inietta una rimappatura radiale arbitraria**: *w*₀ ≠ −1, α_iso puro, *F*_AP puro,
o qualunque combinazione. La parametrizzazione (α_iso, *F*_AP) — scelta nella Fase 1 per ragioni
teoriche — si innesta sull'architettura esistente meglio della griglia cosmologica, e senza toccare
la funzione che calcola le distanze.

### Il lavoro da fare prima di qualunque run di Fase 3

- [ ] **E1 — `set_geometry(dc_tab, box_min=None, box_size=None)` in `phase8_cutsky_mocks.py`.**
      Imposta tutte e nove le costanti **atomicamente**, deriva 2/3/4/5 da `dc_tab` e 8/9 da 7, e
      asserisce a valle: `CELL == BOX_SIZE/NGRID`, `SIGMA_PX == R_SMOOTH/CELL`,
      `D_C_ZMIN/ZMAX == interp(dc_tab, [0.1, 0.4])`. Nessun globale geometrico va più toccato a mano.
- [ ] **E2 — Test di equivalenza, gratuito.** Al fiduciale `set_geometry()` è un no-op: il cancello
      2.1 deve continuare a dare 28 256 e 35 436.7 ± 313.0. Poi far chiamare `set_geometry()` a
      `phase9_sgc_likeforlike.py` e verificare che riproduca 15 122 e 18 713.0 ± 197.8. Se entrambi
      passano, il rifattorizzato è dimostrato equivalente su numeri **pubblicati**, non su un test
      inventato per l'occasione.
- [ ] **E3 — Stessa disciplina sul lato dati.** `phase6_bgs_voxelize.py` deriva il box ma usa la
      cosmologia fiduciale per convertire *z* → *D*_C: va parametrizzato allo stesso modo.

---

## 0.2 — Dipendenza dal Paper 1

**Registrata.** Il Paper 2 cita Prop. 1 (invarianza monotona, §2.3), il criterio w̄ ≳ 0.99 come
condizione differenziale (§8.2), il bound FKP di −78.0 ± 8.0 (§7.2) e la Tab. 8 delle asimmetrie
residue. Tutti possono ancora cambiare in revisione.

**Regola:** non sottomettere il Paper 2 prima che il Paper 1 sia accettato o almeno fuori dal secondo
giro di referee. Nessun vincolo invece sull'**esecuzione**: le Fasi 1–4 possono partire subito, ed è
anzi utile che lo facciano — se la Componente C scopre che l'attribuzione di §8.1 è sbagliata, il
Paper 1 è ancora in tempo per correggersi.

---

## 0.3 — Ri-perimetrazione della Componente B

**Chiusa** nel canovaccio rev. 25 agosto. Formulazione ritirata: *"caratterizzare non è correggere"*.
La correzione FKP alla sorgente **è stata eseguita** nel Paper 1 §7.2 (*w*_FKP dal random, peso medio
in-maschera 0.309, 60 coppie appaiate, Δ*N*_H1 = −78.0 ± 8.0, −1.09% del deficit).

Resta al Paper 2: l'ensemble v2 completo sui 2000, le cinque predizioni a un punto mai misurate
(incluso il restringimento della sensibilità Box–Cox), e il cancello di Tab. 12 sulle quantità che
**non** dipendono dai pesi.

---

## 0.4 — Tensione erosione ↔ FKP

**Registrata.** §8.1 attribuisce il massimo del deficit a *k* = 1 alla rimozione del primo strato
contaminato FKP; §7.2 misura la pesatura FKP a −78 loop mentre l'escursione *k* = 0 → *k* = 1 vale
≈ +1840. **Fattore ~24.** Le due misure non sono compatibili con la stessa spiegazione causale.

**Bloccata da un'ambiguità di provenienza.** Il congelamento ha trovato due coppie di record di
erosione, non copie l'una dell'altra:

```
5 645 byte  af80917abbc4  paper1_erosion_NGC_restrict_bak.json   24 lug 13:14
2 808 byte  57b80df172f0  paper1_erosion_NGC_restrict.json       26 lug 14:21
5 635 byte  3ae1a7c12eb6  paper1_erosion_SGC_restrict_bak.json   24 lug 13:30
2 868 byte  bc63a27eb79f  paper1_erosion_SGC_restrict.json       26 lug 14:17
```

Il più vecchio è il più grande. La finestra 24→26 luglio è quella in cui l'escursione è stata
corretta (M26 R1: *"complete-ladder excursion 6.8/9.8 percentage points, correcting the submitted
2.0/2.7"*). Prima di rieseguire la scala su v2 serve sapere quale file sostiene Tab. 9–10, altrimenti
il confronto v1 ↔ v2 non ha un termine di paragone. Si lega al chiarimento già in sospeso fra `--k`
e `n_mocks` in `paper1_mask_erosion.py`.

---

## 0.7 — Numerazione delle limitazioni

**Chiusa.** M26 R1 elenca da (i) a (xi). Il Paper 2 chiude la **(ix)**. La (vii) è chiusa da R1
stessa; la (xi) è in gran parte chiusa dal Paper 1 §5.2; la (x) è nuova e apre il Paper 3-bis. Il
Paper 2 dichiarerà esplicitamente quali restano aperte dopo di sé.

---

## 0.6 — Perché è rinviato, e non dimenticato

La pre-registrazione deve contenere la **regola di decisione dell'item 1.4** (procedere come misura
di sensibilità se l'AP muove il deficit di più di 3σ_Δ ≈ 750 generatori; riformulare come limite
superiore altrimenti). Quella regola si formula dopo il triage di Fase 1, non prima.

**Vincolo che resta:** la pre-registrazione va depositata **prima di qualunque run di Fase 3**. Le
Fasi 1 e 2 sono triage e cancelli su numeri già pubblicati, quindi non richiedono pre-registrazione;
la Fase 3 produce numeri nuovi e la richiede.

---

## Prossimo passo

Il triage di **Fase 1**, che è dove il paper si decide. Nell'ordine:

1. **1.1** — enunciato e dimostrazione della Proposizione 2 emendata
2. **1.2a/b** — ricalcolo della tabella AP col box effettivo e w̄ per punto
3. **1.5a** — molteplicità di tiling per punto
4. **2.1 → 2.2a/2.2b → 2.3** — i cancelli

**Il punto di decisione è dopo 2.3.** Ma prima serve **E1**, la `set_geometry()` atomica: senza,
qualunque run di Fase 3 può produrre in silenzio un errore da 3.5 voxel che assomiglia a un segnale.
