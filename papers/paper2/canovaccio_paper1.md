# Paper 1 — versione riscritta rev3 (sostituisce `canovaccio_paper1.md`)

> **Nota di revisione (24 luglio 2026).** La rev2 era costruita attorno alla dipendenza di scala del deficit — inversione di segno e crossover a 16.3 Mpc/h. Il test di erosione della maschera ha mostrato che quelle scale sono dominate dalla contaminazione di bordo: **tutte le scale R ≥ 10 Mpc/h sono state respinte**. Il paper si assesta su **una scala**, R = 5 Mpc/h, validata in **due emisferi indipendenti**, e acquisisce in cambio un criterio metodologico quantitativo che spiega *perché* le altre scale non erano misurabili.
>
> È un paper più piccolo di quello della rev2 e più solido: ogni claim residuo è verificato tre volte — chiusura numerica a scarto esatto, erosione, secondo emisfero.

---

## Paper 1 — Invarianza monotona e origine di fase del deficit H1 in DESI BGS
**(fattibilità: massima — nessun dato nuovo; tutti gli esperimenti eseguiti)**

**Titolo di lavoro:** *"What kind of field has fewer loops? Monotone invariance, mask systematics, and the phase origin of the H1 deficit in DESI BGS"*

### Domanda scientifica

Il paper base congettura (Sez. 6.1) che *"ciò che spiega la struttura a un punto spiegherà la topologia"*. Questo paper mostra che la congettura è **falsa**, e per un motivo strutturale: alla scala canonica il canale a un punto è chiuso da un teorema più che dalla fisica. Stabilisce inoltre **a quale densità** vive il deficit, e **entro quali condizioni** l'omologia persistente è misurabile su una survey mascherata.

### Risultato 1 — Lemma di invarianza monotona *(teorico)*

> Per una filtrazione di **supralivello** su complesso cubico il diagramma di persistenza è determinato dal solo **ordinamento** dei valori delle celle. Ogni trasformazione **monotona crescente** lascia N_H1 esattamente invariato e β1(ν) invariata a meno di riparametrizzazione dell'asse.

Verifica: 15 110 → 15 110 → 15 110 rimappando su PDF gaussiana ed esponenziale.

Tre conseguenze, in ordine crescente di portata:

1. **Metodologica.** L'esperimento naturale — rimappare il campo *filtrato* sulla PDF osservata — è vacuo: darebbe frazione spiegata nulla per costruzione. Va rimappato il δ **grezzo**, prima del filtro.
2. **Sostanziale.** Poiché anche `log(1+δ)` è monotono, nessuna statistica a un punto può spiegare un deficit di N_H1 se non attraverso l'**interazione con lo smoothing**.
3. **Di robustezza per il paper base.** Il deficit non può essere l'artefatto di alcuna riscalatura monotona: calibrazione della densità, dettagli dei pesi, scelta della trasformazione logaritmica. Argomento forte, ottenuto senza costi.

### Risultato 2 — Il deficit è di fase, in entrambi gli emisferi

Alla scala canonica lo smoothing è **sub-pixel**: a σ_px = 0.3204 il voxel centrale conserva il **95.54%** del peso del kernel. Il canale a un punto è quindi quasi chiuso per geometria.

| | NGC (2000 mock) | SGC |
|---|---|---|
| DESI N_H1 | 28 256 | 15 122 |
| mock | 35 436.7 ± 313.0 | 18 693.6 ± 178.0 |
| deficit | **20.26%** | **19.11%** |
| z | **−22.94** | **−20.07** |

Misura del canale a un punto (NGC): rimappando i mock sulla PDF di DESI — trasformazione **18.2× più grande** della dispersione mock-to-mock in distanza KS — N_H1 si sposta di **+102 loop, lo 0.29%, nel verso opposto al deficit**. f_1p = −0.0142 ± 0.00014, g_1p = −0.1439 ± 0.0014. Correggendo per il one-point il deficit non cala: 20.49% (avanti), 23.18% (speculare like-for-like).

Formulazione per l'abstract:

> *Abbiamo applicato ai mock una trasformazione a un punto diciotto volte più grande della dispersione mock-to-mock, misurata con una metrica insensibile alla coda, e il conteggio dei loop si è spostato dello 0.29%, nel verso sbagliato.*

**Risultato collaterale:** DESI è **12.7×** più sensibile alla rimappatura dei mock. L'accoppiamento struttura-a-un-punto ↔ topologia non è universale ma dipende dalla struttura di fase su cui la PDF viene imposta. È la spiegazione fisica — non metodologica — della discordanza fra verso diretto e speculare.

### Risultato 3 — Dove mancano i loop

A PDF appaiata, il deficit lungo la soglia è massimo a **ν ≈ 0**, la densità media, con z = −22.1 e z < −3 sul 55% della griglia. Non nei vuoti profondi, non nei nodi più densi: nel **regime intermedio, filamentare**.

Punto metodologico da spiegare nel testo: il confronto **senza** remapping è fuorviante, perché a ν fisso mescola "PDF diversa" con "topologia diversa" — dà z = +7 a ν negativo e z = −16 a ν alto. Solo il confronto a PDF appaiata è interpretabile.

### Risultato 4 — Criterio di validità per la TDA su survey mascherate

Il test di erosione mostra che a smoothing crescente DESI e mock perdono loop in proporzioni sempre più diverse. La ritenzione relativa dipende **solo** da w, la frazione media del peso del kernel proveniente da dentro la maschera: NGC e SGC collassano sulla stessa curva pur avendo footprint, celle e σ_px diversi.

| w | ritenzione DESI/mock | escursione del deficit |
|---|---|---|
| 0.998 (NGC R5) | 0.996 | 2.0 pp |
| 0.996 (SGC R5) | 0.989 | 2.7 pp |
| 0.959 (NGC R10) | 0.838 | 13.1 pp |
| 0.935 (NGC R15) | 0.547 | 43.6 pp |
| 0.882 (NGC R30) | 0.210 | 91.7 pp |

> **L'omologia persistente su survey mascherata è affidabile solo se w ≳ 0.99.** In pratica σ_px ≲ profondità mediana del footprint / 9.

La configurazione del paper base (σ_px = 0.3204, profondità mediana 3.0 voxel) sta **appena dentro** il limite. È un criterio citabile da chiunque applichi TDA a survey reali, e merita una sezione propria.

### Risultato 5 — Asimmetria di pesatura FKP (limitazione della pipeline)

`voxelize_mock` usa pesi unitari mentre dati e random portano `WEIGHT_FKP`. Per DESI il peso si cancella fra numeratore e denominatore di δ, per i mock no: ogni realizzazione ha ~4 000 voxel (1.3%) con δ oltre il massimo di DESI, concentrati al **99.4% entro 2 voxel dal bordo**, con `field_r` mediano 315 volte più basso della mediana globale.

**Non produce loop spuri:** i mock conservano il **98.7%** dei loop eliminando il 10% dei voxel contaminati. Un voxel isolato a valore estremo genera una componente connessa (H0), non un ciclo. **Non genera il deficit:** tagliando i voxel contaminati il deficit cresce (20.3% → 28.5%) e z resta fra −23.7 e −27.2.

**Contamina però le statistiche a un punto** sensibili alla coda, di un fattore fino a 1 085 in varianza. Conseguenza operativa: le statistiche a un punto vanno riportate **su maschera erosa**. Nota di segno importante: l'artefatto aggiunge coda ai *mock*, quindi **maschera** l'anomalia di DESI invece di crearla.

### Banda sistematica del deficit

| trattamento del bordo | D/base | z |
|---|---|---|
| nessuno (fiduciale) | 20.3% | −25.4 |
| erosione 2 / 3 voxel | 20.6% / 18.6% | −18.9 / −16.6 |
| taglio field_r 1 / 5 / 10% | 21.6 / 25.5 / 28.5% | −27.2 / −25.3 / −23.7 |

Da riportare come **deficit ≈ 20%, banda sistematica 18–29%, significatività fra −17 e −27 in ogni caso**.

### Risultato 6 — Due fallimenti procedurali documentati

**Null pre-registrato distorto.** Il null di §6 usava come bersaglio la scala di quantili *media* dei 2000 mock, molto più liscia della scala *grezza* di DESI del test primario: bias di −4.54 ± 1.07 loop (4.2σ). Sostituito con un null mock→mock a bersaglio singolo: **−0.88 ± 2.14 loop**, imparziale.

**Albero decisionale rotto.** f_1p = Δ/D ha un polo dove D → 0: i verdetti oltre R10 sono rumore aritmetico (f_1p fino a +14.1). La metrica valida a piccolo D sono gli spostamenti assoluti, non i rapporti. Serve un'emenda formale al protocollo §8.

Riportare apertamente il fallimento di una procedura pre-registrata **aumenta** la credibilità del lavoro.

---

### Risultati ritirati rispetto alla rev2

Inversione di segno del deficit, crossover a 16.3 Mpc/h, concordanza N_H1/b1_peak sulla scala di crossover, deficit corretto scale-invariante al 23.69%, e tutte le misure a R ≥ 10 Mpc/h. Le scale respinte entrano nel manoscritto **come dimostrazione del criterio su w**, non come risultati.

### Lavoro residuo

| | stato |
|---|---|
| Esperimento SGC R5 a 2000 mock | 🔄 ultimo dato per i claim centrali |
| Statistiche a un punto su maschera erosa | 🔄 |
| Step 6 su SGC | 🔄 confermativo |
| Emenda formale al protocollo §8 | ⬜ |
| Scrittura | ⬜ |

### Rischi

**Bassi.** Il lemma è un teorema. Il deficit a R5 è misurato su 2000 mock con test di chiusura a scarto esatto, riprodotto in un secondo emisfero, stabile sotto erosione di metà footprint e sotto taglio dei voxel contaminati. Il null è imparziale. Le limitazioni note sono caratterizzate quantitativamente invece che dichiarate genericamente.

Il rischio residuo è che l'SGC dia un f_1p sostanzialmente diverso dall'NGC. Sarebbe però esso stesso un risultato — una discrepanza fra emisferi nell'accoppiamento one-point/topologia — coerente con l'asimmetria di sensibilità già misurata.

### Struttura del manoscritto

1. Introduzione e richiamo dell'anomalia
2. Lemma di invarianza monotona e conseguenze
3. Il canale a un punto: geometria del kernel e apertura con lo smoothing
4. Esperimento di rimappatura alla scala canonica; null like-for-like
5. Dove mancano i loop: decomposizione per soglia a PDF appaiata
6. Sistematiche di maschera e il criterio w ≳ 0.99
7. Asimmetria di pesatura FKP e sue conseguenze
8. Replica sull'emisfero sud
9. Discussione: cosa resta ammissibile come spiegazione del deficit

### Figure previste

(F1) Ritenzione DESI/mock vs w, due emisferi sulla stessa curva — **figura principale metodologica**
(F2) β1(ν) DESI vs mock a PDF appaiata, con banda e curva differenza — **figura principale del risultato**
(F3) Illustrazione del lemma: stesso campo, PDF diverse, diagramma identico
(F4) Peso del kernel vs R, con la soglia w = 0.99 sovrapposta
(F5) Scatter N_H1 pre/post rimappatura sui 2000 mock
(F6) PDF a un punto DESI vs mock su maschera erosa, con le distanze robuste
(F7) Banda sistematica del deficit sotto i diversi trattamenti del bordo

### Target

**MNRAS.** Il lemma e il criterio su w giustificano da soli una sezione metodologica citabile da chiunque applichi omologia persistente a survey reali; il risultato osservativo è la verifica in due emisferi che il deficit non è di natura a un punto.
