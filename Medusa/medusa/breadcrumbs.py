"""
module the supplies bread crumb type navigation information

breadcrumbs.py is a derivative of http://docs.turbogears.org/1.0/BreadCrumb
with additional guidances from Marco Mariani <marco at sferacarta dot com> via
the TG list.

this module makes no assumptions about the types of controllers or other 
imports.  Add it to your project, then import it in your controllers.py with::

    import breadcrumbs
  
Next modify your template by adding the following template snippet (assumes kid 
templating)::

    <div id="navbar">
        <span py:for="breadcrumbURL,breadcrumbName in tg.breadcrumbs()">
            <a class="menu" href="${breadcrumbURL}">${breadcrumbName}</a>
        </span>
    </div>
"""
__revision__ = "$Rev: 5 $"
import turbogears as tg
import cherrypy

def breadcrumbs():
    """
    Return link information for constructing bread crumb navigation.
    
    @rtype: list
    @return: a list of items(list) consisting of [breadcrumbURL, breadcrumbName]
    """
    cherry_trail = cherrypy._cputil.get_object_trail()
    #normalize the root path using tg.url()
    href = tg.url('/')
    crumbs = [(href, 'home')]
    for item in cherry_trail:
        # item[0] is the name you use in the URL to access the controller.
        # item[1] is the actual controller
        if item[1] is not None:
            if item[0] != 'root' and item[0] != 'index':
                href = tg.url("%s%s/" % (href, item[0]))
                crumbs.append([href, item[0]])
    return crumbs

def addvars(tgvars):
    """
    function which adds an key:value pair to an existing dictionary -- in this case the 
    dictionary is the builtin TG standard variables
    
    @param  vars: the builtin TG standard variables dictionary
    @type     vars: dictionary
    
    @rtype: None
    """
    tgvars['breadcrumbs'] = breadcrumbs

# now update the built in TG standard variables
tg.view.variable_providers.append(addvars)