#!/usr/bin/env python3
"""
paper2_patch_censimento_15.py  —  paper2_censimento_registri.py da 1.4 a 1.5 (voce 6.2-vi)

Tre correzioni e una dichiarazione:
  - verdetto: il segnale guarda anche dentro il record (fino a 3 livelli) e conosce
    `pass`/`passed`, per nome ESATTO; gate53 e gate53_margini non sono piu'
    «gate senza verdetto»
  - un gate dichiarato si giudica dalla presenza del verdetto, non dal confronto
    con una classe misurata che per costruzione non puo' essere `gate`: chiude la
    DISCORDANZA permanente di gate25.jsonl (record 68)
  - `gate_senza_verdetto` entra nell'uscita, come la docstring di classe_misurata
    diceva che dovesse essere
  - i 67 registri non classificati dal 15 settembre, per nome esatto, fuori scopo
    6.1 perche' chiusi, con la loro citazione nel motivo

Ogni intervento e' una sostituzione con ancora unica; l'inversa deve restituire
l'originale byte per byte prima di scrivere; il dry-run esegue il selftest dello
strumento PATCHATO in una copia temporanea e rifiuta se non passa.

Uso:
  python src\\paper2_patch_censimento_15.py selftest
  python src\\paper2_patch_censimento_15.py dry-run
  python src\\paper2_patch_censimento_15.py apply
  python src\\paper2_patch_censimento_15.py verify
"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "paper2_censimento_registri.py"
SHA_ATTESO = "d8836f745d601027ac97b460ad1e141bb2958b60bb93fe73f173850b25f4971c"
BYTE_ATTESI = 91096

EDITS = json.loads(r'''[
 [
  "E1 versione",
  "VERSIONE = \"1.4\"",
  "VERSIONE = \"1.5\""
 ],
 [
  "E2 campi di verdetto",
  "CAMPI_VERDETTO = (\"verdetto\", \"esito\", \"verdict\", \"status\", \"stato\", \"gate\", \"cancello\")",
  "CAMPI_VERDETTO = (\"verdetto\", \"esito\", \"verdict\", \"status\", \"stato\", \"gate\", \"cancello\",\n                  \"pass\", \"passed\")\n# Profondita' e larghezza della ricerca del verdetto dentro un record (1.5).\nPROFONDITA_VERDETTO = 3\nMAX_ELEMENTI_VERDETTO = 50"
 ],
 [
  "E3 segnale di verdetto per record",
  "        for nome, valore in record.items():\n            minuscolo = nome.lower()\n            if minuscolo in CAMPI_VERDETTO or (\n                isinstance(valore, str) and valore.upper() in VALORI_VERDETTO\n            ):\n                ris[\"segnale_verdetto\"] += 1\n                break\n",
  "        if _porta_verdetto(record):\n            ris[\"segnale_verdetto\"] += 1\n"
 ],
 [
  "E4 funzione _porta_verdetto",
  "def misura_record(dati: bytes, max_forme: int = 12) -> dict:",
  "def _porta_verdetto(oggetto, profondita: int = 0) -> bool:\n    \"\"\"Un verdetto a qualunque livello, fino a PROFONDITA_VERDETTO.\n\n    DIFETTO CORRETTO il 18 set 2026 (voce 6.2-vi, versione 1.5): il segnale\n    guardava solo le chiavi di primo livello e non conosceva `pass`.\n    gate53.jsonl porta `pass` booleano, gate53_margini.jsonl porta `esito`\n    dentro `margine_*`: il censimento del 15 set li dava entrambi «gate senza\n    verdetto», frazione 0.0. Il nome del campo si confronta per UGUAGLIANZA,\n    mai per sottostringa: `mask_pass` e `F_ap_passed` non sono verdetti, e\n    `bypass_signal` nemmeno.\n    \"\"\"\n    if profondita > PROFONDITA_VERDETTO:\n        return False\n    if isinstance(oggetto, dict):\n        for nome, valore in oggetto.items():\n            if str(nome).lower() in CAMPI_VERDETTO:\n                return True\n            if isinstance(valore, str) and valore.upper() in VALORI_VERDETTO:\n                return True\n            if isinstance(valore, (dict, list)) and _porta_verdetto(valore, profondita + 1):\n                return True\n    elif isinstance(oggetto, list):\n        for valore in oggetto[:MAX_ELEMENTI_VERDETTO]:\n            if isinstance(valore, (dict, list)) and _porta_verdetto(valore, profondita + 1):\n                return True\n    return False\n\n\ndef misura_record(dati: bytes, max_forme: int = 12) -> dict:"
 ],
 [
  "E5a stato di classe di un gate",
  "    if dichiarata is None:\n        stato_classe = \"NON_CLASSIFICATO\"\n        classe = misurata\n    elif misurata == \"indeterminato\":",
  "    # Un file DICHIARATO gate non si confronta con la classe misurata: `gate`\n    # non e' una classe misurata (vedi classe_misurata), e il confronto dava\n    # DISCORDANZA per costruzione a ogni cancello che porta un indice —\n    # gate25.jsonl, lasciato cosi' dal record 68: un FAIL permanente per\n    # disegno. Per un gate il controllo e' la presenza del verdetto, e dalla\n    # 1.5 pesa sull'uscita (18 set 2026, voce 6.2-vi).\n    gate_senza_verdetto = (\n        dichiarata == \"gate\" and record[\"n_record\"] > 0\n        and record[\"segnale_verdetto\"] / record[\"n_record\"] < 0.50\n    )\n    if dichiarata is None:\n        stato_classe = \"NON_CLASSIFICATO\"\n        classe = misurata\n    elif dichiarata == \"gate\":\n        stato_classe = \"GATE_SENZA_VERDETTO\" if gate_senza_verdetto else \"GATE_CON_VERDETTO\"\n        classe = dichiarata\n    elif misurata == \"indeterminato\":"
 ],
 [
  "E5b calcolo spostato sopra",
  "    # Un file DICHIARATO gate che non contiene verdetti: quello e' un difetto,\n    # al contrario di un sommario che ne contiene uno.\n    gate_senza_verdetto = (\n        dichiarata == \"gate\" and record[\"n_record\"] > 0\n        and record[\"segnale_verdetto\"] / record[\"n_record\"] < 0.50\n    )\n",
  "    # (gate_senza_verdetto e' calcolato sopra, prima dello stato di classe.)\n"
 ],
 [
  "E6a elenco dei gate senza verdetto",
  "    discordanze = []\n",
  "    discordanze = []\n    gate_muti = []\n"
 ],
 [
  "E6b raccolta",
  "        if record[\"stato_classe\"] == \"DISCORDANZA\":\n            discordanze.append(record[\"percorso\"])\n",
  "        if record[\"stato_classe\"] == \"DISCORDANZA\":\n            discordanze.append(record[\"percorso\"])\n        if record[\"stato_classe\"] == \"GATE_SENZA_VERDETTO\":\n            gate_muti.append(record[\"percorso\"])\n"
 ],
 [
  "E6c sommario",
  "        \"discordanze_classe\": discordanze,\n",
  "        \"discordanze_classe\": discordanze,\n        \"gate_senza_verdetto\": gate_muti,\n"
 ],
 [
  "E6d stampa",
  "    if discordanze:\n        print(\"DISCORDANZA fra classe dichiarata e classe misurata (%d):\" % len(discordanze))",
  "    if gate_muti:\n        print(\"GATE SENZA VERDETTO (%d):\" % len(gate_muti))\n        for p in gate_muti:\n            print(\"  %s\" % p)\n        print()\n    if discordanze:\n        print(\"DISCORDANZA fra classe dichiarata e classe misurata (%d):\" % len(discordanze))"
 ],
 [
  "E6e uscita",
  "    if non_classificati or discordanze or problemi_cancello or baseline_falliti:",
  "    if non_classificati or discordanze or gate_muti or problemi_cancello or baseline_falliti:"
 ],
 [
  "E7 i 67 dichiarati",
  "    (\"censimento_verdetti.jsonl\", \"log\", False, \"uscita del censimento dei verdetti, voce 6.9\"),\n)",
  "    (\"censimento_verdetti.jsonl\", \"log\", False, \"uscita del censimento dei verdetti, voce 6.9\"),\n    # --- i 67 lasciati non classificati dal 15 set: voce 6.2-vi (g), 18 set --\n    # Nome ESATTO, mai un glob: un file nuovo resta non classificato e fa\n    # fallire il censimento, come deve. Fuori scopo 6.1 perche' CHIUSI: le\n    # proprieta' di 6.1 riguardano registri che un runner appende, e nessun\n    # runner li riprende (fasi 3-5 chiuse, record 59-60; revisione del Paper 1\n    # chiusa). L'append storico resta verificato per tutti dalla baseline.\n    # La citazione nel motivo e' cio' che serve alla 6.2; e' un'istantanea.\n    (\"m2_fiducial_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"m2b_hodscatter_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"n10b_control_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"n1_spectra_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 50, 52, 54, 71\"),\n    (\"n1b_spectra_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 50, 52, 54, 71, 75; modifiche_paper1.md\"),\n    (\"n1c_bands_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"n2_persistence_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: checklist\"),\n    (\"n6_fkp_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 56\"),\n    (\"n7_nfw_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; registro del test NFW del Paper 1 §7.1 e della riga 5 del budget; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"n8_masks_128.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 60; budget, modifiche_paper1.md\"),\n    (\"n8b_masks_128_B.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 60; checklist, budget, modifiche_paper1.md\"),\n    (\"n9_res256_NGC.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"per_target_NGC_mirror_lfl.jsonl\", \"run\", False,\n     \"Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"cancello_nu_NGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 54\"),\n    (\"d3_check.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"d6_incertezze.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 63, 64, 65\"),\n    (\"d6bis.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 63, 64, 65\"),\n    (\"dmed_NGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 6\"),\n    (\"dmed_SGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 6, 7\"),\n    (\"due_lati.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 19, 20, 21, 22; checklist\"),\n    (\"fase3_analisi.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 15; checklist, budget, modifiche_paper1.md\"),\n    (\"fase3_budget.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 40, 46, 49; checklist, budget\"),\n    (\"fase3_intersezione.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 25\"),\n    (\"fase3_intersezione_verdetto.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"fase3_maskpass1.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 25\"),\n    (\"fase3_mock_carve777.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 26\"),\n    (\"fase3_mock_carve777_b6.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 39\"),\n    (\"fase3_mock_fid_ripetizione.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: checklist\"),\n    (\"fase3_mock_fixedobs.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 38\"),\n    (\"fase3_mock_realspace.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 35, 37\"),\n    (\"fase3_mock_realspace_NULLO.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 35, 36\"),\n    (\"fase3_mock_smoke.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"fase3_surrogato.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"fase3_surrogato_pass1.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"fasi_desi_pr_NGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"fasi_desi_pr_SGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"fasi_mock_pr_v2_NGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"fasi_mock_pr_v2_SGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"gazione_32d.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 44\"),\n    (\"item12a_cosmo.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 15, 19; checklist\"),\n    (\"item12a_geom_NGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 13; checklist\"),\n    (\"item12b_NGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 2, 71\"),\n    (\"item12b_SGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 2, 3, 7, 71\"),\n    (\"item13a.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"item13rev2_NGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 74\"),\n    (\"item13rev2_SGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 74\"),\n    (\"item15a_NGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"item15a_SGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"item15a_g13_NGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: checklist\"),\n    (\"item15a_g13_SGC.jsonl\", \"run\", False,\n     \"Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: checklist\"),\n    (\"smoke_1punto_NGC.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_1punto_NGC_sommario.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_offset0.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_post32d.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; citato: record 44\"),\n    (\"smoke_pre32d.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; citato: record 44\"),\n    (\"smoke_v2_NGC.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_NGC_ancore.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_NGC_ancore_sommario.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_NGC_appaiato.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_NGC_appaiato_sommario.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_NGC_sommario.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_SGC.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_SGC_ancora.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_SGC_ancora_sommario.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"smoke_v2_SGC_sommario.jsonl\", \"run\", False,\n     \"smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"survey_ancora_SGC.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set\"),\n    (\"tabres_probe.jsonl\", \"run\", False,\n     \"Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 14, 51\"),\n)"
 ],
 [
  "E8 selftest",
  "    totale = c.ok + len(c.ko)\n    print(\"selftest: %d/%d\" % (c.ok, totale))",
  "    # ---- 43. verdetto: annidato e `pass` (1.5, voce 6.2-vi) ---------------\n    # DIFETTO RIPRODOTTO: queste forme davano segnale 0 fino alla 1.4.\n    g53 = b'{\"pass\":false,\"fails\":[\"x\"],\"region\":\"NGC\"}\\n{\"pass\":true,\"fails\":[],\"region\":\"NGC\"}\\n'\n    c.uguale(\"gate53: pass booleano e' un verdetto\", misura_record(g53)[\"segnale_verdetto\"], 2)\n    marg = b'{\"region\":\"NGC\",\"margine_1_z\":{\"soglia\":3,\"esito\":\"confermata\"}}\\n'\n    c.uguale(\"margini: esito annidato e' un verdetto\", misura_record(marg)[\"segnale_verdetto\"], 1)\n    falsi = b'{\"mask_pass\":\"derive\",\"F_ap_passed\":1.03,\"bypass_signal\":3,\"x\":{\"passenger\":1}}\\n'\n    c.uguale(\"nome per uguaglianza: nessun falso positivo\", misura_record(falsi)[\"segnale_verdetto\"], 0)\n    profondo = b'{\"a\":{\"b\":{\"c\":{\"d\":{\"e\":{\"esito\":\"PASS\"}}}}}}\\n'\n    c.uguale(\"oltre la profondita' dichiarata non si cerca\", misura_record(profondo)[\"segnale_verdetto\"], 0)\n\n    # ---- 44. un gate si giudica dal verdetto, non dalla classe -------------\n    with tempfile.TemporaryDirectory() as td:\n        radice = Path(td)\n        (radice / \"results\" / \"paper2\").mkdir(parents=True)\n        g25 = radice / \"results\" / \"paper2\" / \"gate25.jsonl\"\n        g25.write_bytes(b'{\"gate\":\"2.5\",\"pass\":true,\"seed\":1,\"idx\":0}\\n'\n                        b'{\"gate\":\"2.5\",\"pass\":true,\"seed\":2,\"idx\":1}\\n')\n        r25 = censisci_file(g25, radice)\n        c.uguale(\"gate25: indice e verdetto -> GATE_CON_VERDETTO\", r25[\"stato_classe\"], \"GATE_CON_VERDETTO\")\n        c.uguale(\"gate25: nessuna discordanza per costruzione\", r25[\"gate_senza_verdetto\"], False)\n        muto = radice / \"results\" / \"paper2\" / \"gate99.jsonl\"\n        muto.write_bytes(b'{\"idx\":0,\"valore\":1.0}\\n{\"idx\":1,\"valore\":2.0}\\n')\n        c.uguale(\"gate senza verdetto -> GATE_SENZA_VERDETTO\",\n                 censisci_file(muto, radice)[\"stato_classe\"], \"GATE_SENZA_VERDETTO\")\n\n    # ---- 45. i 67 del 15 set, per nome esatto, fuori scopo -----------------\n    sessantasette = [g for g, _, _, m in CLASSI_DICHIARATE if \"fuori scopo 6.1;\" in m]\n    c.uguale(\"i 67 sono dichiarati\", len(sessantasette), 67)\n    c.uguale(\"nessuno dei 67 e' un glob\", [g for g in sessantasette if any(x in g for x in \"*?[\")], [])\n    c.uguale(\"nessuno dei 67 e' in scopo\", [g for g in sessantasette if classe_dichiarata(g)[1]], [])\n    c.uguale(\"ognuno risolve alla propria riga\", [g for g in sessantasette\n             if \"fuori scopo 6.1;\" not in (classe_dichiarata(g)[2] or \"\")], [])\n    c.uguale(\"un nome nuovo resta non classificato\", classe_dichiarata(\"qualcosa_di_nuovo.jsonl\")[0], None)\n\n    totale = c.ok + len(c.ko)\n    print(\"selftest: %d/%d\" % (c.ok, totale))"
 ],
 [
  "E9 controllo 20, stesso principio e nuovo nome dello stato",
  "        c.uguale(\"discordanza rilevata\", record[\"stato_classe\"], \"DISCORDANZA\")",
  "        # 1.5 (18 set): un gate dichiarato si giudica dal verdetto. La proprieta'\n        # che questo controllo protegge resta — un file chiamato gate che e' un\n        # run NON passa — e cambia il nome dello stato, che pesa sull'uscita.\n        c.uguale(\"discordanza rilevata\", record[\"stato_classe\"], \"GATE_SENZA_VERDETTO\")"
 ]
]''')

def sha(b): return hashlib.sha256(b).hexdigest()

def applica(testo: str) -> str:
    for nome, old, new in EDITS:
        n = testo.count(old)
        if n != 1:
            raise SystemExit(f"STOP: ancora «{nome}» trovata {n} volte (attesa 1); nessuna modifica")
        testo = testo.replace(old, new, 1)
    return testo

def inverti(testo: str) -> str:
    for nome, old, new in reversed(EDITS):
        if testo.count(new) != 1:
            raise SystemExit(f"STOP: inversa, «{nome}» non unica")
        testo = testo.replace(new, old, 1)
    return testo

def selftest():
    ok = 0
    fixture = "\n\n# filler\n\n".join(old for _, old, _ in EDITS) + "\n"
    out = applica(fixture)
    assert all(out.count(new) == 1 for _, _, new in EDITS); ok += 1
    assert inverti(out) == fixture; ok += 1
    try: applica(out); raise AssertionError("seconda applicazione accettata")
    except SystemExit: ok += 1
    try: applica(fixture.replace(EDITS[0][1], "")); raise AssertionError("ancora mancante accettata")
    except SystemExit: ok += 1
    olds = [o for _, o, _ in EDITS]
    assert len(olds) == len(set(olds)); ok += 1
    b67 = [e for e in EDITS if e[0].startswith("E7")][0][2]
    assert b67.count('"run", False,') == 67; ok += 1
    print(f"selftest: {ok}/6 OK  ({len(EDITS)} interventi)")

def prepara():
    raw = TARGET.read_bytes()
    if sha(raw) != SHA_ATTESO or len(raw) != BYTE_ATTESI:
        raise SystemExit(f"STOP: ancora attesa {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, "
                         f"trovata {sha(raw)[:12]}… {len(raw)} byte; nessuna modifica")
    if b"\r\n" in raw:
        raise SystemExit("STOP: il file ha CRLF, l'ancora e' stata misurata LF")
    testo = raw.decode("utf-8")
    nuovo = applica(testo)
    if inverti(nuovo) != testo:
        raise SystemExit("STOP: l'inversa non restituisce l'originale byte per byte")
    return raw, nuovo.encode("utf-8")

def selftest_patchato(dati: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "paper2_censimento_registri.py"
        p.write_bytes(dati)
        r = subprocess.run([sys.executable, str(p), "selftest"], capture_output=True, text=True)
        riga = [l for l in r.stdout.splitlines() if l.startswith("selftest:")]
        return r.returncode, (riga[-1] if riga else r.stdout[-300:] + r.stderr[-300:])

def dry_run():
    raw, nuovo = prepara()
    rc, riga = selftest_patchato(nuovo)
    print(f"dry-run: ancora {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte; {len(EDITS)} interventi, inversa esatta")
    print(f"  dopo: {len(nuovo)} byte (Δ {len(nuovo)-len(raw):+d}), sha {sha(nuovo)[:12]}…")
    print(f"  selftest dello strumento patchato: {riga}  (rc {rc})")
    if rc != 0:
        raise SystemExit("STOP: il selftest dello strumento patchato non passa; nessuna modifica")
    print("  nessuna modifica scritta")

def apply():
    raw, nuovo = prepara()
    rc, riga = selftest_patchato(nuovo)
    if rc != 0:
        raise SystemExit(f"STOP: selftest dello strumento patchato: {riga}; nessuna modifica")
    logs = ROOT / "logs"; logs.mkdir(exist_ok=True)
    bak = logs / (TARGET.name + ".bak_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(TARGET, bak)
    fd, tmp = tempfile.mkstemp(dir=str(TARGET.parent), prefix=TARGET.name + ".", suffix=".tmp")
    with os.fdopen(fd, "wb") as fh:
        fh.write(nuovo); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, TARGET)
    print(f"[apply] scritto: sha {sha(TARGET.read_bytes())}  {TARGET.stat().st_size} byte  (backup in logs/)")

def verify():
    dati = TARGET.read_bytes(); t = dati.decode("utf-8")
    err = [nome for nome, old, new in EDITS if t.count(new) != 1]
    rc, riga = selftest_patchato(dati)
    print(f"verify {'OK' if not err and rc == 0 else 'ANOMALIA'}: sha {sha(dati)}  {len(dati)} byte; {riga}")
    for e in err: print("  - intervento assente o duplicato:", e)
    if err or rc != 0: sys.exit(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    {"selftest": selftest, "dry-run": dry_run, "apply": apply, "verify": verify}[ap.parse_args().cmd]()
