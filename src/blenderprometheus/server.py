import socket
from socketserver import ThreadingMixIn
import threading
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
from prometheus_client import CollectorRegistry, REGISTRY
from prometheus_client.exposition import make_wsgi_app, make_server

class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Thread per request HTTP server."""
    # Make worker threads "fire and forget". Beginning with Python 3.7 this
    # prevents a memory leak because ``ThreadingMixIn`` starts to gather all
    # non-daemon threads in a list in order to join on them at server close.
    daemon_threads = True


def _get_best_family(address, port):
    """Automatically select address family depending on address"""
    # HTTPServer defaults to AF_INET, which will not start properly if
    # binding an ipv6 address is requested.
    # This function is based on what upstream python did for http.server
    # in https://github.com/python/cpython/pull/11767
    infos = socket.getaddrinfo(address, port)
    family, _, _, _, sockaddr = next(iter(infos))
    return family, sockaddr[0]

class _SilentHandler(WSGIRequestHandler):
    """WSGI handler that does not log requests."""

    def log_message(self, format, *args):
        """Log nothing."""
        
def start_server(port: int, addr: str = '0.0.0.0', registry: CollectorRegistry = REGISTRY) -> None:
    """Starts a WSGI server for prometheus metrics as a daemon thread."""

    class TmpServer(ThreadingWSGIServer):
        """Copy of ThreadingWSGIServer to update address_family locally"""
        allow_reuse_address = True

    TmpServer.address_family, addr = _get_best_family(addr, port)
    app = make_wsgi_app(registry)
    global httpd
    httpd = make_server(addr, port, app, TmpServer, handler_class=_SilentHandler)
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()

def stop_server():
    global httpd
    httpd.shutdown()
    httpd.socket.close()
