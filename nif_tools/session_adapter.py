"""
Fix for ssl EOF errors in requests for:
 - id.nif.no
 - ka.nif.no (ka needs this session!)
"""
import ssl
import requests
from requests.adapters import HTTPAdapter

class SessionAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        # 1. DO NOT use ssl.create_default_context() directly.
        # Instead, look for a context provided by urllib3 or fall back to system defaults
        ctx = kwargs.get('ssl_context', None)
        if ctx is None:
            ctx = ssl.create_default_context()

        # 2. Safely apply the explicit OpenSSL truncation ignore flags
        # (This protects your Hetzner tasks while leaving the ciphers untouched!)
        ctx.options |= getattr(ssl, "OP_IGNORE_UNEXPECTED_EOF", 0)
        ctx.options |= 0x00000080  # Direct hex bitmask bypass

        # 3. Handle certificate verification toggling in the required sequence
        cert_reqs = kwargs.get('cert_reqs', None)
        if cert_reqs in (ssl.CERT_NONE, 'CERT_NONE', 'NONE', 0):
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        else:
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = True

        kwargs['ssl_context'] = ctx
        return super(SessionAdapter, self).init_poolmanager(*args, **kwargs)

# The Scoped Session Factory remains isolated to the Hetzner Blueprint
def get_session_adpter() -> requests.Session:
    session = requests.Session()
    adapter = SessionAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
