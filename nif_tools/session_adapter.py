"""
Fix for ssl EOF errors in requests for:
 - id.nif.no
 - ka.nif.no (ka needs this session!)
"""
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.connection import HTTPConnection
import socket

class SessionAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        # 1. DO NOT use ssl.create_default_context() directly.
        # Instead, look for a context provided by urllib3 or fall back to system defaults
        ctx = pool_kwargs.get('ssl_context', None)
        if ctx is None:
            ctx = ssl.create_default_context()

        # 2. Safely apply the explicit OpenSSL truncation ignore flags
        # (This protects your Hetzner tasks while leaving the ciphers untouched!)
        ctx.options |= getattr(ssl, "OP_IGNORE_UNEXPECTED_EOF", 0)
        ctx.options |= 0x00000080  # Direct hex bitmask bypass

        # 3. FIX: Disable TLS Session Ticket Caching to stop stale session reuse
        if hasattr(ctx, "session_cache_mode"):
            ctx.session_cache_mode = ssl.SESS_CACHE_OFF

        # 3. Handle certificate verification toggling in the required sequence
        cert_reqs = pool_kwargs.get('cert_reqs', None)
        if cert_reqs in (ssl.CERT_NONE, 'CERT_NONE', 'NONE', 0):
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        else:
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = True

        # kwargs['ssl_context'] = ctx
        # return super(SessionAdapter, self).init_poolmanager(*args, **kwargs)

        pool_kwargs['ssl_context'] = ctx

        # 5. INJECT LOW-LEVEL TCP KEEP-ALIVES
        # This tells the OS to ping Azure every 60s so it doesn't drop the connection
        pool_kwargs['socket_options'] = HTTPConnection.default_socket_options + [
            (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
            (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60),  # Ping every 60 seconds
            (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10), # Retry every 10s if missed
            (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)     # Drop after 3 misses
        ]

        # 5. FIX: Force pool manager to only hold 1 socket and not pool multiple connections.
        # This stops requests from holding onto dead sockets that remote servers closed.
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=1,            # strictly allow only 1 connection per host
            block=block,
            **pool_kwargs
        )


# The Scoped Session Factory remains isolated to the Hetzner Blueprint
def get_session_adpter() -> requests.Session:
    session = requests.Session()
    adapter = SessionAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
