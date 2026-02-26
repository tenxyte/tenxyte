# Tenxyte AIRS (AI Responsibility & Security)

Tenxyte AIRS est une suite exhaustive de responsabilit, scurit et garde-fous pour les agents IA intgrs. Elle traite des dfis majeurs poss par les modles LLMs et l'agentique dans les environnements de production (ex: EchoLeak, Shadow Escape).

## Fonctionnalits Cls

### 1. Parit Agentique de Base (AgentToken)
Le concept de l'`AgentToken` encapsule les informations scuritaires d'un agent.
- **Dlgation scurise**: un agent emprunte les permissions d'un utilisateur sans manipuler ses identifiants.
- **RBAC Strict**: un double contrle de permission est exerc ; l'agent doit tre autoris, et l'utilisateur dlgateur doit lui-mme dtenir les droits sous-jacents.

### 2. Circuit Breaker & Rate Limiting
Un pare-feu autonome pour empcher un drapage (boucle infinie, exfiltration) :
- Dsactivation automatique lors de requtes anormales (fentre glissante).
- Un *Dead Man's Switch* requiert des *heartbeats* priodiques pour prouver que le conteneur de contrle est intact. Sinon, suspension automatique.

### 3. Human in the Loop (HITL)
Des dcorateurs (`@require_agent_clearance`) dtournent les requtes de l'agent si une confirmation humaine est ncessaire, retournant `202 Accepted` et mettant en attente l'excution jusqu' l'approbation du workflow.
- **Liste Globale**: Actions configurables (`TENXYTE_AIRS_CONFIRMATION_REQUIRED`) qui passeront toujours par HITL.

### 4. Guardrails : PII Redaction & Budget
- **PII RedactionMiddleware**: Intercepte automatiquement et anonymise les PII (`***REDACTED***`) dans la rponse JSON pour un requrant agent, empchant l'ingestion de ces donnes par un LLM limit.
- **Budget Tracking**: Suivi prcis du cot LLM (`POST /ai/tokens/{id}/report-usage/`) limitant financiellement l'impact d'un agent.

### 5. Audit Forensique
- **Traabilit via X-Prompt-Trace-ID**: Liaison dans l'`AuditLog` pour cartographier prcisment "Quel prompt a rsult par quelle action backend".

## Configuration

Paramtres activables via `src/tenxyte/conf.py` :
- `TENXYTE_AIRS_ENABLED` (Dfaut : `True`)
- `TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED` (Dfaut : `True`)
- `TENXYTE_AIRS_CONFIRMATION_REQUIRED` (Tableau d'extensions HITL, ex: `['users.delete']`)
- `TENXYTE_AIRS_REDACT_PII` (Dfaut : `False`)
- `TENXYTE_AIRS_BUDGET_TRACKING_ENABLED` (Dfaut : `False`)
