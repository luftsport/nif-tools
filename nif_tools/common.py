def get_headers(realm='ka') -> (str, dict):
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'
    accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    accept_encoding = 'gzip, deflate, br'
    accept_language = 'en-US,en;q=0.5'

    url = 'https://{}.nif.no'.format(realm)

    return url, {'Host': '{}.nif.no'.format(realm),
                 'Referer': '{}/Members'.format(url),
                 'Content-Type': 'application/json',
                 'User-Agent': user_agent,
                 'Accept': 'application/json, text/javascript, */*; q=0.01',
                 'X-Requested-With': 'XMLHttpRequest',
                 'Accept-Encoding': accept_encoding,
                 'Accept-Language': accept_language
                 }


def get_email():
    return {'username': None,
            'password': None,
            'smtp': None,
            'smtp_port': 587,
            'from': None,
            'to': []
            }
