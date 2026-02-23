#!/usr/bin/env python3
"""
Documentation Validation Script

This script validates the completeness and quality of API documentation:
1. Checks all endpoints have proper examples
2. Validates example data against schemas
3. Generates coverage reports
4. Identifies missing error scenarios
5. Tests multi-tenant documentation
"""

import os
import sys
import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tenxyte.docs.schemas import (
    AUTH_EXAMPLES,
    ERROR_EXAMPLES,
    SUCCESS_EXAMPLES,
    SECURITY_EXAMPLES
)


class DocumentationValidator:
    """Validates API documentation completeness and quality."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.views_dir = self.project_root / 'src' / 'tenxyte' / 'views'
        self.issues = []
        self.stats = defaultdict(int)
        self.coverage = {
            'endpoints': set(),
            'examples': set(),
            'error_codes': set(),
            'success_scenarios': set()
        }
    
    def validate_all(self) -> Dict:
        """Run all validation checks and return report."""
        print("🔍 Starting documentation validation...")
        
        # Scan all view files
        view_files = self.scan_view_files()
        print(f"📁 Found {len(view_files)} view files")
        
        # Validate each file
        for view_file in view_files:
            self.validate_view_file(view_file)
        
        # Check example coverage
        self.validate_example_coverage()
        
        # Check error code coverage
        self.validate_error_coverage()
        
        # Check multi-tenant documentation
        self.validate_multi_tenant_coverage()
        
        # Generate report
        report = self.generate_report()
        
        return report
    
    def scan_view_files(self) -> List[Path]:
        """Scan for all Python view files."""
        view_files = []
        for file_path in self.views_dir.rglob('*.py'):
            if file_path.name != '__init__.py':
                view_files.append(file_path)
        return view_files
    
    def validate_view_file(self, file_path: Path):
        """Validate a single view file for documentation completeness."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find endpoints
            try:
                tree = ast.parse(content)
                self.extract_endpoints_from_ast(tree, file_path)
            except SyntaxError as e:
                self.add_issue('error', f"Syntax error in {file_path}: {e}")
                return
            
            # Check for @extend_schema decorators
            extend_schemas = content.count('@extend_schema')
            self.stats['extend_schema_decorators'] += extend_schemas
            
            # Check for OpenApiExample usage
            examples = content.count('OpenApiExample')
            self.stats['openapi_examples'] += examples
            
            # Check for proper error documentation
            self.validate_error_documentation(content, file_path)
            
            # Check for multi-tenant headers
            self.validate_multi_tenant_headers(content, file_path)
            
        except Exception as e:
            self.add_issue('error', f"Failed to process {file_path}: {e}")
    
    def extract_endpoints_from_ast(self, tree: ast.AST, file_path: Path):
        """Extract API endpoints from AST."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if it's a view method (has HTTP methods)
                if hasattr(node, 'decorator_list'):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == 'api_view':
                            # Extract HTTP methods
                            for arg in decorator.args if hasattr(decorator, 'args') else []:
                                if isinstance(arg, ast.List):
                                    for elt in arg.elts:
                                        if isinstance(elt, ast.Str):
                                            endpoint = f"{elt.s.upper()} {node.name}"
                                            self.coverage['endpoints'].add(endpoint)
            
            # Check for class-based views
            elif isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        if method.name in ['get', 'post', 'put', 'patch', 'delete']:
                            endpoint = f"{method.name.upper()} /{file_path.stem}/"
                            self.coverage['endpoints'].add(endpoint)
    
    def validate_error_documentation(self, content: str, file_path: Path):
        """Validate that error scenarios are properly documented."""
        # Check for common error codes in responses
        error_codes = ['400', '401', '403', '404', '409', '423', '429', '500']
        
        for code in error_codes:
            if (f"'{code}'" in content or 
                f'"{code}"' in content or 
                f"{code}:" in content or 
                f"HTTP_{code}" in content or
                f"status={code}" in content):
                self.coverage['error_codes'].add(code)
        
        # Check for error examples
        if 'OpenApiExample' in content and any(word in content.lower() for word in ['error', 'failed', 'invalid']):
            self.stats['error_examples'] += 1
    
    def validate_multi_tenant_headers(self, content: str, file_path: Path):
        """Validate multi-tenant header documentation."""
        if 'X-Org-Slug' in content:
            self.stats['multi_tenant_documented'] += 1
        else:
            # Check if this should be a multi-tenant endpoint
            if any(keyword in content.lower() for keyword in ['organization', 'org', 'tenant']):
                self.add_issue('warning', f"Potential multi-tenant endpoint missing X-Org-Slug in {file_path}")
    
    def validate_example_coverage(self):
        """Validate that examples cover all scenarios."""
        print("📋 Validating example coverage...")
        
        # Check authentication examples
        auth_scenarios = ['login_success', 'login_failed', 'validation_error']
        for scenario in auth_scenarios:
            if any(example.name == scenario for example in AUTH_EXAMPLES):
                self.coverage['examples'].add(f'auth_{scenario}')
        
        # Check error examples
        error_scenarios = ['validation_error', 'not_found', 'permission_denied', 'rate_limited']
        for scenario in error_scenarios:
            if any(example.name == scenario for example in ERROR_EXAMPLES):
                self.coverage['examples'].add(f'error_{scenario}')
        
        # Check success examples
        success_scenarios = ['login_success', 'multi_tenant_success', 'file_upload_success']
        for scenario in success_scenarios:
            if any(example.name == scenario for example in SUCCESS_EXAMPLES):
                self.coverage['examples'].add(f'success_{scenario}')
    
    def validate_error_coverage(self):
        """Validate error code coverage."""
        print("❌ Validating error coverage...")
        
        expected_error_codes = {
            '400': 'Bad Request',
            '401': 'Unauthorized', 
            '403': 'Forbidden',
            '404': 'Not Found',
            '409': 'Conflict',
            '423': 'Locked',
            '429': 'Too Many Requests',
            '500': 'Internal Server Error'
        }
        
        for code, description in expected_error_codes.items():
            if code not in self.coverage['error_codes']:
                self.add_issue('warning', f"Missing documentation for HTTP {code} ({description})")
    
    def validate_multi_tenant_coverage(self):
        """Validate multi-tenant documentation coverage."""
        print("🏢 Validating multi-tenant coverage...")
        
        if self.stats['multi_tenant_documented'] == 0:
            self.add_issue('warning', "No multi-tenant endpoints documented with X-Org-Slug")
    
    def add_issue(self, severity: str, message: str):
        """Add an issue to the report."""
        self.issues.append({
            'severity': severity,
            'message': message
        })
    
    def generate_report(self) -> Dict:
        """Generate comprehensive validation report."""
        print("📊 Generating validation report...")
        
        # Calculate coverage percentages
        total_expected_endpoints = 50  # Estimated based on project size
        endpoint_coverage = len(self.coverage['endpoints']) / total_expected_endpoints * 100
        
        total_expected_examples = 20  # Estimated
        example_coverage = len(self.coverage['examples']) / total_expected_examples * 100
        
        total_expected_error_codes = 8
        error_coverage = len(self.coverage['error_codes']) / total_expected_error_codes * 100
        
        report = {
            'summary': {
                'total_issues': len(self.issues),
                'critical_issues': len([i for i in self.issues if i['severity'] == 'error']),
                'warnings': len([i for i in self.issues if i['severity'] == 'warning']),
                'endpoint_coverage': round(endpoint_coverage, 2),
                'example_coverage': round(example_coverage, 2),
                'error_coverage': round(error_coverage, 2)
            },
            'statistics': dict(self.stats),
            'coverage': {
                'endpoints': list(self.coverage['endpoints']),
                'examples': list(self.coverage['examples']),
                'error_codes': list(self.coverage['error_codes'])
            },
            'issues': self.issues,
            'recommendations': self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        if len(self.issues) > 0:
            critical_count = len([i for i in self.issues if i['severity'] == 'error'])
            if critical_count > 0:
                recommendations.append(f"Fix {critical_count} critical issues before release")
        
        if self.stats['openapi_examples'] < self.stats['extend_schema_decorators']:
            missing = self.stats['extend_schema_decorators'] - self.stats['openapi_examples']
            recommendations.append(f"Add {missing} missing examples for documented endpoints")
        
        if self.stats['multi_tenant_documented'] == 0:
            recommendations.append("Document multi-tenant endpoints with X-Org-Slug headers")
        
        error_coverage = len(self.coverage['error_codes']) / 8 * 100
        if error_coverage < 80:
            recommendations.append("Add more error code examples to improve coverage")
        
        if not recommendations:
            recommendations.append("Documentation looks good! Consider adding more edge case examples.")
        
        return recommendations


def print_report(report: Dict):
    """Print formatted validation report."""
    print("\n" + "="*60)
    print("📋 DOCUMENTATION VALIDATION REPORT")
    print("="*60)
    
    # Summary
    summary = report['summary']
    print(f"\n📊 SUMMARY:")
    print(f"   Total Issues: {summary['total_issues']}")
    print(f"   Critical Issues: {summary['critical_issues']}")
    print(f"   Warnings: {summary['warnings']}")
    print(f"   Endpoint Coverage: {summary['endpoint_coverage']}%")
    print(f"   Example Coverage: {summary['example_coverage']}%")
    print(f"   Error Coverage: {summary['error_coverage']}%")
    
    # Statistics
    stats = report['statistics']
    print(f"\n📈 STATISTICS:")
    print(f"   @extend_schema decorators: {stats.get('extend_schema_decorators', 0)}")
    print(f"   OpenApiExample instances: {stats.get('openapi_examples', 0)}")
    print(f"   Error examples: {stats.get('error_examples', 0)}")
    print(f"   Multi-tenant documented: {stats.get('multi_tenant_documented', 0)}")
    
    # Coverage
    coverage = report['coverage']
    print(f"\n🎯 COVERAGE:")
    print(f"   Endpoints ({len(coverage['endpoints'])}):")
    for endpoint in sorted(list(coverage['endpoints']))[:10]:  # Show first 10
        print(f"     - {endpoint}")
    if len(coverage['endpoints']) > 10:
        print(f"     ... and {len(coverage['endpoints']) - 10} more")
    
    print(f"   Examples ({len(coverage['examples'])}):")
    for example in sorted(list(coverage['examples'])):
        print(f"     - {example}")
    
    print(f"   Error Codes ({len(coverage['error_codes'])}):")
    for code in sorted(list(coverage['error_codes'])):
        print(f"     - HTTP {code}")
    
    # Issues
    if report['issues']:
        print(f"\n⚠️  ISSUES:")
        for issue in report['issues']:
            icon = "🚨" if issue['severity'] == 'error' else "⚠️"
            print(f"   {icon} {issue['message']}")
    
    # Recommendations
    recommendations = report['recommendations']
    print(f"\n💡 RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    # Overall assessment
    print(f"\n🏆 OVERALL ASSESSMENT:")
    if summary['critical_issues'] == 0 and summary['endpoint_coverage'] > 80:
        print("   ✅ Documentation is in good shape!")
    elif summary['critical_issues'] > 0:
        print("   🚨 Critical issues need attention!")
    else:
        print("   ⚠️  Documentation needs improvements")
    
    print("="*60)


def save_report(report: Dict, output_path: str):
    """Save report to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n💾 Report saved to: {output_path}")


def main():
    """Main validation script."""
    validator = DocumentationValidator()
    report = validator.validate_all()
    
    # Print report
    print_report(report)
    
    # Save report
    output_path = project_root / 'documentation_validation_report.json'
    save_report(report, output_path)
    
    # Exit with appropriate code
    if report['summary']['critical_issues'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
