"""
Tests for lazy loading optimizations in middleware.
"""
import sys


class TestLazyLoading:
    """Tests for lazy import optimizations in middleware.py."""

    def test_middleware_module_does_not_import_models_eagerly(self):
        """Importing middleware module should not eagerly import tenxyte.models.Application."""
        # Save the current state
        set(sys.modules.keys())

        # Force re-import of the middleware module
        if 'tenxyte.middleware' in sys.modules:
            # We can't easily force re-import without side effects in Django,
            # so instead we verify the source code doesn't have the eager import
            import inspect
            from tenxyte import middleware
            source = inspect.getsource(middleware)

            # The module-level should NOT have 'from .models import Application'
            lines = source.split('\n')
            module_level_imports = []
            in_class = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('class '):
                    in_class = True
                if not in_class and stripped.startswith(('from ', 'import ')):
                    module_level_imports.append(stripped)

            # Verify no eager model imports at module level
            model_imports = [line for line in module_level_imports if '.models' in line]
            assert len(model_imports) == 0, f"Found eager model imports: {model_imports}"

    def test_middleware_module_does_not_import_jwt_service_eagerly(self):
        """Module-level should not import JWTService."""
        import inspect
        from tenxyte import middleware
        source = inspect.getsource(middleware)

        lines = source.split('\n')
        module_level_imports = []
        in_class = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('class '):
                in_class = True
            if not in_class and stripped.startswith(('from ', 'import ')):
                module_level_imports.append(stripped)

        jwt_imports = [line for line in module_level_imports if 'jwt_service' in line.lower() or 'JWTService' in line]
        assert len(jwt_imports) == 0, f"Found eager JWTService imports: {jwt_imports}"

    def test_jwt_middleware_lazy_service_initialization(self):
        """JWTAuthMiddleware should not instantiate JWTService until first request."""
        from tenxyte.middleware import JWTAuthMiddleware

        middleware = JWTAuthMiddleware(get_response=lambda r: r)
        # The _jwt_service should be None until first access
        assert middleware._jwt_service is None

    def test_jwt_middleware_service_created_on_access(self):
        """JWTService is created when jwt_service property is first accessed."""
        from tenxyte.middleware import JWTAuthMiddleware

        middleware = JWTAuthMiddleware(get_response=lambda r: r)
        service = middleware.jwt_service
        assert service is not None
        assert middleware._jwt_service is not None

    def test_jwt_middleware_service_singleton(self):
        """JWTService is created only once (cached on instance)."""
        from tenxyte.middleware import JWTAuthMiddleware

        middleware = JWTAuthMiddleware(get_response=lambda r: r)
        service1 = middleware.jwt_service
        service2 = middleware.jwt_service
        assert service1 is service2
