#!/usr/bin/env python3
"""Local-only development or Waitress behind a hosting HTTPS proxy."""
import argparse
import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server
from pilot_app import create_app, APP_VERSION

class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass  # Do not log paths, query strings, cookies or personal data.

class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

def main():
    parser=argparse.ArgumentParser(description='Bocali v1.0')
    parser.add_argument('--local', action='store_true', help='HTTP restrito a 127.0.0.1; dados ficticios')
    parser.add_argument('--lan', action='store_true', help='HTTP na rede local privada; somente piloto com dados de teste')
    args = parser.parse_args()
    app = create_app()
    port = int(os.environ.get('PORT','8000'))
    if args.local or args.lan:
        expected = 'lan' if args.lan else 'local'
        if app.settings.mode != expected:
            raise SystemExit('O modo do servidor nao corresponde a PEDE_MODE='+expected+'.')
        bind = '0.0.0.0' if args.lan else '127.0.0.1'
        label = 'rede local privada' if args.lan else 'computador local'
        print('Bocali:', app.settings.origin, '-', label, '- somente dados de teste.', flush=True)
        with make_server(bind, port, app, server_class=ThreadedWSGIServer, handler_class=QuietHandler) as srv:
            srv.serve_forever()
    else:
        if not app.settings.production:
            raise SystemExit('O servidor externo exige BOCALI_MODE=production e HTTPS.')
        try:
            from waitress import serve
        except ImportError:
            raise SystemExit('Instale requirements-hosted.txt para usar Waitress. Nao publique com --local.')
        print(f'Bocali {APP_VERSION} online em {app.settings.origin}', flush=True)
        # No forwarded headers are trusted. TLS is terminated by the hosting platform;
        # cookie security and origin checks use the fixed, validated public origin.
        serve(app, host='0.0.0.0', port=port, threads=8, max_request_body_size=11*1024*1024,
            channel_timeout=30, clear_untrusted_proxy_headers=True, expose_tracebacks=False)

if __name__ == '__main__':
    main()
