#! /usr/bin/env python

from os import abort, getenv, read
import socket
import time
import click
from flask import Flask
import traceback

from core.managers import db_manager
from core.model import *
from core.remote.collectors_api import CollectorsApi

app = Flask(__name__)
app.config.from_object("config.Config")

if getenv("DEBUG").lower() == "true":
    app.logger.debug("Debug Mode: On")

db_manager.initialize(app)

# wait for the database to be ready
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((app.config.get("DB_URL"), 5432))
        s.close()
        break
    except socket.error:
        time.sleep(0.1)


# user account management
@app.cli.command("account")
@click.option("-l", "--list", "opt_list", is_flag=True)
@click.option("-c", "--create", is_flag=True)
@click.option("-e", "--edit", is_flag=True)
@click.option("-d", "--delete", is_flag=True)
@click.option("--username")
@click.option("--name", default="")
@click.option("--password")
@click.option("--roles")
def account_manager(opt_list, create, edit, delete, username, name, password, roles):
    from scripts import permissions

    permissions.run(db_manager.db)

    if opt_list:
        users = user.User.get_all()
        for us in users:
            roles = [r.id for r in us.roles]
            print(f"Id: {us.id}\n\tUsername: {us.username}\n\tName: {us.name}\n\tRoles: {roles}")
        exit()

    if create:
        if not username or not password or not roles:
            app.logger.critical("Username, password or role not specified!")
            abort()

        if user.User.find(username):
            app.logger.critical("User already exists!")
            abort()

        roles = roles.split(",")
        roles = []

        for ro in roles:
            r = None
            try:
                r = role.Role.find(int(ro))
            except Exception:
                r = role.Role.find_by_name(ro)

            if not r:
                app.logger.critical("The specified role '{}' does not exist!".format(ro))
                abort()

            roles.append(r)
        # create user in the appropriate authenticator

    if edit:
        if not username:
            app.logger.critical("Username not specified!")
            abort()
        if not password or not roles:
            app.logger.critical("Please specify a new password or role id!")
            abort()

        if not user.User.find(username):
            app.logger.critical("User does not exist!")
            abort()

        if roles:
            roles = roles.split(",")
            roles = []

            for ro in roles:
                r = None
                try:
                    r = role.Role.find(int(ro))
                except Exception:
                    r = role.Role.find_by_name(ro)

                if not r:
                    app.logger.critical("The specified role '{}' does not exist!".format(ro))
                    abort()

                roles.append(r)

        # update the user

    if delete:
        if not username:
            app.logger.critical("Username not specified!")
            abort()

        if not user.User.find(username):
            app.logger.critical("User does not exist!")
            abort()

        # delete the user


# role management
@app.cli.command("role")
@click.option("-l", "--list", "opt_list", is_flag=True)
@click.option("-c", "--create", is_flag=True)
@click.option("-e", "--edit", is_flag=True)
@click.option("-d", "--delete", is_flag=True)
@click.option("-f", "--filter")
@click.option("--id")
@click.option("--name")
@click.option("--description", default="")
@click.option("--permissions")
def role_manager(opt_list, create, edit, delete, filter, id, name, description, permissions):
    from scripts import permissions

    permissions.run(db_manager.db)

    if opt_list:
        roles = None
        roles = role.Role.get(filter)[0] if filter else role.Role.get_all()
        for ro in roles:
            perms = [p.id for p in ro.permissions]
            print(f"Id: {ro.id}\n\tName: {ro.name}\n\tDescription: {ro.description}\n\tPermissions: {perms}")
        return

    if create:
        if not name or not permissions:
            app.logger.critical("Role name or permissions not specified!")
            abort()

        permissions = permissions.split(",")
        perms = []

        for pe in permissions:
            p = permission.Permission.find(pe)

            if not p:
                app.logger.critical("The specified permission '{}' does not exist!".format(pe))
                abort()

            perms.append(p)

        new_role = role.Role(-1, name, description, perms)
        db_manager.db.session.add(new_role)
        db_manager.db.session.commit()

        print("Role '{}' with id {} created.".format(name, new_role.id))

    if edit:
        if not id or not name:
            app.logger.critical("Role id or name not specified!")
            abort()
        if not name or not description or not permissions:
            app.logger.critical("Please specify a new name, description or permissions!")
            abort()

    if delete and ((not id or not name)):
        app.logger.critical("Role id or name not specified!")
        abort()


# collector management
@app.cli.command("collector")
@click.option("-l", "--list", "opt_list", is_flag=True)
@click.option("-c", "--create", is_flag=True)
@click.option("-e", "--edit", is_flag=True)
@click.option("-d", "--delete", is_flag=True)
@click.option("-u", "--update", is_flag=True)
@click.option("-a", "--all", is_flag=True)
@click.option("--show-api-key", is_flag=True)
@click.option("--id")
@click.option("--name")
@click.option("--description")
@click.option("--api-url")
@click.option("--api-key")
def collector_manager(
    opt_list,
    create,
    edit,
    delete,
    update,
    all,
    show_api_key,
    id,
    name,
    description,
    api_url,
    api_key,
):
    if opt_list:
        collector_nodes = collectors_node.CollectorsNode.get_all()

        for node in collector_nodes:
            capabilities = []
            sources = []
            for c in node.collectors:
                capabilities.append(c.type)
                for s in c.sources:
                    sources.append("{} ({})".format(s.name, s.id))
            print(
                "Id: {}\n\tName: {}\n\tURL: {}\n\t{}Created: {}\n\tLast seen: {}\n\tCapabilities: {}\n\tSources: {}".format(
                    node.id,
                    node.name,
                    node.api_url,
                    "API key: {}\n\t".format(node.api_key) if show_api_key else "",
                    node.created,
                    node.last_seen,
                    capabilities,
                    sources,
                )
            )
        exit()

    if create:
        if not name or not api_url or not api_key:
            app.logger.critical("Please specify the collector node name, API url and key!")
            abort()

        data = {
            "id": "",
            "name": name,
            "description": description if description else "",
            "api_url": api_url,
            "api_key": api_key,
            "collectors": [],
            "status": 0,
        }

        collectors_info, status_code = CollectorsApi(api_url, api_key).get_collectors_info("")

        if status_code != 200:
            print("Cannot create a new collector node!")
            print("Response from collector: {}".format(collectors_info))
            abort()

        collectors = collector.Collector.create_all(collectors_info)
        node = collectors_node.CollectorsNode.add_new(data, collectors)
        collectors_info, status_code = CollectorsApi(api_url, api_key).get_collectors_info(node.id)

        print("Collector node '{}' with id {} created.".format(name, node.id))

    if edit:
        if not id or not name:
            app.logger.critical("Collector node id or name not specified!")
            abort()
        if not name or not description or not api_url or not api_key:
            app.logger.critical("Please specify a new name, description, API url or key!")
            abort()

    if delete:
        if not id or not name:
            app.logger.critical("Collector node id or name not specified!")
            abort()

    if update:
        if not all and not id and not name:
            app.logger.critical("Collector node id or name not specified!")
            app.logger.critical("If you want to update all collectors, pass the --all parameter.")
            abort()

        nodes = None
        if id:
            nodes = [collectors_node.CollectorsNode.get_by_id(id)]
            if not nodes:
                app.logger.critical("Collector node does not exit!")
                abort()
        elif name:
            nodes, count = collectors_node.CollectorsNode.get(name)
            if not count:
                app.logger.critical("Collector node does not exit!")
                abort()
        else:
            nodes, count = collectors_node.CollectorsNode.get(None)
            if not count:
                app.logger.critical("No collector nodes exist!")
                abort()

        for node in nodes:
            # refresh collector node id
            collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)
            if status_code == 200:
                print("Collector node {} updated.".format(node.id))
            else:
                print("Unable to update collector node {}.\n\tResponse: [{}] {}.".format(node.id, status_code, collectors_info))


# dictionary management
@app.cli.command("dictonary")
@click.option("--upload-cve", "opt_cve")
@click.option("--upload-cpe", "opt_cpe")
def dictonary_management(opt_cve, opt_cpe):
    from core.model import attribute

    def upload_to(filename):
        try:
            with open(filename, "wb") as out_file:
                while True:
                    chunk = read(0, 131072)
                    if not chunk:
                        break
                    out_file.write(chunk)
        except Exception:
            app.logger.debug(traceback.format_exc())
            app.logger.critical("Upload failed!")
            abort()

    if opt_cve:
        cve_update_file = getenv("CVE_UPDATE_FILE")
        if cve_update_file is None:
            app.logger.critical("CVE_UPDATE_FILE is undefined")
            abort()

        upload_to(cve_update_file)
        try:
            attribute.Attribute.load_dictionaries("cve")
        except Exception:
            app.logger.debug(traceback.format_exc())
            app.logger.critical("File structure was not recognized!")
            abort()

    if opt_cpe:
        cpe_update_file = getenv("CPE_UPDATE_FILE")
        if cpe_update_file is None:
            app.logger.critical("CPE_UPDATE_FILE is undefined")
            abort()

        upload_to(cpe_update_file)
        try:
            attribute.Attribute.load_dictionaries("cpe")
        except Exception:
            app.logger.debug(traceback.format_exc())
            app.logger.critical("File structure was not recognized!")
            abort()

    app.logger.error("Dictionary was uploaded.")
