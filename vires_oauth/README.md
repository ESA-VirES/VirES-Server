# VirES OAuth2 server.

Django-based User identity provider and OAuth-2 authorization server.
The package marries the 
[Django OAuth Toolkit](https://github.com/jazzband/django-oauth-toolkit/) for the OAuth2 provisioning and 
[Django Allauth](https://github.com/pennersr/django-allauth/) for the social network authetication.


## Installation

Requirements:

- Python >= 3.4
- Django >= 2.0
- [Django OAuth Toolkit](https://github.com/jazzband/django-oauth-toolkit/)
- [Django Allauth](https://github.com/pennersr/django-allauth/)
- [Django Countries](https://github.com/SmileyChris/django-countries/)

```
git clone git@github.com:ESA-VirES/VirES-Server.git
pip install VirES-Server/vires_jhub/
```

## Settings

Beside the `vires_oauth`, Django sites, Allauth and OAuth toolkit has to be installed:
```
INSTALLED_APPS = [
    ...
    'django.contrib.sites',
    'vires_oauth',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.<provider>', # individual social account providers
    'django_countries',
    'oauth2_provider',
    ...
]
```

Following middlewares are provided by the package and are recommended to be applied.

```
MIDDLEWARE += [
    ...
    'vires_oauth.middleware.access_logging_middleware',
    'vires_oauth.middleware.inactive_user_logout_middleware',
    'vires_oauth.middleware.oauth_user_permissions_middleware',
    ....
]
```

Recommended OAuth Toolkit] settings
```
OAUTH2_PROVIDER = {
    'SCOPES_BACKEND_CLASS': 'vires_oauth.scopes.ViresScopes',
    'ALLOWED_REDIRECT_URI_SCHEMES': ['https'],
}
```

For the numerour possible Allauth options see the [package documentation](https://django-allauth.readthedocs.io/en/latest/installation.html)

An optional default user groups can set by the `VIRES_OAUTH_DEFAULT_GROUPS`
```
VIRES_OAUTH_DEFAULT_GROUPS = ["default"]
```
