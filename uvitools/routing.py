import http
import json
import traceback
from typing import Callable, List
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Rule, Map


class Route(object):
    def __init__(self, path: str, app: Callable, methods: List[str]=None, name: str=None):
        if name is None:
            name = 'id<%d>' % id(app)
        self.path, self.app, self.methods, self.name = (path, app, methods, name)


class Router(object):
    def __init__(self, routes: List[Route]):
        mapping = Map([
            Rule(route.path, endpoint=route.name, methods=route.methods)
            for route in routes
        ])
        self.adapter = mapping.bind('')
        self.apps = {
            route.name: route.app for route in routes
        }

    async def routing_exception(self, message, channels):
        exc = message['exc']

        status = exc.code
        headers = [[b'content-type', b'text/plain']]
        content = http.HTTPStatus(status).phrase.encode()

        if getattr(exc, 'new_url', ''):
            location = exc.new_url
            if location.startswith('http:///'):
                location = location[7:]
            headers.append([b'location', location.encode()])

        await channels['reply'].send({
            'status': status,
            'headers': headers,
            'content': content
        })

    async def __call__(self, message, channels):
        path, method = message['path'], message.get('method', 'GET')
        try:
            endpoint, args = self.adapter.match(path, method)
        except HTTPException as exc:
            message['exc'] = exc
            await self.routing_exception(message, channels)
        else:
            message['args'] = args
            app = self.apps[endpoint]
            await app(message, channels)


class ChannelSwitch(object):
    def __init__(self, mapping):
        literal_mappings = {}
        wildcard_mappings = []

        for name, app in mapping.items():
            if name.endswith('*'):
                wildcard_mappings.append((name[:-1], app))
            else:
                literal_mappings[name] = app

        self.literal_mappings = literal_mappings
        self.wildcard_mappings = sorted(wildcard_mappings, key=lambda item: -len(item[0]))

    async def switch_exception(self, message, channels):
        raise Exception('Could not route channel "%s"' % message['channel'])

    async def __call__(self, message, channels):
        channel = message['channel']
        try:
            app = self.literal_mappings[channel]
        except KeyError:
            for name, app in self.wildcard_mappings:
                if channel.startswith(name):
                    break
            else:
                await self.switch_exception(message, channels)
        await app(message, channels)
