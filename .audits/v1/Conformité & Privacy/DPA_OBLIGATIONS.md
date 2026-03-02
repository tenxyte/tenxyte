# Obligations relatives aux DPA (Data Processing Agreements)

Conformément aux recommandations de l'audit (R11), ce document récapitule les obligations de Tenxyte concernant les contrats de sous-traitance de données (DPA) avec les fournisseurs tiers.

## 1. Cadre Réglementaire
Selon l'Article 28 du RGPD, lorsqu'un traitement est effectué pour le compte d'un responsable du traitement, celui-ci doit faire appel uniquement à des sous-traitants qui présentent des garanties suffisantes.

## 2. Fournisseurs Identifiés
Tenxyte interagit avec les providers suivants (selon configuration) :
- **Google** (OAuth2, Workspace)
- **GitHub** (OAuth2)
- **Microsoft** (Azure AD, OAuth2)
- **Facebook** (OAuth2)

## 3. Obligations de l'Intégrateur
Les utilisateurs du package Tenxyte doivent s'assurer :
1. **Signature des DPA** : Vérifier que les conditions générales ou contrats spécifiques avec ces providers incluent des clauses contractuelles types (CCT) ou des accords de protection des données adéquats.
2. **Localisation des Données** : Identifier si les données transitent hors de l'Union Européenne (notamment via le Data Privacy Framework USA-EU pour les providers américains).
3. **Information des Utilisateurs** : Mentionner l'utilisation de ces sous-traitants dans la Politique de Confidentialité de l'application finale.

## 4. Mesures Techniques Tenxyte
Le package Tenxyte facilite la conformité via :
- La limitation des scopes demandés au strict minimum.
- Le chiffrement des secrets au repos.
- Le droit à la portabilité (Export JSON complet).
- Le droit à l'effacement (Soft delete avec anonymisation).

---
*Dernière mise à jour : 2026-03-02*
