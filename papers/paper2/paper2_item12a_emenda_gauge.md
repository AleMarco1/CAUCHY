# Paper 2 — emenda a 1.2a e 1.3: il residuo anisotropo non è invariante di gauge
### 25 agosto 2026 — nasce dalla domanda «con quale peso si fitta α_iso?»

---

## 1. Il problema

La decomposizione *f*(*r*) = α_iso·*r* + residuo non è unica. α_iso da minimi quadrati per
l'origine è una **media pesata** di *g*(*z*) = *f*/*r* con pesi *w*·*r*², quindi cambia con la
pesatura: uniforme in *z*, pesata su *n*(*z*), pesata sui volumi. Qualunque scelta dà
α_iso ∈ [min *g*, max *g*], e il residuo max|*f* − α*r*| cambia di conseguenza.

Quanto? All'angolo (0.25, −1.2), con *g* ∈ [1.0154, 1.0511]:

| α_iso scelto | residuo (h⁻¹Mpc) |
|---|---|
| = min *g* = 1.01541 | 38.60 |
| **minimi quadrati uniforme = 1.04052** | **11.46** |
| **minimax = 1.04292** | **8.88** |
| = max *g* = 1.05113 | 12.74 |

Un fattore **4.3** fra gli estremi. La domanda su *n*(*z*) non era un dettaglio di
implementazione: era la punta di una scelta di gauge non dichiarata.

---

## 2. La risposta, e viene dalla Proposizione 2

La Proposizione 2 dice che la parte isotropa è **esattamente assorbibile** nella convenzione di
griglia: qualunque α è ugualmente gratuito. Quindi il contenuto fisico non è il residuo rispetto a
un α scelto per comodità, ma **il minimo del residuo su tutti gli α ammissibili**:

> Δ_fis ≡ min_α max_*r* |*f*(*r*) − α·*r*|

cioè l'approssimazione di **Chebyshev** lineare per l'origine. È l'unica quantità della
decomposizione che non dipende da come si è scelto di separare isotropo e anisotropo, ed è la sola
che si possa difendere come *"questo è ciò che l'AP fa e che nessuna riconvenzione della griglia può
togliere"*.

**Il fit ai minimi quadrati sovrastima il segnale AP fisico del 20–26%** sulla maggior parte della
griglia (fino al 26.4%). Non è un errore di calcolo: è aver risposto a una domanda leggermente
diversa.

### Numeri, entrambi i gauge

| Ω_m | *w*₀ | α_LSQ | res. LSQ | α_minimax | res. minimax | sovrastima |
|---|---|---|---|---|---|---|
| 0.25 | −1.2 | 1.04052 | 11.46 | 1.04292 | **8.88** | 22.6% |
| 0.25 | −1.0 | 1.01496 | 5.08 | 1.01620 | 3.74 | 26.4% |
| 0.25 | −0.8 | 0.98918 | 1.65 | 0.98921 | 1.64 | 0.6% |
| 0.28 | −1.2 | 1.03201 | 8.45 | 1.03364 | 6.69 | 20.9% |
| 0.28 | −1.0 | 1.00819 | 2.74 | 1.00886 | 2.03 | 26.1% |
| 0.28 | −0.8 | 0.98404 | 3.34 | 0.98361 | 2.87 | 13.9% |
| 0.3175 | −1.2 | 1.02177 | 4.97 | 1.02253 | 4.14 | 16.7% |
| 0.3175 | −0.8 | 0.97777 | 5.38 | 0.97684 | 4.37 | 18.8% |
| 0.35 | −1.2 | 1.01323 | 2.17 | 1.01330 | 2.10 | 3.4% |
| 0.35 | −1.0 | 0.99312 | 2.23 | 0.99260 | 1.66 | 25.5% |
| 0.35 | −0.8 | 0.97247 | 7.07 | 0.97114 | **5.62** | 20.4% |

Verifica di correttezza: al minimax vale l'**equioscillazione**, min(*f*−α*r*) = −max(*f*−α*r*).
Su (0.25, −1.2): −8.8751 e +8.8751 a dodici cifre. È la firma della soluzione di Chebyshev.

---

## 3. Cosa cambia nei numeri già scritti

| quantità | prima (LSQ) | dopo (minimax) |
|---|---|---|
| residuo anisotropo massimo, h⁻¹Mpc | 11.46 | **8.875** |
| in voxel, NGC | 0.735 | **0.569** |
| in voxel, SGC | 0.776 | **0.596** |
| rapporto con l'artefatto di padding (0.0131 vox) | 56× | **46×** |
| canale oltre (α_iso, *F*_AP) a (0.25, −1.2) | 0.165 vox (22.4%) | **0.082 vox (14.5%)** |
| canale oltre (α_iso, *F*_AP) a (0.35, −0.8) | 0.090 vox (19.8%) | **0.047 vox (13.1%)** |
| canale oltre (α_iso, *F*_AP) a (0.25, −0.8) e (0.35, −1.2) | 0.013 / 0.008 vox | **0.0062 / 0.0051 vox** |

Le conclusioni qualitative **non cambiano**, e questo è il punto: il segnale AP resta sub-voxel e
resta 46 volte l'artefatto di padding; la famiglia a due parametri resta incompleta agli angoli
estremi; per (0.25, −0.8) e (0.35, −1.2) il canale residuo scende **sotto** l'artefatto di padding,
il che rafforza la lettura data in 1.3 — lì la parametrizzazione a due parametri è esatta entro il
rumore di costruzione.

### Ricampionamento della linea B di 1.3

Ancorata al residuo minimax massimo, 0.569 voxel NGC:

| | *F*_AP | *A* | res. (vox NGC) | res. (vox SGC) |
|---|---|---|---|---|
| B1 | 0.971070 | 0.81922 | 0.569 | 0.596 |
| B2 | 0.985396 | 0.90559 | 0.284 | 0.298 |
| B3 | 1.000000 | 1.00000 | 0.000 | 0.000 |
| B4 | 1.014889 | 1.10310 | 0.284 | 0.298 |
| B5 | 1.030071 | 1.21556 | 0.569 | 0.596 |

L'intervallo di *F*_AP si stringe da [0.9648, 1.0372] a **[0.9711, 1.0301]**, e ora coincide quasi
con l'intervallo dei *F* efficaci degli angoli (0.9719 – 1.0198), che è il segno che il gauge giusto
rende le due caratterizzazioni coerenti fra loro invece che scollate.

---

## 4. Cosa fare con la pesatura *n*(*z*)

**Il minimax diventa il canonico**, e la domanda su *n*(*z*) si chiude: non serve più scegliere una
pesatura, perché il minimax non ne ha una. La colonna `a_iso(nz)` resta come **diagnostica**, non
come definizione: se differisce molto dal minimax, quantifica quanto era arbitraria la scelta
precedente.

Nel manoscritto va detto in una riga, perché è una trappola in cui cadrà chiunque ripeta il lavoro:

> The split of a radial remapping into an isotropic dilation and an anisotropic residual is not
> unique; by Proposition 2 the isotropic part is absorbed into the grid convention at no cost, so the
> physically meaningful amplitude is the Chebyshev minimum over α, not the least-squares residual,
> which overstates it by up to 26% on our grid.

---

## 5. Due patch allo script

### 5.1 Minimax, senza dipendenze nuove

`minimax_alpha(r_fid, r_new)` risolve per bisezione lo zero di
*h*(α) = max_i *r*_i(α − *g*_i) − max_i *r*_i(*g*_i − α), che è strettamente crescente. Duecento
passi, precisione macchina, solo numpy. Riproduce il risultato di `scipy.optimize` a sei cifre.

Colonne nuove nel JSONL: `alpha_iso_minimax`, `anis_residual_minimax_hMpc`, `gauge_gain_pct`, e
`anis_residual_minimax_vox` nella metà geometrica.

### 5.2 Una trappola nella firma di configurazione — trovata grazie al tuo run

`config_hash` non conteneva `cosmo_only`. La chiave di ripartenza è (region, Ω_m, *w*₀) +
config_hash, e in modalità `--cosmo-only` la regione resta il default **NGC**. Conseguenza: se i
record cosmologici e quelli geometrici finissero nello **stesso** file JSONL, il run geometrico
troverebbe le dodici chiavi già presenti e **salterebbe tutto**, uscendo senza scrivere una riga e
senza errore.

Tu hai usato due file distinti, quindi non è successo — ma sarebbe successo alla prima
semplificazione. Ora la firma include `cosmo_only` ed è passata a `v: 2`.

**Conseguenza operativa:** il file `results\paper2\item12a_cosmo.jsonl` che hai appena scritto ha la
firma vecchia. Rilanciando `--cosmo-only` i dodici record vengono **riscritti in append** con la
firma nuova e le colonne minimax; i vecchi restano, come vuole l'append-only. Nessuna perdita, e la
differenza fra i due blocchi è la traccia di questa emenda.

```powershell
python src\paper2_item12a_apgrid.py --cosmo-only --out results\paper2\item12a_cosmo.jsonl
```

---

## 6. Da aggiornare

1. **`paper2_item11.md` §1.1a′** — il rapporto segnale/artefatto passa da 56× a **46×**; il residuo
   fisico di riferimento da 0.73 a **0.569 voxel** (NGC) / 0.596 (SGC). Il paragrafo inglese per §2
   va corretto in questi due numeri.
2. **`paper2_item12a.md` §2.2** — la discussione sulle due colonne Δ*x* resta valida, ma il numero
   da citare diventa il minimax.
3. **`paper2_item13.md` §2 e §3** — linea B ricampionata come sopra; le quote del canale
   oltre-legge-di-potenza scendono a 14.5% / 13.1% / 5.9% / 3.8%.
4. **Checklist 1.2** — aggiungere la definizione di gauge fra le convenzioni da dichiarare, accanto
   a quella di *F*_AP e a quella di σ_px. Sono tre, e nessuna delle tre era esplicita.
5. **Canovaccio §6.2 di M26, "practice"** — candidata quarta voce: *dichiarare il gauge della
   decomposizione isotropo/anisotropo*.
