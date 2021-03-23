# `eoxs-allauth`

`eoxs-allauth` is a [Django](https://www.djangoproject.com/) app used as an authentication and authorization layer above the VirES-Server data server and/or [EOxServer](https://github.com/EOxServer/eoxserver) in general.
It based on the [`django-allauth`](http://www.intenct.nl/projects/django-allauth) authentication package.


## Configuration

### URLs

The authentication layer is added to an API view via the `wrap_protected_api` wrapper (can be also used as a decorator). The landing page is added via the `workspace` view in the `urls.py`:
```
from eoxs_allauth.views import wrap_protected_api, workspace
from your_app.views import api

urlpatterns = [
    ...
    url(r'^$', workspace(parse_client_state), name="workspace"),
    url(r'^api$', wrap_protected_api(api)),
    ...
]
```


### Applications

These are the required Django application settings (defined in this order) in the `settings.py`:
```
INSTALLED_APPS = [
    ...
    'eoxs_allauth',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'eoxs_allauth.vires_oauth', # VirES-OAuth2 "social account provider"
    'django_countries',
    ...
]
```


### Middlewares

The defines following Django middlewares which should be set in the `settings.py`:
```
MIDDLEWARE = [
    ...
    'eoxs_allauth.middleware.inactive_user_logout_middleware',
    'eoxs_allauth.middleware.access_logging_middleware',
    ...
]
```


### Logging

Beside the regular Django logging, the *access logging middleware* logs messages with additional information about the authenticated users and remote IP address using the `access.*` loggers. The logging setting may look like:
```
LOGGING = {
    'version': 1,
    ...
    'formatters': {
        'default_format': {
            'format': '%(asctime)s.%(msecs)03d %(name)s %(levelname)s: %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
        'access_format': {
            'format': '%(asctime)s.%(msecs)03d %(remote_addr)s %(username)s %(name)s %(levelname)s: %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
        ...
    },
    'handlers': {
        'server_log': {
            ...
            'formatter': 'default_format',
        },
        'access_log': {
            ...
            'formatter': 'access_format',
        },
        ...
    }
    'loggers': {
        'access': {
            'handlers': ['access_log'],
            'propagate': False,
            ...

        },
        'eoxs_allauth': {
            'handlers': ['server_log'],
            'propagate': False,
            ...
        },
        ...
        '': {
            'handlers': ['server_log'],
            ...
        },
    }
```


### VirES-Oauth specific setting

This is the `settings.py` configuration of VirES-OAuth server *social account provider* when deployed on a separate machine:
```
SOCIALACCOUNT_PROVIDERS = {
    'vires': {
        'SERVER_URL': 'https://<host>/<path>'
        'SCOPE': ['read_id', 'read_permissions'],
        'PERMISSION': '<required-permission>',
    },
}
```

This is the configuration of VirES-OAuth server *social account provider* when deployed on the same machine behind a reverse proxy:
```
SOCIALACCOUNT_PROVIDERS = {
    'vires': {
        'SERVER_URL': '/<path>'                      # URL used in the HTML
        'DIRECT_SERVER_URL': 'https://<host>:<port>' # URL used by the server
        'SCOPE': ['read_id', 'read_permissions'],
        'PERMISSION': '<required-permission>',
    },
}
```


### Other options

These are additional `settings.py` configuration options used by this Django app:

`WORKSPACE_TEMPLATE` - Custom workspace (landing page) template location.

`PROFILE_UPDATE_TEMPLATE` - Custom profile update template location.

`PROFILE_UPDATE_SUCCESS_URL` - URL to be displayed by a successful profile update.

`PROFILE_UPDATE_SUCCESS_MESSAGE` - Message to be displayed after successful profile update.



## Managment CLI

The content of the server is managed vi the Django `manage.py` command.

The available commands can be listed by
```
$ <instance>/manage.py --help
...
[eoxs_allauth]
    social_provider
    user
...
```

These commands and their options are described in the following sections:

- [User](#users)
- [Social Providers](#social-providers)



### Users

#### List

The usernames of the existing users can be listed by the `list` command:
```
$ <instance>/manage.py user list
```

By default, all users are listed. The listed users can be restricted by the following options:

| Option | Description |
|:---|:---|
| `--active` | list only active users |
| `--inactive` | list only inactive users |
| `--no-login` | list users who never logged in |
| `--last-login-before <time-spec>`| list users who logged in last time before the given time, accepting ISO-8601 timestamps or duration relative to the current time |
| `--last-login-after <time-spec>`| list users who logged in last time after the given specification, accepting ISO-8601 timestamps or duration relative to the current time |
| `--joined-before <time-spec>`| list users whose account was created before the given time, accepting ISO-8601 timestamps or duration relative to the current time |
| `--joined-after <time-spec>`| list users whose account was created after the given time, accepting ISO-8601 timestamps or duration relative to the current time |

```
$ <instance>/manage.py user list --active --last-login-after=-PT24H --joined-before=2018-01-01
```


#### Export

The full user profiles of one or more users the existing users can be exported in JSON format by the `export` command:
```
$ <instance>/manage.py user export <username> ...
```

If no product identifier is specified all users are exported:
```
$ <instance>/manage.py user export > users.json
```

The exported users can be restricted by the same options as the `list` command:
```
$ <instance>/manage.py user export --active --last-login-after=-PT24H --joined-before=2018-01-01
```


#### Import

The users exported by the `export` command can be imported by the `import` command:
```
$ <instance>/manage.py user import < users.json
```


#### Activate/Deactivate

One or more user accounts can be deactivated (access denial) by the `deactivate` command
```
$ <instance>/manage.py user deactivate <username> ...
```

The deactivation causes immediate blocking of new requests and termination of the active sessions.

The access can be enabled by the `activate` command
```
$ <instance>/manage.py user activate <username> ...
```

All accounts can be activated/deactivated by the `--all` option
```
$ <instance>/manage.py user deactivate --all
$ <instance>/manage.py user activate --all
```


#### Connecting Existing Users to the VirES-Oauth Server

When migrating from a local database to the VirES-Outh setup without removing the existing users the users have to be connected to the VirES-Oauth provider while the other details, social providers and personal data have to be cleared.

This one-off action can be performed by the `connect_to_vires_oauth` command:
```
$ <instance>/manage.py user connect_to_vires_oauth --all
```


### Social Providers

#### Export

One or more registered social providers can be exported in JSON format by the `export` command, e.g.:
```
$ <instance>/manage.py social_provider export vires
[
  {
    "provider": "vires",
    "name": "VirES",
    "client_id": "<hash>",
    "secret": "<hash>",
    "key": ""
  }
]
```

If no provider name is specified all providers are exported:
```
$ <instance>/manage.py social_provider export > social_providers.json

```


#### Import

The social providers exported by the `export` command can be imported by the `import` command:
```
$ <instance>/manage.py social_provider import < social_providers.json
```