# uvitools

[![Build Status](https://travis-ci.org/encode/uvitools.svg?branch=master)](https://travis-ci.org/encode/uvitools)
[![Package version](https://badge.fury.io/py/uvitools.svg)](https://pypi.python.org/pypi/uvitools)
[![Python versions](https://img.shields.io/pypi/pyversions/uvitools.svg)](https://www.python.org/doc/versions/)

A collection of tools for working with the uvicorn messaging interface.

Documentation: http://www.uvicorn.org/

Currently includes:

* Routing.
* Debug middleware.
* Broadcast middleware. (Implemented with Redis pub/sub)
* WSGI->ASGI and ASGI->WSGI adapters. (Provisional)

Things to be added:

* Static files middleware.
* Postgres LISTEN/NOTIFY based broadcast middleware.
* Redis channel layer adapter.
* Request parsing.
* Possibly request/response classes?
* Possibly direct-to-django-channels adapter?
