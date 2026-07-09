# Tests Manuels — Phase 2 « Le pari IA » (z_aud_2)

> Ce document consigne les procédures de vérification **non automatisables** de la phase, et sert
> de **registre d'exécution** : chaque procédure doit être déroulée et son résultat consigné dans
> le tableau final avant de cocher la tâche correspondante dans `tasks.md`.

**Convention :** chaque section porte un identifiant `MT-x` référencé depuis `tasks.md`.
Un test manuel est **PASS** uniquement si toutes ses étapes de vérification sont satisfaites.

---

## MT-1 — Publication et installation des packages d'intégration

**Couvre :** Requirements 4.1, 5.1 · **Tâche :** 11.1
**Prérequis :** pipeline de publication opérationnel (Trusted Publishing Phase 1 ou workflow
dédié) ; comptes TestPyPI/PyPI ; `uv` installé pour le test `uvx`.

### Procédure

1. **TestPyPI d'abord** — publier `tenxyte-langchain==0.1.0` et `tenxyte-mcp-server==0.1.0` sur
   TestPyPI via le workflow.
2. **Installation LangChain** dans un venv vierge :
   ```bash
   python -m venv /tmp/vx-lc && source /tmp/vx-lc/bin/activate
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ tenxyte-langchain
   python -c "from tenxyte_langchain import TenxyteAIRSClient, TenxyteAgentAuth, TenxyteHITLPending; print('OK')"
   pip show tenxyte-langchain   # vérifier: deps = httpx, langchain-core UNIQUEMENT (pas de tenxyte)
   ```
3. **Installation MCP** :
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ tenxyte-mcp-server
   tenxyte-mcp-server --help 2>&1 | head -5      # ou vérifier le message d'env manquantes + exit != 0
   echo $?                                        # DOIT être != 0 sans variables d'env
   ```
4. **Test uvx** (exécution éphémère) :
   ```bash
   TENXYTE_BASE_URL=http://localhost:8000 TENXYTE_AGENT_TOKEN=dummy \
   TENXYTE_ACCESS_KEY=k TENXYTE_ACCESS_SECRET=s uvx tenxyte-mcp-server &
   # DOIT démarrer et attendre sur stdio (tuer après vérification)
   ```
5. Répéter 1–4 sur **PyPI production** après validation TestPyPI.

✅ Attendu : les deux packages installables, imports OK, dépendances conformes à la
HTTP_Only_Rule, `uvx` fonctionnel, démarrage sans env → échec explicite.

---

## MT-2 — Serveur MCP de bout en bout dans Claude Desktop

**Couvre :** Requirements 5.3, 5.5, 5.7 · **Tâches :** 6.1, 6.4
**Prérequis :** Claude Desktop installé ; instance Tenxyte locale (docker-compose de
`examples/crewai/` ou projet de test) avec `AIRS_ENABLED=True` ; un Agent_Token actif émis via
`POST /ai/tokens/` (conserver le brut).

### Configuration

Ajouter au `claude_desktop_config.json` (bloc fourni par le README du package) :
```json
{
  "mcpServers": {
    "tenxyte-airs": {
      "command": "uvx",
      "args": ["tenxyte-mcp-server"],
      "env": {
        "TENXYTE_BASE_URL": "http://localhost:8000",
        "TENXYTE_AGENT_TOKEN": "<raw_agent_token>",
        "TENXYTE_ACCESS_KEY": "<access_key>",
        "TENXYTE_ACCESS_SECRET": "<access_secret>"
      }
    }
  }
}
```
Redémarrer Claude Desktop.

### Scénarios

| # | Scénario | Étapes | Attendu |
|---|---|---|---|
| 2.1 | **Découverte des tools** | Ouvrir le panneau tools de Claude Desktop | Exactement 5 tools `airs_*` visibles ; AUCUN tool de création de token ni de confirmation HITL |
| 2.2 | **Statut du token** | Demander « quel est le statut de ton token AIRS ? » | Appel `airs_token_status`, réponse avec statut ACTIVE, expiration, budget restant |
| 2.3 | **Heartbeat** | Demander à l'agent d'envoyer un heartbeat | `airs_heartbeat` OK ; vérifier `last_heartbeat_at` mis à jour côté serveur (admin ou API) |
| 2.4 | **Rapport d'usage** | Demander de rapporter 0.05 USD / 1000 / 200 tokens | `airs_report_usage` OK ; `current_spend_usd` incrémenté côté serveur |
| 2.5 | **Actions en attente** | Créer une pending action côté serveur (endpoint HITL de démo), puis demander la liste | `airs_list_pending_actions` retourne l'action avec son expiration (SANS le confirmation_token utilisable pour confirmer côté agent — lecture seule) |
| 2.6 | **Token suspendu** | Suspendre le token (`POST /ai/tokens/<id>/suspend/`), puis redemander le statut | Erreur MCP structurée portant la raison ; le serveur MCP ne crashe pas (les appels suivants répondent encore) |
| 2.7 | **Inspection stdio** | Optionnel : rejouer 2.2–2.6 avec `npx @modelcontextprotocol/inspector uvx tenxyte-mcp-server` | Mêmes résultats dans l'inspector MCP |

✅ Attendu : les 7 scénarios conformes ; en particulier 2.1 (surface exacte) et 2.6 (fail-safe).

---

## MT-3 — Connecteur LangChain avec un vrai LLM

**Couvre :** Requirements 4.4, 4.5, 4.6, 4.9 · **Tâches :** 5.2, 5.3, 5.9
**Prérequis :** Tenxyte local `AIRS_ENABLED=True` + `AIRS_BUDGET_TRACKING_ENABLED=True` ; une clé
API LLM (ou le FakeLLM documenté) ; l'exemple minimal du README du connecteur.

### Scénarios

| # | Scénario | Étapes | Attendu |
|---|---|---|---|
| 3.1 | **Exemple minimal du README** | Copier-coller l'exemple du README tel quel, exécuter | Fonctionne sans modification (le README est le premier test) |
| 3.2 | **Auth systématique** | Activer le logging HTTP (`HTTPX_LOG_LEVEL=debug`), dérouler un run d'agent | Chaque requête sortante porte `AgentBearer` + `X-Prompt-Trace-ID` |
| 3.3 | **Heartbeat de fond** | Émettre un token avec `heartbeat_required_every=10`, lancer un run > 30 s | `last_heartbeat_at` serveur rafraîchi à intervalle < 10 s ; arrêt du script → thread stoppé proprement (pas de process zombie) |
| 3.4 | **Budget en conditions réelles** | Token avec `budget_limit_usd=0.01`, callback budget actif, run avec vrai LLM jusqu'au dépassement | Suspension serveur `BUDGET_EXCEEDED` ; le connecteur lève `TenxyteBudgetExceededError` ; l'agent s'arrête (pas de retry) |
| 3.5 | **HITL complet** | Outil pointant un endpoint `@require_agent_clearance(human_in_the_loop_required=True)` ; run | `TenxyteHITLPending` levée avec token ; confirmer côté humain (`POST /ai/pending-actions/<token>/confirm/` avec JWT user) ; `resume()` → l'action s'exécute |
| 3.6 | **Recette LangGraph** | Dérouler la recette `interrupt()` du README dans un graphe minimal | Le graphe s'interrompt sur HITL, reprend après confirmation, aboutit |

✅ Attendu : les 6 scénarios conformes ; consigner les latences observées en 3.4/3.5 (utiles pour
recouper MT-6).

---

## MT-4 — Walkthrough CrewAI complet

**Couvre :** Requirements 6.1, 6.2, 6.3, 6.4 · **Tâches :** 9.1, 9.2
**Prérequis :** Docker + docker-compose ; AUCUNE clé LLM requise (FakeLLM par défaut).

### Procédure

1. `cd examples/crewai && docker-compose up -d` — vérifier que le backend démo répond
   (`GET /ai/.well-known/airs/` → 200 avec les 5 niveaux).
2. Suivre le README **pas à pas, sans dévier** — le test valide autant la doc que le code :
   a. Émission du token par l'« humain » (script fourni) — noter que le brut n'est affiché qu'une fois.
   b. Lancement du crew (`python crew.py`) — les deux agents travaillent, requêtes AgentBearer visibles dans les logs.
   c. L'outil « émettre une facture » déclenche le HITL → le crew se met en pause avec le message d'attente.
   d. Confirmation humaine via le script/curl fourni → le crew reprend et termine.
   e. Relancer avec `--demo-budget` → suspension `BUDGET_EXCEEDED` en direct, arrêt propre du crew.
3. Option : basculer sur un vrai LLM selon la section dédiée du README et rejouer b–d.
4. `docker-compose down -v` — vérifier l'absence de résidus.

✅ Attendu : chaque étape du README correspond exactement au comportement observé ; toute
divergence = FAIL du README (à corriger avant de re-tester).

---

## MT-5 — Suite de conformité contre une implémentation externe simulée

**Couvre :** Requirements 3.1, 3.2 · **Tâches :** 4.1, 4.2
**Objectif :** vérifier que la suite est réellement utilisable par un implémenteur tiers (pas
seulement par notre CI).

### Procédure

1. Sur une machine/venv sans le repo Tenxyte, récupérer uniquement `spec/airs/conformance/`.
2. Lancer contre un Tenxyte distant (ou local mais traité comme boîte noire) :
   ```bash
   pytest spec/airs/conformance/ \
     --airs-base-url=http://localhost:8000/api/v1/auth \
     --airs-user-jwt=<jwt> --airs-app-key=<k> --airs-app-secret=<s> -v
   ```
3. Vérifier : la suite découvre les niveaux, saute proprement les niveaux désactivés (re-tester
   avec `AIRS_BUDGET_TRACKING_ENABLED=False` → module budget SKIPPED, pas FAILED).
4. Vérifier que la sortie référence les identifiants normatifs `[AIRS-*-n]` en cas d'échec
   (provoquer un échec artificiel pour contrôle).

✅ Attendu : exécutable hors du repo, skip corrects, messages traçables vers la spec.

---

## MT-6 — Campagne de benchmarks de référence

**Couvre :** Requirement 7.3 · **Tâche :** 10.2
**Prérequis :** machine dédiée au repos (pas de CI partagée), Docker, specs machine notées.

### Procédure

1. `cd benchmarks/airs && docker-compose up -d` (environnement figé, seed standard).
2. `python bench_validation.py --requests 10000 --warmup 500` — trois cibles mesurées
   (AgentBearer+Double_Validation, JWT nu, baseline). Trois runs consécutifs.
3. `python bench_hitl.py --cycles 1000` — cycle 202 → confirm → rejeu auto-confirmé.
4. Vérifier la stabilité inter-runs (écart p95 < 10 % entre les 3 runs ; sinon investiguer et
   recommencer).
5. Renseigner `RESULTS.md` : specs machine (CPU, RAM, OS, Docker), versions, tableaux
   p50/p95/p99, delta AgentBearer vs JWT en ms et en %.
6. Archiver les JSON bruts à côté du RESULTS.md.

✅ Attendu : résultats stables et consignés — c'est la matière de l'article (11.2).

---

## MT-7 — Publication de la spec et soumissions communautaires

**Couvre :** Requirements 1.1, 1.2, 8.1, 8.2, 8.3 · **Tâches :** 1.1, 1.2, 11.2, 11.3, 11.4

### Procédure

1. **Revue de la spec** : rendu GitHub de `spec/airs/AIRS-1.0.md` correct (ancres, tableaux,
   machine à états) ; licence CC BY 4.0 visible dans le document ET dans `spec/airs/LICENSE` ;
   relecture par une personne n'ayant PAS participé à la rédaction, avec pour consigne :
   « pourrais-tu implémenter un serveur AIRS sans lire le code de Tenxyte ? » — toute réponse
   négative sur une section = FAIL de la section.
2. **Vérification d'indépendance** : recherche plein-texte de `django`/`tenxyte` dans les
   sections normatives (hors annexe) → zéro occurrence.
3. **READMEs** : sections AIRS des deux READMEs liant spec + connecteurs + exemple.
4. **Article** : draft complet dans `spec/airs/launch/`, chiffres issus de MT-6, relu.
5. **Soumissions** (consigner URL + date pour chacune) :
   - Annuaire d'intégrations LangChain (PR sur le repo de docs LangChain).
   - `awesome-mcp-servers` (PR).
   - Annuaire(s) MCP publics pertinents au moment de la soumission.
6. L'**acceptation** des PRs tierces est hors Definition of Done — seule la soumission tracée
   compte.

✅ Attendu : spec publiable et réimplémentable, article prêt, 3+ soumissions tracées.

---

## Registre d'exécution

> À compléter à chaque exécution. Une ligne par run (garder l'historique en cas de re-run).

| ID | Intitulé | Date | Exécutant | Environnement | Résultat | Notes / lien preuve |
|----|----------|------|-----------|---------------|----------|---------------------|
| MT-1 | Publication + installation packages | — | — | — | ⬜ À exécuter | TestPyPI d'abord |
| MT-2 | MCP E2E Claude Desktop (2.1–2.7) | — | — | — | ⬜ À exécuter | |
| MT-3 | LangChain E2E vrai LLM (3.1–3.6) | — | — | — | ⬜ À exécuter | |
| MT-4 | Walkthrough CrewAI | — | — | — | ⬜ À exécuter | |
| MT-5 | Conformité en implémenteur tiers | — | — | — | ⬜ À exécuter | |
| MT-6 | Benchmarks de référence | — | — | — | ⬜ À exécuter | machine dédiée |
| MT-7 | Spec + soumissions communautaires | — | — | — | ⬜ À exécuter | URLs des PRs |

**Légende résultat :** ✅ PASS · ❌ FAIL (ouvrir une issue, référencer ici) · ⚠️ PASS avec réserve
(documenter la réserve) · ⬜ À exécuter

## Critère de sortie de la phase

La phase est validée lorsque : toutes les lignes du registre sont ✅ (ou ⚠️ avec réserve acceptée
par le mainteneur), la suite automatisée est verte (tâche 12.1), la suite de conformité passe en
CI contre l'implémentation de référence et échoue contre le mock négatif, et le checkpoint final
de `tasks.md` est coché. L'annonce publique d'AIRS/1.0 n'intervient qu'après.
