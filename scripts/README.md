# Documentation Scripts

This directory contains scripts for validating, optimizing, and generating documentation for the Tenxyte API.

## 📋 Available Scripts

### 🔍 Validation Scripts

#### `validate_openapi_spec.py`
**Purpose**: Comprehensive OpenAPI specification validation

```bash
python scripts/validate_openapi_spec.py
```

**Features**:
- ✅ OpenAPI 3.0 compliance validation
- ✅ Schema consistency checking
- ✅ Duplicate detection
- ✅ Example validation
- ✅ Performance analysis
- ✅ Quality scoring (0-100)
- ✅ JSON report generation

**Output**: `openapi_validation_report.json`

**Use Cases**:
- Pre-release validation
- CI/CD pipeline integration
- Quality monitoring
- Schema compliance checking

#### `validate_documentation.py`
**Purpose**: Documentation coverage and quality analysis

```bash
python scripts/validate_documentation.py
```

**Features**:
- ✅ Endpoint coverage analysis
- ✅ Example completeness checking
- ✅ Multi-tenant documentation validation
- ✅ Issue detection and reporting
- ✅ Improvement recommendations
- ✅ CI/CD ready exit codes

**Output**: `documentation_validation_report.json`

**Use Cases**:
- Documentation quality monitoring
- Coverage tracking
- Multi-tenant validation
- Automated documentation checks

### ⚡ Optimization Scripts

#### `optimize_schemas.py`
**Purpose**: OpenAPI schema performance optimization

```bash
python scripts/optimize_schemas.py
```

**Features**:
- ✅ Duplicate schema removal
- ✅ Reference optimization
- ✅ Size reduction (up to 40%)
- ✅ Caching hints addition
- ✅ Performance metrics
- ✅ Optimization reports

**Output**: 
- `openapi_schema_optimized.json`
- `schema_optimization_report.json`

**Use Cases**:
- Performance optimization
- Size reduction
- Loading time improvement
- Production preparation

### 📮 Generation Scripts

#### `generate_postman_collection.py`
**Purpose**: Generate complete Postman collection

```bash
python scripts/generate_postman_collection.py
```

**Features**:
- ✅ Complete API collection (50+ endpoints)
- ✅ Authentication setup with JWT tokens
- ✅ Test scripts for responses
- ✅ Environment variables
- ✅ Multi-tenant examples
- ✅ Organized by categories

**Output**:
- `tenxyte_api_collection.postman_collection.json`
- `tenxyte_api_environment.postman_environment.json`

**Use Cases**:
- API development and testing
- Team collaboration
- Client integration
- API exploration

#### `generate_docs_site.py`
**Purpose**: Generate static documentation website

```bash
python scripts/generate_docs_site.py
```

**Features**:
- ✅ Responsive static website
- ✅ Interactive code examples
- ✅ Multi-language support
- ✅ Search functionality
- ✅ Mobile optimization
- ✅ Professional design

**Output**: `docs_site/` directory with complete website

**Use Cases**:
- Public documentation hosting
- Offline documentation
- Custom documentation sites
- Brand customization

## 🚀 Quick Start

### Basic Validation
```bash
# Validate OpenAPI specification
python scripts/validate_openapi_spec.py

# Check documentation coverage
python scripts/validate_documentation.py
```

### Optimization
```bash
# Optimize schema performance
python scripts/optimize_schemas.py
```

### Generation
```bash
# Generate Postman collection
python scripts/generate_postman_collection.py

# Generate documentation site
python scripts/generate_docs_site.py
```

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Documentation Validation

on: [push, pull_request]

jobs:
  validate-docs:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Validate OpenAPI spec
      run: python scripts/validate_openapi_spec.py
    
    - name: Test documentation examples
      run: python tests/test_documentation_examples.py
    
    - name: Optimize schemas
      run: python scripts/optimize_schemas.py
    
    - name: Generate artifacts
      run: |
        python scripts/generate_postman_collection.py
        python scripts/generate_docs_site.py
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v2
      with:
        name: documentation
        path: |
          *.json
          docs_site/
```

### GitLab CI Example
```yaml
documentation:
  stage: test
  script:
    - python scripts/validate_openapi_spec.py
    - python tests/test_documentation_examples.py
    - python scripts/optimize_schemas.py
  artifacts:
    reports:
      junit: test_reports.xml
    paths:
      - openapi_validation_report.json
      - schema_optimization_report.json
      - tenxyte_api_collection.postman_collection.json
      - docs_site/
```

## 📊 Output Files

### Validation Reports
- `openapi_validation_report.json` - Comprehensive validation results
- `documentation_validation_report.json` - Coverage and quality metrics
- `schema_optimization_report.json` - Optimization analysis

### Generated Files
- `openapi_schema_optimized.json` - Performance-optimized schema
- `tenxyte_api_collection.postman_collection.json` - Postman collection
- `tenxyte_api_environment.postman_environment.json` - Postman environment
- `docs_site/` - Static documentation website

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Custom output directory
export DOCS_OUTPUT_DIR="./custom_output"

# Optional: Custom base URL for documentation site
export DOCS_BASE_URL="https://api.tenxyte.com"

# Optional: Custom organization slug for examples
export DEFAULT_ORG_SLUG="demo-org"
```

### Script Configuration
Most scripts support configuration through command-line arguments:

```bash
# Custom output directory
python scripts/validate_openapi_spec.py --output ./reports/

# Custom schema file
python scripts/optimize_schemas.py --schema ./custom_schema.json

# Verbose output
python scripts/generate_postman_collection.py --verbose
```

## 🐛 Troubleshooting

### Common Issues

#### Schema Generation Fails
```bash
# Ensure Django settings are configured
export DJANGO_SETTINGS_MODULE=your_project.settings

# Check for missing dependencies
pip install drf-spectacular django
```

#### Permission Errors
```bash
# Ensure write permissions for output directory
chmod +w ./docs_site/
chmod +w ./
```

#### Memory Issues with Large Schemas
```bash
# Use optimized schema generation
python scripts/optimize_schemas.py --memory-efficient
```

### Debug Mode
Enable debug output for troubleshooting:

```bash
# Enable verbose logging
export DEBUG=1
python scripts/validate_openapi_spec.py --verbose
```

## 📈 Performance Tips

### Large Schema Optimization
1. **Use optimized schema** - Always use `openapi_schema_optimized.json`
2. **Enable caching** - Add caching headers for static documentation
3. **Compress output** - Use gzip for JSON files
4. **CDN hosting** - Host static files on CDN

### CI/CD Performance
1. **Cache dependencies** - Cache pip packages
2. **Parallel execution** - Run validation and optimization in parallel
3. **Artifact caching** - Cache generated files between runs
4. **Conditional generation** - Only regenerate when sources change

## 🤝 Contributing

### Adding New Scripts
1. Follow existing naming conventions
2. Add comprehensive docstrings
3. Include error handling
4. Add command-line argument support
5. Update this README

### Script Requirements
- Python 3.8+ compatibility
- Django and DRF Spectacular support
- JSON output for reports
- Command-line interface
- Error handling and logging
- CI/CD integration ready

## 📞 Support

For issues with these scripts:
1. Check the troubleshooting section
2. Review script output logs
3. Validate Django configuration
4. Check dependencies versions
5. Review [Documentation Enhancements](../docs/DOCUMENTATION_ENHANCEMENTS.md)

---

## 📝 Script Summary

| Script | Purpose | Output | CI/CD Ready |
|--------|---------|--------|-------------|
| `validate_openapi_spec.py` | OpenAPI validation | JSON report | ✅ |
| `validate_documentation.py` | Coverage analysis | JSON report | ✅ |
| `optimize_schemas.py` | Performance optimization | Optimized schema | ✅ |
| `generate_postman_collection.py` | Postman collection | Collection files | ✅ |
| `generate_docs_site.py` | Static website | HTML site | ✅ |

All scripts are production-ready and designed for automated workflows.
