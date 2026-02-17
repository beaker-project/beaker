# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
import sys
if sys.version_info[0] >= 3:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
else:
    try:
        __import__('pkg_resources').declare_namespace(__name__)
    except ImportError:
        from pkgutil import extend_path
        __path__ = extend_path(__path__, __name__)
