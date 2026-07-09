# Tests Manuels — z_aud_backlog

> Procédures de vérification non automatisables (OAuth réel chez chaque provider, envois SMS
> réels, parcours VDP, console Windows réelle) + **registre d'exécution**. Chaque procédure
> doit être déroulée et consignée avant de cocher la tâche correspondante dans `tasks.md`.

**Convention :** identifiants `MT-x` référencés depuis `tasks.md`. PASS uniquement si toutes
les étapes sont satisfaites.

---

## MT-1 — E2E OAuth réel pour chacun des 6 providers

**Couvre :** Requirements 1.1–1.6 · **Tâches :** 5.1, 5.2, 5.4
**Prérequis :** une app OAuth créée chez chaque provider (GitLab, LinkedIn, Slack, Discord,
X, Bitbucket) EN SUIVANT UNIQUEMENT la doc Tenxyte du provider (le test valide la doc autant
que le code) ; instance Tenxyte de test.

### Procédure (à dérouler pour CHAQUE provider)

1. Créer l'app OAuth chez le provider avec la doc Tenxyte seule ; toute étape manquante ou
   périmée (les consoles changent) ⇒ correction de la doc avant de continuer.
2. Login social complet : redirection → consentement provider → callback → tokens Tenxyte ;
   vérifier le Normalized_Dict persisté (nom, email, avatar) et la `SocialConnection`.
3. Second login avec le même compte : liaison sur le compte existant, pas de doublon.
4. Cas particuliers obligatoires :
   - **X** : vérifier le refus si PKCE absent (requête forgée) ; login d'un compte sans
     email → compte créé/lié selon les règles existantes, jamais de liaison auto par email.
   - **Discord** : compte à email non vérifié → pas de liaison automatique.
   - **GitLab/LinkedIn/Slack** : id_token vérifié (log de validation OIDC), altérer le
     `state` au retour → rejet.
5. Vérifier la non-régression : un login Google et un login Apple fonctionnent toujours.

✅ Attendu : 6/6 providers E2E verts avec doc auto-suffisante, cas particuliers conformes,
providers historiques intacts. Consigner date et version de chaque console provider.

---

## MT-2 — Envoi SMS réel par backend

**Couvre :** Requirements 2.1–2.5 · **Tâches :** 3.1, 3.2, 3.4
**Prérequis :** comptes d'essai Vonage, AWS (SNS), MessageBird ; un numéro de test réel.

### Procédure (pour CHAQUE backend)

1. Configurer le backend via ses settings en suivant uniquement la doc Tenxyte.
2. Dérouler un OTP login réel : le SMS arrive, le code fonctionne.
3. Inspecter les logs : numéro masqué, aucun corps de message.
4. Contre-épreuves : credentials invalides → log explicite nommant les settings, le flux
   OTP répond son erreur générique sans crash ; pour SNS, désinstaller boto3 → message
   pointant `pip install "tenxyte[sns]"`.
5. Vérifier qu'un venv `pip install tenxyte[django]` frais ne contient ni boto3 ni SDK SMS.

✅ Attendu : 3/3 backends opérationnels, logs propres, dépendances par défaut inchangées.

---

## MT-3 — Soumission VDP à blanc

**Couvre :** Requirements 3.1–3.4 · **Tâches :** 6.1, 6.2
**Prérequis :** SECURITY.md étendu publié (branche), un testeur externe jouant le chercheur.

### Procédure

1. Le testeur lit SECURITY.md et soumet un « faux vrai » rapport (vulnérabilité bénigne
   réelle ou plausible) par le canal documenté, sans aide privée.
2. Vérifier côté mainteneur : réception, triage selon la grille de sévérité, réponse dans le
   SLA, chemin advisory simulé jusqu'au bout.
3. Le testeur évalue : « le périmètre in/out est-il sans ambiguïté ? le safe harbor me
   protège-t-il clairement ? » — retours intégrés.
4. Ajouter le testeur au Hall_of_Fame (et tester l'opt-out).
5. Soumettre un rapport volontairement hors périmètre → vérifier la réponse type.

✅ Attendu : parcours complet fluide des deux côtés, SLA tenu, Hall_of_Fame fonctionnel,
ambiguïtés corrigées avant annonce publique.

---

## MT-4 — Scripts sur console Windows réelle

**Couvre :** Requirements 4.1, 4.2, 4.3 · **Tâches :** 1.1, 1.2
**Prérequis :** machine Windows avec console cmd par défaut (cp1252/cp850), SANS
`PYTHONIOENCODING` défini (vérifier avec `set PYTHONIOENCODING` → non défini).

### Procédure

1. Exécuter `python scripts\validate_endpoints.py` (et chaque script émetteur) dans cmd,
   PowerShell 5 et Windows Terminal : sortie complète, zéro `UnicodeEncodeError`.
2. Vérifier que la doc et CONTRIBUTING ne mentionnent plus le contournement.
3. Rechercher dans `docs/` toute mention résiduelle de redaction (« secrets redacted ») :
   zéro occurrence ; sonder 5 exemples réécrits — placeholders `<YOUR_...>` clairs.
4. Re-dérouler la portion outillage du parcours contributeur (z_aud_5 MT-5) sur Windows :
   plus de friction d'encodage.

✅ Attendu : scripts autonomes sur les 3 consoles, doc purgée, onboarding Windows fluide.

---

## Registre d'exécution

| ID | Intitulé | Date | Exécutant | Environnement | Résultat | Notes / lien preuve |
|----|----------|------|-----------|---------------|----------|---------------------|
| MT-1 | E2E OAuth des 6 providers | — | — | — | ⬜ À exécuter | par provider : — |
| MT-2 | Envoi SMS réel (Vonage/SNS/MessageBird) | — | — | — | ⬜ À exécuter | |
| MT-3 | Soumission VDP à blanc | — | — | — | ⬜ À exécuter | testeur : — |
| MT-4 | Scripts console Windows | — | — | — | ⬜ À exécuter | consoles : — |

**Légende :** ✅ PASS · ❌ FAIL (issue ouverte, référencée ici) · ⚠️ PASS avec réserve · ⬜ À exécuter

## Critère de sortie

Spec validée lorsque : registre entièrement ✅ (ou ⚠️ accepté), les 8 propriétés vertes en CI,
suite existante inchangée, OpenAPI existant intact, docs EN/FR validées. À la clôture,
l'analyse de couverture AUDIT.md ↔ specs est mise à jour : **les 4 écarts résiduels passent
à ✅ et la couverture de l'audit est de 100 %.**
