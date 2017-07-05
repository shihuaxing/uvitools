import asyncio
from uvitools.routing import Route, Router
from uvitools.debug import DebugMiddleware


def run_task(task):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task)


class MockReplyChannel(object):
    def __init__(self):
        self.message = None
    async def send(self, message):
        self.message = message


async def exception(message, channels):
    raise Exception('Failed!')


async def no_exception(message, channels):
    await channels['reply'].send({'status': 204})


routes = [
    Route('/exception/', exception),
    Route('/no_exception/', no_exception)
]

app = DebugMiddleware(Router(routes))


def test_no_exception():
    message = {'method': 'GET', 'path': '/no_exception/', 'query_string': b'', 'http_version': '1.1', 'headers': []}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert channels['reply'].message == {'status': 204}


def test_exception():
    message = {'method': 'GET', 'path': '/exception/', 'query_string': b'', 'http_version': '1.1', 'headers': []}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert channels['reply'].message['status'] == 500


def test_debugger_command():
    query_string = b'__debugger__=yes&cmd=resource&f=debugger.js'
    message = {'method': 'GET', 'path': '/', 'query_string': query_string, 'http_version': '1.1', 'headers': []}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert channels['reply'].message['status'] == 200
