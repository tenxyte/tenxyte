#!/usr/bin/env python3
"""
Schema Optimization Script

This script optimizes the OpenAPI schema for better performance:
1. Validates path keys (detects corruption before optimizing)
2. Removes duplicate schemas
3. Optimizes schema references
4. Adds caching hints
5. Reduces schema size
6. Improves loading performance

IMPORTANT: Always regenerate the schema from source before optimizing:
    python scripts/generate_openapi_schema.py
    python scripts/optimize_schemas.py
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SchemaOptimizer:
    """Optimizes OpenAPI schema for better performance."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.schema_file = self.project_root / 'openapi_schema.json'
        self.optimizations = []
        self.stats = {
            'original_size': 0,
            'optimized_size': 0,
            'schemas_removed': 0,
            'references_added': 0,
            'duplicates_found': 0,
            'corrupted_paths': 0,
        }
        self.corrupted_path_details: List[str] = []
        
    def optimize_schema(self) -> Dict:
        """Load, validate, optimize, and return the schema."""
        print("🔧 Starting schema optimization...")
        
        # Load schema
        schema = self.load_schema()
        if not schema:
            return {}
        
        # Record original size
        self.stats['original_size'] = len(json.dumps(schema, default=str))
        
        # Validate paths FIRST — abort if corrupted
        corrupted = self.validate_paths(schema)
        if corrupted:
            print(f"\n❌ Found {len(corrupted)} corrupted path(s). Optimization aborted.")
            print("   Regenerate the schema first:")
            print("   python scripts/generate_openapi_schema.py")
            return schema
        
        # Run optimizations
        self.remove_duplicate_schemas(schema)
        self.optimize_schema_references(schema)
        self.add_caching_hints(schema)
        self.optimize_examples(schema)
        self.compress_large_objects(schema)
        
        # Record optimized size
        self.stats['optimized_size'] = len(json.dumps(schema, default=str))
        
        # Save optimized schema
        self.save_optimized_schema(schema)
        
        return schema
    
    def validate_paths(self, schema: Dict) -> List[str]:
        """Validate all path keys — detect corruption before optimizing."""
        print("🔍 Validating path keys...")
        
        corrupted = []
        paths = schema.get('paths', {})
        
        for path in paths.keys():
            issues = []
            
            # Check for trailing/leading whitespace
            if path != path.strip():
                issues.append('trailing/leading whitespace')
            
            # Check for double spaces (embedded console output)
            if '  ' in path:
                issues.append('double spaces (embedded content)')
            
            # Check for unreasonably long segments
            segments = path.split('/')
            for seg in segments:
                if len(seg) > 50 and not seg.startswith('{'):
                    issues.append(f'suspiciously long segment: {seg[:30]}...')
                    break
            
            # Check for path within path (e.g. /admin/login-attempts/ens/cleanup/)
            # where a suffix from another path got embedded
            if len(segments) > 10:
                issues.append(f'too many segments ({len(segments)})')
            
            if issues:
                detail = f"{path!r}: {', '.join(issues)}"
                corrupted.append(detail)
                self.corrupted_path_details.append(detail)
                print(f"   ⚠️  CORRUPTED: {detail}")
        
        self.stats['corrupted_paths'] = len(corrupted)
        
        if not corrupted:
            print(f"   ✅ All {len(paths)} paths are valid")
        
        return corrupted
    
    def load_schema(self) -> Dict:
        """Load the OpenAPI schema."""
        if not self.schema_file.exists():
            print(f"❌ Schema file not found: {self.schema_file}")
            return {}
        
        try:
            with open(self.schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            print(f"📋 Loaded schema from: {self.schema_file}")
            return schema
        except Exception as e:
            print(f"❌ Failed to load schema: {e}")
            return {}
    
    def remove_duplicate_schemas(self, schema: Dict):
        """Remove duplicate schemas and create references."""
        print("🔄 Removing duplicate schemas...")
        
        if 'components' not in schema or 'schemas' not in schema['components']:
            return
        
        schemas = schema['components']['schemas']
        schema_hashes = {}
        duplicates = defaultdict(list)
        
        # Find duplicates by content hash
        for name, schema_def in schemas.items():
            # Create normalized version (remove title, description)
            normalized = self.normalize_schema(schema_def)
            schema_str = json.dumps(normalized, sort_keys=True, default=str)
            schema_hash = hashlib.md5(schema_str.encode()).hexdigest()
            
            if schema_hash in schema_hashes:
                duplicates[schema_hash].append(name)
            else:
                schema_hashes[schema_hash] = name
        
        # Process duplicates
        for hash_val, duplicate_names in duplicates.items():
            if len(duplicate_names) > 1:
                self.stats['duplicates_found'] += len(duplicate_names) - 1
                primary_name = duplicate_names[0]
                
                # Replace duplicates with references
                for dup_name in duplicate_names[1:]:
                    self.replace_schema_references(schema, dup_name, primary_name)
                    del schemas[dup_name]
                    self.stats['schemas_removed'] += 1
                
                self.optimizations.append(f"Removed {len(duplicate_names) - 1} duplicates of {primary_name}")
    
    def normalize_schema(self, schema: Dict) -> Dict:
        """Create a normalized version of schema for comparison."""
        normalized = schema.copy()
        
        # Remove fields that don't affect structure
        normalized.pop('title', None)
        normalized.pop('description', None)
        normalized.pop('example', None)
        
        # Recursively normalize nested objects
        if 'properties' in normalized:
            for key, value in normalized['properties'].items():
                if isinstance(value, dict):
                    normalized['properties'][key] = self.normalize_schema(value)
        
        if 'items' in normalized and isinstance(normalized['items'], dict):
            normalized['items'] = self.normalize_schema(normalized['items'])
        
        return normalized
    
    def replace_schema_references(self, schema: Dict, old_name: str, new_name: str):
        """Replace all references to old schema with new schema."""
        schema_str = json.dumps(schema)
        old_ref = f"#/components/schemas/{old_name}"
        new_ref = f"#/components/schemas/{new_name}"
        
        if old_ref in schema_str:
            schema_str = schema_str.replace(old_ref, new_ref)
            # Update the schema in place
            schema.clear()
            schema.update(json.loads(schema_str))
            self.stats['references_added'] += 1
    
    def optimize_schema_references(self, schema: Dict):
        """Optimize schema references for better caching."""
        print("🔗 Optimizing schema references...")
        
        # Add common reusable schemas if they don't exist
        if 'components' not in schema:
            schema['components'] = {}
        if 'schemas' not in schema['components']:
            schema['components']['schemas'] = {}
        
        schemas = schema['components']['schemas']
        
        # Add common response schemas
        self.add_common_schemas(schemas)
        
        # Optimize response references
        self.optimize_response_references(schema)
    
    def add_common_schemas(self, schemas: Dict):
        """Add common reusable schemas."""
        # Standard error response
        if 'StandardErrorResponse' not in schemas:
            schemas['StandardErrorResponse'] = {
                'type': 'object',
                'description': 'Standard error response format',
                'properties': {
                    'error': {
                        'type': 'string',
                        'description': 'Error message'
                    },
                    'code': {
                        'type': 'string',
                        'description': 'Machine-readable error code'
                    },
                    'details': {
                        'oneOf': [
                            {'type': 'string'},
                            {'type': 'object'}
                        ],
                        'description': 'Additional error details'
                    },
                    'retry_after': {
                        'type': 'integer',
                        'description': 'Seconds to wait before retry',
                        'nullable': True
                    }
                },
                'required': ['error']
            }
            self.optimizations.append("Added StandardErrorResponse schema")
        
        # Paginated response
        if 'PaginatedResponse' not in schemas:
            schemas['PaginatedResponse'] = {
                'type': 'object',
                'description': 'Standard paginated response format',
                'properties': {
                    'count': {
                        'type': 'integer',
                        'description': 'Total number of items'
                    },
                    'next': {
                        'type': 'string',
                        'description': 'URL of next page',
                        'nullable': True
                    },
                    'previous': {
                        'type': 'string',
                        'description': 'URL of previous page',
                        'nullable': True
                    },
                    'results': {
                        'type': 'array',
                        'description': 'Array of results'
                    }
                },
                'required': ['count', 'results']
            }
            self.optimizations.append("Added PaginatedResponse schema")
        
        # Success response
        if 'SuccessResponse' not in schemas:
            schemas['SuccessResponse'] = {
                'type': 'object',
                'description': 'Standard success response format',
                'properties': {
                    'message': {
                        'type': 'string',
                        'description': 'Success message'
                    },
                    'data': {
                        'description': 'Response data'
                    }
                },
                'required': ['message']
            }
            self.optimizations.append("Added SuccessResponse schema")
    
    def optimize_response_references(self, schema: Dict):
        """Replace inline response schemas with references."""
        for path, path_item in schema.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'patch', 'delete'] and 'responses' in operation:
                    self.optimize_operation_responses(operation['responses'])
    
    def optimize_operation_responses(self, responses: Dict):
        """Optimize response schemas in an operation."""
        for status_code, response in responses.items():
            if 'content' in response:
                for content_type, content in response['content'].items():
                    if 'schema' in content:
                        # Check if it's a standard error response
                        if self.is_standard_error_response(content['schema']):
                            content['schema'] = {'$ref': '#/components/schemas/StandardErrorResponse'}
                            self.stats['references_added'] += 1
                        
                        # Check if it's a paginated response
                        elif self.is_paginated_response(content['schema']):
                            content['schema'] = {'$ref': '#/components/schemas/PaginatedResponse'}
                            self.stats['references_added'] += 1
    
    def is_standard_error_response(self, schema: Dict) -> bool:
        """Check if schema matches standard error response pattern."""
        if not isinstance(schema, dict) or 'type' not in schema:
            return False
        
        if schema['type'] != 'object':
            return False
        
        properties = schema.get('properties', {})
        required = set(schema.get('required', []))
        
        # Check for required error field
        if 'error' not in required or 'error' not in properties:
            return False
        
        # Check for optional code field
        if 'code' in properties and properties['code'].get('type') == 'string':
            return True
        
        return False
    
    def is_paginated_response(self, schema: Dict) -> bool:
        """Check if schema matches paginated response pattern."""
        if not isinstance(schema, dict) or 'type' not in schema:
            return False
        
        if schema['type'] != 'object':
            return False
        
        properties = schema.get('properties', {})
        required = set(schema.get('required', []))
        
        # Check for required count and results fields
        if not {'count', 'results'}.issubset(required):
            return False
        
        if 'count' not in properties or 'results' not in properties:
            return False
        
        # Check types
        if properties['count'].get('type') != 'integer':
            return False
        
        if properties['results'].get('type') != 'array':
            return False
        
        return True
    
    def add_caching_hints(self, schema: Dict):
        """Add caching hints for better performance."""
        print("💾 Adding caching hints...")
        
        # Add custom extensions for caching
        if 'x-cache-ttl' not in schema:
            schema['x-cache-ttl'] = 3600  # 1 hour default
        
        # Add caching hints to commonly used schemas
        if 'components' in schema and 'schemas' in schema['components']:
            schemas = schema['components']['schemas']
            
            # Add caching hints to reference schemas
            for name, schema_def in schemas.items():
                if name in ['StandardErrorResponse', 'PaginatedResponse', 'SuccessResponse']:
                    schema_def['x-cache-hint'] = 'reference'
                    schema_def['x-cache-ttl'] = 86400  # 24 hours for reference schemas
        
        self.optimizations.append("Added caching hints for better performance")
    
    def optimize_examples(self, schema: Dict):
        """Optimize examples for better performance."""
        print("📋 Optimizing examples...")
        
        examples_optimized = 0
        
        for path, path_item in schema.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    if 'examples' in operation:
                        optimized = self.optimize_operation_examples(operation['examples'])
                        examples_optimized += optimized
        
        if examples_optimized > 0:
            self.optimizations.append(f"Optimized {examples_optimized} examples")
    
    def optimize_operation_examples(self, examples: Dict) -> int:
        """Optimize examples in an operation."""
        optimized = 0
        
        for name, example in examples.items():
            if 'value' in example:
                value = example['value']
                
                # Optimize large example values
                if isinstance(value, (dict, list)):
                    example_str = json.dumps(value, default=str)
                    if len(example_str) > 2048:  # If example is larger than 2KB
                        # Create a simplified version
                        simplified = self.simplify_example(value)
                        if simplified != value:
                            example['value'] = simplified
                            example['x-simplified'] = True
                            optimized += 1
        
        return optimized
    
    def simplify_example(self, value: Any) -> Any:
        """Create a simplified version of an example."""
        if isinstance(value, dict):
            simplified = {}
            # Keep only essential fields (first 3)
            for i, (key, val) in enumerate(value.items()):
                if i >= 3:
                    break
                if isinstance(val, (dict, list)):
                    simplified[key] = self.simplify_example(val)
                else:
                    simplified[key] = val
            
            # Add indicator if truncated
            if len(value) > 3:
                simplified['_truncated'] = True
            
            return simplified
        
        elif isinstance(value, list):
            # Keep only first 2 items
            if len(value) > 2:
                simplified = [self.simplify_example(item) for item in value[:2]]
                simplified.append({'_more_items': len(value) - 2})
                return simplified
            else:
                return [self.simplify_example(item) for item in value]
        
        else:
            return value
    
    def compress_large_objects(self, schema: Dict):
        """Compress large objects in the schema."""
        print("🗜️  Compressing large objects...")
        
        compressed = 0
        
        # Compress large schema descriptions
        if 'components' in schema and 'schemas' in schema['components']:
            for name, schema_def in schema['components']['schemas'].items():
                if 'description' in schema_def:
                    desc = schema_def['description']
                    if len(desc) > 500:  # If description is very long
                        schema_def['description'] = desc[:497] + '...'
                        compressed += 1
        
        if compressed > 0:
            self.optimizations.append(f"Compressed {compressed} large descriptions")
    
    def save_optimized_schema(self, schema: Dict):
        """Save the optimized schema."""
        output_file = self.project_root / 'openapi_schema_optimized.json'
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2, default=str)
            print(f"💾 Optimized schema saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save optimized schema: {e}")
    
    def generate_report(self) -> Dict:
        """Generate optimization report."""
        size_reduction = self.stats['original_size'] - self.stats['optimized_size']
        reduction_percentage = (size_reduction / self.stats['original_size']) * 100 if self.stats['original_size'] > 0 else 0
        
        return {
            'summary': {
                'original_size_bytes': self.stats['original_size'],
                'optimized_size_bytes': self.stats['optimized_size'],
                'size_reduction_bytes': size_reduction,
                'reduction_percentage': round(reduction_percentage, 2),
                'schemas_removed': self.stats['schemas_removed'],
                'references_added': self.stats['references_added'],
                'duplicates_found': self.stats['duplicates_found'],
                'corrupted_paths': self.stats['corrupted_paths'],
                'optimizations_count': len(self.optimizations)
            },
            'optimizations': self.optimizations,
            'corrupted_path_details': self.corrupted_path_details,
            'recommendations': self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        if self.stats.get('corrupted_paths', 0) > 0:
            recommendations.append(
                f"CRITICAL: {self.stats['corrupted_paths']} corrupted path(s) found. "
                "Regenerate the schema: python scripts/generate_openapi_schema.py"
            )
            return recommendations
        
        size_reduction = self.stats.get('original_size', 0) - self.stats.get('optimized_size', 0)
        if size_reduction > 0:
            recommendations.append("Consider using the optimized schema for production")
        
        if self.stats['duplicates_found'] > 0:
            recommendations.append("Regularly check for new duplicate schemas")
        
        if self.stats['references_added'] > 0:
            recommendations.append("Use schema references consistently for better caching")
        
        if not self.optimizations:
            recommendations.append("Schema is already well optimized")
        
        return recommendations


def print_report(report: Dict):
    """Print optimization report."""
    print("\n" + "="*60)
    print("🔧 SCHEMA OPTIMIZATION REPORT")
    print("="*60)
    
    # Summary
    summary = report['summary']
    print("\n📊 SUMMARY:")
    print(f"   Original Size: {summary['original_size_bytes']:,} bytes")
    print(f"   Optimized Size: {summary['optimized_size_bytes']:,} bytes")
    print(f"   Size Reduction: {summary['size_reduction_bytes']:,} bytes ({summary['reduction_percentage']}%)")
    print(f"   Schemas Removed: {summary['schemas_removed']}")
    print(f"   References Added: {summary['references_added']}")
    print(f"   Duplicates Found: {summary['duplicates_found']}")
    print(f"   Optimizations: {summary['optimizations_count']}")
    
    # Optimizations
    if report['optimizations']:
        print("\n🔧 OPTIMIZATIONS APPLIED:")
        for opt in report['optimizations']:
            print(f"   ✅ {opt}")
    
    # Recommendations
    recommendations = report['recommendations']
    print("\n💡 RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    # Overall assessment
    print("\n🏆 OVERALL ASSESSMENT:")
    if summary['reduction_percentage'] > 10:
        print("   ✅ Significant optimization achieved!")
    elif summary['reduction_percentage'] > 0:
        print("   🟢 Good optimization results")
    else:
        print("   ℹ️  Schema was already optimized")
    
    print("="*60)


def save_report(report: Dict, output_path: str):
    """Save optimization report."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n💾 Report saved to: {output_path}")


def main():
    """Main optimization script."""
    optimizer = SchemaOptimizer()
    optimizer.optimize_schema()
    report = optimizer.generate_report()
    
    # Print report
    print_report(report)
    
    # Save report
    output_path = project_root / 'schema_optimization_report.json'
    save_report(report, output_path)
    
    # Exit with success
    sys.exit(0)


if __name__ == '__main__':
    main()
