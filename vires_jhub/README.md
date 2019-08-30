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

The authenticator can be configured via the following environment variables or class configuration options (`c.ViresOAuthenticator.*`)

| Environment Variable | Class Configuration | Default | Description |
|:-----|:-------|:---------:|:------------|
|`VIRES_OAUTH_SERVER_URL`|`server_url`|*blank*| client-side base OAuth2 server URL (absolute path accepted, .e.g. `/auth/`)|
|`VIRES_OAUTH_DIRECT_SERVER_URL`|`direct_server_url`|defaults to `server_url`| optional server-side base OAuth2 server URL (full URL including protocol and host-name, can be an internal network URL)|
|`VIRES_CLIENT_ID`|`client_is`|*none*| OAuth2 client identifier|
|`VIRES_CLIENT_SECRET`|`client_secret`|*none*| OAuth2 client secret|
|`VIRES_USER_PERMISSION`|`user_permission`|`user`| Name of the required basic user permission.|
|`VIRES_ADMIN_PERMISSION`|`admin_permission`|`admin`| Name of the optional administrator permission.|
