import pytest
import tenxyte

class TestInit:
    def test_getattr_valid(self):
        """Test that accessing a valid attribute in __all__ works and dynamically imports it."""
        # Unload from sys.modules to simulate cold import if needed, 
        # but just accessing tenxyte.AbstractUser might be enough
        # if it hasn't been accessed yet or even if it has, it goes through getattr
        # or it is already in tenxyte namespace. Wait, if it's already imported elsewhere, 
        # `tenxyte.AbstractUser` might not trigger `__getattr__` if it's already populated in the module dict.
        # Let's forcibly remove it from tenxyte.__dict__ if it exists, to trigger __getattr__.
        
        attr_name = 'AbstractUser'
        if attr_name in tenxyte.__dict__:
            del tenxyte.__dict__[attr_name]
            
        # This will trigger tenxyte.__getattr__('AbstractUser')
        model = getattr(tenxyte, attr_name)
        assert model is not None
        assert model.__name__ == attr_name

    def test_getattr_invalid(self):
        """Test that accessing an invalid attribute raises AttributeError."""
        with pytest.raises(AttributeError, match="has no attribute 'NonExistentModel'"):
            _ = tenxyte.NonExistentModel
