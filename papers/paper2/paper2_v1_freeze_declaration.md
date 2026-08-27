# Congelamento dell'ensemble v1
### Paper 2, checklist item 0.1 — 25 agosto 2026

---

## 1. Dichiarazione

**L'ensemble v1 è l'ensemble di mock prodotto da `voxelize_mock` con pesi unitari**, quello su cui
poggia ogni numero di M26 (MN-26-2100-P, inclusa R1) e del Paper 1 (MN-26-2388-P).

**v1 è immutabile.** Nessun run del Paper 2 può sovrascrivere, rigenerare o "aggiornare" un artefatto
di v1. Il Paper 2 crea un **ensemble v2** (voxelizzazione mock pesata FKP, checklist 4.2a), che è un
oggetto **diverso** e vive in file diversi.

**Regola di etichettatura, senza eccezioni.** Ogni numero riportato nel Paper 2 — nel manoscritto,
nelle figure, nei record congelati, negli script — porta l'etichetta `v1` o `v2`. L'espressione
*"ensemble fiduciale"* senza suffisso è **ritirata** dal vocabolario del progetto: era ambigua già
prima e diventerebbe una fonte di errore silenzioso appena v2 esiste.

Motivo, per il record: modificare `voxelize_mock` cambia la **definizione del campo mock**. Non è
un'analisi a valle, è un intervento sulla pipeline, e rompe la confrontabilità con tutti i valori
congelati del paper base. Il Paper 2 deve presentare il confronto **v1 ↔ v2** esplicitamente, il che
è possibile solo se v1 sopravvive intatto.

---

## 2. Cosa rende questa dichiarazione verificabile

Una dichiarazione di congelamento che non si può controllare non è un congelamento: è un'intenzione.
Due artefatti la rendono controllabile.

### `paper2_v1_reference.json`

Il set completo dei **valori di riferimento v1**, raccolti per la prima volta in un unico posto
(erano sparsi fra due manoscritti), in forma leggibile da macchina, con la provenienza di ciascuno
(paper, sezione, tabella). Porta un `_self_sha256`: se qualcuno lo edita, ogni script del Paper 2 si
rifiuta di partire con exit 3.

**Verifica di coerenza interna eseguita, 10 controlli su 10 passati:**

| controllo | valore | atteso | scarto rel. |
|---|---|---|---|
| σ_fixed² = σ_HOD² + σ_real² | 29 584 | 29 594 | 3.4e−04 |
| σ_tot² = σ_cos² + σ_fixed² | 97 969 | 97 966 | 2.8e−05 |
| deficit = media mock − DESI | 7180.7 | 7180.7 | 3.8e−16 |
| deficit frazionario | 0.2026 | 0.2026 | 1.7e−04 |
| margine = mock minimo − DESI | 2970 | 2970 | 0 |
| residuo = (DESI_φ − DESI) − (mock_φ − mock) | 1710.5 | 1710.5 | 0 |
| frazione spettrale = D_φ/D | 0.763 | 0.7625 | 6.2e−04 |
| significatività = residuo/σ_Δ | 6.8 | 6.83 | 4.2e−03 |
| frazione indipendente = celle distinte / voxel | 0.696 | 0.6959 | 8.1e−05 |
| molteplicità media = voxel / celle distinte | 1.44 | 1.4369 | 2.2e−03 |

I due manoscritti sono aritmeticamente coerenti fra loro. Non era scontato: i valori vengono da run
diversi, a distanza di mesi, e la decomposizione della varianza è stata corretta fra la versione
originale di M26 e R1.

### `paper2_freeze_v1.py`

Due modalità.

- **`freeze`** — percorre l'albero degli artefatti v1, calcola SHA-256 di ogni file, scrive un JSONL
  append-only e un digest aggregato. Append-only, scrittura atomica con `os.replace` + `fsync`,
  ripartibile: un secondo run salta i file già presenti.
- **`verify`** — riesegue la scansione e confronta. Riporta `CHANGED`, `REMOVED`, `added` ed esce
  con codice **1** in caso di drift. È questo che, fra sei mesi, prova che v1 non si è mosso.

Il gate della reference gira **prima** di qualunque altra cosa, in entrambe le modalità.

**Test eseguiti in sandbox:**

| test | esito |
|---|---|
| freeze su albero sintetico | 4 file, digest aggregato deterministico |
| verify subito dopo | `CLEAN`, exit 0 |
| freeze ripetuto (resume) | 4 saltati, nessun ri-hash |
| file v1 modificato | `CHANGED` sul file giusto, `DRIFT DETECTED`, exit 1 |
| file v1 rimosso | `REMOVED`, exit 1 |
| reference manomessa | `GATE FAILED`, exit 3, nessuna scansione |

> **Un difetto reale è emerso dai test e è stato corretto.** Nella prima versione la directory di
> output cadeva dentro un root scansionato, quindi **il manifest faceva l'hash di sé stesso**. Non è
> solo rumore: quella voce cambia a ogni run e **maschera il drift vero** degli artefatti che il
> manifest esiste per proteggere. Nel test 4 la modifica a `desi_ngc.json` era invisibile dietro il
> `CHANGED` sul manifest. Ora la directory di output è esclusa esplicitamente dalla scansione.

---

## 3. I valori di riferimento v1 (estratto)

Il file JSON contiene molto di più; questi sono quelli che il Paper 2 asserirà più spesso.

### Statistica primaria

| | NGC | SGC (n=2000) |
|---|---|---|
| *N*_H1 DESI | **28 256** | **15 122** |
| mock | 35 436.7 ± 313.0 | 18 713.0 ± 197.8 |
| deficit | 7180.7 (20.26%) | 3591.0 (19.19%) |
| rango empirico | 1/2001 | 1/2001 |
| margine sotto il minimo | +2970 | +1100 |
| distanza di famiglia *z* | −22.9 | −18.2 |

> **Attenzione, doppio record per la SGC.** Paper 1 quota l'ensemble SGC a *n* = 2000
> (18 713.0 ± 197.8); M26 R1 §5.4 quota lo **stesso ensemble v1** a *n* = 200 (18 694 ± 178).
> Sono due sottoinsiemi dello stesso oggetto, non due misure da mediare. Nel JSON stanno come chiavi
> distinte `SGC_n2000` e `SGC_n200`, con la nota esplicita.

### Geometria (definisce cosa cambia sotto AP)

| | NGC | SGC |
|---|---|---|
| *L* cubo (h⁻¹Mpc) | 1997.36 | 1904.5 |
| Δ*x* (h⁻¹Mpc) | 15.604 | 14.88 |
| σ_px | 0.3204 | 0.3361 |
| voxel in maschera | 307 805 (14.7%) | 172 225 (8.2%) |
| profondità mediana | 3.0 voxel | 2.8 voxel |
| occupazione | 0.71 gal/voxel | — |

### Decomposizione della varianza (M26 R1 §5.5)

σ_tot = 313.0 = σ_cos 261.5 (69.8%) ⊕ σ_HOD 128.3 (16.8%) ⊕ σ_real 114.6 (13.4%);
σ_fixed = 172.0. *Questo è l'esperimento M2 del canovaccio Paper 5, già eseguito.*

### Le quantità che il Paper 2 deve muovere o non muovere

| quantità | v1 | dipende dai pesi? | uso |
|---|---|---|---|
| curtosi in eccesso di ν, mock | +3.90 (DESI +0.20) | **sì** | predizione 4.2b |
| ν₉₉ − ν₁, mock | 5.6σ (DESI 3.22σ) | **sì** | predizione 4.2b |
| rapporto varianze δ mock/DESI | 1085 | **sì** | predizione 4.2b |
| δ massimo, mock | 32 244 (DESI 125) | **sì** | predizione 4.2b |
| escursione Box–Cox del deficit | 20.3% → 17.6% | **sì** | predizione 4.2b ★ |
| frazione voxel multi-occupati | 0.21–0.27% (DESI 1.65%) | **no** | cancello 4.2d |
| molteplicità massima di voxel | 3–4 (DESI 52) | **no** | cancello 4.2d |
| residuo beyond-two-point | 1710.5 ± 40.6, 6.8σ | non dovrebbe | cancello 5.3 |
| split in persistenza | +1908 / −9408 / +332.5 | parzialmente | cancello 5.3 ★ |
| scala di erosione *k* = 0–3 | 20.2 / 25.4 / 20.6 / 18.6% | **è la domanda** | Componente C |
| molteplicità di tiling | 1.44, indip. 70% | no (dipende da α_iso) | confondente 1.5 |

---

## 4. Cosa serve da te per chiudere l'item

Una cosa sola: **l'elenco delle directory che costituiscono v1.** Io ho i valori, non i percorsi.

Candidati probabili, da confermare o correggere:

```
results\paper1\                    record congelati del Paper 1
results\m26\      (o simile)       record congelati del paper base
data\cache\<cache dei δ mock>      i campi mock v1 a pesi unitari
```

La domanda che decide l'ampiezza: **la cache dei δ mock v1 è su disco, o viene rigenerata a ogni
run?** Se è rigenerata, il congelamento deve coprire il *codice* che la produce (commit git + hash di
`voxelize_mock` e delle sue dipendenze) invece dei dati, e la 4.2a va progettata per scrivere in un
percorso nuovo — non per rigenerare in loco, che distruggerebbe v1 senza che nessuno se ne accorga.

### Esecuzione, da `D:\projects\cauchy`

```powershell
python src\paper2_freeze_v1.py freeze `
    --roots results\paper1 results\m26 data\cache\mock_delta `
    --ref   src\paper2_v1_reference.json `
    --out   results\paper2
```

Poi incollami il digest aggregato e il conteggio dei file. Quel digest va nel protocollo congelato e
nella pre-registrazione (item 0.6): è l'oggetto che rende falsificabile la frase *"v1 non è
cambiato"*.

---

## 5. Stato

| item | stato |
|---|---|
| 0.1 dichiarazione scritta | ✅ |
| 0.1 valori di riferimento raccolti e verificati | ✅ 10/10 |
| 0.1 strumento di congelamento scritto e testato | ✅ 6/6 in sandbox |
| 0.1 manifest generato sui dati reali | ⬜ **serve la lista dei percorsi** |
| 0.2 → 0.7 | ⬜ |

**Prossimo in coda dopo il manifest:** item **0.5** (ispezione del codice, tre domande binarie).
Nell'ordine di esecuzione è il primo che produce informazione, e la sua prima domanda — se il cubo di
embedding sia ricalcolato dai random o hard-coded a `L = 1997.36` — decide se la Proposizione 2 si
applica alla pipeline com'è, cioè se metà del Paper 2 esiste.
