# -*- coding: utf-8 -*-
"""
    flaskext.csrf
    ~~~~~~~~~~~~~

    A small Flask extension for adding CSRF protection.

    :copyright: (c) 2010 by Steve Losh.
    :license: MIT, see LICENSE for more details.
"""

import os
from base64 import b64encode, b64decode

from flask import abort, request, session, g
from itsdangerous import (
    JSONWebSignatureSerializer, constant_time_compare, bytes_to_int,
    int_to_bytes
)
from werkzeug.routing import NotFound

_exempt_views = []


def csrf_exempt(view):
    _exempt_views.append(view)
    return view


def csrf(app, on_csrf=None):
    @app.before_request
    def _csrf_check_exemptions():
        try:
            dest = app.view_functions.get(request.endpoint)
            g._csrf_exempt = dest in _exempt_views
        except NotFound:
            g._csrf_exempt = False
    
    @app.before_request
    def _csrf_protect():
        if request.method in ("POST", "DELETE", "PUT") and not g._csrf_exempt:
            csrf_secret = session.get('_csrf_secret')
            csrf_token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')

            if is_csrf_token_bad(csrf_token, csrf_secret):
                if on_csrf:
                    on_csrf(*app.match_request())
                abort(400)
   
    def is_csrf_token_bad(token, csrf_secret):
        try:
            jsw = JSONWebSignatureSerializer(app.secret_key) 
            tobj = jsw.loads(token)

            nonce_int = bytes_to_int(b64decode(tobj["n"]))
            key_int = bytes_to_int(b64decode(tobj["k"]))

            user_secret = int_to_bytes(nonce_int ^ key_int)

            return not constant_time_compare(
                user_secret,
                csrf_secret        
            )
        except Exception as exc:
            return True

    def generate_csrf_token():
        nonce = os.urandom(16)
        secret = session.setdefault('_csrf_secret', os.urandom(16))

        nonce_int = bytes_to_int(nonce)
        secret_int = bytes_to_int(secret)

        jsw = JSONWebSignatureSerializer(app.secret_key) 
        token = jsw.dumps({
            "n": b64encode(nonce),
            "k": b64encode(int_to_bytes(nonce_int ^ secret_int))
        })
        
        return token

    app.jinja_env.globals['csrf_token'] = generate_csrf_token

