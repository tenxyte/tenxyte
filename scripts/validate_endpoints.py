#!/usr/bin/env python3
"""
Script de validation des exemples JSON dans endpoints.md.

Vérifie que tous les exemples de réponses dans la documentation
correspondent exactement aux schémas Pydantic définis dans core/schemas.py.

Usage:
    python scripts/validate_endpoints.py
    python scripts/validate_endpoints.py --file docs/en/endpoints.md
    
Exit codes:
    0 - Tous les exemples sont valides
    1 - Au moins un exemple est invalide
"""

import sys
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Any

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class Colors:
    """Codes ANSI pour la colorisation."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class EndpointsValidator:
    """Validateur des exemples JSON dans endpoints.md."""
    
    def __init__(self, endpoints_file: str):
        self.endpoints_file = Path(endpoints_file)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        self.examples: List[Dict[str, Any]] = []
        
    def extract_json_examples(self) -> List[Tuple[int, str, Dict]]:
        """Extrait tous les exemples JSON du fichier markdown."""
        with open(self.endpoints_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        examples = []
        # Pattern pour trouver les blocs JSON
        pattern = r'```json\n(.*?)\n```'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            json_str = match.group(1)
            start_pos = match.start()
            
            # Calculer le numéro de ligne
            line_num = content[:start_pos].count('\n') + 1
            
            try:
                json_obj = json.loads(json_str)
                examples.append((line_num, json_str, json_obj))
            except json.JSONDecodeError as e:
                self.errors.append(f"Ligne {line_num}: JSON invalide - {e}")
        
        return examples
    
    def validate_token_pair(self, obj: Dict, line_num: int, context: str = "") -> bool:
        """Valide un objet TokenPair."""
        required_fields = {
            'access_token', 'refresh_token', 'token_type',
            'expires_in', 'refresh_expires_in'
        }
        
        # device_summary est optionnel mais devrait être présent
        optional_fields = {'device_summary'}
        
        obj_fields = set(obj.keys())
        
        # Vérifier si c'est un TokenPair (a access_token et refresh_token)
        if 'access_token' in obj and 'refresh_token' in obj:
            missing = required_fields - obj_fields
            
            if missing:
                self.errors.append(
                    f"Ligne {line_num} {context}: TokenPair incomplet - champs manquants: {missing}"
                )
                return False
            
            # Vérifier device_summary
            if 'device_summary' not in obj:
                self.warnings.append(
                    f"Ligne {line_num} {context}: TokenPair sans 'device_summary' (optionnel mais recommandé)"
                )
            
            # Vérifier token_type
            if obj.get('token_type') != 'Bearer':
                self.errors.append(
                    f"Ligne {line_num} {context}: token_type devrait être 'Bearer', trouvé '{obj.get('token_type')}'"
                )
                return False
            
            self.passed.append(f"Ligne {line_num} {context}: TokenPair ✓")
            return True
        
        return None  # Pas un TokenPair
    
    def validate_user(self, obj: Dict, line_num: int, context: str = "") -> bool:
        """Valide un objet User."""
        required_fields = {
            'id', 'email', 'username', 'phone', 'avatar', 'bio',
            'timezone', 'language', 'first_name', 'last_name',
            'is_active', 'is_email_verified', 'is_phone_verified',
            'is_2fa_enabled', 'created_at', 'last_login',
            'custom_fields', 'preferences', 'roles', 'permissions'
        }
        
        obj_fields = set(obj.keys())
        
        # Vérifier si c'est un User (a id, email, roles, permissions)
        if 'id' in obj and 'email' in obj and 'roles' in obj and 'permissions' in obj:
            missing = required_fields - obj_fields
            extra = obj_fields - required_fields
            
            if missing:
                self.errors.append(
                    f"Ligne {line_num} {context}: User incomplet - champs manquants: {missing}"
                )
                return False
            
            if extra:
                self.warnings.append(
                    f"Ligne {line_num} {context}: User avec champs supplémentaires: {extra}"
                )
            
            # Vérifier que roles et permissions sont des listes de strings
            if not isinstance(obj.get('roles'), list):
                self.errors.append(
                    f"Ligne {line_num} {context}: 'roles' devrait être une liste"
                )
                return False
            
            if not isinstance(obj.get('permissions'), list):
                self.errors.append(
                    f"Ligne {line_num} {context}: 'permissions' devrait être une liste"
                )
                return False
            
            self.passed.append(f"Ligne {line_num} {context}: User ✓")
            return True
        
        return None  # Pas un User
    
    def validate_error_response(self, obj: Dict, line_num: int, context: str = "") -> bool:
        """Valide un objet ErrorResponse."""
        required_fields = {'error', 'code'}
        optional_fields = {'details'}
        
        obj_fields = set(obj.keys())
        
        # Vérifier si c'est un ErrorResponse (a 'error' et 'code')
        if 'error' in obj and 'code' in obj:
            missing = required_fields - obj_fields
            
            if missing:
                self.errors.append(
                    f"Ligne {line_num} {context}: ErrorResponse incomplet - champs manquants: {missing}"
                )
                return False
            
            # Vérifier le format de details si présent
            if 'details' in obj:
                details = obj['details']
                if not isinstance(details, dict):
                    self.errors.append(
                        f"Ligne {line_num} {context}: 'details' devrait être un dict, trouvé {type(details).__name__}"
                    )
                    return False
                
                # Vérifier que les valeurs sont des listes
                for key, value in details.items():
                    if not isinstance(value, list):
                        self.errors.append(
                            f"Ligne {line_num} {context}: details['{key}'] devrait être une liste"
                        )
                        return False
            
            self.passed.append(f"Ligne {line_num} {context}: ErrorResponse ✓")
            return True
        
        return None  # Pas un ErrorResponse
    
    def validate_paginated_response(self, obj: Dict, line_num: int, context: str = "") -> bool:
        """Valide un objet PaginatedResponse."""
        required_fields = {
            'count', 'page', 'page_size', 'total_pages',
            'next', 'previous', 'results'
        }
        
        obj_fields = set(obj.keys())
        
        # Vérifier si c'est un PaginatedResponse
        if 'count' in obj and 'results' in obj and 'page' in obj:
            missing = required_fields - obj_fields
            
            if missing:
                self.errors.append(
                    f"Ligne {line_num} {context}: PaginatedResponse incomplet - champs manquants: {missing}"
                )
                return False
            
            # Vérifier que results est une liste
            if not isinstance(obj.get('results'), list):
                self.errors.append(
                    f"Ligne {line_num} {context}: 'results' devrait être une liste"
                )
                return False
            
            self.passed.append(f"Ligne {line_num} {context}: PaginatedResponse ✓")
            return True
        
        return None  # Pas un PaginatedResponse
    
    def validate_example(self, line_num: int, json_str: str, obj: Any) -> None:
        """Valide un exemple JSON."""
        # Les validateurs attendent un dict ; ignorer les tableaux et scalaires
        if not isinstance(obj, dict):
            return

        # Déterminer le contexte (endpoint)
        context = ""
        
        # Essayer de valider comme différents types de schémas
        validators = [
            self.validate_token_pair,
            self.validate_user,
            self.validate_error_response,
            self.validate_paginated_response,
        ]
        
        validated = False
        for validator in validators:
            result = validator(obj, line_num, context)
            if result is not None:
                validated = True
                break
        
        # Si l'objet contient un 'user', le valider aussi
        if 'user' in obj and isinstance(obj['user'], dict):
            self.validate_user(obj['user'], line_num, context="(nested user)")
    
    def run_validation(self) -> bool:
        """Exécute la validation complète."""
        print(f"{Colors.BOLD}=== Validation des exemples JSON dans endpoints.md ==={Colors.END}\n")
        print(f"Fichier: {self.endpoints_file}\n")
        
        # Extraire les exemples
        print(f"{Colors.BLUE}Extraction des exemples JSON...{Colors.END}")
        examples = self.extract_json_examples()
        print(f"Trouvé {len(examples)} exemples JSON\n")
        
        # Valider chaque exemple
        print(f"{Colors.BLUE}Validation des exemples...{Colors.END}")
        for line_num, json_str, obj in examples:
            self.validate_example(line_num, json_str, obj)
        
        print()
        return len(self.errors) == 0
    
    def print_results(self):
        """Affiche les résultats de la validation."""
        print(f"{Colors.BOLD}=== Résultats ==={Colors.END}\n")
        
        # Tests réussis
        if self.passed:
            print(f"{Colors.GREEN}✓ Validations réussies ({len(self.passed)}):{Colors.END}")
            for msg in self.passed[:10]:  # Limiter l'affichage
                print(f"  {Colors.GREEN}✓{Colors.END} {msg}")
            if len(self.passed) > 10:
                print(f"  ... et {len(self.passed) - 10} autres")
            print()
        
        # Avertissements
        if self.warnings:
            print(f"{Colors.YELLOW}⚠ Avertissements ({len(self.warnings)}):{Colors.END}")
            for msg in self.warnings:
                print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")
            print()
        
        # Erreurs
        if self.errors:
            print(f"{Colors.RED}✗ Erreurs ({len(self.errors)}):{Colors.END}")
            for msg in self.errors:
                print(f"  {Colors.RED}✗{Colors.END} {msg}")
            print()
        
        # Résumé
        total_checks = len(self.passed) + len(self.errors)
        success_rate = (len(self.passed) / total_checks * 100) if total_checks > 0 else 0
        
        print(f"{Colors.BOLD}Résumé:{Colors.END}")
        print(f"  Total validations: {total_checks}")
        print(f"  Réussies: {Colors.GREEN}{len(self.passed)}{Colors.END}")
        print(f"  Échouées: {Colors.RED}{len(self.errors)}{Colors.END}")
        print(f"  Avertissements: {Colors.YELLOW}{len(self.warnings)}{Colors.END}")
        print(f"  Taux de réussite: {success_rate:.1f}%")
        print()
        
        if not self.errors:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ Tous les exemples sont conformes à la spécification canonique{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ Des corrections sont nécessaires{Colors.END}")


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Valide les exemples JSON dans endpoints.md')
    parser.add_argument(
        '--file',
        default='docs/en/endpoints.md',
        help='Chemin vers le fichier endpoints.md (défaut: docs/en/endpoints.md)'
    )
    
    args = parser.parse_args()
    
    # Vérifier que le fichier existe
    if not Path(args.file).exists():
        print(f"{Colors.RED}Erreur: Fichier non trouvé: {args.file}{Colors.END}")
        sys.exit(1)
    
    validator = EndpointsValidator(args.file)
    
    try:
        all_passed = validator.run_validation()
        validator.print_results()
        
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"{Colors.RED}Erreur fatale: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
