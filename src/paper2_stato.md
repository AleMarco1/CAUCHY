# Paper 2 — stato consolidato
### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **7 settembre 2026, sera**

> **Perché questo file esiste.** Le voci sono state etichettate due volte con lo stesso schema di
> lettere in contesti diversi, e due voci sono uscite dal discorso per collisione di nomi. Da qui in
> avanti ogni voce ha un prefisso che ne dichiara la famiglia, e questo file è l'unico indice.

**Famiglie:** `F` fase della checklist · `P` provenienza · `G` geometria/codice · `S` sottoprodotto
scientifico · `R` rilascio · `X` risposta al referee · `Y` secondo report · **`Z` Fase 4** (nuova)

> **Cosa è cambiato in questa revisione.** La sessione di Fase 4 ha chiuso la giornata di
> dichiarazione: **quattro predizioni su sei erano scritte su una quantità diversa da quella che il
> run avrebbe misurato**, e sono state ritirate prima di qualunque misura. Sono entrati i record
> 50–53. Due affermazioni della revisione precedente sono state verificate e **corrette**: la voce
> F3.17 e il conteggio del registro.

---

## 0. Verifiche fatte su questa revisione

| verificato | esito |
|---|---|
| non-ASCII nel registro «dal record 50» | **SMENTITO**: è presente **dal record 9**. Nei primi 49 ci sono 94 `§`, 43 `—` e una coppia `«»` al record 45; 39 record su 49 ne contengono. F3.17 riscritto |
| chiavi non ordinate dal record 50 | **CONFERMATO**: i primi 49 le hanno tutte ordinate, i record 50–52 no. **Corretto dal 53 in avanti** |
| conteggio del registro a 55 record | **NON RICONCILIATO**: `freeze_verify` alle 13:04 del 7 set dà `disco = 52`, `documentati = 52`, CLEAN. Vedi `Z-numerazione` fra gli aperti |
| dimensione dei campi δ | **VERIFICATO**: 8 388 736 byte esatti su tutti e 4000, nessuno scarto |
| i deficit del ladder contro Tab. 9 di P1 | **VERIFICATO**: 20.234 / 25.400 / 20.591 e 19.110 / 27.109 / 19.996 |

---

## Stato in una riga

| | 5 settembre | 7 settembre (mattina) | **7 settembre (sera)** |
|---|---|---|---|
| registro emendamenti | 41 record | 49 record | **53 record** (49 Fase 3 + 50–53 Fase 4) |
| checklist | rev. 3.17 | rev. 3.18 | rev. 3.18 |
| risposta al referee | 26 sezioni | 33 sezioni | 33 sezioni |
| Fase 3 | chiusa come misura | chiusa, risultato più piccolo | invariata |
| Fase 4 | non iniziata | dichiarazioni da completare | **dichiarazioni chiuse, run non iniziati** |
| run in coda | nessuno | nessuno | **passata a un punto su v1, poi 4.2a** |

---

## 1. Il risultato principale della Fase 3, corretto

**La versione del 5 settembre diceva: «il lato mock risponde all'AP 2–6 volte più del lato dati, e
tre meccanismi candidati sono stati esclusi». È superata.**

I quattro rapporti da 2.10 a 5.56 sono **la stessa affermazione quattro volte**:
(1 − 1/*R*)/(sd/media) dà **0.97, 0.94, 0.77 e 1.05σ**. Il 5.56 è *meno* estremo del 2.10, perché il
suo denominatore è più grande.

> **Δ*D*_max = −98.3 ± 11.2 (media mock) ± ~100 (realizzazione del lato dati)** — compatibile con
> zero.

Il numero che lo dimostra era **già nel nostro documento**: la dispersione delle 200 pendenze per
realizzazione, riportata alla risposta 2 senza trarne la conseguenza.

**Il tetto.** L'incertezza di realizzazione è irriducibile perché l'universo osservato è uno: vale
~100 generatori, l'1.4% del deficit NGC e il 2.8% del SGC. Δ*D*_max = 75–114 **è già lì**.

### Cosa resta, e regge

1. **Quanto sposta il fiduciale il risultato pubblicato**: rango **1/201 in ogni punto**, deficit
   20.04–20.61% a *k*=0 e 25.27–25.66% a *k*=1, escursione ≤0.57 pp. La limitazione (ix) di M26 si
   chiude in tre righe.
2. **Il campo osservato risponde all'AP diversamente da un campo ΛCDM?** **No, a 0.77–1.05σ.**
3. **La regola dei denominatori.**

---

## 2. I tre principi che valgono ovunque

### La regola dei denominatori — §A.3 del secondo report, adottata

> La **SEM** è il denominatore giusto quando l'oggetto della domanda è una proprietà dell'**ensemble
> di mock**. La **dispersione per realizzazione** lo è quando l'affermazione riguarda il **campo
> osservato**, che ha *N* = 1.

Il modo di fallire del programma — M26 con *w*₀ = −294, Paper 1 con Mahalanobis 34, l'estrapolazione
61–247 — è sempre stato lo stesso: una quantità misurata con precisione, il denominatore scelto dopo.

### La regola delle soglie — emendamento 48

> Nessuna soglia si attraversa senza l'**incertezza della quantità testata**, dichiarata quando la
> regola si dichiara.

**P1 non decide**: |*r*(*w*₀)| = 0.0549 dista **0.22σ** da 0.05, e in SGC vale 0.0474 — lati opposti
della soglia. Se SGC fosse stato riportato per primo, P1 sarebbe stata registrata come confermata.

### La regola della scomposizione — record 50 e 51, **nuova**

> **Una soglia si scrive solo sulla parte della quantità che il trattamento può muovere.**

Trovata **due volte in posti indipendenti**, e nessuna delle due era prevedibile a tavolino:

- **Box–Cox**: l'escursione del deficit vale −2.714 pp, di cui **−2.288 pp (84.3%) lato dati**. La
  ripesatura dei mock non li tocca.
- **Picco di erosione**: la prominenza a *k*=1 è **23.9% lato dati in NGC e 47.5% in SGC**.

**Il modo di procedere**: scomporre la quantità nella parte che il trattamento raggiunge e in quella
che non raggiunge, **misurare le due**, scrivere la soglia solo sulla prima. Se non si sa scomporla,
la predizione non è pronta.

---

## 3. Chiuso in questo ciclo — la seconda tornata di referee

| id | rilievo | esito |
|---|---|---|
| **Y-A** | la discrepanza è rumore di una realizzazione | **accettato**; quattro sottrazioni dichiarate |
| **Y-A.5.1** | ρ(pendenza, *N*_H1) | segno giusto, **nullo in NGC**, 3.2σ solo SGC *k*=1; l'estrapolazione cambia segno |
| **Y-A.5.2** | ρ(pendenza, parametri) | solo *n*_s, −0.15 in NGC, nulla in SGC; 28 confronti |
| **Y-A.5.3** | il prefisso dei primi 200 | **il §3.7 REGGE**: spostamento **< 1%** |
| **Y-B.1** | il cancello 2.3 ha tre descrizioni | è il cancello di **σ_px**; ritiriamo **noi** la riformulazione |
| **Y-B.2** | la firma asimmetrica | declassata a **osservazione a 1.6σ**, *una* non quattro |
| **Y-B.3** | blocco A solo lato dati | **il controllo c'era già**: `n_mock` = 200 su sei punti |
| **Y-B.4** | P1 riportata come falsificata | **ritirata**; audit su tutte le soglie (record 48) |
| **Y-C** | scartiamo un segnale vero | **test costruito, esito NEGATIVO** |
| **Y-D.2** | il canale RSD nel budget | accettato come **coefficiente** e **limite superiore** |
| **Y-D.3–D.6** | quattro minori | accettati, ciascuno con la sua ragione |

**Le quattro sottrazioni**: E1–E4 ritirata dichiaratamente; il fattore 2.1–5.6 esce dai risultati; i
tre meccanismi esclusi diventano una nota; il budget si riscrive con (c) unico sistematico.

---

## 4. Il registro degli emendamenti

### Fase 3, record 39–49

| # | contenuto |
|---|---|
| 39 | termine (c) indipendente dal punto — prima predizione dichiarata che regge |
| 40 | pavimento a sei punti |
| 41 | budget ai quattro livelli |
| 42 | vitalità **posizionale** nel registro compD |
| 43 | Componente D tracciata **a posteriori per riproduzione** |
| 44 | ripattern del tiling **sotto soglia**; appaiamento fallito; soglia fortunata |
| 45 | scala geometrica del ripattern, e lo **scan** che ne limita la portata |
| 46 | terzo canale misurato, **firma SMENTITA nel verso opposto** |
| 47 | sei fine riga anomali nel registro, inerti e registrati |
| 48 | **audit delle predizioni a soglia**; P1 ritirata; il 44 corretto in SGC |
| 49 | budget a quattro livelli, pavimento a sei punti; **la copertura crolla** |

### Fase 4, record 50–53 — verificati

| # | contenuto |
|---|---|
| **50** | **quattro predizioni di 4.2b ritirate**; sei regole di decisione al loro posto; specifica di uscita di 4.2a |
| **51** | **la soglia numerica di 4.3b**, misurata, sul **lato mock**; l'asimmetria emisferica è lato dati |
| **52** | **inventario misurato di v1**; un nome di campo non identifica la grandezza |
| **53** | **cache dei δ manifestata**; il tier `fields` congela altro; correzione al 52 |

---

## 5. Le sei regole di decisione, e la soglia che resta aperta

Tutte in `paper2_item4_2b_dichiarazione.md` e nei record 50–51. **Dichiarate prima che v2 giri.**

| regola | quantità | soglia | denominatore |
|---|---|---|---|
| 4.2b-1 varianza di δ | *R* = ⟨Var⟩_mock / Var_DESI | successo < **7.358** (NGC), **16.203** (SGC) | SEM; lato dati deterministico |
| 4.2b-2 curtosi di ν | *z* a **footprint pieno** | successo \|*z*\| < 3, fallimento > 5 | dispersione per realizzazione |
| 4.2b-3 ν₉₉−ν₁ | *r*_f = (p99−p1)/σ | **NON SCRITTA**: `p1` non esiste | dispersione per realizzazione |
| 4.2b-4 massimo di δ | rango di 125 fra i 2000 | dentro il 95% centrale | nessuno: è un rango |
| 4.2b-5 Box–Cox | *s* appaiata su 50 mock | successo < **45.8** gen, fallimento > 137.5 | SEM appaiata |
| 4.3b prominenza | ***P*_mock**, non *P* | successo < **1.2648** pp (NGC), **1.3223** (SGC) | SEM appaiata |

**La soglia di 4.2b-1 è derivata, non scelta**: viene dal taglio P10, che su v1 porta *R* a 3.6791
(NGC) e 8.1016 (SGC), raddoppiato per tolleranza.

**Condizioni di invalidazione, dichiarate.** 4.3b: se σ su v2 supera un terzo di *P*_mock — 1.26 pp
NGC, 1.32 SGC — la regola smette di decidere. 4.2b-5: se σ(*s*^v2) > 15 generatori, idem. Va detto
**prima** di leggere l'esito.

### Le quattro predizioni ritirate, con la ragione

| predizione | perché non reggeva |
|---|---|
| curtosi di ν «+3.90 → +0.20 a footprint pieno» | +3.90 e +0.20 sono una coppia **P10**; a footprint pieno DESI ha curtosi **negativa** (−0.4382 NGC, −1.1352 SGC) |
| massimo di δ «32 244 → ~125» | 32 244 è il **massimo dell'ensemble** dei massimi; la mediana per mock è 3474.58 |
| escursione Box–Cox «deve comprimersi» | **84.3% lato dati**, invariante sotto ripesatura |
| varianza di δ «da 1085 verso 1» | «verso» non è una soglia, e 1085 è una fra **due implementazioni** |

---

## 6. Costanti misurate — da non ricalcolare

### Cache dei δ, manifestata (record 53)

| | radice | campi | byte | aggregato |
|---|---|---:|---:|---|
| NGC | `data/processed/paper1_mock_deltas/NGC` | 2000 | 16 777 472 000 | `631b0703fe3b…` |
| SGC | `data/processed/paper1_mock_deltas/SGC` | 2000 | 16 777 472 000 | `92cb5e8dd26c…` |

Verifica: OK 2000, MISMATCH 0, MISSING 0, EXTRA 0 in entrambi. **8 388 736 byte esatti per campo** —
128³ float32 più l'intestazione npy — senza un solo scarto su 33.55 GB. **Manifestata, non
congelata**: il tier `fields` congela `results/phase8_test2_fields/`, 2202 file.

### Inventario di v1 per realizzazione (record 52)

| grandezza | file | *n* NGC | SGC |
|---|---|---:|---|
| momenti di δ | `n1_spectra_NGC.jsonl` | **50** | assente |
| momenti di ν | `n1b_spectra_NGC.jsonl` | **1800**, `idx` da 200 | assente |
| scala *k*=0…3 | `fase3_mock.jsonl` FID | 200 | 200 |
| massimo δ, p1, p99, patologici | — | **0** | **0** |

**I campi ci sono tutti**: mancano le passate, non i dati. La passata a un punto costa ~81 ms di CPU
per campo più 12.4 ms di impronta: **dieci minuti per emisfero**, non ore.

### Scala di erosione, v1, n=200 (record 51)

| | *D*(0) | *D*(1) | *D*(2) | *P* | *P*_mock | residuo | σ(*P*_mock) |
|---|---:|---:|---:|---:|---:|---:|---:|
| NGC | 20.234 | 25.400 | 20.591 | +4.9870 | **+3.7943** | +1.1926 | 0.0165 |
| SGC | 19.110 | 27.109 | 19.996 | +7.5561 | **+3.9668** | +3.5893 | 0.0221 |

*N*_H1 DESI: 28256 / 23790 / 20066 (NGC), 15122 / 12011 / 10049 (SGC). Scarti dall'interpolazione
lineare: mock **+1543.5** e **+850.5**, DESI **−371.0** e **−574.5** — entrambi alzano il deficit a
*k*=1: il picco è prodotto dai due lati insieme. σ appaiata contro jackknife concordano al 2.7% e
1.1%; la non appaiata è 4.0–4.7 volte più grande.

### Box–Cox, v1, NGC, 50 mock appaiati (record 50)

| ε | DESI | spost. dati | media mock | spost. mock appaiato | deficit |
|---|---:|---:|---:|---:|---:|
| 0 | 28256 | — | 35445.64 | — | 20.284% |
| 0.25 | 28606 | +350 | 35574.64 | **+129.00 ± 4.19** | 19.589% |
| 0.5 | 28754 | +498 | 35570.16 | +124.52 ± 7.08 | 19.163% |
| 1.0 | 29067 | **+811** | 35262.32 | **−183.32 ± 11.12** | 17.569% |

Appaiamento: 11.12 contro 48.25 non appaiata, *r* = 0.958. **Il lato mock non è monotono in ε**:
escursione di 312 generatori con cambio di segno, invisibile leggendo i due estremi.

### Statistiche a un punto, footprint pieno, v1, n=200

| | Var δ DESI | ⟨Var δ⟩ mock ± sd | *R* | ν kurt DESI | ν kurt mock ± sd | *z* |
|---|---:|---:|---:|---:|---:|---:|
| NGC | 2.9166 | 2918.40 ± 649.26 | 1000.60 | −0.4382 | 2.7638 ± 0.4718 | −6.787 |
| SGC | 4.8155 | 9960.08 ± 1240.73 | 2068.32 | −1.1352 | 1.1027 ± 0.2743 | −8.160 |

A `field_r > P10`: *R* = 3.6791 (NGC), 8.1016 (SGC). Massimo di δ per mock: mediana **3474.58**,
minimo 2417.18, massimo 32244.41. DESI: 125.

### Bersagli del cancello, e il loro *n*

| | *N*_H1(DESI) | media mock | sd (ddof=1) | *n* | deficit |
|---|---:|---:|---:|---:|---:|
| NGC | 28 256 | 35 436.686 | 312.9891651683112 | 2000 | 20.26% |
| SGC | 15 122 | 18 712.9675 | 197.7873817207103 | 2000 | 19.19% |

**A n=200 i deficit sono altri**: 20.234 pp (NGC) e **19.108** pp (SGC, dal blocco `SGC_n200` del
reference, media mock 18694.0). Riproduzione per realizzazione, NGC indice 0: ***N*_H1 = 35318**.

---

## 7. Il contratto di uscita di 4.2a — tredici campi

In forma verificabile in `src\paper2_contratto_4_2a.py`.

| campo | serve a |
|---|---|
| `delta.sigma_in_mask`, `delta.kurt_in_mask` | 4.2b-1 |
| `nu.sigma_in_mask`, `nu.kurt_in_mask` | 4.2b-2, 4.2b-3 |
| `max_delta` | 4.2b-4 |
| `nu.p1`, `nu.p99` | 4.2b-3 |
| `n_patologici` | 4.2c |
| `N_H1_k0…k3` in un registro solo | 4.3a–b |
| `delta_sha256` | ancoraggio agli ingressi, contro il manifest della cache |

**I nomi vanno col prefisso**: `sigma_in_mask` piatto significa δ in `n1_spectra` e ν in
`n1b_spectra`. **ν₉₉−ν₁ non è un campo**: è un derivato. **Le prove di fumo in un registro
separato**: le 38 dentro `fase3_mock.jsonl` hanno prodotto sei conflitti coi valori di produzione.

---

## 8. Aperti

| id | voce | costo | perché conta |
|---|---|---|---|
| **Z-numerazione** | **il conteggio del registro non torna** | una riga | Questo file diceva 55 record con 50–54 dalla Fase 4 e il §C al 55. `freeze_verify` alle 13:04 del 7 set dà **`disco = 52`**, e la sessione di Fase 4 ha appeso esattamente 50, 51, 52. Da riconciliare **prima** del prossimo append: `--attesi` rifiuterà se il conteggio non torna, ed è il comportamento voluto |
| **Z-maschera** | **su quale maschera si calcolano `p1` e `p99`** | decisione | Piena o erosa è la stessa scelta che in 4.2b-2 distingue footprint pieno da P10, e lì è già costata una predizione ritirata. Va dichiarata **prima** della passata a un punto |
| **Z-4.2b-3** | la soglia di ν₉₉−ν₁ | dopo la passata | `p1` non è calcolato in nessun registro. È l'unica delle sei regole che non può decidere |
| **F3.10** | **B1 anomalo a *k*=0 in NGC** | scrittura | +153.2 ± 11.7 contro il fiduciale (13σ) mentre gli altri quattro stanno entro ±40. Si scioglie in **Fase 7, punto 5** |
| **F-copertura** | il crollo a *k*=2,3 | scrittura | Da riprendere in **Fase 7, punto 5**, con **entrambe** le letture |
| **F3.17** | **il registro non è uniforme nell'ordine delle chiavi** | segnalazione | *Riscritta.* Il non-ASCII **non** arriva dal record 50: è nel registro dal record 9 (94 `§`, 43 `—`, una coppia `«»` al 45; 39 record su 49). Quello che cambia dal 50 è **solo l'ordine delle chiavi**: i primi 49 ordinate, i record 50–52 no. **Corretto dal record 53**, quindi l'isola resta di tre. La raccomandazione **hashare i record, non i byte** resta |
| **X-manoscritto** | le sottrazioni nel testo | Fase 7 | La risposta **dichiara** cosa si toglie; il testo di MN-26-2100-P non è stato toccato |

### Rilascio — stato non verificato da settimane

`R1` tag retroattivi e Zenodo · `R2` `REPRODUCIBILITY.md`, bloccato da `P-A1` · `R3` tarball del tier
`features` · `R4` `git gc` · `P-A1` rimuovere `phase8_test2_permock.csv` e ricostruire il manifest
`records`.

---

## 9. Strumenti, tutti con selftest

| strumento | cosa fa | selftest |
|---|---|---|
| `paper2_freeze_verify.py` | il cancello; `DOCUMENTED_AMENDMENTS` alla riga 87 | — |
| `paper2_lettura_4_2b.py` | provenienza delle chiavi; distingue per realizzazione da aggregato | 15/15 |
| `paper2_prominenza_v1.py` | *P*, scomposizione lato mock/lato dati, tre σ | 20/20 |
| `paper2_ladder_sigma.py` | ricompone il ladder per unione, filtri, cancelli | 18/18 |
| `paper2_contratto_4_2a.py` | verifica il contratto di uscita; **non calcola nulla** | 19/19 |
| `paper2_manifest_cache.py` | manifesta e verifica la cache dei δ | 20/20 |
| `paper2_patch_documented_amendments.py` | incrementa la costante, **con riscontro sul ledger** | 19/19 |
| `paper2_append_amend50…53.py` | appender, cancelli importati dal 50 | 15–16 |
| `paper2_contrasti.py` | contrasti pari/dispari, due denominatori, *D* = mock − dati | — |
| `paper2_pendenze.py` · `paper2_ripattern_*.py` · `paper2_surrogato_fit.py` | Fase 3 | — |

`paper2_ladder_sigma` importa *P* da `paper2_prominenza_v1`; `paper2_contratto_4_2a` importa lettura
e unione da `paper2_ladder_sigma`; gli appender 51–53 importano i cancelli dal 50. **Una sola
implementazione per grandezza**, con un controllo di selftest che verifica che l'import sia quello
vero.

---

## 10. Regole adottate

Le precedenti valgono tutte. In cima le tre che cambiano i verdetti: **i due denominatori come primo
passo**, **nessuna soglia senza l'incertezza della quantità testata**, **scomporre prima di
dichiarare**.

**Un nome non è una garanzia di contenuto, a nessun livello.** Quattro casi il 7 settembre: una
costante (`max_delta_mock`, estremo d'ensemble), un campo (`config_hash`), una colonna condivisa da
due registri (`sigma_in_mask`), un **tier** (`fields`, che congela `phase8_test2_fields`). La
grandezza è identificata dalla **coppia (file, nome)** finché i nomi non sono univoci.

**Un elenco di comandi non è uno script.** PowerShell esegue la riga dopo anche se la precedente
fallisce: tre append falliti e un patcher riuscito hanno lasciato la costante avanti al file. Il
rimedio è nel patcher — `--ledger`, che rifiuta se il conteggio non torna — non nella prudenza.

**Una tolleranza si sceglie sapendo lo scarto che deve ammettere.** I registri float32 chiedono
`1e-5`; a `1e-6` un valore corretto fallisce.

**Le soglie calibrate a un *n* non si applicano a un altro.** Il bersaglio a n=2000 su una misura a
n=200 ha fermato l'SGC e ha lasciato passare l'NGC per 0.0296 pp contro una tolleranza di 0.05.

**Un parametro che cambia la misura entra nel RECORD e nella CHIAVE di ripresa.**
**Un selftest sul comportamento non è un selftest sulla provenienza.**
**Riprodurre il difetto nel selftest prima di correggerlo.**
**Una sostituzione senza asserzione sull'ancora è un difetto.**
**Un fixture non deve concedere più del bersaglio.**
**Riprodurre una quantità non è la stessa cosa che quella quantità predica.**
**Correggere il disegno prima di eseguirlo, non dopo.**

---

## 11. Errori, e la loro forma

| # | errore | forma |
|---|---|---|
| 8 | il numero c'era e non ne abbiamo tratto la conseguenza | **misurare e non leggere** |
| 9 | `--origin-offset` fuori dalla chiave | un parametro che cambia la misura e non lascia traccia |
| 10 | confronto grezzo contro un pavimento corretto per (e) | confrontare quantità su **domini diversi** |
| 11 | controlli di prosa sensibili a maiuscole e fine riga | **cinque volte**, su codice sano |
| 12 | `str.replace` senza asserzione | una modifica che non fallisce quando non avviene |
| 13 | ordinamento verificato con `index()` su stringa non unica | confrontare occorrenze di sezioni diverse |
| **14** | predizioni scritte su una restrizione, una statistica o un lato diversi da quelli misurati | **quattro volte su sei**; la forma è dichiarare senza scomporre |
| **15** | bersaglio a n=2000 applicato a una misura a n=200 | passato per 0.0296 pp in NGC: **il caso pericoloso è quello che passa** |
| **16** | verificatore che accredita una misura di ν a un campo di δ | un nome trattato come identificatore |
| **17** | patcher eseguito dopo tre append falliti | comandi in fila senza dipendenza |
| **18** | tolleranza scelta a occhio, non sullo scarto da ammettere | 1e-6 dove servivano 1e-5 |

La **10** ha la stessa forma della 6 del ciclo precedente. La **11** è la più ripetuta. La **14** è
la più costosa in termini di risultato: quattro predizioni ritirate.

---

## 12. Stato dei file

**Registri in `results/paper2/`**

| file | contenuto |
|---|---|
| `fase3_mock.jsonl` | 2038 record, `k0 k1 k2 k3` su tutti e sedici i punti, **due emisferi**, **38 record `smoke`** |
| `fase3.jsonl` | 44 record, lato dati, `ladder.0..3.N_H1` per punto e regione |
| `fase3_mock_ripattern.jsonl` | 400 record, repliche randomizzate, `rot_seed` 20260905 |
| `fase3_mock_off_lo.jsonl` · `off_hi.jsonl` | §C, offset +4.0 e −2.1, 400 record ciascuno |
| `fase3_surrogato_fisso.jsonl` | maschera fissa: 305 533 voxel NGC, 168 643 SGC |
| `surrogato_aff.jsonl` · `ripattern_geom.jsonl` | fit e diagnostica geometrica |
| **`cachedelta_manifest_{NGC,SGC}.jsonl`** | **nuovi**: manifest della cache δ, 2000 voci ciascuno |
| **`cachedelta_header_{NGC,SGC}.json`** | **nuovi**: intestazioni, `is_freeze_tier: false`, ricetta dell'aggregato dichiarata |

**Da leggere per UNIONE, mai last-wins**, e **senza i record `smoke`**: con last-wins su
`fase3_mock.jsonl` restano solo `k2 k3` sui quattro punti nuovi; con lo smoke si ottengono sei
conflitti in NGC, il primo 35318 contro 35538.

**Convenzione di segno:** *D* = **mock − dati**. Fissata da un controllo in `paper2_contrasti.py`.

**Ambiente**: Windows/PowerShell, `D:\projects\cauchy`, comandi dalla radice.

---

## 13. Cosa NON rifare

- Il **fattore 2.1–5.6** non è un risultato: è 0.77–1.05σ, quattro volte lo stesso.
- La **firma asimmetrica** vale 1.6σ ed è **una** osservazione: *k*=0 e *k*=1 condividono l'84.6% dei
  voxel.
- **P1 non è falsificata**: non decide, e cade su lati opposti nei due emisferi.
- Il **cancello 2.3** è il cancello di **σ_px**: geometria e maschera identiche, cambia solo
  `R_SMOOTH`.
- La **frazione di ripattern non è una proprietà della geometria** e **non è la leva**. Sopravvive
  solo lo spostamento **relativo**, 0.0076 contro 0.3822 voxel.
- Il **blocco A ha il lato mock**, `n_mock` = 200 su sei punti: il pavimento è su *D*.
- **`config_hash` non è un ancoraggio degli ingressi.**
- La **soglia D5c** vale 28 e viene da **metà della SEM più piccola** (record 36).
- **Le quattro predizioni ritirate non si riaprono** (§5).
- Il **rapporto di varianze canonico è quello di `step6`** (1000.60 NGC), non quello di
  `fkp_asymmetry` (1084.81). Nessun numero pubblicato è in gioco: P1 §7.2 scrive «un fattore 10³» e
  entrambi ci rientrano.
- **La prominenza si misura su *P*_mock**, non su *P*.
- **σ appaiata, non in quadratura**: il fattore fra le due è 4.0–4.7.
- **La cache dei δ è manifestata, non congelata**, e il suo aggregato **non** è affermato uguale a
  quello di `freeze_verify`.
- **L'asimmetria emisferica del picco a *k*=1 è lato dati**: *P* differisce del 51.5%, *P*_mock del
  4.5%. Il 4.5% vale però **6.24σ**, e i due emisferi condividono la suite: l'accordo non è una
  conferma.
- **Il lato mock del Box–Cox non è monotono in ε.**
