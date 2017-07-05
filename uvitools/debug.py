import os
from uvitools import utils
from werkzeug.debug import DebuggedApplication
from werkzeug.debug.tbtools import get_current_traceback


class DebugMiddleware(DebuggedApplication):
    def __init__(self, *args, **kwargs):
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        super().__init__(*args, **kwargs)

    async def __call__(self, message, channels):
        environ = utils.message_to_environ(message)
        wsgi_status = None
        wsgi_headers = None

        def start_response(status, headers, exc_info=None):
            nonlocal wsgi_status, wsgi_headers
            wsgi_status = status
            wsgi_headers = headers

        response = super().__call__(environ, start_response)
        if response is None:
            await self._debug_application(message, channels)
        else:
            # Requests to the debugger.
            # Eg. load resource, pin auth, issue command.
            status = utils.status_line_to_status_code(wsgi_status)
            headers = utils.str_headers_to_byte_headers(wsgi_headers)
            content = b''.join(response)
            await channels['reply'].send({
                'status': status,
                'headers': headers,
                'content': content
            })

    def debug_application(self, environ, start_response):
        return None

    async def _debug_application(self, message, channels):
        """Run the application and conserve the traceback frames."""
        try:
            await self.app(message, channels)
        except Exception:
            traceback = get_current_traceback(
                skip=1, show_hidden_frames=self.show_hidden_frames,
                ignore_system_exceptions=True)
            for frame in traceback.frames:
                self.frames[frame.id] = frame
            self.tracebacks[traceback.id] = traceback

            status = 500
            headers = [
                (b'Content-Type', b'text/html; charset=utf-8'),
                # Disable Chrome's XSS protection, the debug
                # output can cause false-positives.
                (b'X-XSS-Protection', b'0'),
            ]
            environ = utils.message_to_environ(message)
            is_trusted = bool(self.check_pin_trust(environ))
            content = traceback.render_full(
                evalex=self.evalex,
                evalex_trusted=is_trusted,
                secret=self.secret
            ).encode('utf-8', 'replace')
            await channels['reply'].send({
                'status': status,
                'headers': headers,
                'content': content
            })
