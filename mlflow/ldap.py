import os
import ldap3
from typing import Union
from flask import Response, make_response, request
from mlflow.server.auth import store as auth_store
from werkzeug.datastructures import Authorization

LDAP_HOST = os.getenv("LDAP_SERVER", "example.com")
DOMAIN = os.getenv("LDAP_DOMAIN", "example_domain")
USER_AD_GROUP = os.getenv("USER_AD_GROUP", "example_user_ad")
ADMIN_AD_GROUP = os.getenv("ADMIN_AD_GROUP", "example_admin_ad")
BASE_DN = os.getenv("BASE_DN", "dn")

_auth_store = auth_store

def update_db_user(user_info: dict):
    """
    Update or create a user in the auth store.
    Logic: Create users if the record does not exist.
    """
    username = user_info["username"]
    is_admin = user_info["is_admin"]

    if not _auth_store.has_user(username):
        _auth_store.create_user(username, username, is_admin)
    else:
        _auth_store.update_user(username, username, is_admin)

def resolve_user_cn_and_adgroup(ldap_host, domain, base_dn, username, password):
    """
    Resolve user common name and AD group membership.
    Fetch the list of AD groups that the user belongs to.
    """
    server = ldap3.Server(ldap_host)
    connection = ldap3.Connection(server, user=f"{username}@{domain}", password=password)
    connection.bind()

    # Search for the user by sAMAccountName
    search_filter = f'(sAMAccountName={username})'
    connection.search(base_dn, search_filter, attributes=['cn'])

    if not connection.entries:
        return False, "User cannot be found in the AD"

    entry = connection.entries[0]
    full_name = entry.cn.value

    # Search for the user's AD group memberships
    cn_filter = f'(cn={full_name})'
    connection.search(base_dn, cn_filter, attributes=['memberOf'])

    ad_group_list = [
        group[group.find("CN=") + 3:group.find(",", group.find("CN=") + 3)]
        for group in connection.entries[0].memberOf.values
    ]

    connection.unbind()
    return True, ad_group_list

def ldap_auth(ldap_host, domain, base_dn, user_ad_group, admin_ad_group, username, password):
    """
    Authenticate the user with LDAP.
    Determine if the user is an admin or a normal user based on AD group membership.
    """
    user_exist, ad_group_list = resolve_user_cn_and_adgroup(ldap_host, domain, base_dn, username, password)
    if user_exist:
        if admin_ad_group in ad_group_list:
            return True, True
        if user_ad_group in ad_group_list:
            return True, False
    return False, False

def authenticate_request() -> Union[Authorization, Response]:
    """
    Using for the basic.ini as auth function
    Authenticate the incoming request.
    Grant the admin role if the user is in the admin AD group; otherwise, grant normal user access.
    """
    user_info = {}
    resp = make_response()

    if request.authorization is None:
        message = "Your login has been cancelled"
        return _unauthorized_response(resp, message)
      
    if not request.authorization.username or not request.authorization.password:
        message = "Username or password cannot be empty."
        return _unauthorized_response(resp, message)
    else:
        username = request.authorization.username
        password = request.authorization.password

        user_info["username"] = username
        authenticated, is_admin = ldap_auth(
            LDAP_HOST, DOMAIN, BASE_DN, USER_AD_GROUP, ADMIN_AD_GROUP, username, password
        )
        if authenticated:
            user_info["is_admin"] = is_admin
            update_db_user(user_info)
            return request.authorization
        else:
            return _unauthorized_response(resp, "Please ensure you are included in the AD group and input correct credentials!")

def _unauthorized_response(resp, message="You are not authenticated. Please enter your username and password."):
    """Return an unauthorized response with a custom message."""
    resp.status_code = 401
    resp.set_data(message)
    resp.headers["WWW-Authenticate"] = 'Basic realm="mlflow"'
    return resp
