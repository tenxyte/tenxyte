# Cas Pratiques : Incidents IA et Réponses de Tenxyte AIRS

L'année 2024 et surtout 2025 ont marqué un tournant dans la cybersécurité avec l'explosion des vulnérabilités ciblant spécifiquement les assistants et agents autonomes (IA). Les attaques ne visent plus seulement le code traditionnel, mais exploitent la *logique émergente* et les permissions des agents.

Voici un récapitulatif des incidents majeurs récents et comment le module **Tenxyte AIRS (AI Responsibility & Security)** de votre plateforme aurait pu les bloquer.

---

## 1. L'Exploit "Shadow Escape" et l'Exfiltration de Données (2025)

**Incident :** Des chercheurs d'Operant AI ont découvert "Shadow Escape", une vulnérabilité "zero-click" affectant les agents basés sur le *Model Context Protocol* (MCP), notamment via ChatGPT et Google Gemini. L'attaque permettait de détourner silencieusement les workflows de l'agent (**Agent Hijacking**) pour exfiltrer des données clients privées en quelques minutes sans que l'utilisateur ne s'en aperçoive.

**Mots-clés OWASP :** *Excessive Agency (LLM06)*, *Sensitive Information Disclosure (LLM02)*.

**Comment Tenxyte AIRS bloque l'attaque :**
*   **Redaction Middleware** : Même si l'agent est détourné et tente d'exfiltrer un profil client, le middleware Tenxyte intercepte la réponse. Si le token utilisé est un `AgentToken`, il masque les informations PII (emails, numéros de SSN) avant que les données ne quittent le système.
*   **Shadow Audit IA (Anomalies)** : L'extraction massive et anormale de données vers un endpoint non reconnu aurait déclenché le coupe-circuit de Tenxyte (budget dépensé trop vite ou franchissement de seuil), faisant passer l'`AgentToken` en statut `SUSPENDED` automatiquement.

---

## 2. Le Détournement de GitHub Copilot / Microsoft 365 (CVE-2025-32711)

**Incident :** La vulnérabilité *EchoLeak* (CVSS 9.3) sur Microsoft 365 Copilot et des failles similaires dans GitHub MCP permettaient à des attaquants d'intégrer des commandes malveillantes dans des issues publiques. Lorsqu'un développeur consultait ces issues, son IA (Copilot) ingérait la commande indirecte et exfiltrait des codes sources ou des clés cryptographiques privées via de simples requêtes HTTP.

**Mots-clés OWASP :** *Prompt Injection (LLM01)*, *Supply Chain Vulnerabilities (LLM03)*.

**Comment Tenxyte AIRS bloque l'attaque :**
*   **Tenant & Scope Data Boundaries** : L'AgentToken restreint strictement la portée spatiale de l'agent. Le jeton délégué n'aurait autorisé l'agent qu'à lire le dépôt actif de l'utilisateur. Toute tentative d'accéder aux *secrets* du compte ou à d'autres dépôts (action non autorisée par le jeton) est immédiatement rejetée par `@require_agent_clearance`.
*   **Dead Man's Switch** : Si l'agent tente une action d'exfiltration en tâche de fond prolongée (pendant que le développeur ne code plus), l'absence de "heartbeat" du front-end suspend le token de l'agent automatiquement.

---

## 3. Le Bot Twitter "Remoteli.io" et la Perte de Contrôle (2024-2025)

**Incident :** Un bot Twitter automatisé (Remoteli.io) relié à ChatGPT a été manipulé par d'innombrables utilisateurs publics. En lui envoyant la simple commande *"Ignore previous instructions" (Prompt Injection classique)*, ils lui ont fait publier des propos embarrassants, des menaces et assumer la responsabilité d'événements tragiques.

**Mots-clés OWASP :** *Prompt Injection (LLM01)*, *Improper Output Handling (LLM05)*.

**Comment Tenxyte AIRS bloque l'attaque :**
*   **Forensic Audit Log (Prompt Provenance)** : Tenxyte trace l'origine de l'action. Chaque appel API initié par le bot pour "publier un tweet" est consigné avec l'identifiant du prompt source. L'entreprise peut prouver immédiatement d'où vient l'attaque.
*   **Human in the Loop (HITL)** : Pour des actions d'écriture publiques, Tenxyte peut être configuré (via `@require_agent_clearance(human_in_the_loop_required=True)`) pour exiger une confirmation humaine. Pour un bot autonome, cela passerait par un flux de validation asynchrone avant que le tweet critique (si le "risk score" est élevé) ne soit validé.

---

## 4. Attaque de Phishing via l'IA de Slack (2024)

**Incident :** Les chercheurs ont démontré qu'en plaçant une "injection de prompt indirecte" dans un document partagé dans un canal public de Slack, l'outil Slack AI (lorsqu'il scannait les documents pour résumer les conversations) pouvait être forcé d'envoyer des messages de phishing aux utilisateurs du canal ou d'exfiltrer des canaux privés (auxquels l'attaquant n'avait pas accès, mais l'IA oui).

**Mots-clés OWASP :** *Excessive Agency (LLM06)*.

**Comment Tenxyte AIRS bloque l'attaque :**
*   **Contrat de Délégation (RBAC Dynamique)** : C'est le cœur de Tenxyte AIRS. L'agent IA n'opère *jamais* avec des super-pouvoirs globaux. Si Bob déclenche Slack AI pour résumer une chaîne, l'agent utilise un `AgentToken` généré par Bob. Si l'agent tente d'accéder au document "Salaires RH" auquel Bob n'a pas accès, le moteur DRF de Tenxyte rejette avec une erreur `403 Agent Insufficient Permissions`. L'IA ne peut jamais contourner les permissions de l'utilisateur qui l'invoque.

---

## Conclusion : Le Rôle Critique de Tenxyte AIRS

Ces incidents "Zero-Day" liés aux agents autonomes ne relèvent pas de failles de code SQL ou de faiblesses cryptographiques. Ce sont des **failles de confiance et d'autorisation logiques**. 

Aujourd'hui, l'IAM traditionnel (qui vérifie simplement "qui est là ?") ne suffit plus car l'attaquant *est* l'agent légitimé qui a subi un lavage de cerveau (injection).

La valeur unique de **Tenxyte AIRS** réside dans sa capacité à passer d'une sécurité d'**Accès** à une sécurité de **Gouvernance Comportementale** (Quotas financiers pris en charge au niveau de l'API, HITL natif, Sandbox de données, Coupe-circuit instantané). Tenxyte permet ainsi aux développeurs de déléguer leur confiance à l'IA sans risquer leur entreprise.
