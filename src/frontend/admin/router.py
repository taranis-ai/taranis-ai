import uuid
from flask import Flask, render_template, Blueprint, request, jsonify
from flask.views import MethodView
from flask_htmx import HTMX
from admin.filters import human_readable_trigger

from admin.core_api import CoreApi
from admin.config import Config
from dataclasses import dataclass

@dataclass 
class Address(object):
    city: str
    country: str
    street: str
    zip: str

@dataclass
class Organization(object):
    id: int
    name: str
    description: str
    address: Address
@dataclass
class User(object):
    id: int
    name: str
    organization: str
    permissions: list[str]
    profile: list[str]
    roles: list[int]
    username: str

def is_htmx_request() -> bool:
    return "HX-Request" in request.headers


class Dashboard(MethodView):
    def get(self):
        result = CoreApi().get_dashboard()

        if result is None:
            return f"Failed to fetch dashboard from: {Config.TARANIS_CORE_URL}", 500

        return render_template("index.html", data=result)
    
# create a users index view

class UsersAPI(MethodView):
    def get(self):
        result = CoreApi().get_users()
        # current_app.logger.info(parsed_result)
        if result:
            # TODO: maybe use dacite https://github.com/konradhalas/dacite
            users = [User(**user) for user in result['items']]
        if result is None:
            return f"Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

        return render_template("users.html", users=users)
    
    
class NewUser(MethodView):
    def get(self):
        result = CoreApi().get_organizations()
        if result:
            organizations = [Organization(**organization) for organization in result['items']]
        if result is None:
            return f"Failed to fetch organizations from: {Config.TARANIS_CORE_URL}", 500
        return render_template("new_user.html", organizations=organizations)

    # def post(self):
    #     data = request.json
    #     result = CoreApi().create_user(data)

    #     if result is None:
    #         return f"Failed to create user at: {Config.TARANIS_CORE_URL}", 500

    #     return jsonify(result)

class OrganizationsAPI(MethodView):
    def get(self):
        result = CoreApi().get_organizations()
        if result:
            organizations = [Organization(**organization) for organization in result['items']]
        if result is None:
            return f"Failed to fetch organizations from: {Config.TARANIS_CORE_URL}", 500

        return render_template("organizations.html", organizations=organizations)
    
class NewOrganization(MethodView):
    def get(self):
        return render_template("new_organization.html")


def init(app: Flask):
    HTMX(app)
    app.url_map.strict_slashes = False
    app.jinja_env.filters["human_readable"] = human_readable_trigger

    admin_bp = Blueprint("admin", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    admin_bp.add_url_rule("/", view_func=Dashboard.as_view("dashboard"))
    admin_bp.add_url_rule("/users/", view_func=UsersAPI.as_view("users"))
    admin_bp.add_url_rule("/users/new", view_func=NewUser.as_view("new_user"))
    admin_bp.add_url_rule("/organizations/", view_func=OrganizationsAPI.as_view("organizations"))
    admin_bp.add_url_rule("/organizations/new", view_func=NewOrganization.as_view("new_organization"))
    # just render the new user form
                    

    app.register_blueprint(admin_bp)
