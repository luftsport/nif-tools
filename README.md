# NIF Tools
A set of tools based upon `requests` to programatically interact with the web instances at minidrett, ka and sa.nif.no.

Logging in and retrieving a valid federation cookie is done with the `passbuy` class, and all classes depend upon this.
## Install
```
pip install git+https://github.com/luftsport/nif-tools
```

## Examples

### Login
```
from nif_tools import Passbuy

pb = Passbuy(username='username', password='password', realm='ka', verify=True)
status, person_id, fed_cookie_jar = pb.login()
if status is True:
    print('Person Id:', person_id)
```

## Build documentation

The documentation is built with sphinx `sphinx-build -b html docs-source docs` which builds the documentation from docs-source to docs. Docs folder is for local viewing.

To build documentation for a release, use `make gh-pages` which will build and commit the documentation to the projects gh-pages.
