
from flask import Flask
from turbogears import config

# This is NOT the right way to do this, we should just use SCRIPT_NAME properly instead.
# But this is needed to line up with TurboGears server.webpath way of doing things.
class PrefixedFlask(Flask):
    def add_url_rule(self, rule, *args, **kwargs):
        prefixed_rule = config.get('server.webpath', '').rstrip('/') + rule
        return super(PrefixedFlask, self).add_url_rule(prefixed_rule, *args, **kwargs)

app = PrefixedFlask('bkr.server', static_folder='../../assets')
