# Since bkr is a namespace package (and thus cannot have version specific
# code in bkr.__init__), the version details are retrieved from here in
# order to correctly handle module shadowing on sys.path

__version__ = '28.3'
