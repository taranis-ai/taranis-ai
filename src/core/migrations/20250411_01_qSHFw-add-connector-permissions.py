"""
Add Connector permissions
"""

from yoyo import step

__depends__ = {"20250324_02_vL3hN-add-last-change-column"}

steps = [
    step(
        """
        INSERT INTO public.permission (id, name, description)
        VALUES
            ('CONFIG_CONNECTOR_ACCESS', 'Config connector access', 'Access to connector configuration'),
            ('CONFIG_CONNECTOR_CREATE', 'Config connector create', 'Create to connector configuration'),
            ('CONFIG_CONNECTOR_UPDATE', 'Config connector update', 'Update to connector configuration'),
            ('CONFIG_CONNECTOR_DELETE', 'Config connector delete', 'Delete to connector configuration'),
            ('CONNECTOR_USER_ACCESS', 'Connector user access', 'Access to connector management')
        ON CONFLICT (id) DO NOTHING;
        """,
        """
        DELETE FROM public.permission
        WHERE id IN (
            'CONFIG_CONNECTOR_ACCESS',
            'CONFIG_CONNECTOR_CREATE',
            'CONFIG_CONNECTOR_UPDATE',
            'CONFIG_CONNECTOR_DELETE',
            'CONNECTOR_USER_ACCESS'
        );
        """,
    )
]
