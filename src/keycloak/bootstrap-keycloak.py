#!/usr/bin/env python

from keycloak import KeycloakAdmin
import click
import json


@click.command()
@click.argument("url", default="http://keycloak.local")
@click.argument("user", default="admin")
@click.argument("password", default="supersecret")
@click.argument("realm", default="master")
@click.argument("verify", default=False)
def main(url, user, password, realm, verify):
    keycloak_admin = KeycloakAdmin(
        server_url=url,
        username=user,
        password=password,
        realm_name=realm,
        verify=verify,
    )

    keycloak_admin.create_client(
        payload={"enabled": True, "clientId": "taranis", "name": "Taranis"},
        skip_exists=True,
    )

    taranis_user = keycloak_admin.create_user(
        payload={
            "username": "taranis",
            "enabled": True,
            "firstName": "Taranis",
            "credentials": [{"value": password, "type": "password"}],
        }
    )
    print(taranis_user)
    taranis_client = keycloak_admin.get_client_id(client_name="taranis")
    client_secrets = keycloak_admin.generate_client_secrets(client_id=taranis_client)
    with open("client_secrets.json", "w") as outfile:
        json.dump(client_secrets, outfile, indent=4)


if __name__ == "__main__":
    main(auto_envvar_prefix="TARANIS_KEYCLOAK")
