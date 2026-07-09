# z_aud_backlog — Résidus de couverture de l'audit

> **Source :** analyse de couverture `AUDIT.md` vs specs `z_aud_1` → `z_aud_5`. Quatre items
> de l'audit ont été volontairement relégués « en backlog » par les phases — cette spec les
> trace et les livre, portant la couverture de l'audit à 100 %.
> **Prérequis :** z_aud_1 (le provider Apple et le pattern d'extras existent).
> **Parallélisable :** oui, avec toute phase ≥ 2 ; chaque chantier est indépendant des autres.

## Les 4 écarts résiduels

| # | Écart | Origine AUDIT.md | Relégué par |
|---|---|---|---|
| 1 | **4–6 providers sociaux supplémentaires** (au-delà d'Apple) | F8, §8 🟠 P1 « effort faible » | z_aud_1 (« → backlog ») |
| 2 | **Backends SMS** : Vonage, AWS SNS, MessageBird | F10 (« importante ») | mentionné seulement comme vivier GFI dans z_aud_5 |
| 3 | **Bug bounty léger** | §8 P0, parenthèse de la ligne audit externe | z_aud_1 ne couvre que le signalement privé (D4) |
| 4 | **DX résiduelle** : encodage console Windows, exemples doc « secrets redacted » | §4.3 (mineures) | vivier GFI z_aud_5 uniquement |

## Décisions structurantes

- **D1 — Providers sociaux : 6 choisis par l'ICP, pas par le catalogue.** GitLab, LinkedIn,
  Discord, Slack, X (Twitter) et Spotify n'ont pas la même valeur : l'ICP primaire (builders
  d'agents, z_aud_5) et le secondaire (SaaS B2B) dictent **GitLab, LinkedIn, Discord, Slack,
  X, Bitbucket**. Chacun dérive d'`AbstractOAuthProvider` (pattern Apple z_aud_1), zéro
  modification des providers en place.
- **D2 — Les providers OIDC-compliant réutilisent l'acquis.** GitLab, LinkedIn et Slack
  parlent OIDC : leurs providers s'appuient sur les mêmes helpers de validation
  (state/nonce/JWKS) que le flux Apple et le `GenericOIDCProvider` (z_aud_4) s'il est
  disponible — pas de troisième pile OAuth.
- **D3 — Backends SMS : gabarit Twilio strict.** Chaque backend suit `backends/sms.py` :
  `BaseSMSBackend`, import paresseux, extra dédié (`tenxyte[vonage]`, `[sns]`,
  `[messagebird]`) jamais tiré par défaut, numéro masqué dans les logs, échec loggé sans
  exception dans le flux OTP. AWS SNS via boto3 (extra) ; Vonage et MessageBird en HTTP pur
  (`requests`, déjà dépendance) pour éviter deux SDK.
- **D4 — Bug bounty « léger » = VDP + reconnaissance, pas de plateforme payante.** Extension
  de SECURITY.md (z_aud_1) : périmètre in/out, safe harbor, hall of fame public, récompenses
  symboliques discrétionnaires (swag/mention). Une plateforme (HackerOne…) est explicitement
  hors périmètre tant que le volume ne le justifie pas — cohérent avec « léger » et le bus
  factor réel.
- **D5 — DX Windows : réparer à la source, pas dans la doc.** Les scripts de validation
  forcent eux-mêmes un stdout UTF-8 (reconfigure) au lieu d'exiger
  `set PYTHONIOENCODING=utf-8` ; les exemples de doc affectés par la redaction de secrets
  sont réécrits avec des placeholders explicites (`<YOUR_API_KEY>`) et re-validés par
  `validate_endpoints.py`.

## Definition of Done

1. Les 6 providers fonctionnels, E2E réel validé pour chacun (MT-1), zéro régression sur les
   5 existants ; total ≥ 10 providers (l'écart « 4–6 supplémentaires » de F8 est clos).
2. Les 3 backends SMS livrés derrière leurs extras, envoi réel validé (MT-2), install par
   défaut inchangée.
3. Politique de bug bounty publiée, testée par une soumission à blanc (MT-3), hall of fame
   en place.
4. Scripts de validation verts sur console Windows cp1252 SANS variable d'environnement
   (MT-4) ; plus aucun « secrets redacted » dans les exemples publiés.
5. Les 8 propriétés de correction passent (≥ 100 exemples) ; suite existante verte sans
   modification ; docs EN/FR à jour (`validate_endpoints.py` vert).

## Fichiers de la spec

| Fichier | Rôle |
|---|---|
| `base.md` | État des lieux mesuré + plan brut |
| `requirements.md` | 5 requirements EARS + glossaire |
| `design.md` | Conception, propriétés de correction, stratégie de test |
| `tasks.md` | Plan d'implémentation + graphe de dépendances |
| `manual_tests.md` | MT-1 → MT-4 + registre + critère de sortie |
