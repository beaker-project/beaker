
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import errno
import logging
from decorator import decorator
import itsdangerous
import cherrypy
import flask
from turbogears import config
from bkr.common.helpers import AtomicFileReplacement
from bkr.server.util import absolute_url

log = logging.getLogger(__name__)

_token_cookie_name = 'beaker_auth_token'
_fallback_key_path = '/var/lib/beaker/fallback-token-key'

def _get_serializer():
    key = config.get('visit.token_secret_key')
    if not key:
        # If the admin hasn't configured a secret key we generate one and keep 
        # it in /var/lib/beaker. Doing these filesystem operations all the time 
        # is less efficient, so admins should set a key in the config; this is 
        # just a convenience so that Beaker is usable with a default config.
        try:
            key = open(_fallback_key_path, 'r').read()
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise
            with AtomicFileReplacement(_fallback_key_path, mode=0600) as f:
                key = os.urandom(64)
                f.write(key)
    return itsdangerous.URLSafeTimedSerializer(key)

def _generate_token():
    token_value = {'user_name': flask.g._beaker_validated_user.user_name}
    if flask.g._beaker_proxied_by_user is not None:
        token_value['proxied_by_user_name'] = \
            flask.g._beaker_proxied_by_user.user_name
    return _get_serializer().dumps(token_value)

def _check_token(token):
    # visit.timeout (from TG) is in minutes, max_age is in seconds
    max_age = int(config.get('visit.timeout')) * 60
    try:
        return _get_serializer().loads(token, max_age=max_age)
    except itsdangerous.SignatureExpired:
        return False
    except itsdangerous.BadSignature:
        log.warning('Corrupted or tampered token value %r', token)
        return False

def _try_autocreate(user_name):
    """
    If the necessary WSGI environment variables are populated, automatically 
    creates a new Beaker user account based on their values and returns it. 
    Otherwise returns None.
    """
    from bkr.server.model import session, User
    if not flask.request.environ.get('REMOTE_USER_FULLNAME'):
        log.debug('User autocreation attempted for %r but '
                'REMOTE_USER_FULLNAME env var was not populated',
                user_name)
        return
    if not flask.request.environ.get('REMOTE_USER_EMAIL'):
        log.debug('User autocreation attempted for %r but '
                'REMOTE_USER_EMAIL env var was not populated',
                user_name)
        return
    user = User()
    user.user_name = user_name.decode('utf8')
    user.display_name = flask.request.environ['REMOTE_USER_FULLNAME'].decode('utf8')
    user.email_address = flask.request.environ['REMOTE_USER_EMAIL'].decode('utf8')
    session.add(user)
    session.flush()
    log.debug('Autocreated user %s', user)
    return user

def check_authentication():
    """
    Checks the current request for:
        * REMOTE_USER in the WSGI environment, indicating that the container 
          has already authenticated the request for us; or
        * a valid signed token, indicating that the user has authenticated to 
          us successfully on a previous request.
    Sets up the "current identity" state according to what's found.
    """
    from bkr.server.model import User
    if 'REMOTE_USER' in flask.request.environ:
        # strip realm if present
        user_name, _, realm = flask.request.environ['REMOTE_USER'].partition('@')
        user = User.by_user_name(user_name.decode('utf8'))
        if user is None and config.get('identity.autocreate', True):
            # handle automatic user creation if possible
            user = _try_autocreate(user_name)
        if user is None:
            log.debug('REMOTE_USER %r does not exist', user_name)
            return
        proxied_by_user = None
    elif _token_cookie_name in flask.request.cookies:
        token = flask.request.cookies[_token_cookie_name]
        if token == 'deleted':
            return
        token_value = _check_token(token)
        if not token_value or 'user_name' not in token_value:
            return
        user_name = token_value['user_name']
        user = User.by_user_name(user_name.decode('utf8'))
        if user is None:
            log.warning('Token claimed to be for non-existent user %r',
                    user_name)
            return
        # handle "proxy authentication" support
        proxied_by_user_name = token_value.get('proxied_by_user_name', None)
        if proxied_by_user_name:
            proxied_by_user = User.by_user_name(proxied_by_user_name.decode('utf8'))
            if proxied_by_user is None:
                log.warning('Token for %r claimed to be proxied by non-existent user %r',
                        user_name, proxied_by_user_name)
                return
            if not proxied_by_user.can_log_in():
                log.debug('Denying login for %r proxied by disabled user %r',
                        user_name, proxied_by_user_name)
                return
        else:
            proxied_by_user = None
    else:
        return
    if not user.can_log_in():
        log.debug('Denying login for disabled user %s', user)
        return
    flask.g._beaker_validated_user = user
    flask.g._beaker_proxied_by_user = proxied_by_user

def set_authentication(user, proxied_by=None):
    """
    Sets the "current identity" to be the given user.

    IMPORTANT: the caller is promising that they have already authenticated the 
    user (by checking their password or other means).
    """
    flask.g._beaker_validated_user = user
    flask.g._beaker_proxied_by_user = proxied_by

def clear_authentication():
    if hasattr(flask.g, '_beaker_validated_user'):
        del flask.g._beaker_validated_user
    if hasattr(flask.g, '_beaker_proxied_by_user'):
        del flask.g._beaker_proxied_by_user

def update_response(response):
    # visit.timeout (from TG) is in minutes, max_age is in seconds
    max_age = int(config.get('visit.timeout')) * 60
    if hasattr(flask.g, '_beaker_validated_user'):
        response.set_cookie(_token_cookie_name, _generate_token(),
                            max_age=max_age)
    else:
        response.set_cookie(_token_cookie_name, 'deleted', max_age=max_age)
    return response

# Mimics the identity.current interface (SqlAlchemyIdentity) from TurboGears:

class RequestRequiredException(RuntimeError):
    """
    The caller tried to touch identity.current outside of a request handler 
    (for example, in beakerd).
    """
    def __init__(self):
        super(RequestRequiredException, self).__init__(
                'identity.current is not available outside a request')

class CurrentIdentity(object):

    @property
    def user(self):
        """
        The currently authenticated user, or None.

        :rtype: User or None
        """
        if flask._app_ctx_stack.top is None:
            raise RequestRequiredException()
        return getattr(flask.g, '_beaker_validated_user', None)

    @property
    def groups(self):
        """
        Set of group names of which the currently authenticated user is 
        a member, or empty.

        :rtype: frozenset of str
        """
        if self.user is None:
            return frozenset()
        return frozenset(group.group_name for group in self.user.groups)

    @property
    def anonymous(self):
        return self.user == None

    @property
    def proxied_by_user(self):
        if flask._app_ctx_stack.top is None:
            raise RequestRequiredException()
        return getattr(flask.g, '_beaker_proxied_by_user', None)

current = CurrentIdentity()

# Mimics the identity.require decorator and predicates from TurboGears:

class IdentityFailure(cherrypy.HTTPRedirect, cherrypy.HTTPError):

    # This is a CherryPy exception, so normally it will be raised out to 
    # CherryPy which will return a redirect or other response as appropriate. 
    # For XML-RPC we instead catch it and return it as a fault.

    def __init__(self, message=None):
        self._message = message or _(u'Please log in')
        self.args = [self._message]
        if cherrypy.request.method not in ('GET', 'HEAD'):
            # Other HTTP methods cannot be safely redirected through the login 
            # form, so we will just show a 403.
            self.status = 403
        else:
            self.status = 302
            if current.anonymous:
                forward_url = cherrypy.request.path
                if cherrypy.request.query_string:
                    forward_url += '?%s' % cherrypy.request.query_string
                self.urls = [absolute_url('/login', forward_url=forward_url)]
            else:
                self.urls = [absolute_url('/forbidden', reason=message)]

    def set_response(self):
        # This is a bit awkward... CherryPy has two unrelated exceptions, 
        # HTTPRedirect for redirects and HTTPError for errors. We could be 
        # either.
        if self.status < 400:
            return cherrypy.HTTPRedirect.set_response(self)
        else:
            return cherrypy.HTTPError.set_response(self)

class IdentityPredicate(object):

    def __bool__(self):
        raise AssertionError('Do not use outside of @identity.require')

class NotAnonymousPredicate(IdentityPredicate):

    def check(self):
        if current.anonymous:
            raise IdentityFailure(_(u'Anonymous access denied'))

not_anonymous = NotAnonymousPredicate

class InGroupPredicate(IdentityPredicate):

    def __init__(self, group_name):
        self.group_name = group_name

    def check(self):
        if current.user is None:
            raise IdentityFailure(_(u'Anonymous access denied'))
        if not current.user.in_group([self.group_name]):
            raise IdentityFailure(_(u'Not member of group: %s') % self.group_name)

in_group = InGroupPredicate

class HasPermissionPredicate(IdentityPredicate):

    def __init__(self, permission_name):
        self.permission_name = permission_name

    def check(self):
        if current.user is None:
            raise IdentityFailure()
        if not current.user.has_permission(self.permission_name):
            raise IdentityFailure(_(u'Permission denied: %s') % self.permission_name)

has_permission = HasPermissionPredicate

def require(predicate):
    @decorator
    def require(func, *args, **kwargs):
        predicate.check()
        return func(*args, **kwargs)
    return require
