"""
Regression Test Report Template

This document tracks the results of running the Django test suite
to verify zero regression after framework-agnostic refactoring.

Date: {date}
Version: {version}
Commit: {commit}

Test Execution
==============

Command:
    pytest tests/integration/django/ -v --tb=short

Results:
    Total Tests: {total_tests}
    Passed: {passed}
    Failed: {failed}
    Skipped: {skipped}
    Errors: {errors}

Test Breakdown
==============

Core Tests:
    Location: tests/core/
    Count: {core_count}
    Status: {core_status}
    
Django Integration Tests:
    Location: tests/integration/django/
    Count: {django_count}
    Status: {django_status}
    
    Sub-categories:
        - Unit Tests: {unit_count}
        - Multi-DB Tests: {multidb_count}
        - Security Tests: {security_count}

Regression Checklist
====================

API Compatibility:
    [ ] All DRF endpoints return identical responses
    [ ] All HTTP status codes unchanged
    [ ] Request/response payloads match
    
Configuration Compatibility:
    [ ] settings.py variables work unchanged
    [ ] Default values preserved
    [ ] Custom settings respected
    
Database Compatibility:
    [ ] No migrations required
    [ ] Models unchanged
    [ ] ORM queries work identically
    
Feature Compatibility:
    [ ] JWT authentication works
    [ ] 2FA/TOTP works
    [ ] WebAuthn/Passkeys work
    [ ] Magic Links work
    [ ] RBAC works
    [ ] B2B Organizations work

Conclusion
==========

Status: {overall_status}

Notes:
    {notes}

Signed off by: _________________
Date: _________________
"""
