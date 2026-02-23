#!/usr/bin/env python3
"""
OpenAPI Specification Validation Script

This script validates the generated OpenAPI specification for:
1. Schema consistency and completeness
2. Duplicate definitions
3. Missing examples
4. Performance issues
5. OpenAPI 3.0 compliance
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root))

try:
    import django
    from django.conf import settings
    from django.urls import reverse
    from django.test import Client
    
    # Configure Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
    django.setup()
    
    from drf_spectacular.openapi import AutoSchema
    from drf_spectacular.generators import SchemaGenerator
    from drf_spectacular.validation import validate_schema
    
except ImportError as e:
    print(f"⚠️  Django/DRF Spectacular not available: {e}")
    print("Running in validation-only mode...")


class OpenAPIValidator:
    """Validates OpenAPI specification for quality and compliance."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues = []
        self.stats = defaultdict(int)
        self.performance_issues = []
        self.duplicates = defaultdict(list)
        
    def validate_all(self) -> Dict:
        """Run all validation checks and return comprehensive report."""
        print("🔍 Starting OpenAPI specification validation...")
        
        # Generate schema if possible
        schema = self.generate_schema()
        if not schema:
            return self.generate_empty_report()
        
        # Run validation checks
        self.validate_schema_structure(schema)
        self.check_duplicates(schema)
        self.validate_examples(schema)
        self.check_performance_issues(schema)
        self.validate_openapi_compliance(schema)
        self.check_security_documentation(schema)
        self.validate_multi_tenant_coverage(schema)
        
        # Generate report
        report = self.generate_report(schema)
        
        return report
    
    def generate_schema(self) -> Dict:
        """Generate OpenAPI schema from Django project."""
        try:
            print("📋 Generating OpenAPI schema...")
            generator = SchemaGenerator(title='Tenxyte API', description='Enhanced DRF Spectacular Documentation')
            schema = generator.get_schema(None, public=True)
            
            # Save schema for inspection
            schema_file = self.project_root / 'openapi_schema.json'
            with open(schema_file, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2, default=str)
            print(f"💾 Schema saved to: {schema_file}")
            
            return schema
            
        except Exception as e:
            print(f"❌ Failed to generate schema: {e}")
            self.add_issue('error', f"Schema generation failed: {e}")
            return {}
    
    def validate_schema_structure(self, schema: Dict):
        """Validate basic OpenAPI schema structure."""
        print("🏗️  Validating schema structure...")
        
        required_fields = ['openapi', 'info', 'paths']
        for field in required_fields:
            if field not in schema:
                self.add_issue('error', f"Missing required field: {field}")
        
        # Check info section
        if 'info' in schema:
            info = schema['info']
            required_info = ['title', 'version']
            for field in required_info:
                if field not in info:
                    self.add_issue('warning', f"Missing info field: {field}")
        
        # Check paths
        if 'paths' in schema:
            paths = schema['paths']
            self.stats['total_paths'] = len(paths)
            
            for path, path_item in paths.items():
                self.validate_path_item(path, path_item)
    
    def validate_path_item(self, path: str, path_item: Dict):
        """Validate individual path items."""
        methods = ['get', 'post', 'put', 'patch', 'delete']
        
        for method in methods:
            if method in path_item:
                operation = path_item[method]
                self.validate_operation(path, method, operation)
    
    def validate_operation(self, path: str, method: str, operation: Dict):
        """Validate individual operations."""
        self.stats['total_operations'] += 1
        
        # Check for operation ID
        if 'operationId' not in operation:
            self.add_issue('warning', f"Missing operationId for {method.upper()} {path}")
        
        # Check for summary
        if 'summary' not in operation:
            self.add_issue('warning', f"Missing summary for {method.upper()} {path}")
        
        # Check for description
        if 'description' not in operation:
            self.add_issue('info', f"Missing description for {method.upper()} {path}")
        
        # Check for tags
        if 'tags' not in operation:
            self.add_issue('info', f"Missing tags for {method.upper()} {path}")
        
        # Check responses
        if 'responses' not in operation:
            self.add_issue('error', f"Missing responses for {method.upper()} {path}")
        else:
            self.validate_responses(operation['responses'], f"{method.upper()} {path}")
        
        # Check for examples
        if 'requestBody' in operation:
            req_str = str(operation.get('requestBody', {}))
            if "'examples'" not in req_str and "'example'" not in req_str:
                self.add_issue('info', f"Missing examples for {method.upper()} {path}")
    
    def validate_responses(self, responses: Dict, operation_id: str):
        """Validate response definitions."""
        if '200' not in responses and '201' not in responses and '204' not in responses:
            self.add_issue('warning', f"Missing success response for {operation_id}")
        
        for status_code, response in responses.items():
            if 'description' not in response:
                self.add_issue('warning', f"Missing description for response {status_code} in {operation_id}")
    
    def check_duplicates(self, schema: Dict):
        """Check for duplicate schemas and definitions."""
        print("🔍 Checking for duplicates...")
        
        # Check component schemas
        if 'components' in schema and 'schemas' in schema['components']:
            schemas = schema['components']['schemas']
            self.check_schema_duplicates(schemas)
        
        # Check for duplicate operation IDs
        operation_ids = set()
        for path, path_item in schema.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    op_id = operation.get('operationId')
                    if op_id:
                        if op_id in operation_ids:
                            self.add_issue('error', f"Duplicate operationId: {op_id}")
                        else:
                            operation_ids.add(op_id)
    
    def check_schema_duplicates(self, schemas: Dict):
        """Check for duplicate schema definitions."""
        schema_hashes = {}
        
        for name, schema_def in schemas.items():
            # Create a hash of the schema structure (excluding title)
            schema_copy = schema_def.copy()
            schema_copy.pop('title', None)
            schema_str = json.dumps(schema_copy, sort_keys=True, default=str)
            schema_hash = hash(schema_str)
            
            if schema_hash in schema_hashes:
                self.duplicates[schema_hash].append(name)
            else:
                schema_hashes[schema_hash] = name
        
        # Report duplicates
        for hash_val, names in self.duplicates.items():
            if len(names) > 1:
                self.add_issue('warning', f"Duplicate schemas: {', '.join(names)}")
    
    def validate_examples(self, schema: Dict):
        """Validate example completeness and quality."""
        print("📋 Validating examples...")
        
        example_count = 0
        def count_examples(obj):
            nonlocal example_count
            if isinstance(obj, dict):
                if 'examples' in obj and isinstance(obj['examples'], dict):
                    example_count += len(obj['examples'])
                elif 'example' in obj:
                    example_count += 1
                for v in obj.values():
                    count_examples(v)
            elif isinstance(obj, list):
                for item in obj:
                    count_examples(item)
                    
        count_examples(schema)
        
        self.stats['total_examples'] = example_count
        
        if example_count == 0:
            self.add_issue('warning', "No examples found in the specification")
    
    def validate_example(self, name: str, example: Dict):
        """Validate individual example."""
        if 'value' not in example:
            self.add_issue('warning', f"Example {name} missing value")
        
        if 'summary' not in example:
            self.add_issue('info', f"Example {name} missing summary")
    
    def check_performance_issues(self, schema: Dict):
        """Check for performance-related issues."""
        print("⚡ Checking performance issues...")
        
        # Check schema size
        schema_size = len(json.dumps(schema, default=str))
        self.stats['schema_size_bytes'] = schema_size
        
        if schema_size > 5 * 1024 * 1024:  # 5MB
            self.add_issue('warning', f"Large schema size: {schema_size / 1024 / 1024:.2f}MB")
        
        # Check for deeply nested structures
        self.check_nesting_depth(schema, max_depth=20)
        
        # Check for large arrays in examples
        self.check_large_examples(schema)
    
    def check_nesting_depth(self, obj: Any, current_depth: int = 0, max_depth: int = 20, path: str = ""):
        """Check for excessively nested structures."""
        if current_depth > max_depth:
            self.performance_issues.append(f"Deep nesting at {path}: {current_depth} levels")
            return
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                self.check_nesting_depth(value, current_depth + 1, max_depth, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self.check_nesting_depth(item, current_depth + 1, max_depth, f"{path}[{i}]")
    
    def check_large_examples(self, schema: Dict):
        """Check for excessively large examples."""
        def find_and_check_examples(obj, path_info=""):
            if isinstance(obj, dict):
                if 'examples' in obj and isinstance(obj['examples'], dict):
                    for name, example in obj['examples'].items():
                        if 'value' in example:
                            example_size = len(json.dumps(example['value'], default=str))
                            if example_size > 10240:  # 10KB
                                self.performance_issues.append(
                                    f"Large example {name} in {path_info}: {example_size / 1024:.2f}KB"
                                )
                for k, v in obj.items():
                    find_and_check_examples(v, path_info)
            elif isinstance(obj, list):
                for item in obj:
                    find_and_check_examples(item, path_info)

        for path, path_item in schema.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    find_and_check_examples(operation, f"{method.upper()} {path}")
    
    def validate_openapi_compliance(self, schema: Dict):
        """Validate OpenAPI 3.0 compliance."""
        print("📜 Validating OpenAPI compliance...")
        
        # Check OpenAPI version
        if 'openapi' not in schema:
            self.add_issue('error', "Missing OpenAPI version")
        else:
            version = schema['openapi']
            if not version.startswith('3.0'):
                self.add_issue('warning', f"Non-OpenAPI 3.0 version: {version}")
        
        # Validate against DRF Spectacular validator if available
        try:
            validate_schema(schema)
            print("✅ DRF Spectacular validation passed")
        except Exception as e:
            self.add_issue('error', f"DRF Spectacular validation failed: {e}")
    
    def check_security_documentation(self, schema: Dict):
        """Check security documentation completeness."""
        print("🔒 Checking security documentation...")
        
        # Check for security schemes
        if 'components' not in schema or 'securitySchemes' not in schema['components']:
            self.add_issue('warning', "No security schemes defined")
        
        # Check for global security requirements
        if 'security' not in schema:
            self.add_issue('info', "No global security requirements defined")
        
        # Check operations for security documentation
        secure_operations = 0
        total_operations = 0
        
        for path, path_item in schema.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    total_operations += 1
                    if 'security' in operation:
                        secure_operations += 1
        
        if total_operations > 0:
            security_coverage = (secure_operations / total_operations) * 100
            self.stats['security_coverage'] = security_coverage
            
            if security_coverage < 50:
                self.add_issue('warning', f"Low security documentation coverage: {security_coverage:.1f}%")
    
    def validate_multi_tenant_coverage(self, schema: Dict):
        """Check multi-tenant header documentation."""
        print("🏢 Checking multi-tenant coverage...")
        
        org_header_found = False
        org_header_operations = 0
        
        for path, path_item in schema.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    # Check parameters for X-Org-Slug
                    if 'parameters' in operation:
                        for param in operation['parameters']:
                            if param.get('name') == 'X-Org-Slug':
                                org_header_found = True
                                org_header_operations += 1
        
        self.stats['org_header_operations'] = org_header_operations
        
        if not org_header_found:
            self.add_issue('info', "No X-Org-Slug header documentation found")
    
    def add_issue(self, severity: str, message: str):
        """Add an issue to the report."""
        self.issues.append({
            'severity': severity,
            'message': message
        })
    
    def generate_report(self, schema: Dict) -> Dict:
        """Generate comprehensive validation report."""
        print("📊 Generating validation report...")
        
        # Calculate quality score
        quality_score = self.calculate_quality_score()
        
        report = {
            'summary': {
                'total_issues': len(self.issues),
                'critical_issues': len([i for i in self.issues if i['severity'] == 'error']),
                'warnings': len([i for i in self.issues if i['severity'] == 'warning']),
                'info': len([i for i in self.issues if i['severity'] == 'info']),
                'quality_score': quality_score,
                'performance_issues': len(self.performance_issues)
            },
            'statistics': dict(self.stats),
            'issues': self.issues,
            'performance_issues': self.performance_issues,
            'duplicates': {k: v for k, v in self.duplicates.items() if len(v) > 1},
            'recommendations': self.generate_recommendations(),
            'schema_info': {
                'version': schema.get('openapi', 'unknown'),
                'title': schema.get('info', {}).get('title', 'unknown'),
                'paths_count': len(schema.get('paths', {})),
                'components_count': len(schema.get('components', {}))
            }
        }
        
        return report
    
    def generate_empty_report(self) -> Dict:
        """Generate report when schema generation failed."""
        return {
            'summary': {
                'total_issues': len(self.issues),
                'critical_issues': len([i for i in self.issues if i['severity'] == 'error']),
                'warnings': len([i for i in self.issues if i['severity'] == 'warning']),
                'info': len([i for i in self.issues if i['severity'] == 'info']),
                'quality_score': 0,
                'performance_issues': 0
            },
            'statistics': {},
            'issues': self.issues,
            'performance_issues': [],
            'duplicates': {},
            'recommendations': ['Fix schema generation issues first'],
            'schema_info': {}
        }
    
    def calculate_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        base_score = 100.0
        
        # Deduct points for issues
        for issue in self.issues:
            if issue['severity'] == 'error':
                base_score -= 10
            elif issue['severity'] == 'warning':
                base_score -= 5
            elif issue['severity'] == 'info':
                base_score -= 1
        
        # Deduct points for performance issues
        base_score -= len(self.performance_issues) * 3
        
        # Deduct points for duplicates
        duplicate_count = sum(len(names) - 1 for names in self.duplicates.values())
        base_score -= duplicate_count * 2
        
        return max(0.0, round(base_score, 1))
    
    def generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        critical_count = len([i for i in self.issues if i['severity'] == 'error'])
        if critical_count > 0:
            recommendations.append(f"Fix {critical_count} critical issues for production readiness")
        
        warning_count = len([i for i in self.issues if i['severity'] == 'warning'])
        if warning_count > 0:
            recommendations.append(f"Address {warning_count} warnings to improve documentation quality")
        
        if self.stats.get('total_examples', 0) == 0:
            recommendations.append("Add examples to improve API usability")
        
        if self.performance_issues:
            recommendations.append("Optimize large examples and reduce nesting depth")
        
        if self.duplicates:
            recommendations.append("Refactor duplicate schemas to reduce specification size")
        
        if self.stats.get('security_coverage', 0) < 50:
            recommendations.append("Improve security documentation coverage")
        
        if not recommendations:
            recommendations.append("Excellent! OpenAPI specification is production-ready")
        
        return recommendations


def print_report(report: Dict):
    """Print formatted validation report."""
    print("\n" + "="*60)
    print("📋 OPENAPI VALIDATION REPORT")
    print("="*60)
    
    # Summary
    summary = report['summary']
    print(f"\n📊 SUMMARY:")
    print(f"   Quality Score: {summary['quality_score']}/100")
    print(f"   Total Issues: {summary['total_issues']}")
    print(f"   Critical Issues: {summary['critical_issues']}")
    print(f"   Warnings: {summary['warnings']}")
    print(f"   Info: {summary['info']}")
    print(f"   Performance Issues: {summary['performance_issues']}")
    
    # Schema info
    schema_info = report.get('schema_info', {})
    if schema_info:
        print(f"\n📜 SCHEMA INFO:")
        print(f"   Version: {schema_info['version']}")
        print(f"   Title: {schema_info['title']}")
        print(f"   Paths: {schema_info['paths_count']}")
        print(f"   Components: {schema_info['components_count']}")
    
    # Statistics
    stats = report.get('statistics', {})
    if stats:
        print(f"\n📈 STATISTICS:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    
    # Issues
    if report['issues']:
        print(f"\n⚠️  ISSUES:")
        for issue in report['issues']:
            icon = "🚨" if issue['severity'] == 'error' else "⚠️" if issue['severity'] == 'warning' else "ℹ️"
            print(f"   {icon} {issue['message']}")
    
    # Performance issues
    if report['performance_issues']:
        print(f"\n⚡ PERFORMANCE ISSUES:")
        for issue in report['performance_issues']:
            print(f"   ⚡ {issue}")
    
    # Duplicates
    if report['duplicates']:
        print(f"\n🔄 DUPLICATES:")
        for hash_val, names in report['duplicates'].items():
            print(f"   🔄 {', '.join(names)}")
    
    # Recommendations
    recommendations = report['recommendations']
    print(f"\n💡 RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    # Overall assessment
    print(f"\n🏆 OVERALL ASSESSMENT:")
    score = summary['quality_score']
    if score >= 90:
        print("   ✅ Excellent! Ready for production")
    elif score >= 80:
        print("   🟢 Good! Minor improvements recommended")
    elif score >= 70:
        print("   🟡 Fair! Several improvements needed")
    else:
        print("   🔴 Needs significant work before production")
    
    print("="*60)


def save_report(report: Dict, output_path: str):
    """Save report to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n💾 Report saved to: {output_path}")


def main():
    """Main validation script."""
    validator = OpenAPIValidator()
    report = validator.validate_all()
    
    # Print report
    print_report(report)
    
    # Save report
    output_path = project_root / 'openapi_validation_report.json'
    save_report(report, output_path)
    
    # Exit with appropriate code
    if report['summary']['critical_issues'] > 0:
        sys.exit(1)
    elif report['summary']['quality_score'] < 80:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
