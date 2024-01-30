# MLFlow Basic Authentication and Server Setup

This README provides guidance on setting up basic authentication for MLFlow using LDAP and starting the MLFlow server with the necessary configurations.

## Configuration File: `basic_auth.ini`

This file configures the basic authentication for MLFlow. The settings include:

- Default permissions
- Database URI for authentication
- Admin credentials
- LDAP authentication function

### basic_auth.ini example:

```ini
[mlflow]
default_permission = NO_PERMISSION
database_uri = sqlite:///basic_auth.db
admin_username = admin
admin_password = password
authorization_function = mlflow.ldap:ldap_auth
```

### Server Startup Instructions

Step 0: Git clone and replace the files to your local directory.

Step 1: install MLFlow

Install the offical MLFlow (2.10.0 as example):

```bash
pip install mlflow==2.10.0
pip install ldap3
```

Step 2: Set Environment Variables
Configure the environment variables for LDAP and logging:

```bash
# Replace the file to the source code
mv /server/__init__.py  /usr/local/lib/python3.10/site-packages/mlflow/server/__init__.py && \
mv /utils/logging_utils.py /usr/local/lib/python3.10/site-packages/mlflow/utils/logging_utils.py && \
mv /mlflow/ldap_auth.py /usr/local/lib/python3.10/site-packages/mlflow/ldap_auth.py
export MLFLOW_AUTH_CONFIG_PATH=$BASE_DIR/basic_auth.ini
export ldap_host=your_ldap_server_address
export domain=your_ad_domain
export log_file=your_log_file_name   # Example: /usr/local/etc/audit.log
```

Replace your_ldap_server_address, your_ad_domain, and your_log_file_name with your actual LDAP server address, Active Directory domain, and desired log file name.

Step 3: Start MLFlow Server

Use the following command to start the MLFlow server:

```bash
mlflow server --dev --serve-artifacts --app-name basic-auth --host 0.0.0.0 --port 8000 --artifacts-destination <URI>
```

Replace <URI> with your artifacts destination URI.




