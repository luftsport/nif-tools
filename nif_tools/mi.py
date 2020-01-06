import requests
from nif_tools.passbuy import Passbuy
from nif_tools.common import get_headers


class MI:

    def __init__(self, username, password, realm='mi'):
        self.username = username
        self.KA_REALM = realm
        self.KA_URL, self.KA_HEADERS = get_headers(realm=realm)

        pb = Passbuy(username=username,
                     password=password,
                     realm=self.KA_REALM)
        status, self.person_id, self.fed_cookie = pb.login()

        if status is not True:
            raise Exception('Could not log in via passbuy')

    def get_person_id(self):

        if self.person_id is None:

            profile = requests.get(url='https://minidrett.nif.no/MyProfile/Profiles',
                                   cookies=self.fed_cookie,
                                   allow_redirects=False
                                   )

            if profile.status_code == 200:
                try:
                    self.person_id = int(profile.text.split('onclick="javaScript:DownloadCV(')[1].split(');"')[0])
                except:
                    self.person_id = None

        return True if self.person_id is not None else False, self.person_id
