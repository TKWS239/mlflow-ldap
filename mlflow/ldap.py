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

ldap_host = os.getenv("LDAP_SERVER" , "example.com")
domain = os.getenv("LDAP_DOMAIN", "example_domain")
ad_group = os.getenv("AD_GROUP", "example_ad")
base_dn = os.getenv("BASE_DN", "dn")
_auth_store = auth_store

def update_user(user_info: dict = None):
    if _auth_store.has_user(user_info["username"]) is False:
        _auth_store.create_user(user_info["username"], user_info["username"], user_info["is_admin"])
    else:
        _auth_store.update_user(user_info["username"], user_info["username"], user_info["is_admin"])


def resolve_user_cn_and_adgroup(ldap_host, domain, base_dn, username, password):
  server = ldap3.Server(ldap_host)
  connection = ldap3.Connection(server, user=f"{username}@{domain}", password=password)
  connection.bind()
  search_filter = f'(sAMAccountName={username})'
  connection.search(base_dn, search_filter, attributes=['cn'])
  if connection.entries:
    entry = connection.entries[0]
    full_name = entry.cn.value
  else:
    message = "User cannot found in the AD"
    return False, message
  cn_filter = f'(cn={full_name})'
  connection.search(base_dn, cn_filter, attributes=['memberOf'])
  ad_group_list = []
  entry = connection.entries[0]
  member_of_groups = entry.memberOf.values
  for group in member_of_groups:
    start_index = group.find("CN=") + 3
    end_index = group.find(",", start_index)
    ad_group = group[start_index:end_index]
    ad_group_list.append(ad_group)
  connection.unbind()
  return True, ad_group_list


def ldap_auth(ldap_host, domain, base_dn, ad_group, username, password):
    mlflow_ad_group = ad_group
    user_exist, ad_group_list = resolve_user_cn_and_adgroup(ldap_host, domain, base_dn, username, password)
    if user_exist:
        if mlflow_ad_group in ad_group_list:
            return True
        else:
            return False
    else:
        return False


def authenticate_request() -> Union[Authorization, Response]:
  user_info = dict()
  resp = make_response()

  if request.authorization is None:
    resp.status_code = 401
    resp.set_data("You are not authenticated. Please enter your username and password \n Make sure you have been added to the ad group. \n For details, submit jira ticket to DSL Team")
    resp.headers["WWW-Authenticate"] = 'Basic realm="mlflow"'
    return resp

  username = request.authorization.username
  password = request.authorization.password

  if username or password is not None:
      user_info["username"] = username
      user_info["is_admin"] = False
      if username == "admin":
        return request.authorization
      if ldap_auth(ldap_host, domain, base_dn, ad_group, username, password):
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
