from nif_tools.session_adapter import get_session_adpter
from bs4 import BeautifulSoup
from nif_tools.common import get_headers
from nif_tools.passbuy import Passbuy
import pandas as pd
from io import StringIO


class SA:
    def __init__(self, username, password, realm='sa', email_recepients=[], ssl_verify=False, debug=False):
        self.username = username
        self.SA_REALM = realm
        self.SA_URL, self.SA_HEADERS = get_headers(realm=realm)
        self.ssl_verify = ssl_verify
        self.debug = debug
        self._login(password)
        self.email_recepients = email_recepients or []

    def _login(self, password):
        pb = Passbuy(username=self.username,
                     password=password,
                     realm=self.SA_REALM,
                     ssl_verify=self.ssl_verify,
                     debug=self.debug)
        status, self.person_id, self.fed_cookie = pb.login()

        if status is not True:
            raise Exception('Could not log in via passbuy')

        self.session = get_session_adpter()
        self.session.headers.update(self.SA_HEADERS)
        self.session.cookies.update(self.fed_cookie)

    def get_realm(self):
        return self.SA_REALM

    def get_url(self):
        return self.SA_URL

    def requests_html(self, url):
        """Gets html page"""

<<<<<<< Updated upstream
        r = self.session.get('{}/{}'.format(self.SA_URL, url))
=======
        r = requests.get('{}{}'.format(self.KA_URL, url),
                         headers=self.KA_HEADERS,
                         cookies=self.fed_cookie,
                         verify=self.ssl_verify)
>>>>>>> Stashed changes

        return r.status_code, r.text

    def get_organization(self, org_id):
        status, html = self.requests_html(f'{self.SA_URL}/Mvc5/Org/Index/{org_id}')
        if status == 200:
            soup = BeautifulSoup(html, 'html.parser')

            # Info labels!
            labels = {}
            for group in soup.select('.info-wrapper'):
                l = [label.text.strip() for label in group.select('.control-label')]
                v = [value.text.strip() for value in group.select('.col-xs-9')]
                if len(l) == len(v):
                    labels.update(dict(zip(l, v)))

            # org logo
            try:
                img = soup.select('#image_upload_preview')[0]
                if img and 'src' in img.attrs:
                    org_logo = img['src'].strip('data:image/png;base64,')
                else:
                    org_logo = None
            except:
                org_logo = None

            # table data
            tables = soup.find_all('table')
            table_list = []
            for t in tables:
                table_list.append(pd.read_html(StringIO(str(t)))[0])

            table_list_dict = []
            for item in table_list:
                table_list_dict.append(item.to_dict('records'))

            return status, {'labels': labels, 'org_logo': org_logo, 'tables': table_list_dict}

        return status, None

    def get_person(self, person_id):
        status, html = self.requests_html(f'/Person/Index/About/{person_id}')
        if status == 200:
            pass

    def verify_person_is_ssn_validated(self, person_id):
        status, html = self.requests_html(f'/Person/Index/About/{person_id}')
        if status == 200:
            dfs = pd.read_html(StringIO(html))

            # It's table index 5:
            for index, row in dfs[5].iterrows():
                try:
                    if "Bekreftet med f" in row[0]:
                        if 'Ja' in row[1]:
                            return True
                        elif 'Nei' in row[1]:
                            return False
                except Exception as e:
                    pass

        return False
