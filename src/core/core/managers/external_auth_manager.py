import os
from keycloak import KeycloakAdmin


def keycloak_user_management_enabled():
    return os.getenv("KEYCLOAK_USER_MANAGEMENT", "false").lower() == "true"


def get_keycloak_admin():
    return KeycloakAdmin(
        server_url=os.getenv("KEYCLOAK_SERVER_URL"),
        username=os.getenv("KEYCLOAK_ADMIN_USERNAME"),
        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD"),
        realm_name=os.getenv("KEYCLOAK_REALM_NAME"),
        client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET_KEY"),
        verify=(os.getenv("KEYCLOAK_VERIFY").lower() == "true"),
    )


def create_user(user_data):
    if not keycloak_user_management_enabled():
        return
    keycloak_admin = get_keycloak_admin()
    keycloak_admin.create_user(
        {"username": user_data["username"], "credentials": [{"value": user_data["password"], "type": "password"}], "enabled": True}
    )


def update_user(user_data, original_username):
    if not keycloak_user_management_enabled():
        return
    if "password" in user_data and user_data["password"] or original_username != user_data["username"]:
        keycloak_admin = get_keycloak_admin()
        keycloak_user_id = keycloak_admin.get_user_id(original_username)
        if keycloak_user_id is not None:
            if original_username != user_data["username"]:
                keycloak_admin.update_user(user_id=keycloak_user_id, payload={"username": user_data["username"]})

            if "password" in user_data and user_data["password"]:
                keycloak_admin.set_user_password(user_id=keycloak_user_id, password=user_data["password"], temporary=False)


def delete_user(username):
    if not keycloak_user_management_enabled():
        return
    keycloak_admin = get_keycloak_admin()
    keycloak_user_id = keycloak_admin.get_user_id(username)
    if keycloak_user_id is not None:
        keycloak_admin.delete_user(user_id=keycloak_user_id)
