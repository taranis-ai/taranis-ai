from os import abort, path, chdir, getenv, read
import sys
import socket
import time

chdir('/app/taranis-ng-core/')
sys.path.append(path.abspath('.'))
sys.path.append(path.abspath('../taranis-ng-common'))

import logging
from flask import Flask
from flask_script import Manager,Command
from flask_script.commands import Option

from managers import db_manager
from model import *

app = Flask(__name__)
app.config.from_object('config.Config')
manager = Manager(app=app)
app.logger = logging.getLogger('gunicorn.error')
app.logger.level = logging.INFO

db_manager.initialize(app)

# wait for the database to be ready
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((app.config.get('DB_URL'), 5432))
        s.close()
        break
    except socket.error as ex:
        time.sleep(0.1)

# user account management
class Account(Command):
    
    option_list = (
        Option('--list', '-l', dest='opt_list', action='store_true'),
        Option('--create', '-c', dest='opt_create', action='store_true'),
        Option('--edit', '-e', dest='opt_edit', action='store_true'),
        Option('--delete', '-d', dest='opt_delete', action='store_true'),
        Option('--username', dest='opt_username'),
        Option('--name', dest='opt_name', default=""),
        Option('--password', dest='opt_password'),
        Option('--roles', dest='opt_roles'),
    )

    def run(self, opt_list, opt_create, opt_edit, opt_delete, opt_username, opt_name, opt_password, opt_roles):
        from scripts import permissions
        permissions.run(db_manager.db)

        if (opt_list):
            users = user.User.get_all()
            for us in users:
                roles = []
                for r in us.roles:
                    roles.append(r.id)
                print('Id: {}\n\tUsername: {}\n\tName: {}\n\tRoles: {}'.format(us.id, us.username, us.name, roles))
            exit()

        if (opt_create):
            if (not opt_username or not opt_password or not opt_roles):
                app.logger.critical("Username, password or role not specified!")
                abort()
            
            if user.User.find(opt_username):
                app.logger.critical("User already exists!")
                abort()
            
            opt_roles = opt_roles.split(',')
            roles = []

            for ro in opt_roles:
                r = None
                try:
                    r = role.Role.find(int(ro))
                except:
                    r = role.Role.find_by_name(ro)
                
                if not r:
                    app.logger.critical("The specified role '{}' does not exist!".format(ro))
                    abort()
                
                roles.append(r)

            # create user in the appropriate authenticator
            

        if (opt_edit):
            if (not opt_username):
                app.logger.critical("Username not specified!")
                abort()
            if (not opt_password or not opt_roles):
                app.logger.critical("Please specify a new password or role id!")
                abort()

            if not user.User.find(opt_username):
                app.logger.critical("User does not exist!")
                abort()

            if (opt_roles):
                opt_roles = opt_roles.split(',')
                roles = []

                for ro in opt_roles:
                    r = None
                    try:
                        r = role.Role.find(int(ro))
                    except:
                        r = role.Role.find_by_name(ro)
                    
                    if not r:
                        app.logger.critical("The specified role '{}' does not exist!".format(ro))
                        abort()
                    
                    roles.append(r)

            # update the user
                
        if (opt_delete):
            if (not opt_username):
                app.logger.critical("Username not specified!")
                abort()

            if not user.User.find(opt_username):
                app.logger.critical("User does not exist!")
                abort()

            # delete the user

# role management
class Role(Command):
    
    option_list = (
        Option('--list', '-l', dest='opt_list', action='store_true'),
        Option('--create', '-c', dest='opt_create', action='store_true'),
        Option('--edit', '-e', dest='opt_edit', action='store_true'),
        Option('--delete', '-d', dest='opt_delete', action='store_true'),
        Option('--filter', '-f', dest='opt_filter'),
        Option('--id', dest='opt_id'),
        Option('--name', dest='opt_name'),
        Option('--description', dest='opt_description', default=""),
        Option('--permissions', dest='opt_permissions'),
    )

    def run(self, opt_list, opt_create, opt_edit, opt_delete, opt_filter, opt_id, opt_name, opt_description, opt_permissions):
        from scripts import permissions
        permissions.run(db_manager.db)

        if (opt_list):
            roles = None
            if (opt_filter):
                roles = role.Role.get(opt_filter)[0]
            else:
                roles = role.Role.get_all()
            
            for ro in roles:
                perms = []
                for p in ro.permissions:
                    perms.append(p.id)
                print('Id: {}\n\tName: {}\n\tDescription: {}\n\tPermissions: {}'.format(ro.id, ro.name, ro.description, perms))
            exit()

        if (opt_create):
            if (not opt_name or not opt_permissions):
                app.logger.critical("Role name or permissions not specified!")
                abort()

            opt_permissions = opt_permissions.split(',')
            perms = []

            for pe in opt_permissions:
                p = permission.Permission.find(pe)

                if not p:
                    app.logger.critical("The specified permission '{}' does not exist!".format(pe))
                    abort()

                perms.append(p)

            new_role = role.Role(-1, opt_name, opt_description, perms)
            db_manager.db.session.add(new_role)
            db_manager.db.session.commit()

            print('Role \'{}\' with id {} created.'.format(opt_name, new_role.id))


        if (opt_edit):
            if (not opt_id or not opt_name):
                app.logger.critical("Role id or name not specified!")
                abort()
            if (not opt_name or not opt_description or not opt_permissions):
                app.logger.critical("Please specify a new name, description or permissions!")
                abort()

        if (opt_delete):
            if (not opt_id or not opt_name):
                app.logger.critical("Role id or name not specified!")
                abort()

# dictionary management
class DictionaryManagement(Command):

    option_list = (
        Option('--upload-cve', dest='opt_cve', action='store_true'),
        Option('--upload-cpe', dest='opt_cpe', action='store_true'),
    )

    def run(self, opt_cve, opt_cpe):
        from model import attribute

        if (opt_cve):
            cve_update_file = getenv('CVE_UPDATE_FILE')
            if cve_update_file is None:
                app.logger.critical("CVE_UPDATE_FILE is undefined")
                abort()

            self.upload_to(cve_update_file)
            try:
                attribute.Attribute.load_dictionaries('cve')
            except:
                app.logger.critical("File structure was not recognized!")
                abort()

        if (opt_cpe):
            cpe_update_file = getenv('CPE_UPDATE_FILE')
            if cpe_update_file is None:
                app.logger.critical("CPE_UPDATE_FILE is undefined")
                abort()

            self.upload_to(cpe_update_file)
            try:
                attribute.Attribute.load_dictionaries('cpe')
            except:
                app.logger.critical("File structure was not recognized!")
                abort()

        app.logger.error("Dictionary was uploaded.")
        exit()

    def upload_to(self, filename):
        try:
            with open(filename, 'wb') as out_file:
                while True:
                    chunk = read(0, 131072)
                    if not chunk:
                        break
                    out_file.write(chunk)
        except:
            app.logger.critical("Upload failed!")
            abort()

class SampleData(Command):
    def run(self):
        with app.app_context():
            from scripts import permissions
            from scripts import sample_data

            data, count = user.User.get(None, None)
            if count:
                app.logger.error("Sample data already installed.")
                sys.exit()

            app.logger.error("Installing sample data...")
            permissions.run(db_manager.db)
            sample_data.run(db_manager.db)
            app.logger.error("Sample data installed.")
        sys.exit()
        

manager.add_command('account', Account)
manager.add_command('role', Role)
manager.add_command('dictionary', DictionaryManagement)
manager.add_command('sample-data', SampleData)

if __name__ == '__main__':
    manager.run()
