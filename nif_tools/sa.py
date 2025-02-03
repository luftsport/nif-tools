
from bs4 import BeautifulSoup
import requests
from nif_tools.common import get_headers
from nif_tools.passbuy import Passbuy
import pandas as pd
from io import StringIO

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class SA:
    def __init__(self, username, password, realm='sa', email_recepients=[], ssl_verify=False):
        self.username = username
        self.KA_REALM = realm
        self.KA_URL, self.KA_HEADERS = get_headers(realm=realm)
        self.ssl_verify = ssl_verify

        pb = Passbuy(username=username,
                     password=password,
                     realm=self.KA_REALM,
                     ssl_verify=self.ssl_verify)
        status, self.person_id, self.fed_cookie = pb.login()

        if status is not True:
            raise Exception('Could not log in via passbuy')

        self.email_recepients = email_recepients

    def get_realm(self):
        return self.KA_REALM

    def get_url(self):
        return self.KA_URL

    def requests_html(self, url):
        """Gets html page"""

        r = requests.get('{}/{}'.format(self.KA_URL, url),
                         headers=self.KA_HEADERS,
                         cookies=self.fed_cookie,
                         verify=self.ssl_verify)

        return r.status_code, r.text


    def get_organization(self, org_id):
        status, html = self.requests_html(f'/Mvc5/Org/Index/{org_id}')
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