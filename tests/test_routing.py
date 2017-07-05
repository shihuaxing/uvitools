from uvitools.routing import ChannelSwitch, Router, Route
import asyncio
import json
import pytest


def run_task(task):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(task)


class MockReplyChannel(object):
    def __init__(self):
        self.message = None
    async def send(self, message):
        self.message = message


async def hello_world(message, channels):
    data = {'hello': 'world'}
    await channels['reply'].send({
        'status': 200,
        'headers': [
            [b'content-type', b'application/json']
        ],
        'content': json.dumps(data).encode()
    })


async def hello_user(message, channels):
    data = {'hello': message['args']['username']}
    await channels['reply'].send({
        'status': 200,
        'headers': [
            [b'content-type', b'application/json']
        ],
        'content': json.dumps(data).encode()
    })


app = Router([
    Route('/hello/', hello_world, methods=['GET']),
    Route('/hello/<username>/', hello_user, methods=['GET'])
])


def test_literal_lookup():
    message = {'path': '/hello/'}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert channels['reply'].message == {
        'status': 200,
        'headers': [
            [b'content-type', b'application/json']
        ],
        'content': json.dumps({'hello': 'world'}).encode()
    }


def test_pattern_lookup():
    message = {'path': '/hello/tom/'}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert channels['reply'].message == {
        'status': 200,
        'headers': [
            [b'content-type', b'application/json']
        ],
        'content': json.dumps({'hello': 'tom'}).encode()
    }


def test_not_found():
    message = {'path': '/goodbye/'}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert {
        'status': 404,
        'headers': [
            [b'content-type', b'text/plain']
        ],
        'content': b'Not Found'
    }


def test_redirect():
    message = {'path': '/hello'}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert channels['reply'].message == {
        'status': 301,
        'headers': [
            [b'content-type', b'text/plain'],
            [b'location', b'/hello/']
        ],
        'content': b'Moved Permanently'
    }


def test_method_not_allowed():
    message = {'path': '/hello/', 'method': 'POST'}
    channels = {'reply': MockReplyChannel()}
    run_task(app(message, channels))
    assert channels['reply'].message == {
        'status': 405,
        'headers': [
            [b'content-type', b'text/plain']
        ],
        'content': b'Method Not Allowed'
    }


async def http_routes(message, channels):
    await channels['reply'].send('http')


async def websocket_routes(message, channels):
    await channels['reply'].send('websocket')


async def wildcard_routes(message, channels):
    await channels['reply'].send('wildcard')


switched = ChannelSwitch({
    'http.request': http_routes,
    'websocket.*': websocket_routes,
    '*': wildcard_routes
})


def test_channel_switcher():
    message, channels = {'channel': 'http.request'}, {'reply': MockReplyChannel()}
    run_task(switched(message, channels))
    assert channels['reply'].message == 'http'

    message, channels = {'channel': 'websocket.connect'}, {'reply': MockReplyChannel()}
    run_task(switched(message, channels))
    assert channels['reply'].message == 'websocket'

    message, channels = {'channel': 'unknown'}, {'reply': MockReplyChannel()}
    run_task(switched(message, channels))
    assert channels['reply'].message == 'wildcard'


def test_unknown_channel_switch():
    switched = ChannelSwitch({
        'http.request': http_routes,
        'websocket.*': websocket_routes
    })

    message, channels = {'channel': 'unknown'}, {'reply': MockReplyChannel()}
    with pytest.raises(Exception):
        run_task(switched(message, channels))
