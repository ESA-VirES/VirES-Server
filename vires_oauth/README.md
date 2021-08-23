# VirES OAuth2 server.

Django-based User identity provider and OAuth-2 authorization server.
The package marries the
[Django OAuth Toolkit](https://github.com/jazzband/django-oauth-toolkit/) for the OAuth2 provisioning and
[Django Allauth](https://github.com/pennersr/django-allauth/) for the social network authentication.


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

For the numerous possible Allauth options see the [package documentation](https://django-allauth.readthedocs.io/en/latest/installation.html)

An optional default user groups can set by the `VIRES_OAUTH_DEFAULT_GROUPS`
```
VIRES_OAUTH_DEFAULT_GROUPS = ["default"]
```

## Management CLI

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

- [Users](#users)
- [E-mails](#e-mails)
- [Groups](#groups)
- [Permissions](#permissions)
- [Apps](#apps)
- [Social Providers](#social-providers)
- [Site](#site)

### Users

#### List

The usernames of the existing users can be listed by the `list` command:
```
$ <instance>/manage.py user list
```

By default, all users are listed. The listed users can be restricted by the following options:

| Option | Description |
|:---|:---|
| `--active` | select only active users |
| `--inactive` | select only inactive users |
| `--no-login` | select users who never logged in |
| `--no-login` | select users who never logged in |
| `--verified-primary-email` | select users with verified primary e-mail address |
| `--not-verified-primary-email` | select users with non-verified primary e-mail address |
| `--verified-email ANY\|ALL` | select users with ANY\|ALL verified primary e-mail address(es) |
| `--not-verified-email ANY\|ALL` | select users with ANY\|ALL non-verified primary e-mail address(es) |
| `--last-login-before <time-spec>`| select users who logged in last time before the given time, accepting ISO-8601 timestamps or duration relative to the current time |
| `--last-login-after <time-spec>`| select users who logged in last time after the given specification, accepting ISO-8601 timestamps or duration relative to the current time |
| `--joined-before <time-spec>`| select users whose account was created before the given time, accepting ISO-8601 timestamps or duration relative to the current time |
| `--joined-after <time-spec>`| select users whose account was created after the given time, accepting ISO-8601 timestamps or duration relative to the current time |

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

The deactivation causes immediate blocking of new requests to the identity
service and termination of the active sessions.

The access can be enabled by the `activate` command
```
$ <instance>/manage.py user activate <username> ...
```

All accounts can be activated/deactivated by the `--all` option
```
$ <instance>/manage.py user deactivate --all
$ <instance>/manage.py user activate --all
```


#### Set/Unset User Group

One or more users can be added to one or more user groups by the `set_group`
command
```
$ <instance>/manage.py user set_group -g <group> -g <group> <username>  ...
```

Alternatively one or more users can removed from one or more user groups by the
`unset_group` command
```
$ <instance>/manage.py user unset_group -g <group> -g <group> <username>  ...
```

The `set_group`/`unset_group` commands accept the `--all` and other user
selectors listed for the [`list` command](#list)

### E-mails

#### List E-mails

The e-mail address and their owners can be listed by the `list` command
```
$ <instance>/manage.py email list
john.doe/john.doe@foobar.com VERIFIED PRIMARY
...
```
The list appends additional text labels for `VERIFIED` and `PRIMARY`
e-mail addresses.

The listed e-mail addresses can be selected by specifying the e-mail address
```
$ <instance>/manage.py email list john.doe@foobar.com
john.doe/john.doe@foobar.com VERIFIED PRIMARY
```
or by using these selectors

| Option | Description |
|:---|:---|
| `--primary` | select primary e-mail addresses |
| `--not-primary` | select non-primary e-mail addresses |
| `--verified` | select verified e-mail addresses |
| `--not-verified` | select non-verified e-mail addresses |

#### Send Confirmation E-mails

A confirmation e-mail to one or more non-verified e-mail addresses can be sent
by the `send_confirmation` command
```
$ <instance>/manage.py email send_confirmation <e-mail> ...
```

The `send_confirmation` command refuses to send a confirmation e-mail to
an already verified e-mail address.

```
$ <instance>/manage.py email send_confirmation john.doe@foobar.com
INFO: confirmation email sent to martin.paces@gmail.com/martin.paces@gmail.com
```


To send the confirmation e-mail to all non-verified e-mail addresses use
the `--all` and `--not-verified` options
```
$ <instance>/manage.py email send_confirmation --all --not-verified
```

#### Verify E-mail Address

Normally, the e-mail address is verified by the user responding via the
HTTP link sent in the confirmation e-mail.

Under special circumstances, the e-mail address may be verified
manually by the administrator
```
$ <instance>/manage.py email verify <e-mail> ...
```

### Groups

User groups in VirES identity server are used as a link between
the [users](#users) and their [permissions](#permissions).

A group consists of these attributes

| Attribute | Description |
|:---|:---|
| `name` | name of the user group |
| `title` | simple human-readable description of the user group |
| `permissions` | list of [permission names](#permissions) granted to members of the user group |

The groups can be imported from or exported to a JSON file.

#### Export

One or more user groups can be exported in JSON format by the `export` command, e.g.:
```
$ <instance>/manage.py group export [<group> ...]
```

If no group name is specified, all user groups are exported.
```
$ <instance>/manage.py group export > vires_groups.json
```

#### Import

The group `import` command is used to import new user groups and update
the existing ones
```
$ <instance>/manage.py group import < vires_groups.json
```

The `--default` option loads the set of default Swarm user groups
```
$ <instance>/manage.py group import --default
```

Note that it is recommended to import new permissions before the users groups
which make use of them.

### Permissions

User permission in VirES identity granted to the [users](#users)
via their membership in one or more [user groups](#groups).

The permissions are simple text labels. The meaning of these labels depends
of the interpretation of these labels by the apps(s).

A group consists of these attributes

| Attribute | Description |
|:---|:---|
| `name` | name of the permission (the label) |
| `description` | simple human-readable description of the permission |

The permissions can be imported from or exported to a JSON file.

#### Export

One or more permissions can be exported in JSON format by the `export` command, e.g.:
```
$ <instance>/manage.py permission export [<permission> ...]
```

If no permission name is specified, all user permission are exported.
```
$ <instance>/manage.py permission export > vires_permissions.json
```

#### Import

The permission `import` command is used to import new user permissions and update
the existing ones
```
$ <instance>/manage.py permission import < vires_permissions.json
```

The `--default` option loads the set of default Swarm user permissions
```
$ <instance>/manage.py permission import --default
```

Note that it is recommended to import new permissions before the users groups
which make use of them.


### Apps

The VirES identity server implements the OAuth2 protocol. Namely the client
Apps can be allowed to the user profiles.

An OAuth2 app specification consists of these attributes

| Attribute | Description |
|:---|:---|
| `name` | name of the app |
| `owner` | username of owner or `null` |
| `client_type` | `confidential` \| `public` |
| `authorization_grant_type` | `authorization-code` \| `implicit` \| `password` \| `client-credentials` |
| `skip_authorization` | boolean flag (`false` \| `true`) indicating whether the access authorization should be requested |
| `client_id` | client identifier |
| `client_secret` | client secret |
| `redirect_uris` | a list of callback (redirect) URIs |

For description of the meaning of the `client_type` and `authorization_grant_type`
see the [OAuth 2.0 specification](https://oauth.net/2/)

#### Export

One or more apps can be exported in JSON format by the `export` command, e.g.:
```
$ <instance>/manage.py app export [<app> ...]
```

The apps are selected either by the client id or the app name.

If no app is specified, all user apps are exported.
```
$ <instance>/manage.py app export > vires_apps.json
```

#### Import

The apps `import` command is used to import new apps and update
the existing ones
```
$ <instance>/manage.py apps import < vires_apps.json
```

### Social Providers

A social provider specification consists of these attributes

| Attribute | Description |
|:---|:---|
| `provider` | identifier of the provider |
| `name` | name of the provider |
| `client_id` | client identifier |
| `secret` | client secret |
| `key` | additional key, set to a blank string if not used |

Note the social providers needs to be configured in the `settings.py`
`INSTALLED_APPS`.

#### Export

One or more registered social providers can be exported in JSON format by the `export` command, e.g.:
```
$ <instance>/manage.py social_provider export <provider> ...
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

### Site

#### Show Site
The currently applied Django site configuration can be displayed by the `show`
command
```
$ <instance>/manage.py site show
site name:   <site-name>
site domain: <site-domain>
```

#### Set Site
The site is configured by the `set` command
```
$ <instance>/manage.py site set -n <site-name> -d <site-domain>
```
