from flask import Flask, render_template, Blueprint, request, Response
from flask.views import MethodView
from flask_htmx import HTMX
from flask_caching import Cache
from admin.filters import human_readable_trigger
from werkzeug.datastructures import ImmutableMultiDict

from admin.core_api import CoreApi
from admin.config import Config
from pydantic import BaseModel

class TaranisBaseModel(BaseModel):
    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class Address(TaranisBaseModel):
    city: str
    country: str
    street: str
    zip: str

class Organization(TaranisBaseModel):
    _core_endpoint = "/config/organizations"
    id: int
    name: str
    description: str
    address: Address


class Role(TaranisBaseModel):
    _core_endpoint = "/config/roles"
    id: int
    name: str
    description: str
    permissions: list[str]
    tlp_level: int | None = None

class User(TaranisBaseModel):

    _core_endpoint = "/config/users"

    id: int | None = None
    name: str
    organization: Organization | int | dict
    permissions: list[str] | None = None
    profile: dict | None = None
    roles: list[Role] | list[int] | list[dict]
    username: str
    password: str | None = None


class DataPersistenceLayer:

    def __init__(self, jwt_token=None):
        self.jwt_token = jwt_token or self.get_jwt_from_request()
        self.api = CoreApi(jwt_token=self.jwt_token)

    def get_jwt_from_request(self):
        return request.cookies.get(Config.JWT_ACCESS_COOKIE_NAME)
    
    def get_object(self, object_model: any, object_id: int | str):
        if result := self.get_objects(object_model):
            for object in result:
                print(f'{type(object.id)} == {type(object_id)}')
                if object.id == object_id:
                    return object


    def store_object(self, object: any):
        store_object = object.model_dump()
        # hack: remove all key/values that are None or empty
        # store_object = {k: v for k, v in store_object.items() if v is not None and v != ""}
        print(f'Storing object: {store_object}')
        result = self.api.api_post(object._core_endpoint, json_data=store_object)
        print(f'Result: {result}')

    def get_endpoint(self, object_model: any):
        if isinstance(object_model, BaseModel):
            return object_model._core_endpoint
        return object_model._core_endpoint.get_default()

    def get_objects(self, object_model: any):
        # if the object model has a field from another model we need to call ourself recursively to get all the data
        # to test this we will check each field of the object model if any field is an object we will call ourself recursively
        
        endpoint = self.get_endpoint(object_model)
        # print(endpoint)

        result = self.api.api_get(endpoint)

        # for field in object_model.__annotations__:
        #     print(field)
        #     if isinstance(object_model.__annotations__[field], type):
        #         # print("is object")
        #         result[field] = self.get_objects(object_model.__annotations__[field])
        if result:
            return [object_model(**object) for object in result['items']]
        
    def delete_object(self, object_model: any, object_id: int | str):
        endpoint = self.get_endpoint(object_model)
        result = self.api.api_delete(f"{endpoint}/{object_id}")
        return result
    
    def update_object(self, object_model: any, object_id: int | str):
        endpoint = self.get_endpoint(object_model)
        result = self.api.api_put(f"{endpoint}/{object_id}", json_data=object_model.model_dump())
        return result


def is_htmx_request() -> bool:
    return "HX-Request" in request.headers

def parse_formdata(formdata: ImmutableMultiDict):
    parsed_data = {}
    for key in formdata.keys():
        if key.endswith("[]"):
            parsed_data[key[:-2]] = request.form.getlist(key)
        else:
            parsed_data[key] = request.form.get(key)
    return parsed_data


class Dashboard(MethodView):
    def get(self):
        result = CoreApi().get_dashboard()

        if result is None:
            return f"Failed to fetch dashboard from: {Config.TARANIS_CORE_URL}", 500

        return render_template("index.html", data=result)

class RolesAPI(MethodView):
    def get(self):
        result = CoreApi().get_roles()
        if result:
            roles = [Role(**role) for role in result['items']]
        if result is None:
            return f"Failed to fetch roles from: {Config.TARANIS_CORE_URL}", 500

        return render_template("roles.html", roles=roles)

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
    def post(self):
        user = User(**parse_formdata(request.form))
        result = DataPersistenceLayer().store_object(user)
        if result == "error":
            return render_template("new_user.html", organizations=organizations, roles=roles, user=user, error={"globalerror": "This is a global error message"})
        if (user.name == "errortest"):
            return render_template("new_user.html", organizations=organizations, roles=roles, user=user, error={"name": "This is an error message"})
        
        users = DataPersistenceLayer().get_objects(User)
        response =  render_template("users_table.html", users=users)
        return response, 200, {"HX-Refresh":"true"}
    
class UpdateUser(MethodView):
    def put(self,id):

        user = User(**parse_formdata(request.form))
        print(f"sending {parse_formdata(request.form)} to API")
        result = DataPersistenceLayer().update_object(user, id)
        print(f"got result: {result}")
        
        users = DataPersistenceLayer().get_objects(User)
        response = render_template("users_table.html", users=users)
        return response, 200, {"HX-Refresh":"true"}
    
class DeleteUser(MethodView):
    def delete(self, id):
        result = DataPersistenceLayer().delete_object(User, id)
        return "error" if result == "error" else Response(status=200)

  
class NewUser(MethodView):
    def get(self):
        organizations = DataPersistenceLayer().get_objects(Organization)
        roles = DataPersistenceLayer().get_objects(Role)
        return render_template("new_user.html", organizations=organizations, roles=roles, action='new', user=User(name="", username="", organization=1, roles=[]), error={})
    
    

class EditUser(MethodView):
    def get(self, id):
        # orga_result = CoreApi().get_organizations()
        # if orga_result:
        #     organizations = [Organization(**organization) for organization in orga_result['items']]
        # if orga_result is None:
        #     return f"Failed to fetch organizations from: {Config.TARANIS_CORE_URL}", 500
        # roles_result = CoreApi().get_roles()
        # if roles_result:
        #     roles = [Role(**role) for role in roles_result['items']]
        # if roles_result is None:
        #     return f"Failed to fetch roles from: {Config.TARANIS_CORE_URL}", 500
        # # user_id = request.view_args.get("id")
        # result = CoreApi().get_user(id)
        # user=User(**result)
        organizations = DataPersistenceLayer().get_objects(Organization)
        roles = DataPersistenceLayer().get_objects(Role)
        user = DataPersistenceLayer().get_object(User, int(id))
        print(f"{user=}")
        return render_template("edit_user.html", organizations=organizations, roles=roles, user=user)
    
 

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
    cache = Cache(app)
    app.url_map.strict_slashes = False
    app.jinja_env.filters["human_readable"] = human_readable_trigger

    admin_bp = Blueprint("admin", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    admin_bp.add_url_rule("/", view_func=Dashboard.as_view("dashboard"))
    admin_bp.add_url_rule("/users/", view_func=UsersAPI.as_view("users"))
    admin_bp.add_url_rule("/users/new", view_func=NewUser.as_view("new_user"))
    admin_bp.add_url_rule("/users/<id>/edit", view_func=EditUser.as_view("edit_user"))
    admin_bp.add_url_rule("users/<id>", view_func=DeleteUser.as_view("delete_user"), methods=["DELETE"])
    admin_bp.add_url_rule("users/<id>", view_func=UpdateUser.as_view("update_user"), methods=["PUT"])
    admin_bp.add_url_rule("/organizations/", view_func=OrganizationsAPI.as_view("organizations"))
    admin_bp.add_url_rule("/organizations/new", view_func=NewOrganization.as_view("new_organization"))

    app.register_blueprint(admin_bp)
