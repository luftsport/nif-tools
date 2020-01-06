# NIF Tools
A set of tools based upon `requests` to programatically interact with the web instances at minidrett, ka and sa.nif.no.

Logging in and retrieving a valid federation cookie is done with the `passbuy` class, and all classes depend upon this.
## Install
```
pip install git+https://github/luftsport/nif-tools
```

## Examples

### Login
```
from nif-tools import passbuy

pb = Passbuy(username='username', password='password', realm='ka', verify=True)
status, person_id, fed_cookie_jar = pb.login()
if status is True:
    print('Person Id:', person_id)
```

