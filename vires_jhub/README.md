# VirES Jupyter Hub Integration.

This is an extension of the [JHub OAuth-2 authenticator](https://github.com/jupyterhub/oauthenticator)
implementing a custom VirES OAuth-2 authenticator.

## Installation

Requirements:
- Python 3.x
- JupyterHub

```
git clone git@github.com:ESA-VirES/VirES-Server.git
pip install VirES-Server/vires_jhub/
```

## Usage

To use the VirES autheticator run the Jupyter Hub with the following command-line option
```
jupyterhub ... --JupyterHub.authenticator_class='vires_jhub.authenticator.ViresOAuthenticator'
  
```
or in case of local accounts
```
jupyterhub ... --JupyterHub.authenticator_class='vires_jhub.authenticator.LocalViresOAuthenticator'
  
```

## Configuration

The authenticator is configured via the following environment variables

| Name | Default | Mandatory | Description |
|:-----|:-------:|:---------:|:------------|
|`VIRES_OAUTH_SERVER_URL`|*none*|yes| client-side base OAuth2 server URL (absolute path accepted, .e.g. `/auth/`)|
|`VIRES_OAUTH_DIRECT_SERVER_URL`|`$VIRES_OAUTH_SERVER_URL`|no| server-side base OAuth2 server URL (full URL including protocol and host-name, can be an internal network URL)|
|`VIRES_CLIENT_ID`|*none*|yes| OAuth2 client id|
|`VIRES_CLIENT_SECRET`|*none*|yes| OAuth2 client secret|
|`VIRES_USER_PERMISSION`|`user`|no|Name of the required bacis user permission.|
|`VIRES_ADMIN_PERMISSION`|`admin`|no|Name of the optional admin permission.|
