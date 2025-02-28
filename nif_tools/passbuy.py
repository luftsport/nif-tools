import requests
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class MaintenanceError(Error):
    pass


class InputError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class Passbuy:
    nif_jar = None
    bp_jar = None
    person_id = None
    code = None

    def __init__(self, username, password, realm='minidrett', verify=True, ssl_verify=False):

        self.username = username
        self.password = password
        self.realm = realm
        self.person_id = None
        self.ssl_verify = ssl_verify

        if realm in ['mi', 'minidrett']:
            self.realm = 'minidrett'
            self.login_page = 'Login'
        elif realm in ['ka', 'klubbadmin']:
            self.realm = 'ka'
            self.login_page = 'Home/Login'
        elif realm in ['sa', 'sportsadmin']:
            self.realm = 'sa'
            self.login_page = ''
        else:
            self.login_page = ''

        # Simple logic to verify not maintance
        if verify:
            if self.is_maintanance():
                raise MaintenanceError('{} is down for maintance'.format(self.realm))

    def is_maintanance(self):
        """Check if maintanance mode

        NIF web (KA/MI/SA) gives normal http 200, need to check title
        Also: re.search('(?<=<title>).+?(?=</title>)', mytext, re.DOTALL).group().strip()

        :returns boolean is_maintanance:
        """

        r = requests.get('https://{}.nif.no'.format(self.realm), verify=self.ssl_verify)

        if r.status_code == 503:
            return True

        elif r.status_code == 200:
            html = BeautifulSoup(r.text, 'lxml')
            if html.title.text.strip() == 'Vedlikehold':
                return True
            elif html.title.text.strip().startswith('Release'):
                return True

        return False

    def login(self):
        return self.minidrett()

    def nif_realm(self):

        r = requests.get('https://{}.nif.no/'.format(self.realm), verify=self.ssl_verify)

        self.nif_jar = r.cookies

        # Login page
        resp = requests.get('https://{}.nif.no/{}'.format(self.realm, self.login_page),
                            cookies=self.nif_jar,
                            allow_redirects=False,
                            verify=self.ssl_verify)
        self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, resp.cookies)

        if resp.status_code == 302:

            # id.nif.no/connect/authorize
            r1 = requests.get(resp.headers.get('Location', ''),
                              cookies=self.nif_jar,
                              allow_redirects=False)
            self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, r1.cookies)

            if r1.status_code == 302:

                # id.nif.no/Account/Login
                r2 = requests.get(r1.headers.get('Location', ''),
                                  cookies=self.nif_jar,
                                  allow_redirects=False)
                cookiejar = requests.cookies.merge_cookies(self.nif_jar, r2.cookies)

                if r2.status_code == 302:

                    # id.nif.no/ExternalLogin/Challenge
                    r3 = requests.get('https://id.nif.no{}'.format(r2.headers.get('Location', '')),
                                      cookies=self.nif_jar,
                                      allow_redirects=False,
                                      verify=self.ssl_verify)
                    self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, r3.cookies)
                    return True, r3

        return False, None

    def buypass(self):
        """Returns
        login url
        challenge
        """

        status, mi = self.nif_realm()

        if status is True:

            # auth.nif.buypass.no/auth/realms/nif/protocol/openid-connect/auth
            r = requests.get(mi.headers.get('Location', ''),
                             allow_redirects=False,
                             verify=self.ssl_verify)

            if r.status_code == 200:
                self.bp_jar = r.cookies
                bp_html = BeautifulSoup(r.text, 'lxml')
                login_url = bp_html.find('form', attrs={'class': 'nif-login-form'}).get_attribute_list('action')[0]
                challenge = bp_html.find('input', attrs={'name': 'challenge'}).get_attribute_list('value')[0]

                # Login 1
                login1 = requests.post(url=login_url, data={'challenge': challenge,
                                                           'username': self.username,
                                                           'rememberMe': 'off',
                                                           'origin_url': '',
                                                           'authMethod': ''},
                                      cookies=self.bp_jar,
                                      allow_redirects=False,
                                      verify=self.ssl_verify)
                if login1.status_code == 200:
                    self.bp_jar = requests.cookies.merge_cookies(self.bp_jar, login1.cookies)

                    bp2_html = BeautifulSoup(login1.text, 'lxml')
                    login_url2 = bp2_html.find('form', attrs={'class': 'nif-login-form'}).get_attribute_list('action')[0]
                    challenge2 = bp2_html.find('input', attrs={'name': 'challenge'}).get_attribute_list('value')[0]

                    # Login 1
                    login2 = requests.post(url=login_url2, data={'challenge': challenge2,
                                                                'password': self.password,
                                                                'rememberMe': 'off',
                                                                'origin_url': '',
                                                                'authMethod': ''},
                                           cookies=self.bp_jar,
                                           allow_redirects=False,
                                           verify=self.ssl_verify)
                    if login2.status_code == 200:
                        self.bp_jar = requests.cookies.merge_cookies(self.bp_jar, login2.cookies)

                        return True, login2

        return False, None

    def nif_id(self):

        status, buypass = self.buypass()

        if status is True:
            bp_html = BeautifulSoup(buypass.text, 'lxml')
            login_url = bp_html.find('form').get_attribute_list('action')[0]
            self.code = bp_html.find('input', attrs={'name': 'code'}).get_attribute_list('value')[0]
            state = bp_html.find('input', attrs={'name': 'state'}).get_attribute_list('value')[0]
            session_state = bp_html.find('input', attrs={'name': 'session_state'}).get_attribute_list('value')[0]

            resp = requests.post(url=login_url,
                                 data={'code': self.code,
                                       'state': state,
                                       'session_state': session_state},
                                 cookies=self.nif_jar,
                                 allow_redirects=False,
                                 verify=self.ssl_verify)

            if resp.status_code == 302:
                self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, resp.cookies)

                callback = requests.get(url='https://id.nif.no{}'.format(resp.headers.get('Location', '')),
                                        cookies=self.nif_jar,
                                        allow_redirects=False,
                                        verify=self.ssl_verify)
                                        

                if callback.status_code == 302:
                    self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, callback.cookies)

                    connect = requests.get(url='https://id.nif.no{}'.format(callback.headers.get('Location', '')),
                                           cookies=self.nif_jar,
                                           allow_redirects=False,
                                           verify=self.ssl_verify)
                    if connect.status_code == 200:
                        self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, connect.cookies)

                        mi_html = BeautifulSoup(connect.text, 'lxml')
                        id_url = mi_html.find('form').get_attribute_list('action')[0]
                        id_token = mi_html.find('input', attrs={'name': 'id_token'}).get_attribute_list('value')[0]
                        scope = mi_html.find('input', attrs={'name': 'scope'}).get_attribute_list('value')[0]
                        state = mi_html.find('input', attrs={'name': 'state'}).get_attribute_list('value')[0]
                        session_state =  mi_html.find('input', attrs={'name': 'session_state'}).get_attribute_list('value')[0]

                        resp = requests.post(url=id_url,
                                             data={'id_token': id_token,
                                                   'scope': scope,
                                                   'state': state,
                                                   'session_state': session_state},
                                             cookies=self.nif_jar,
                                             allow_redirects=False,
                                             verify=self.ssl_verify)
                        if resp.status_code == 302:
                            self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, resp.cookies)

                            return True, resp

        return False, None

    def minidrett(self):

        status, nif_id = self.nif_id()
        print(nif_id.headers, nif_id.text, nif_id.cookies)
        if status is True:
            resp = requests.get(url=nif_id.headers.get('Location', ''),
                                cookies=self.nif_jar,
                                allow_redirects=False,
                                verify=self.ssl_verify)
            if resp.status_code == 302:
                self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, resp.cookies)

                if self.realm in ['mi', 'minidrett']:
                    # Get profile and find person_id
                    profile = requests.get(url='https://minidrett.nif.no/MyProfile/Profiles',
                                           cookies=self.nif_jar,
                                           allow_redirects=False,
                                           verify=self.ssl_verify)

                    if profile.status_code == 200:
                        # soup = BeautifulSoup(profile.text, 'lxml')
                        # profile_img_id = soup.find(alt='Profilbilde')['id']
                        # self.person_id = int(profile_img_id.split('_')[1])
                        try:
                            self.person_id = int(profile.text.split('onclick="javaScript:DownloadCV(')[1].split(');"')[0])
                        except:
                            self.person_id = None

                return True, self.person_id, self.nif_jar

        return False, None, None

    def ka_login(self):

        if self.person_id is not None:

            r = requests.get('https://ka.nif.no/Members', cookies=self.nif_jar, allow_redirects=False, verify=self.ssl_verify)

            if r.status_code == 302:
                self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, r.cookies)
                frm = requests.get(r.headers.get('Location', ''),
                                   cookies=self.nif_jar,
                                   allow_redirects=False,
                                   verify=self.ssl_verify)

                if frm.status_code == 200:
                    self.nif_jar = requests.cookies.merge_cookies(self.nif_jar, frm.cookies)

                    ka_html = BeautifulSoup(frm.text, 'lxml')
                    id_url = ka_html.find('form').get_attribute_list('action')[0]
                    id_token = ka_html.find('input', attrs={'name': 'id_token'}).get_attribute_list('value')[0]
                    scope = ka_html.find('input', attrs={'name': 'scope'}).get_attribute_list('value')[0]
                    state = ka_html.find('input', attrs={'name': 'state'}).get_attribute_list('value')[0]
