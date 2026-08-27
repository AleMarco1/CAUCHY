# Paper 4 — canovaccio, rev. 25 agosto 2026
## Il deficit sopravvive a una costruzione realistica?

> **Origine.** Fonde tre cose: la sezione «Paper 4» di `canovaccio_6_paper_followup.md` (altMTL,
> Uchuu, SHAM), la sezione «Paper 3» dello stesso documento (BOSS DR12), e un **ramo nuovo** —
> il multi-tracciatore dentro DESI — che nasce dalla sonda di localizzazione dei cataloghi del
> 25 agosto. Il BOSS retrocede da paper autonomo a ramo di robustezza; la motivazione è in §5.

**Titolo di lavoro:** *"Does the H₁ deficit survive a realistic forward model? Multi-tracer, fiber
assignment and independent-survey tests"*

**Cita:** M26, Paper 1, Paper 2, Paper 3.

---

## 1. La domanda

È il paper in cui l'anomalia vive o muore. Tutti i test precedenti la interrogano **dall'interno**
della stessa costruzione: stessi mock Quijote, stesso HOD, stesso tracciante, stessa pipeline
osservativa. Questo la interroga dall'esterno, su tre assi indipendenti.

**Un punto da tenere fermo, perché è controintuitivo: la concordanza NGC/SGC non discrimina.**
20.26% e 19.19% leggono come robustezza, ma sia un segnale fisico sia un disallineamento di
costruzione sono **comuni ai due emisferi**. La consistenza fra cap esclude un errore *locale*, non
un errore *comune*. Tutti e tre i rami di questo paper servono a fornire l'asse che manca.

---

## 2. Ramo A — multi-tracciatore dentro DESI
### *(il discriminante più forte, il più economico, e quello da fare per primo)*

### Perché

I cataloghi LRG, ELG_LOPnotqso e QSO DR1 sono **già sul disco**, accanto a BGS: stessa survey, stessa
pipeline osservativa, stesso codice di analisi, stessa geometria di footprint — ma **mock e
calibrazioni HOD indipendenti**.

- Deficit presente in **tutti** i tracciatori, con ampiezza comparabile → punta alla pipeline dati o
  a qualcosa di fisico.
- Deficit **solo in BGS** → punta alla calibrazione dei mock BGS, cioè direttamente alla
  limitazione (v).

Nessun altro test della serie separa queste due ipotesi con questo rapporto costo/beneficio.

### La complicazione, da dichiarare invece che minimizzare

LRG, ELG e QSO hanno densità numerica **molto più bassa** di BGS e coprono intervalli di redshift
diversi. Conseguenze dirette:

1. L'occupazione di **0.71 galassie per voxel a 128³** non si trasferisce. La griglia va **riderivata
   per tracciatore** secondo il criterio del Paper 1 (la cella è imposta dal campionamento, non
   scelta).
2. σ_px, w̄ e il limite *d*_med/9 vanno ricalcolati per tracciatore — e il Paper 2 ha già mostrato,
   con il caso SGC a σ_px = 0.336 sopra il limite 0.333 derivato da NGC, che **una soglia scalare
   unica non è ammissibile**.
3. Il confronto onesto è **«compare un deficit?»**, non «è lo stesso 20%?». È un confronto fra regimi
   di campionamento diversi, e va presentato come tale.

Il ramo A non è quindi una replica: è un **test di presenza**. Vale comunque più di tutto il resto,
perché è l'unico che separa «pipeline» da «mock BGS».

### Passi

- [ ] **A.1** Per ciascun tracciatore: derivare box, Δ*x*, maschera, σ_px, w̄, *d*_med dai random —
      la macchina di `paper2_item12a_geom.py` è già scritta e riusabile.
- [ ] **A.2** Verificare l'ammissibilità con i criteri **per tracciatore**; escludere a priori e
      dichiararlo.
- [ ] **A.3** Mock like-for-like per ciascun tracciatore. **È qui che sta il costo vero del ramo:**
      servono mock con HOD calibrato sul tracciatore, non su BGS.
- [ ] **A.4** Deficit frazionario e rango empirico per tracciatore.
- [ ] **A.5** Dichiarare **prima** la regola di lettura: quanti tracciatori con rango 1/(*N*+1)
      servono per dire «comune», e quale ampiezza relativa conta come «comparabile».

---

## 3. Punto di decisione, dopo il ramo A

Fissato prima di eseguire.

- **Se A dissolve l'anomalia** — deficit assente o fortemente ridotto negli altri tracciatori — i
  rami B e C si riducono a conferme, il paper si scrive prima e la conclusione è già in mano. È
  l'esito al ~60% del pronostico dichiarato.
- **Se A la conferma su tre tracciatori**, B e C diventano il corpo del paper, e l'anomalia entra nel
  territorio in cui vale la pena cercare un collaboratore affiliato prima di procedere.

---

## 4. Ramo B — il forward model ufficiale DESI
### *(chiude (i), (v), (vi), (viii))*

Sostituire i surrogati con i prodotti ufficiali.

**B1 — fiber assignment.** Mock DR1 con assegnazione reale (altMTL) e veloce (FFA), pubblicati con
DR1 su `data.desi.lbl.gov`: 25 Abacus-2 altMTL, 25 FFA, 1000 EZmocks-FFA, con varianti *complete* per
il nullo. Per ciascun mock BGS, *N*_H1 nelle tre varianti. **La differenza altMTL − complete è
l'effetto fibra reale sulla topologia**, da confrontare con il segno «sbagliato» trovato dai due
surrogati di M26.

**B2 — lightcone SHAM.** Uchuu-BGS (Fernández-García et al. 2025/26) riproduce l'evoluzione in *z*
del clustering BGS-BRIGHT entro il 5%, eliminando in un colpo snapshot-vs-lightcone, fedeltà HOD e in
parte assembly bias.

**B3 — HOD su NFW.** Ramo esplicito, **più economico dello SHAM e rivolto alla stessa domanda**. Il
Paper 1 lo indica come *"the one small-scale channel whose amplitude the present experiments do not
bound"*: non il profilo satellite a HOD fisso, già bounded a −0.8%, ma l'HOD **ricalibrato** su mock
a profilo NFW.

**B4 — sintesi.** Tab. 1 di M26 versione 2.0, con fiber assignment reale, lightcone reale e SHAM al
posto delle voci surrogate.

**Attenzione statistica.** Con 25 realizzazioni il risultato è lo **spostamento della media** mock,
non un nuovo *p*-value fine. Dichiararlo prima evita di trasformare 25 mock in un rango che non
possono sostenere.

**Rischio specifico.** I mock BGS altMTL DR1 potrebbero coprire il campione BGS_BRIGHT standard e non
esattamente il taglio −21.5: prevedere il sotto-campionamento in magnitudine assoluta dal mock, e
dichiararlo come passo aggiuntivo rispetto al like-for-like di M26.

---

## 5. Ramo C — BOSS DR12, come robustezza e non come tesi
### *(chiude (iii) insieme al ramo A)*

Survey con strumento, targeting, imaging e pipeline osservativa completamente indipendenti da DESI.
2048 mock MultiDark-PATCHY. **I random CMASS North e South sono già scaricati.**

**Perché è retrocesso da paper autonomo a ramo.** PATCHY **non è N-body completo** e sbaglia
notoriamente le piccole scale — che sono esattamente le scale su cui vive il deficit. Un deficit
misurato su BOSS con denominatore PATCHY sarebbe ambiguo quasi quanto quello su BGS con denominatore
Quijote: si sposterebbe la domanda da «i mock BGS sono calibrati bene?» a «i mock PATCHY lo sono?»,
senza risolverla. Il doppio denominatore (PATCHY + Quijote) mitiga ma non elimina.

Come sezione costa poco e dice quanto può dire. Come paper autonomo prometterebbe più di quanto
mantiene, ed è il motivo per cui non passa il test di sopravvivenza.

**Da scrivere esplicitamente nel manoscritto**, perché un referee lo chiederà: il limite del ramo C
è nel denominatore, non nel dato.

---

## 6. Struttura del manoscritto

1. Introduzione: cosa i test interni non possono decidere, e perché la concordanza NGC/SGC non
   discrimina.
2. **Ramo A:** multi-tracciatore, con le griglie riderivate e i criteri di ammissibilità per
   tracciatore.
3. Il punto di decisione, e cosa ha deciso.
4. **Ramo B:** fiber assignment reale, lightcone SHAM, HOD-su-NFW; Tab. 1 di M26 v2.0.
5. **Ramo C:** BOSS DR12, con il limite del denominatore dichiarato.
6. **Budget sistematico congiunto**, con la **covarianza fra canali** — la parte che nessun paper
   precedente della serie produce.
7. Verdetto, e cosa resta aperto.

### Figure

- **(F1)** Deficit frazionario e rango per tracciatore, con le densità di campionamento sull'asse
  secondario — **la figura del ramo A**.
- **(F2)** altMTL − complete contro FFA − complete, con il segno dei surrogati di M26 sovrapposto —
  **la figura del ramo B**.
- **(F3)** Tab. 1 di M26 v2.0 come figura a barre, surrogati e prodotti ufficiali affiancati.
- **(F4)** BOSS contro DESI, con la banda di incertezza del denominatore PATCHY esplicita.
- **(F5)** **Matrice di covarianza fra canali sistematici** — il prodotto nuovo del paper.

---

## 7. Rischi

| rischio | probabilità | mitigazione |
|---|---|---|
| I mock per LRG/ELG/QSO non sono disponibili con HOD adeguato | **alta** | è il costo vero del ramo A: verificarlo prima di tutto il resto |
| Il regime di campionamento diverso rende il confronto poco leggibile | media | dichiarato come test di presenza, non di ampiezza |
| Download dei prodotti ufficiali proibitivi | media | lotti; il ramo A non ne dipende |
| altMTL sposta la media mock verso DESI di migliaia di generatori | media | **l'anomalia muore, e va scritto lo stesso** |
| Il paper diventa tre paper | **media** | il punto di decisione dopo A è la valvola: se A decide, B e C si accorciano |

---

## 8. Risorse

Ramo A: dati già sul disco; il costo è nei mock per tracciatore. Rami B e C: centinaia di GB dal
portale pubblico DESI e da Skies & Universes, a lotti; padroneggiare il data model DESI richiede
tempo. **Mesi**, ed è il paper più lungo della serie.

---

## 9. Target

**MNRAS** o **JCAP**. Chiude (i), (iii), (iv), (v), (vi), (viii) — sei limitazioni su undici, più di
qualunque altro paper della serie.

È anche il paper che qualunque referee del paper base chiederà, prima o poi. Averlo pianificato per
iscritto prima che lo chieda è già un vantaggio.
