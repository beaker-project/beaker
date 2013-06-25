
from turbogears import config
import shlex
# pipes.quote has been moved to the more reasonable shlex.quote in Python 3.3:
# http://bugs.python.org/issue9723
import pipes

def _parse(s): # based on Cobbler's string_to_hash
    result = {}
    if isinstance(s, unicode):
        s = s.encode('utf8') # shlex.split can't handle unicode :-(
    for token in shlex.split(s or ''):
        if '=' not in token:
            result.setdefault(token, None)
            continue
        name, value = token.split('=', 1)
        if not name:
            continue

        if name in result.keys():
            if isinstance(result[name], list):
                result[name].append(value)
            else:
                result[name] = list([result[name], value])
        else:
            result[name] = value
    return result

def _unparse(d):
    # items are sorted for predictable ordering of the output,
    # but a better solution would be to use OrderedDict in Python 2.7+

    items = []
    for key, value in sorted(d.iteritems()):
        if value is None:
            items.append(key)
        else:
            if isinstance(value, list):
                for v in value:
                    items.append('%s=%s' % (key, pipes.quote(str(v))))
            else:
                items.append('%s=%s' % (key, pipes.quote(str(value))))

    return ' '.join(items)

def _consolidate(base, other): # based on Cobbler's consolidate
    result = dict(base)
    for key, value in other.iteritems():
        if key.startswith('!'):
            result.pop(key[1:], None)
        else:
            result[key] = value
    return result

class InstallOptions(object):

    """
    Convenience class for representing the set of (ks_meta, kernel_options,
    kernel_options_post) variables for generating kickstarts.

    This stuff is all derived in one way or another from Cobbler.
    """

    def __init__(self, ks_meta, kernel_options, kernel_options_post):
        self.ks_meta = ks_meta
        self.kernel_options = kernel_options
        self.kernel_options_post = kernel_options_post

    def __repr__(self):
        return '%s(ks_meta=%r, kernel_options=%r, kernel_options_post=%r)' \
                % (self.__class__.__name__, self.ks_meta, self.kernel_options,
                   self.kernel_options_post)

    @classmethod
    def from_strings(cls, ks_meta, kernel_options, kernel_options_post):
        return cls(_parse(ks_meta), _parse(kernel_options),
                _parse(kernel_options_post))

    def as_strings(self):
        return dict(ks_meta=_unparse(self.ks_meta),
                kernel_options=_unparse(self.kernel_options),
                kernel_options_post=_unparse(self.kernel_options_post))

    @property
    def kernel_options_str(self):
        return _unparse(self.kernel_options)

    @property
    def kernel_options_post_str(self):
        return _unparse(self.kernel_options_post)

    def combined_with(self, other):
        """
        Returns a new InstallOptions which is the result of taking these
        options as a base and overriding them with the given other options.
        """
        return InstallOptions(_consolidate(self.ks_meta, other.ks_meta),
                _consolidate(self.kernel_options, other.kernel_options),
                _consolidate(self.kernel_options_post, other.kernel_options_post))

def global_install_options():
    return InstallOptions.from_strings(
            config.get('beaker.ks_meta', ''),
            config.get('beaker.kernel_options', 'ksdevice=bootif'),
            config.get('beaker.kernel_options_post', ''))
