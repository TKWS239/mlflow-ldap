import os
import sys
import logging
import uuid
import ldap3
import requests
from typing import Union

from flask import Response, make_response, session, request, url_for
from mlflow.server.auth import store as auth_store

from werkzeug.datastructures import Authorization

ldap_host = os.getenv("ldap_server" , "xxxx.com")
domain = os.getenv("domain", "domain")
_auth_store = auth_store

def update_user(user_info: dict = None):
    if _auth_store.has_user(user_info["username"]) is False:
        _auth_store.create_user(user_info["username"], user_info["username"], user_info["is_admin"])
    else:
        _auth_store.update_user(user_info["username"], user_info["username"], user_info["is_admin"])

def ldap_auth(ldap_host, domain, username, password):
    # Please add your custom ad logic here
    # For the AD group integration, please dm to me if you interested.
    server = ldap3.Server(ldap_host)
    connection = ldap3.Connection(server, user=f"{username}@{domain}", password=password)

    if connection.bind():
        result = connection.result
        logging.info('LDAP authentication successful for user: %s', username)
        logging.debug('LDAP connection result: %s', result)
        # unbind for preventing connection pool limit
        connection.unbind()
        return True
    else:
        return False

def authenticate_request() -> Union[Authorization, Response]:
  user_info = dict()
  resp = make_response()

  if request.authorization is None:
    resp.status_code = 401
    resp.set_data("You are not authenticated. Please enter your username and password \n Make sure you have been added to our active directory.")
    resp.headers["WWW-Authenticate"] = 'Basic realm="mlflow"'
    return resp

  username = request.authorization.username
  password = request.authorization.password

  if username or password is not None:
      user_info["username"] = username
      user_info["is_admin"] = False
      if ldap_auth(ldap_host, domain, username, password):
        update_user(user_info)
        return request.authorization
      else:
        resp.status_code = 401
        resp.set_data("You are not authenticated. Please make sure u are included in the AD group and input a correct credentials")
        resp.headers["WWW-Authenticate"] = 'Basic realm="mlflow"'
        return resp
  else:
    resp.status_code = 401
    resp.set_data("You are not authenticated. Please enter your username and password with the request")
    resp.headers["WWW-Authenticate"] = 'Basic realm="mlflow"'
  return resp