# - *- coding: utf- 8 - *-

"""
    KA class
    ~~~~~~~~

    A simple class to interface KA

    - Login done with PassBuy
    - Access the KA webpages programatically
    - Read and write support

"""

import requests, json
from nif_tools.passbuy import Passbuy
import dateutil.parser
from pprint import pprint
import datetime
from nif_tools.common import get_headers
from bs4 import BeautifulSoup
import re
from packaging import version

MAX_SUPPORTED_VERSION = '3.73.8511'
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class KA:
    def __init__(self, username, password, realm='ka', email_recepients=[], ssl_verify=False):
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

    def get_headers(self):
        return self.KA_HEADERS

    def get_username(self):
        return self.username

    def get_person_id(self):
        return self.person_id

    def get_version(self) -> (str, str):
        try:
            r = requests.get(self.KA_URL, verify=self.ssl_verify)
            soup = BeautifulSoup(r.text, 'html.parser')
            p = soup.findAll('p', {'hidden': True})
            versions = re.findall('[0-9]+\.[0-9]+\.?[0-9]+\.?[0-9]*', str(p[0]))
            return versions[0], versions[1]
        except Exception as e:
            pass

        return None, None

    def is_version_supported(self) -> bool:
        v, b = self.get_version()
        if v is not None:
            return version.parse(v) <= version.parse(MAX_SUPPORTED_VERSION)

        return False

    def req(self, r):
        """Just parse the request object

        :parameter requests r: requests response object
        :returns int, dict status_code, requests.json:
        """
        if r.status_code == 200:
            try:
                result = r.json()
                if 'ErrorMessageViewModel' in result and \
                        'ErrorMessage' in result['ErrorMessageViewModel'] and \
                        result['ErrorMessageViewModel']['ErrorMessage'] is None:
                    return r.status_code, result
                elif len(result) > 0:
                    return r.status_code, result
                else:
                    return r.status_code, {}
            except Exception as e:
                result = {'result': r.text}
                return r.status_code, result

        return r.status_code, r.text

    def remove_keys(self, d, keys):
        """Remove keys from dict

        :parameter dict d: dictionary object
        :parameter list keys: keys to remove
        :returns dict d: Dictionary with removed keys
        """
        for k in keys:
            if k in d:
                d.pop(k, None)

        return d

    def post(self, url=None, params=None, remove_keys=[]):
        """Posts json to a resource-ish

        :param str url: the relative url to the resource
        :param dict params: a dictionary for the parameters
        :parameter list remove_keys: keys to remove
        :returns int, dictionary requests.status_code, result:
        """

        r = requests.post('{}/{}'.format(self.KA_URL, url),
                          json=params,
                          headers=self.KA_HEADERS,
                          cookies=self.fed_cookie,
                          verify=self.ssl_verify)

        status, result = self.req(r)
        result = self.remove_keys(result, remove_keys)
        if status != 200 or status != 201:
            # print(status, result)
            pass
        return status, result

    def get(self, url=None, params=None, remove_keys=[]):
        """Gets json from a resource

        :param str url: the relative url to the resource
        :param dict params: a dictionary for the parameters
        :parameter list remove_keys: keys to remove
        :returns int, dictionary requests.status_code, result:
        """

        r = requests.get('{}/{}'.format(self.KA_URL, url),
                         json=params,
                         headers=self.KA_HEADERS,
                         cookies=self.fed_cookie,
                         verify=self.ssl_verify)

        status, result = self.req(r)
        result = self.remove_keys(result, remove_keys)

        return status, result

    def requests_html(self, url, params, key1, key2=None, remove_keys=[], pre_pad='', post_pad=''):
        """Gets html page and returns json from jquery"""
        error = {}
        if key2 is None:
            key2 = ');'

        r = requests.get('{}/{}'.format(self.KA_URL, url),
                         headers=self.KA_HEADERS,
                         cookies=self.fed_cookie,
                         verify=self.ssl_verify)

        if r.status_code == 200:
            try:
                js = r.text.split(key1)[1].split(key2)[0]
                result = json.loads('{}{}{}'.format(pre_pad, js, post_pad))

                result = self.remove_keys(result, remove_keys)

                return r.status_code, result
            except Exception as e:
                print('Error ', e)
                return r.status_code, e

        return r.status_code, {}

    def _get_search_filter(self):
        """Get member search filter"""

        url = '{}/Members/'.format(self.KA_URL)
        page = requests.get(url, cookies=self.fed_cookie, headers=self.KA_HEADERS, verify=self.ssl_verify)
        en = page.text.split('var model = {')
        to = en[1].split('};')
        flt = json.loads("{%s}" % to[0])
        return flt['MemberSearchRequest']

    def get_clubs(self):
        """Get clubs in search filter"""

        clubs_filter = {'ClubName': None,
                        'CouncilIds': {},
                        'CountyIds': {},
                        'CurrentPage': 1,
                        'Direction': True,
                        'Email': None,
                        'From': 0,
                        'MobilePhoneNumber': None,
                        'OrderBy': 1,
                        'Size': 1000}

        resp = requests.post('{}/Members/SearchClub'.format(self.KA_URL),
                             cookies=self.fed_cookie,
                             json=clubs_filter,
                             headers=self.KA_HEADERS,
                             verify=self.ssl_verify)

        if resp.status_code == 200:
            return resp.json()['Items']
        else:
            return []

    def touch_person(self, person_id):
        """Just generate a change message"""

        status, person = self.get_person(person_id, False)
        save_url = 'PersonDetail/Save'

        if status == 200:
            s, r = self.post(save_url, person)

            if s in [200, 201]:
                return True

        return False

    def get_person(self, person_id, remove=True):
        """Get person from ka

        :parameter int person_id: Person Id
        :returns int status: http code
        :returns dict person: person
        """

        url = 'PersonDetail/Index/{}'.format(person_id)
        # key = 'Nif.PersonDetailViewModel.create('
        key1 = 'var baseModel = {'
        key2 = '};'

        status, person = self.requests_html(url=url, params=None, key1=key1, key2=key2, pre_pad='{', post_pad='}')

        # print('RESULT', status, person)

        if remove is True:
            remove_keys = ['Genders', 'Countries']
            person = self.remove_keys(person['EditPersonViewModel'], remove_keys)

        return status, person

    def get_person_details(self, person_id):

        url = 'PersonMemberDetail/Index/{}'.format(person_id)
        key = 'Nif.PersonMemberDetailViewModel.create('
        remove_keys = ['CurrentPage', 'Title', 'TitleCssClass', 'Pages',
                       'NavigationTarget', 'PageCount',
                       'BindingContainerId', 'ErrorMessageViewModel']

        status, details = self.requests_html(url=url, params=None, key1=key, remove_keys=remove_keys)

        return status, details

    def get_person_reskonto(self, person_id):
        url = 'PersonInvoice/Index/{}'.format(person_id)
        key = 'Nif.PersonInvoiceViewModel.create('
        remove_keys = ['CurrentPage']
        status, result = self.requests_html(url=url, params=None, key1=key, remove_keys=remove_keys)

        return status, result

    def get_person_reskonto_year(self, person_id, year=2019):

        resp = requests.post('{}/PersonInvoice/ChangeYear'.format(self.KA_URL),
                             json={'Year': year, 'PersonId': person_id},
                             headers=self.KA_HEADERS,
                             cookies=self.fed_cookie,
                             verify=self.ssl_verify)

        if resp.status_code == 200:
            return True, resp.json()

        return False, []

    def get_person_orgs(self, person_id):
        """Return orgs

        p['MembershipOrgSelectionViewModel']['FederationClubSelectionViewModel'].keys()
        dict_keys(['ClubList', 'ExistingClubs', 'PassiveClubs', 'NewClubOrgId', 'ExistingFederationFunctionFromDate', 'ReturnToIndex', 'ReturnUrl'])


        """
        url = 'PersonActivity/Index/{}'.format(person_id)
        key = 'Nif.PersonActivityViewModel.create('
        status, result = self.requests_html(url=url, params=None, key1=key)

        r = {'ExistingClubs': result['MembershipOrgSelectionViewModel']['FederationClubSelectionViewModel'][
            'ExistingClubs'],
             'PassiveClubs': result['MembershipOrgSelectionViewModel']['FederationClubSelectionViewModel'][
                 'PassiveClubs'],
             'NewClubOrgId': result['MembershipOrgSelectionViewModel']['FederationClubSelectionViewModel'][
                 'NewClubOrgId']
             }
        return status, r

    def save_person_orgs(self):
        pass

    def _sanitize_person_orgs(self, orgs):
        """Fixes the missing group/club/gren

        :param list orgs: list of orgs
        :returns list orgs: list of santized orgs
        """
        pass

    def get_person_products(self, person_id):
        """"""
        url = 'PersonProduct/Index/{}'.format(person_id)
        key = 'Nif.PersonProductViewModel.create('
        remove_keys = ['BannerViewModel', 'BindingContainerId', 'CurrentPage', 'HasMissingEmail',
                       'IsInactive', 'NavigationTarget', 'PageCount', 'Pages', 'ReturnToIndex',
                       'ReturnUrl', 'Title', 'TitleCssClass']
        status, result = self.requests_html(url=url, params=None, key1=key, remove_keys=remove_keys)

        return status, result

    def save_person_products(self, products):
        """Save persons products

        :parameter dict products: products from get_person_products, should be sanitized in sanitize_products
        :returns int status:
        :returns dict result:
        """
        url = 'PersonProduct/Save'
        params = products

        status, result = self.post(url, params)

        return status, result

    # def _sanitize_tandem_products(self):
    #    pass

    def sanitize_person_products(self, person_id, products, org_id=None, tandem=False):
        """Sanitizes products by checking correct according to organization and if is tandem

        :parameter int person_id: Person Id
        :parameter dict products: Products from get_person_products (and sanitized?)
        :parameter int org_id: OrgId, only when this is given can Unntak be set
        :parameter boolean tandem: If this is a tandem person, True else False
        :returns dict products: Sanitized products
        """
        # Get all sports!
        sports = []
        for p in products['PersonProductDetailSports']:
            sports.append(p['ProductDetailId'])

        # Modell 'modellmedlem' Modellinformasjon', 'ProductDetailId': 15
        if 15 in sports:
            age = self.get_age(person_id)
            if age > 25 and age < 67:
                sports.append(14)

        cat_i = -1
        cat_blad_i = -1
        cat_unntak_i = -1

        for c in products['Categories']:
            cat_i += 1

            if c['CategoryName'] == 'Blad':
                cat_blad_i += 1

                cat_orgs_i = -1
                for o in c['Orgs']:
                    cat_orgs_i += 1
                    cat_details_i = -1
                    if o['ClubOrgId'] == 376:

                        for d in o['Details']:
                            cat_details_i += 1

                            # Select magazine for all members
                            if not tandem and d['ProductDetailId'] in sports:
                                products['Categories'][cat_i]['Orgs'][cat_orgs_i]['Details'][cat_details_i][
                                    'Selected'] = True

                            # Deselect magazine for tandem
                            if tandem and d['ProductDetailId'] == 11 and \
                                    products['Categories'][cat_i]['Orgs'][cat_orgs_i]['Details'][cat_details_i][
                                        'Selected']:
                                products['Categories'][cat_i]['Orgs'][cat_orgs_i]['Details'][cat_details_i][
                                    'Selected'] = False

            elif c['CategoryName'] == 'Unntak':
                cat_unntak_i += 1

                cat_orgs_i = -1
                for o in c['Orgs']:
                    cat_orgs_i += 1
                    cat_details_i = -1

                    # Vanlig medlem, org_id og tandem
                    # For applications
                    if org_id is not None and o['ClubOrgId'] == org_id:

                        for d in o['Details']:
                            cat_details_i += 1
                            if d['ProductDetailId'] in sports:
                                products['Categories'][cat_i]['Orgs'][cat_orgs_i]['Details'][cat_details_i][
                                    'Selected'] = True

        return products

    def magazines(self, products):
        """Legacy
        @TODO Remove
        """

        return False
        """
        27 	Luftsport 	235 	Ballongflyging
        27 	Luftsport 	109 	Fallskjerm
        27 	Luftsport 	110 	Hang- og paraglider
        27 	Luftsport 	237 	Mikrofly
        27 	Luftsport 	236 	Modellfly
        27 	Luftsport 	238 	Motorfly
        27 	Luftsport 	111 	Seilfly

        """

        for cat in products['Categories']:

            if cat['CategoryName'] == 'Unntak':

                for org in cat['Orgs']:

                    r = requests.get(url='{}/ka/orgs/activity/{}'.format(self.API_URL, org['ClubOrgId']),
                                     headers=self.API_HEADERS,
                                     verify=self.ssl_verify)

                    if r.status_code == 200:
                        club = r.json()

                        print(club)

    # def _sanitize_orgs(self):
    #    pass

    def get_person_licenses(self, person_id):
        url = 'PersonLicense/Index/{}'.format(person_id)
        key = 'Nif.PersonLicenseViewModel.create('

        status, result = self.requests_html(url=url, params=None, key1=key)

        return status, result.get('Licenses', [])

    def get_person_competence(self, person_id):
        url = 'PersonCompetence/Index/{}'.format(person_id)
        key = 'Nif.PersonCompetenceViewModel.create('

        status, result = self.requests_html(url=url, params=None, key1=key)

        return status, result.get('Competences', [])

    def get_age(self, person_id):
        """Get person from ka, calculate age by calendar year

        :parameter int person_id: Person Id
        :returns int age: Person age by calendar year
        """

        status, person = self.get_person(person_id)

        if status == 200 and 'BirthDate' in person:

            try:
                birthdate = dateutil.parser.parse(person['BirthDate'])

                if datetime.datetime.now().month - birthdate.month < 0 and datetime.datetime.now().day - birthdate.day < 0:
                    return int(datetime.datetime.now().year - birthdate.year - 1)
                else:
                    return int(datetime.datetime.now().year - birthdate.year)
            except Exception as e:
                pass

        # Return default
        return 40

    def get_members(self, member_from=None, member_to=None, unntak=None):

        url = ''

    def get_invoices(self):
        """Get list of invoices

        :returns list invoices: list of invoices from search
        """

    def get_applications(self):
        """Get membership applications

        These are the applications by the members themselves

        :returns int: http status code
        :returns list: list of inbox items = applications
        """

        key = 'nif.memberMessagesMembershipApplicationsViewModel = Nif.PersonInboxLineListViewModel.create('
        url = 'Messages'
        params = {}
        status, result = self.requests_html(url=url, key1=key, params=params)

        return status, result['Items']

    def get_inbox(self):
        """
        alias for get_applications
        :return:
        """
        return self.get_applications()

    def approve_application(self, application):
        """Approve an application

        Sanitizes, approves and invoices
        """

        status, application_orgs = self._get_application_orgs(application)

        if application:
            message = 'Hei {0}! Velkommen som medlem i {1}.\r\n' \
                      'Du vil nå motta faktura for {2} i Min Idrett' \
                .format(application['FullName'],
                        application['DescribingName'],
                        application['Status'].strip())

            params = {"ConfirmationResponse": 1,
                      "EndedMemberships": [],
                      "FunctionApplications": application_orgs,
                      "Message": message,
                      "OrgTypeId": 2,
                      "SendEmail": True if len(self.email_recepients) > 0 else False,
                      "Items": [application]
                      }
            url = 'Messages/HandleMembershipApplications'

            return self.post(url=url, params=params)

    def _get_application_orgs(self, application):
        """Get one application org - via post??"""

        url = 'Messages/GetMembershipApplications'
        params = {"items": [application]}

        status, result = self.post(url=url, params=params)
        return status, result

    def get_person_activities(self, person_id):

        url = 'PersonActivity/Index/{}'.format(person_id)
        key = 'Nif.PersonActivityViewModel.create('
        remove_keys = ['HasMissingEmail', 'ReturnToIndex', 'ReturnUrl', 'BannerViewModel',
                       'CurrentPage', 'Title', 'TitleCssClass', 'ErrorMessageViewModel',
                       'Pages', 'NavigationTarget', 'PageCount', 'BindingContainerId']
        return self.requests_html(url=url, key1=key, params=None, remove_keys=remove_keys)

    def select_person_activities(self, person_id, org_id, activities):
        """Select the club/org_id to get activities which we then can save later

        :parameter int person_id: Person Id
        :parameter int org_id: Org Id for organization (club)
        :parameter dict activities: Activities got in get_person_activities
        :returns int, dict status_code, activities: ?
        """

        try:
            from_date = dateutil.parser.parse(activities['MembershipOrgSelectionViewModel']['FromDate'])
        except:
            from_date = datetime.date.today()

        params = {'FederationClubSelectionViewModel': {'ExistingFederationFunctionFromDate': None,
                                                       'NewClubOrgId': org_id,
                                                       'PassiveClubs': {},
                                                       },
                  'FromDate': from_date.strftime('%d.%m.%Y'),  # Today/Now
                  'HasMissingEmail': activities['MembershipOrgSelectionViewModel']['HasMissingEmail'],
                  'PersonId': activities['MembershipOrgSelectionViewModel']['PersonId'],
                  'SelectedOrgId': activities['MembershipOrgSelectionViewModel']['SelectedOrgId'],
                  }
        url = 'PersonActivity/SelectClub'

        return self.post(url=url, params=params)

    def save_person_activities(self, org_id, selected_activities):
        """We process the selected in select_person_activities"""

        try:
            from_date = dateutil.parser.parse(selected_activities['MembershipOrgSelectionViewModel']['FromDate'])
        except:
            from_date = datetime.date.today()

        if selected_activities['SelectedOrgId'] == org_id:

            # 5 klubb, 6 gruppe, 14 gren
            org_needed = [5, 6, 14]
            org_nums = 0
            org_types = []
            org_types_selected = []
            org_types_not_selected = []

            for o in selected_activities['AvailableOrgs']:
                org_nums += 1
                org_types.append(o['OrgTypeId'])
                if o['Selected']:
                    org_types_selected.append(o['OrgTypeId'])
                else:
                    org_types_not_selected.append(o['OrgTypeId'])

            org_types = list(set(org_types))
            org_types_selected = list(set(org_types_selected))
            org_types_not_selected = list(set(org_types_not_selected))

            # print(org_types, org_types_selected, org_types_not_selected)

            """
            if all(x in org_needed for x in org_types) and all(x in org_needed for x in org_types_selected):
                print('Alle medlemsskap eksisterer!')
                print('Alle medlemsskap er sjekket!')
                print(org_types_selected)
                pass
            """
            if all(x in org_types_selected for x in org_needed):
                pass
            elif org_nums == 3 and all(x in org_types for x in org_needed):
                print('V[A] Mangler i valg av gren - men kan fikses')

                # If not all needed orgs are selected we need to select!
                # @TODO only select if one gren!!!
                orgs = []
                for o in selected_activities['AvailableOrgs']:
                    if not o['Selected'] and o['OrgTypeId'] in org_needed:
                        o['Selected'] = True
                        # o['IsPassive'] = False
                        # o['IsOrgTypeSelectable'] = True
                        print('+[A] Selected', o['ShortName'])
                    orgs.append(o)

                selected_activities['AvailableOrgs'] = orgs
            elif org_nums != 3 and 14 in org_types_selected:
                print('?[A] Kun gren valgt')
                pass
            else:
                pass

            params = {
                'MembershipOrgSelectionViewModel': {
                    'AvailableOrgs': selected_activities['AvailableOrgs'],
                    'FromDate': from_date.strftime('%d.%m.%Y'),  # Today/Now
                    'HasMissingEmail': selected_activities['HasMissingEmail'],
                    'PersonId': selected_activities['PersonId'],
                    'SelectedOrgId': selected_activities['SelectedOrgId'],
                    'success': True
                },

            }

            url = 'PersonActivity/Save'

            return self.post(url=url, params=params)

    def check_person_activities_org(self, org_id, activities):
        """Returns true if acitivity org in application org"""
        for item in activities['MembershipOrgSelectionViewModel']['FederationClubSelectionViewModel']['ExistingClubs']:
            if item['Id'] == org_id:
                return True

        return False

    def get_inbox_ended(self):
        """Get inbox items for applications for ending membership

        :returns list: inbox list of current applications to cancel membership(s)
        """

        url = 'Messages'
        key = 'nif.memberMessagesEndedMembershipsViewModel = Nif.PersonInboxLineListViewModel.create('
        params = {}
        status, result = self.requests_html(url=url, key1=key, params=params)
        return status, result['Items']

    def _get_application_ended(self, inboxline):
        """Get the application from inbox item (item from get_applications_ended)

        """
        url = 'Messages/GetEndedMemberships'
        params = {'Items': [inboxline]}

        status, result = self.post(url=url, params=params)

        return status, result

    def approve_application_ended(self, inboxline, refund=True):
        """Approve the cancellation - 1 application a time, or?

        Will it refund invoices?
        :parameter dict inboxline: one item from get_applications_ended
        :parameter boolean refund: if to refund invoices or not, default True
        :returns boolean result: result of approval
        """

        # Get the complete application including invoices
        status_application, application = self._get_application_ended(inboxline)

        if status_application == 200:

            # Refund all invoices
            if refund:
                i = 0
                for e in application[0]['Invoices']:
                    application[0]['Invoices'][i]['IsChecked'] = True
                    i += 1

            params = {'EndedMemberships': [{'Invoices': application[0]['Invoices'], 'PersonInboxLine': inboxline}],
                      'FunctionApplications': [],
                      'Items': [inboxline],
                      'OrgTypeId': 2}

            url = 'Messages/HandleEndedMemberships'

            status, approval = self.post(url, params)

            return status, approval

        else:
            return status_application, application

    def get_applications_deceased(self):
        """Get and process dead people"""

        key = 'nif.memberMessagesDeceasedMembersViewModel = Nif.PersonInboxLineListViewModel.create('
        url = 'Messages'
        params = {}
        status, result = self.requests_html(url=url, key1=key, params=params)

        return status, result['Items']

    def approve_deceased(self):
        """Approve and refund invoices for deceased member"""
        raise NotImplementedError

    def _get_all_org_products(self, org_id=376):
        """Get all invoicable products for org_id, sort accordingly"""

        url = 'SendInvoice/GetProductsForOrg/?orgId={1}'.format(self.KA_URL, org_id)

        status, result = self.post(url=url, params=None)

        # Build fees
        fees_new = []

        for f in result:
            fees_new.append({'OrgId': 376,
                             'OrgName': 'Norges Luftsportforbund',
                             'Product': f})

        fees_sorted = sorted(fees_new, key=lambda k: k['Product']['ProductTypeId'])

        return status, fees_sorted

    def _get_filter(self):
        """Get member search filter"""

        url = 'Members/'

        status, result = self.requests_html(url=url, params=None,
                                            key1='var model = {',
                                            key2='};',
                                            pre_pad='{',
                                            post_pad='}')
        if 'MemberSearchRequest' in result:
            return status, result['MemberSearchRequest']
        else:
            return status, {'Error': result}

    def get_members_in_org(self, org_id) -> (int, list):
        url = 'Members/Search'

        flt_status, flt = self._get_filter()

        flt['Size'] = 9999
        flt['ClubSearchModel']['SelectedClubs'].append({'Id': org_id})

        status, result = self.post(url=url, params=flt)

        # get('TotalResults', 0) => should be returned too....
        return status, result.get('SearchResult', {}).get('members', [])

    def get_members_from_search(self, from_date=None, to_date=None):

        if from_date is None:
            from_date = datetime.datetime.now()

        if to_date is None:
            to_date = datetime.datetime.now()

        if from_date > to_date:
            return 501, {'Error': 'Dates from to are wrong order'}

        url = 'Members/Search'

        flt_status, flt = self._get_filter()

        flt['Size'] = 9999

        # From date
        flt['Criteria'][13]['CriteriaOptions'][0]['Checked'] = True
        flt['Criteria'][13]['CriteriaOptions'][0]['FromDate'] = from_date.strftime('%d.%m.%Y')
        flt['Criteria'][13]['CriteriaOptions'][0]['ToDate'] = to_date.strftime('%d.%m.%Y')

        status, result = self.post(url=url, params=flt)

        return status, result.get('SearchResult', {}).get('members', [])

    def _get_invoices(self, person_ids) -> (int, dict):
        """Gets all the invoices to send

        :parameter list person_ids: list of person_id's to get invoices
        :returns list invoices: list of invoices objects
        """

        url = 'SendInvoice?ids={}'.format(','.join(str(x) for x in person_ids))
        params = None
        key1 = 'var model = {'
        key2 = '};'
        pre_pad = '{'
        post_pad = '}'

        status, result = self.requests_html(url=url,
                                            params=params,
                                            key1=key1,
                                            key2=key2,
                                            pre_pad=pre_pad,
                                            post_pad=post_pad)
        return status, result

        if status in [200, 201]:
            return True, result

        return False, {}

    def can_invoice(self) -> bool:

        person_ids = [1]
        status, result = self._get_invoices(person_ids)

        if status == 200 and person_ids == result.get('InvoiceRequest', {}).get('PersonIds', []):
            return True

        return False

    def send_invoices(self, person_ids, notify=False) -> (int, dict):
        """This actually sends the invoice"""

        # NIF can't handle non-unique person_ids, it will make invoice for each
        person_ids = list(set(person_ids))

        if len(person_ids) > 0:

            inv_status, invoices = self._get_invoices(person_ids)

            if inv_status == 200 and invoices and len(invoices['InvoiceRequest']['PersonIds']) > 0:
                fees_status, fees = self._get_all_org_products()
                params = {'Fees': fees,
                          'FromEmailAddress': invoices['InvoiceRequest']['FromEmailAddress'],
                          'InvoiceText': invoices['InvoiceRequest']['InvoiceText'],
                          'PaymentDueDate': dateutil.parser.parse(
                              invoices['InvoiceRequest']['PaymentDueDate']).strftime(
                              '%d.%m.%Y'),
                          'PersonIds': invoices['InvoiceRequest']['PersonIds'],
                          'SendEmailAutomatically': invoices['InvoiceRequest']['SendEmailAutomatically'],  # true/false
                          'SendPdfToEveryone': invoices['InvoiceRequest']['SendPdfToEveryone'],  # true/false
                          'SendPdfToThoseWithoutEmail': invoices['InvoiceRequest']['SendPdfToThoseWithoutEmail'],
                          # true/false
                          'SendPdfWithKidAsEmail': invoices['InvoiceRequest']['SendPdfWithKidAsEmail'],  # true/false
                          'SendSms': invoices['InvoiceRequest']['SendSms'],  # true/false
                          'ToEmailAddress': ','.join(str(x) for x in self.email_recepients)
                          # inv['InvoiceRequest']['ToEmailAddress']
                          }

                if notify is False:
                    params['SendEmailAutomatically'] = False
                    params['SendPdfToEveryone'] = False
                    params['SendPdfToThoseWithoutEmail'] = False
                    params['SendPdfWithKidAsEmail'] = False
                    params['SendSms'] = False

                url = 'SendInvoice/Send'

                status, result = self.post(url=url, params=params)

                return status, result

            else:
                return 500, {'result': 'false'}
        else:
            return 200, {'result': 'true'}
