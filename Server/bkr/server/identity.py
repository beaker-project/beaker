
import os
import errno
import logging
import string
from functools import wraps
import urllib
import itsdangerous
import cherrypy, cherrypy.filters.basefilter
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
    token_value = {'user_name': cherrypy.request._beaker_validated_user.user_name}
    if cherrypy.request._beaker_proxied_by_user is not None:
        token_value['proxied_by_user_name'] = \
            cherrypy.request._beaker_proxied_by_user.user_name
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

def check_authentication():
    """
    Checks the current request for:
        * REMOTE_USER in the WSGI environment, indicating that the container 
          has already authenticated the request for us; or
        * a valid signed token, indicating that the user has authenticated to 
          us successfully on a previous request.
    Sets up the "current identity" state according to what's found.
    Also sets a fresh signed token, in order to update the timestamp.
    """
    # cherrypy.request.login is set to REMOTE_USER in a WSGI environment
    if cherrypy.request.login:
        # strip realm if present
        user_name, _, realm = cherrypy.request.login.partition('@')
        proxied_by_user_name = None
    elif _token_cookie_name in cherrypy.request.simple_cookie:
        token = cherrypy.request.simple_cookie[_token_cookie_name].value
        if token == 'deleted':
            return
        token_value = _check_token(token)
        if not token_value or 'user_name' not in token_value:
            return
        user_name = token_value['user_name']
        proxied_by_user_name = token_value.get('proxied_by_user_name', None)
    else:
        return
    # XXX transaction -- are we inside or outside of sa_rwt? does it matter?
    from bkr.server.model import User
    user = User.by_user_name(user_name.decode('utf8'))
    if user is None:
        return
    if not user.can_log_in():
        return
    if proxied_by_user_name is not None:
        proxied_by_user = User.by_user_name(proxied_by_user_name.decode('utf8'))
        if proxied_by_user is None:
            return
        if not proxied_by_user.can_log_in():
            return
    else:
        proxied_by_user = None
    cherrypy.request._beaker_validated_user = user
    cherrypy.request._beaker_proxied_by_user = proxied_by_user
    cherrypy.response.simple_cookie[_token_cookie_name] = _generate_token()
    cherrypy.response.simple_cookie[_token_cookie_name]['path'] = '/'

def set_authentication(user, proxied_by=None):
    """
    Sets the "current identity" to be the given user, and also sets a signed 
    cookie on the response so that they can be re-authenticated on subsequent 
    requests.

    IMPORTANT: the caller is promising that they have already authenticated the 
    user (by checking their password or other means).
    """
    cherrypy.request._beaker_validated_user = user
    cherrypy.request._beaker_proxied_by_user = proxied_by
    cherrypy.response.simple_cookie[_token_cookie_name] = _generate_token()
    cherrypy.response.simple_cookie[_token_cookie_name]['path'] = '/'

def clear_authentication():
    del cherrypy.request._beaker_validated_user
    cherrypy.response.simple_cookie[_token_cookie_name] = 'deleted'
    cherrypy.response.simple_cookie[_token_cookie_name]['path'] = '/'

class IdentityFilter(cherrypy.filters.basefilter.BaseFilter):

    def before_main(self):
        check_authentication()

# Mimics the identity.current interface (SqlAlchemyIdentity) from TurboGears:

class CurrentIdentity(object):

    @property
    def user(self):
        """
        The currently authenticated user, or None.

        :rtype: User or None
        """
        return getattr(cherrypy.request, '_beaker_validated_user', None)

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
        return getattr(cherrypy.request, '_beaker_proxied_by_user', None)

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
    def _decorator(func):
        @wraps(func)
        def _decorated(*args, **kwargs):
            predicate.check()
            return func(*args, **kwargs)
        return _decorated
    return _decorator
