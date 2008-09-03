from cherrypy import request
from turbogears import validators
from turbogears.widgets import RepeatingFormField, register_static_directory
from turbogears.widgets import CSSLink, JSLink

class ExpandingForm(RepeatingFormField):
    javascript = [JSLink('tg_expanding_form_widget', 'javascript/expanding_form.js'), ]
    css = [CSSLink('tg_expanding_form_widget', 'css/expanding_form.css'), ]
    template = "tg_expanding_form_widget.templates.expanding_form"
    
    def display(self, value=None, **params):
        if value and isinstance(value, list) and len(value) > 1:
            params['repetitions'] = len(value)
        
        # If this form has already been validated and is being shown again because
        #   of a validation error, then set the correct number of repetitions to
        #   what existed when the form was submitted (i.e. including JavaScript
        #   added/remove fields).
        # if self.is_validated:
        if self.error:
            # Note: this line may not work if this widget is embedded lower than the
            #   the top of the widget tree.  It may be necessary to use self.fq_name
            #   for this case, maybe?
            input_values = request.input_values.get(self.name, None)
            if input_values and isinstance(input_values, list) and len(input_values) > 1:
                params['repetitions'] = len(input_values)
        
        return super(ExpandingForm, self).display(value, **params)
    


import os.path
import pkg_resources

pkg_path = pkg_resources.resource_filename('tg_expanding_form_widget', 'javascript')
register_static_directory("tg_expanding_form_widget/javascript", pkg_path)
pkg_path = pkg_resources.resource_filename('tg_expanding_form_widget', 'css')
register_static_directory("tg_expanding_form_widget/css", pkg_path)
