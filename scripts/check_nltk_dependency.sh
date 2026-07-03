#!/bin/bash
#
# Script de vérification : s'assurer que nltk n'est pas une dépendance de Tenxyte
#
# Usage: ./scripts/check_nltk_dependency.sh
#

set -e

echo "🔍 Vérification : nltk ne doit PAS être une dépendance de Tenxyte"
echo "================================================================"
echo ""

# Couleurs pour le terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Compteur d'erreurs
ERRORS=0

# 1. Vérifier pyproject.toml
echo "1️⃣  Vérification de pyproject.toml..."
if grep -qi "nltk" pyproject.toml 2>/dev/null; then
    echo -e "${RED}❌ ERREUR: nltk trouvé dans pyproject.toml${NC}"
    grep -n "nltk" pyproject.toml
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ OK: nltk absent de pyproject.toml${NC}"
fi
echo ""

# 2. Vérifier requirements-*.txt
echo "2️⃣  Vérification des fichiers requirements-*.txt..."
if grep -qi "nltk" requirements-*.txt 2>/dev/null; then
    echo -e "${RED}❌ ERREUR: nltk trouvé dans requirements-*.txt${NC}"
    grep -n "nltk" requirements-*.txt
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ OK: nltk absent des requirements-*.txt${NC}"
fi
echo ""

# 3. Vérifier requirements de documentation
echo "3️⃣  Vérification des requirements de documentation..."
if grep -qi "nltk" docs/*/requirements.txt 2>/dev/null; then
    echo -e "${RED}❌ ERREUR: nltk trouvé dans docs/*/requirements.txt${NC}"
    grep -n "nltk" docs/*/requirements.txt
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ OK: nltk absent de docs/*/requirements.txt${NC}"
fi
echo ""

# 4. Vérifier le code source
echo "4️⃣  Vérification du code source (imports)..."
if grep -r "import nltk\|from nltk" src/ 2>/dev/null; then
    echo -e "${RED}❌ ERREUR: import nltk trouvé dans le code source${NC}"
    grep -rn "import nltk\|from nltk" src/
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ OK: Aucun import nltk dans le code source${NC}"
fi
echo ""

# 5. Vérifier l'installation locale (si environnement virtuel activé)
echo "5️⃣  Vérification de l'installation locale..."
if command -v pip &> /dev/null; then
    if pip list 2>/dev/null | grep -qi "nltk"; then
        echo -e "${YELLOW}⚠️  AVERTISSEMENT: nltk est installé dans l'environnement actuel${NC}"
        pip list | grep -i nltk
        echo -e "${YELLOW}   Ceci peut être normal dans un environnement CI/CD${NC}"
    else
        echo -e "${GREEN}✅ OK: nltk n'est pas installé localement${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  SKIP: pip non disponible${NC}"
fi
echo ""

# 6. Vérifier les dépendances transitives (si pip-tools installé)
echo "6️⃣  Vérification des dépendances transitives..."
if command -v pip-compile &> /dev/null; then
    echo "   Génération de l'arbre complet des dépendances..."
    pip-compile --quiet --output-file=/tmp/tenxyte-full-deps.txt pyproject.toml 2>/dev/null || true
    
    if [ -f /tmp/tenxyte-full-deps.txt ]; then
        if grep -qi "nltk" /tmp/tenxyte-full-deps.txt; then
            echo -e "${RED}❌ ERREUR: nltk est une dépendance transitive${NC}"
            grep -n "nltk" /tmp/tenxyte-full-deps.txt
            ERRORS=$((ERRORS + 1))
        else
            echo -e "${GREEN}✅ OK: nltk n'est pas une dépendance transitive${NC}"
        fi
        rm /tmp/tenxyte-full-deps.txt
    fi
else
    echo -e "${YELLOW}⚠️  SKIP: pip-compile (pip-tools) non installé${NC}"
    echo "   Installer avec: pip install pip-tools"
fi
echo ""

# Résultat final
echo "================================================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ SUCCÈS: nltk n'est pas une dépendance de Tenxyte${NC}"
    echo ""
    echo "Résumé :"
    echo "  - pyproject.toml : ✅ OK"
    echo "  - requirements-*.txt : ✅ OK"
    echo "  - docs requirements : ✅ OK"
    echo "  - Code source : ✅ OK"
    echo ""
    echo "La vulnérabilité PYSEC-2026-597 peut être ignorée en toute sécurité."
    echo "Voir: SECURITY_ALERT_NLTK.md pour plus de détails."
    exit 0
else
    echo -e "${RED}❌ ÉCHEC: $ERRORS erreur(s) détectée(s)${NC}"
    echo ""
    echo "⚠️  ATTENTION: nltk a été détecté comme dépendance de Tenxyte."
    echo ""
    echo "Actions requises :"
    echo "  1. Retirer nltk des dépendances si non nécessaire"
    echo "  2. Si nltk est nécessaire :"
    echo "     - Mettre à jour vers une version patchée (> 3.9.4)"
    echo "     - Documenter l'utilisation dans SECURITY_ALERT_NLTK.md"
    echo "     - Ajouter des tests de sécurité"
    echo ""
    echo "Voir: SECURITY_ALERT_NLTK.md pour plus d'informations."
    exit 1
fi
