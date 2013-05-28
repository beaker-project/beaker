# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)

# We import from a subpackage to ensure we can handle multiple sys.path
# entries correctly (for example, when the released RPMs are installed on
# the system while we're actually running from a development checkout)

# We get away with having extra code in a namespace package __init__.py file
# because this is the module that provides that file for the Linux system
# packages

# Use an absolute import for Python 2.4 compatibility on RHEL 5
from bkr.common import __version__
