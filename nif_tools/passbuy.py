import requests
from bs4 import BeautifulSoup, Comment
import os
import inspect
from pprint import pprint

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

    def __init__(self, username, password, realm='minidrett', verify=True, ssl_verify=False, debug=False):

        self.username = username
        self.password = password
        self.realm = realm
        self.person_id = None
        self.ssl_verify = ssl_verify

        # Use session to persist cookies and headers across requests
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0'})
        if debug is True:
            print("[WARNING] Debug mode enabled: Adding response hook to print request and response details")
            self.session.hooks["response"].append(self.debug_response)

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

    def debug_response(self, r, *args, **kwargs):

        print(f"\n\rDEBUG: {r.request.method} {r.request.url}")
        print(f"Status: {r.status_code}")

        caller_frame = inspect.currentframe().f_back.f_back.f_back.f_back

        print(f"##### Called from Line: {caller_frame.f_lineno}")

        print(f"Request Headers:")
        pprint(r.request.headers)
        if r.request.body:
            print(f"Request Body: {r.request.body}")
        print(f"Response Headers:")
        pprint(r.headers)
        if r.text:
            print("Response Body")
            try:
                soup = BeautifulSoup(r.text, "html.parser")
                for element in soup(["script", "style"]):
                    element.decompose()
                for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                    comment.extract()
                    print(soup.prettify()[:500])  # Print first 500 chars of cleaned response body
            except Exception as e:
                print(f"Error parsing response body: {e}")
                print(r.text[:500])  # Print first 500 chars of response body

    def is_maintanance(self):
        """Check if maintanance mode

        NIF web (KA/MI/SA) gives normal http 200, need to check title
        Also: re.search('(?<=<title>).+?(?=</title>)', mytext, re.DOTALL).group().strip()

        :returns boolean is_maintanance:
        """

        r = self.session.get('https://{}.nif.no'.format(self.realm), verify=self.ssl_verify)

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

        r = self.session.get('https://{}.nif.no/'.format(self.realm), verify=self.ssl_verify)

        self.session.cookies.update(r.cookies)

        # Login page
        resp = self.session.get('https://{}.nif.no/{}'.format(self.realm, self.login_page),
                            allow_redirects=False,
                            verify=self.ssl_verify)
        self.nif_jar = self.session.cookies.update(resp.cookies)

        if resp.status_code == 302:

            # id.nif.no/connect/authorize
            r1 = self.session.get(resp.headers.get('Location', ''),
                              allow_redirects=False)
            self.session.cookies.update(r1.cookies)

            if r1.status_code == 302:

                # id.nif.no/Account/Login
                r2 = requests.get(r1.headers.get('Location', ''),
                                  allow_redirects=False)
                self.session.cookies.update(r2.cookies)

                if r2.status_code == 302:
                    # id.nif.no/ExternalLogin/Challenge
                    r3 = self.session.get('https://id.nif.no{}'.format(r2.headers.get('Location', '')),
                                      allow_redirects=False,
                                      verify=self.ssl_verify)
                    self.session.cookies.update(r3.cookies)


                    if r3.status_code == 302:
                        # auth/nif/buypass.no/auth/realms/nif/protocol/openid-connect/auth
                        r4 = self.session.get('{}'.format(r3.headers.get('Location', '')),
                                              allow_redirects=False,
                                              verify=self.ssl_verify)
                        self.session.cookies.update(r4.cookies)
                        return True, r4

        return False, None

    def buypass(self):
        """Returns
        login url
        challenge
        """

        status, mi = self.nif_realm()
        if status is True:

            # auth.nif.buypass.no/auth/realms/nif/protocol/openid-connect/auth
            r = self.session.get(mi.headers.get('Location', ''),
                             allow_redirects=False,
                             verify=self.ssl_verify)

            if r.status_code == 200:
                self.bp_jar = r.cookies
                bp_html = BeautifulSoup(r.text, 'lxml')
                # login_url = bp_html.find('form', attrs={'class': 'nif-login-form'}).get_attribute_list('action')[0]
                login_url = bp_html.find('form').get_attribute_list('action')[0]
                challenge = bp_html.find('input', attrs={'name': 'challenge'}).get_attribute_list('value')[0]

                # Login 1
                login1 = self.session.post(url=login_url, data={'challenge': challenge,
                                                            'username': self.username,
                                                            'rememberMe': 'off',
                                                            'origin_url': '',
                                                            'authMethod': ''},
                                       allow_redirects=False,
                                       verify=self.ssl_verify)
                if login1.status_code == 200:
                    self.session.cookies.update(login1.cookies)

                    bp2_html = BeautifulSoup(login1.text, 'lxml')
                    login_url2 = bp2_html.find('form', attrs={'id': 'login-form'}).get_attribute_list('action')[0]
                    # challenge2 = bp2_html.find('input', attrs={'name': 'challenge'}).get_attribute_list('value')[0]
                    # Login 1
                    login2 = self.session.post(url=login_url2, data={  # 'challenge': challenge2,
                        'password': self.password,
                        'rememberMe': 'off',
                        'origin_url': '',
                        'authMethod': ''},
                                           allow_redirects=False,
                                           verify=self.ssl_verify)
                    if login2.status_code == 200:
                        self.session.cookies.update(login2.cookies)

                        return True, login2

        return False, None

    def nif_id(self):

        status, buypass = self.buypass()
        if status is True:
            bp_html = BeautifulSoup(buypass.text, 'lxml')
            login_url = bp_html.find('form', attrs={'id': 'register'}).get_attribute_list('action')[0]
            # self.code = bp_html.find('input', attrs={'name': 'code'}).get_attribute_list('value')[0]
            # state = bp_html.find('input', attrs={'name': 'state'}).get_attribute_list('value')[0]
            # session_state = bp_html.find('input', attrs={'name': 'session_state'}).get_attribute_list('value')[0]

            resp = self.session.post(url=login_url,
                                 # data={'code': self.code,
                                 #      'state': state,
                                 #      'session_state': session_state},
                                 data={
                                     'clientDataJSON': '',
                                     'attestationObject': '',
                                     'publicKeyCredentialId': '',
                                     'authenticatorLabel': '',
                                     'transports': '',
                                     'error': '',
                                     'skipPasskeyRegistration': 'true'
                                 },
                                 allow_redirects=False,
                                 verify=self.ssl_verify)
            self.session.cookies.update(resp.cookies)

            if resp.status_code == 200:
                t_html = BeautifulSoup(resp.text, 'lxml')
                t_url = t_html.find('form').get_attribute_list('action')[0]
                self.code = t_html.find('input', attrs={'name': 'code'}).get_attribute_list('value')[0]
                state = t_html.find('input', attrs={'name': 'state'}).get_attribute_list('value')[0]
                session_state = t_html.find('input', attrs={'name': 'session_state'}).get_attribute_list('value')[0]
                iss = t_html.find('input', attrs={'name': 'iss'}).get_attribute_list('value')[0]
                t_resp = self.session.post(url=t_url,
                                       data={'code': self.code,
                                             'state': state,
                                             'session_state': session_state,
                                             'iss': iss
                                             },
                                       allow_redirects=False,
                                       verify=self.ssl_verify)

            # This is nif!!
            if t_resp.status_code == 302:
                self.session.cookies.update(t_resp.cookies)

                callback = self.session.get(url='https://id.nif.no{}'.format(t_resp.headers.get('Location', '')),
                                        allow_redirects=False,
                                        verify=self.ssl_verify)

                if callback.status_code == 302:
                    self.nif_jar = self.session.cookies.update(callback.cookies)

                    connect = self.session.get(url='https://id.nif.no{}'.format(callback.headers.get('Location', '')),
                                           allow_redirects=False,
                                           verify=self.ssl_verify)

                    if connect.status_code == 200:
                        self.session.cookies.update(connect.cookies) # self.session.cookies.update(connect.cookies)

                        mi_html = BeautifulSoup(connect.text, 'lxml')
                        id_url = mi_html.find('form').get_attribute_list('action')[0]

                        scope = mi_html.find('input', attrs={'name': 'scope'}).get_attribute_list('value')[0]
                        state = mi_html.find('input', attrs={'name': 'state'}).get_attribute_list('value')[0]
                        session_state = mi_html.find('input', attrs={'name': 'session_state'}).get_attribute_list('value')[0]
                        data = {'scope': scope,
                                'state': state,
                                'session_state': session_state}

                        # Optional fields
                        for field in ['code', 'id_token', 'iss']:
                            try:
                                value = mi_html.find('input', attrs={'name': field}).get_attribute_list('value')[0]
                                data[field] = value
                            except:
                                pass
                        try:
                            # Make sure to add these cookies
                            if 'nif.start.url' not in self.nif_jar.keys():
                                self.nif_jar.set('nif.start.url', '', domain='.nif.no')
                            if 'cookieconsent' not in self.nif_jar.keys():
                                self.nif_jar.set('cookieconsent','yes', domain='.nif.no')
                        except:
                            pass # Silent

                        resp = self.session.post(url=id_url,
                                             data=data,
                                             headers={
                                                 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0',
                                                 'Origin': 'null',
                                                 'Host': '{0}.nif.no'.format(self.realm),
                                                 'Sec-Fetch-Dest': 'document',
                                                 'Sec-Fetch-Mode': 'navigate',
                                                 'Sec-Fetch-Site': 'same-site',
                                                 'Sec-GPC': '1',
                                                 'Upgrade-Insecure-Requests': '1',
                                                 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                                 'Pragma': 'no-cache',
                                                 'Cache-Control': 'no-cache'
                                             },
                                             allow_redirects=False,
                                             verify=self.ssl_verify)

                        if resp.status_code == 302:
                            self.session.cookies.update(resp.cookies)

                            return True, resp

        return False, None

    def minidrett(self):

        status, nif_id = self.nif_id()

        if status is True:
            resp = self.session.get(url=nif_id.headers.get('Location', ''),
                                allow_redirects=False,
                                verify=self.ssl_verify)
            if resp.status_code == 302:
                self.session.cookies.update(resp.cookies)

                resp2 = self.session.get(url=resp.headers.get('Location', ''),
                                        allow_redirects=False,
                                        verify=self.ssl_verify)
                if resp2.status_code == 200:

                    if self.realm in ['mi', 'minidrett']:
                        # Get profile and find person_id
                        profile = self.session.get(url='https://minidrett.nif.no/MyProfile/Profiles',
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

                    return True, self.person_id, self.session.cookies

        return False, None, None

    def ka_login(self):

        if self.person_id is not None:

            r = self.session.get('https://ka.nif.no/Members', allow_redirects=False, verify=self.ssl_verify)

            if r.status_code == 302:
                self.nif_jar = self.session.cookies.update(r.cookies)
                frm = self.session.get(r.headers.get('Location', ''),
                                   allow_redirects=False,
                                   verify=self.ssl_verify)

                if frm.status_code == 200:
                    self.session.cookies.update(frm.cookies)

                    ka_html = BeautifulSoup(frm.text, 'lxml')
                    id_url = ka_html.find('form').get_attribute_list('action')[0]
                    id_token = ka_html.find('input', attrs={'name': 'id_token'}).get_attribute_list('value')[0]
                    scope = ka_html.find('input', attrs={'name': 'scope'}).get_attribute_list('value')[0]
                    state = ka_html.find('input', attrs={'name': 'state'}).get_attribute_list('value')[0]
