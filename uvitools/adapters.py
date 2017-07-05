from uvitools import utils
import asyncio
import io
import http

# TODO:
# Encodings
# Path / Path Info
# Handling multiple headers
# exc_info
# wsgi.errors
# wsgi.sendfile
# max request body


# Request conversions...




# Response conversions...

async def read_body(message, channels):
    """
    Read and return the entire body from an incoming ASGI message.
    """
    body = message.get('body', b'')
    if 'body' in channels:
        while True:
            message_chunk = await channels['body'].receive()
            body += message_chunk['content']
            if not message_chunk.get('more_content', False):
                break
    return body


# Adapters...

def enumerate_with_markers(iterator):
    # Transform an WSGI response iterator into (is_first, item, is_last).
    previous_is_first = True
    previous = None
    for item in iterator:
        if previous is not None:
            # Yield each non-final item in the iterator.
            yield (previous_is_first, previous, False)
            previous_is_first = False
        previous = item

    if previous is None:
        # Handle the empty case.
        yield (True, b'', True)
    else:
        # Yield the final item in the iterator.
        yield (previous_is_first, previous, True)


class ASGIAdapter(object):
    """
    Expose an ASGI interface, given a WSGI application.
    """
    def __init__(self, wsgi):
        self.wsgi = wsgi

    async def __call__(self, message, channels):
        response = {}
        def start_response(status, response_headers, exc_info=None):
            response.update({
                'status': utils.status_line_to_status_code(status),
                'headers': utils.str_headers_to_byte_headers(response_headers)
            })

        body = await read_body(message, channels)
        environ = utils.message_to_environ(message)
        environ['wsgi.input'] = io.BytesIO(body)

        iterator = self.wsgi(environ, start_response)
        for is_first, content, is_last in enumerate_with_markers(iterator):
            if is_first:
                response.update({
                    'content': content,
                    'more_content': not(is_last)
                })
            else:
                response = {
                    'content': content,
                    'more_content': not(is_last)
                }
            await channels['reply'].send(response)


class WSGIAdapter(object):
    """
    Expose an WSGI interface, given an ASGI application.
    """
    def __init__(self, asgi):
        self.asgi = asgi
        self.loop = asyncio.get_event_loop()

    def __call__(self, environ, start_response):
        class ReplyChannel():
            def __init__(self, queue):
                self._queue = queue

            async def send(self, message):
                self._queue.append(message)

        class BodyChannel():
            def __init__(self, environ):
                self._stream = environ['wsgi.input']

            async def receive(self):
                return self._stream.read()

        reply = []
        message = utils.environ_to_message(environ)
        channels = {
            'reply': ReplyChannel(reply),
            'body': BodyChannel(environ)
        }

        coroutine = self.asgi(message, channels)
        self.loop.run_until_complete(coroutine)

        assert(reply)
        status = utils.status_code_to_status_line(reply[0]['status'])
        headers = utils.byte_headers_to_str_headers(reply[0]['headers'])
        exc_info = None
        start_response(status, headers, exc_info)
        return [message['content'] for message in reply]
