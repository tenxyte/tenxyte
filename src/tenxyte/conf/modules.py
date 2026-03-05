class ModulesSettingsMixin:

    @property
    def APPLICATION_AUTH_ENABLED(self):
        """
        Activer/désactiver l'authentification par application (X-Access-Key / X-Access-Secret).
        """
        return self._get("APPLICATION_AUTH_ENABLED", True)

    @property
    def ORGANIZATIONS_ENABLED(self):
        """
        Enable Organizations feature (opt-in).
        Default: False (disabled for backward compatibility)
        """
        return self._get("ORGANIZATIONS_ENABLED", False)

    @property
    def ORGANIZATION_MODEL(self):
        """
        Swappable Organization model (like AUTH_USER_MODEL).
        Default: 'tenxyte.Organization'
        """
        return self._get("ORGANIZATION_MODEL", "tenxyte.Organization")

    @property
    def ORGANIZATION_ROLE_MODEL(self):
        """
        Swappable OrganizationRole model.
        Default: 'tenxyte.OrganizationRole'
        """
        return self._get("ORGANIZATION_ROLE_MODEL", "tenxyte.OrganizationRole")

    @property
    def ORGANIZATION_MEMBERSHIP_MODEL(self):
        """
        Swappable OrganizationMembership model.
        Default: 'tenxyte.OrganizationMembership'
        """
        return self._get("ORGANIZATION_MEMBERSHIP_MODEL", "tenxyte.OrganizationMembership")

    @property
    def CREATE_DEFAULT_ORGANIZATION(self):
        """
        Create a default organization for new users.
        Default: True
        """
        return self._get("CREATE_DEFAULT_ORGANIZATION", True)

    # =============================================
    # Agent / AIRS Settings (Phase 1)
    # =============================================
