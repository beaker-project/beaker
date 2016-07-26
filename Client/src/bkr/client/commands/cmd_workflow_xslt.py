# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.client.task_watcher import *
from bkr.client import BeakerCommand
from optparse import OptionValueError, OptionGroup
import ConfigParser
import sys, os, re
import libxml2, libxslt


class JobArguments(object):
    "Internal object for the JobConfiguration class - A simple argument container"

    def __init__(self):
        "Constructor"
        self.arguments = {}
        self.current = None
        self.current_node = None
        self.re_tag = re.compile('(.*)(\[@(.*)=(.*)\])')

    def AddArgument(self, name, argtype, tagname, tagvaltype, tagvalname, tagnamelmnt,
                    value, optional):
        "Registers a new argument with a unique name"
        self.arguments[name] = {'argtype': argtype,
                                'optional': optional,
                                'tagname': tagname,
                                'tagvaluetype': tagvaltype,
                                'tagvaluename': tagvalname,
                                'tagname_childs': tagnamelmnt,
                                'value': value,
                                'processed': False}


    def GetArgumentKeys(self):
        "Returns all the unique argument keys"
        return self.arguments.keys()


    def GetNextArgumentOnTag(self, tagname):
        """Returns an argument setup for a specific XML tag which has
not yet been processed.  When all arguments for the given
tagname are processed, None will be returned"""

        for key in self.arguments.keys():
            if self.arguments[key]['processed'] is False and self.arguments[key]['tagname'] == tagname:
                self.current = key
                return self.arguments[key]
        return None


    def CreateTag(self, key):
        """Creates an libxml2.xmlNode for a given argument key.  It
returns the tag name and the created xmlNode."""

        tagname = self.arguments[key]['tagname']
        rxp = self.re_tag.match(tagname)
        if rxp:
            res = rxp.groups()
            if len(res) != 4:
                raise Exception("Error in <tag/> - value '%s' is not parseable" % tagname)

            tagnode = libxml2.newNode(res[0])
            tagnode.newProp(res[2].strip("\"'"), res[3].strip("\"'"))
        else:
            tagnode = libxml2.newNode(tagname)

        self.current_node = tagnode;
        return (tagname, tagnode)


    def CreateChildTag(self, key):
        """Create a child node for a node created by CreateTag(), used by lists"""

        tagname = self.arguments[key]['tagname_childs']
        tagnode = libxml2.newNode(tagname)
        self.current_node.addChild(tagnode)
        return tagnode


    def IsValid(self, key):
        "Returns True if the argument has a value if it is not an optional argument"
        return not (self.arguments[key]['optional'] is False and self.arguments[key]['value'] is None)


    def IsProcessed(self, key):
        "Returns True if the argument has been processed"
        return self.arguments[key]['processed']


    def SetValue(self, key, value):
        "Sets a new value for an argument"
        self.arguments[key]['value'] = value


    def SetProcessed(self):
        "Marks the argument returned by GetNextArgumentOnTag() as processed"
        self.arguments[self.current]['processed'] = True


    def PrintArguments(self):
        "Dumps the registered arguments which are set to stdout"
        print '   Job arguments:'
        for key in self.arguments.keys():
            if self.arguments[key]['value'] is not None:
                print '     - %s: %s' % (key, self.arguments[key]['value'])



class JobConfig(object):
    "Class which parses the job configuration XML and validates the script arguments parameters"

    def __init__(self, argpars, jobdefaults):
        "Constructor - Needs a optparse.OptionParser object and a JobDefaults object"

        self.argpars       = argpars
        self.grparser      = OptionGroup(argpars, 'XSLT Job Config Specific Options',
                                                  'These options are specific to and defined in '\
                                                  'the Job Configuration XML')
        self.defaults      = jobdefaults

        self.jobargs       = JobArguments()
        self.internalxml   = None
        self.beakerxml     = None
        self.whiteboard    = None
        self.savexml       = None
        self.saveintxml    = None
        self.xslt          = None
        self.xsltfile      = None
        self.xslt_nodes    = None
        self.xslt_override = None
        self.xslt_name     = None
        self.__jobxml_parsed = False

        # Add global job options
        globgrp = OptionGroup(argpars, 'Global XSLT Workflow Options',
                                       'Generic options for the parser and Beaker XML generator')
        globgrp.add_option('--xslt-override', None, dest='xslt_override',
                           type='string', default=None, metavar='FILENAME', action='store',
                           help='Override the XSLT file to use')
        globgrp.add_option('-X', '--xslt-name', dest='xslt_name',
                           type='string', default=None, metavar='NAME', action='store',
                           help='Use another named XSLT template defined in the job XML')
        globgrp.add_option('-W','--whiteboard', dest='whiteboard',
                           type='string', default=None, metavar='TEXT', action='store',
                           help='Whiteboard text for the job')
        globgrp.add_option('--save-xml', None, dest='savexml',
                           type='string', metavar='FILENAME', action='store',
                           help='Save Beaker XML to FILENAME')
        globgrp.add_option('--save-internal-xml', None, dest='saveintxml',
                           type='string', metavar='FILENAME', action='store',
                           help='Save raw submission XML to FILENAME')
        argpars.add_option_group(globgrp)


    def parserCB_ParseJobXML(self, option, opt_str, value, parser):
        "Callback function used by optparse for parsing the given job XML file"

        # Check that not more --job-xml arguments are used
        if parser.values.jobxml is not None:
            raise OptionValueError('You cannot use %s multiple times' % opt_str)

        if value is None:
            return

        # Parse the Job XML
        try:
            self.ParseJobXML(parser, value)
            setattr(parser.values, option.dest, value)
            self.defaults.parserCBhelper_jobxml_parsed()
        except Exception, e:
            # Re-throw the exception as optparse.OptionValueError instead
            raise OptionValueError(str(e))


    def ParseJobXML(self, parser, jobxml):
        "Parses the given --job-xml file and extends the group option parser with the configured arguments"

        if jobxml is None:
            raise Exception('No Job XML file given')

        try:
            jobcfg = libxml2.parseFile(jobxml)
        except Exception, e:
            raise Exception('Failed to parse Job XML (%s): %s' % (jobxml, str(e)))

        # Extract job config name and XSLT file to use
        xp = jobcfg.xpathNewContext()
        try:
            self.name = xp.xpathEval('/jobConfig/name')[0].get_content()
            self.xslt_nodes = xp.xpathEval('/jobConfig/xslt')
            if self.xslt_nodes is None or len(self.xslt_nodes) < 1:
                raise Exception('Job XML (%s) is missing <xslt/> tag(s)' % jobxml)
        except IndexError:
            raise Exception('Job XML (%s) is missing <name/> and/or <xslt/> tags' % jobxml)

        # Parse /jobConfig/arguments/arg tags
        arguments = {}
        jobdefaults = self.defaults.GetJobDefaults(jobxml)

        for xnode in xp.xpathEval('/jobConfig/arguments/arg'):
            if xnode.name != 'arg' or xnode.prop('section') != 'recipe':
                continue

            # Extract information from the <arg section='recipe' [type='xxxx'] [optional='1']/> tag
            # The only supported 'section' type is 'recipe' at the moment.  This
            # will define which XML tags which will be added in the internal
            # XML document.  The values will be defined inside the //submit/recipe tag.
            #
            # <arg/> attribues:
            # - type: defaults to string.  Can be 'string' or 'bool
            # - optional: Will mark the argument as optional if set to 1.  If not optional
            #   the option parser will complain about missing options to the command line
            #
            argtype     = xnode.prop('type') or 'string'
            argoptional = xnode.prop('optional') == '1'
            argaction   = (argtype == 'bool') and 'store_true' or 'store'
            arglong     = None
            argshort    = None
            argmetavar  = None
            argdefault  = None
            tagname     = None
            tagvaltype  = None
            tagnamelmnt = None
            descr       = None

            # Parse the <arg/> children nodes
            node = xnode.children.next
            while node:
                if node.name == 'text':
                    # We ignore pure text nodes - should not be processed here
                    node = node.next
                    continue
                elif node.name == 'name':
                    # <name short='{short arg}'/> tag
                    # - Defines the long option name in the text node and the short option
                    #   is defined via the 'short' attribute.
                    arglong = node.get_content().strip()
                    if node.prop('short'):
                        argshort = node.prop('short').strip()
                elif node.name == 'tag':
                    # <tag type='{string, attribute}' [attrname='attribute name']/>
                    # - Defines the XML tag name for the internal XML this option will set.  If
                    #   type is 'string' the given tag content value will be used for as the
                    #   tag name.  If type is 'attribute' it will be added as an XML tag attribute
                    #   to the tag defined by the (text node) value.  The name of the attribute
                    #   variable is set by a required 'attrname' attribute in the <tag/>.
                    tagname = node.get_content().strip()
                    tagvaltype = node.hasProp('type') and node.prop('type').strip() or None
                    tagvalname = node.hasProp('attrname') and node.prop('attrname').strip() or None
                    tagnamelmnt = None
                    if tagvaltype == "list":
                        tagnamelmnt = node.hasProp('element_tag') and node.prop('element_tag') or 'value'
                elif node.name == 'description':
                    # <description/>
                    # - Describes the option in plain English, used by the --help screen
                    descr = ' '.join([s.strip() for s in node.get_content().expandtabs(1).split(' ') if len(s.strip()) > 0])
                elif node.name == 'metavar':
                    # <metavar/>
                    # - Defines a illustrative option value, used by the --help screen
                    argmetavar = node.get_content().strip()

                elif node.name == 'default':
                    # <default/>
                    # - Will give a default value to the option if the option is not given
                    #   via the command line
                    argdefault = node.get_content().strip()

                node = node.next

            # Some quick sanity checks on important tags
            if arglong is None or len(arglong) < 1:
                raise Exception('The <name/> tag must be present with a value.')

            # We need tagname and tag-value-type
            if tagname is None or tagvaltype is  None:
                raise Exception("The <tag/> tag on '%s' must be present with a "
                                "value and must have a 'type' attribute" % arglong)

            # Make sure tag-value-type is of a known type
            if tagvaltype != 'value' and tagvaltype != 'attribute' and tagvaltype != 'list':
                raise Exception("The <tag/> type attribute on '%s' must be either "
                                "'value', 'attribute' or 'list'" % arglong)

            # If 'attribute' we need an attribute name too
            if tagvaltype == 'attribute' and tagvalname is None:
                raise Exception("The <tag/> on '%s' is missing a 'name' attribute" % arglong);

            # If we have another default value from the bks-defaults file, use that instead
            if jobdefaults.has_key(arglong):
                argdefault = jobdefaults[arglong]

            # If argument type is 'bool', remove type flag
            # as 'store_true' cannot have type flag in optparse
            op_argtype = (argtype != 'bool' and argtype or None)

            # Register the entry as a command line argument
            if argshort is not None and len(argshort) > 0:
                self.grparser.add_option('-%s' % argshort,
                                         '--%s' % arglong,
                                         dest=arglong,
                                         type=op_argtype,
                                         default=argdefault,
                                         metavar=argmetavar,
                                         action=argaction,
                                         help='%s%s (default: %s)' %
                                         (argoptional and 'Optional, ' or 'Required, ', descr, argdefault)
                                         )
            else:
                self.grparser.add_option('--%s' % arglong,
                                         dest=arglong,
                                         type=op_argtype,
                                         default=argdefault,
                                         metavar=argmetavar,
                                         action=argaction,
                                         help='%s%s (default: %s)' %
                                         (argoptional and 'Optional, ' or 'Required, ', descr, argdefault)
                                         )

            # Save some important information about this option
            self.jobargs.AddArgument(arglong, argtype, tagname, tagvaltype, tagvalname, tagnamelmnt,
                                     argdefault, argoptional)

        parser.add_option_group(self.grparser)
        self.__jobxml_parsed = True
        del jobcfg
    # EOFNC: def ParseJobXML()


    def ValidateArguments(self, kwargs):
        "Validates command line arguments, and checks if all required arguments are set"

        if self.__jobxml_parsed is False:
            self.argpars.error('Missing --job-xml <filename>.  See --help for more information.')

        # Validate the input from the command line
        # against what the XML jobConfig defines
        for optkey in self.jobargs.GetArgumentKeys():
            try:
                optval = kwargs.get(optkey, None)
            except AttributeError, e:
                raise e
                # optval = None

            if optval is None:
                if not self.jobargs.IsValid(optkey):
                    raise Exception('Missing required argument: --%s' %optkey)
            else:
                self.jobargs.SetValue(optkey, optval)

        # Save global arguments we need
        self.whiteboard    = kwargs.get('whiteboard', None)
        self.savexml       = kwargs.get('savexml', None)
        self.saveintxml    = kwargs.get('saveintxml', None)
        self.xslt_override = kwargs.get('xslt_override', None)
        self.xslt_name     = kwargs.get('xslt_name', None)

    def LoadXSLT(self):
        "Loads the XSLT file configured in the Job XML or overridden by the command line ."

        no_error_print = False
        try:
            if self.xslt_override is None:
                # Which XSLT file should we load?
                if len(self.xslt_nodes) > 1:
                    for n in self.xslt_nodes:
                        if self.xslt_name is None and n.hasProp('name') is None:
                            # If no named XSLT template is given, grab the <xslt/>
                            # without a name attribute
                            self.xsltfile = n.get_content()
                            break
                        elif self.xslt_name is not None and n.hasProp('name') is not None:
                            # If looking for a named XSLT template
                            if n.prop('name') == self.xslt_name:
                                self.xsltfile = n.get_content()
                                break
                else:
                    self.xsltfile = self.xslt_nodes[0].get_content()
            else:
                self.xsltfile = self.xslt_override
                self.xslt_name = None

            if self.xsltfile is None:
                no_error_print = True
                if self.xslt_name:
                    raise Exception("No matching <xslt/> tag was found for the named XSLT '%s'." %
                                    self.xslt_name)
                else:
                    raise Exception('No XSLT file is configured')

            # Do the loading and XSLT document parsing
            xsltdoc = libxml2.parseFile(self.xsltfile)
            self.xslt = libxslt.parseStylesheetDoc(xsltdoc)
            del self.xslt_nodes

        except Exception, e:
            if not no_error_print:
                print '** ERROR ** Failed to parse the XSLT template: %s'% self.xsltfile
            raise e


    def __format_xml_value(self, argtype, argvalue):
        "Private method: Formats an argument value for XML tags according to the argument type"

        if argtype == 'bool':
            # Convert Python True/False value to 'true' or 'false' string
            return argvalue is True and 'true' or 'false'
        else:
            # Pass through on all other types, using the native type
            return argvalue


    def __generate_internal_xml(self):
        "Private method: Generates the internal XML needed for XSLT template"

        # Generate new XML document and set <submit/> to be the root tag
        xml = libxml2.newDoc('1.0')
        submit_node = libxml2.newNode('submit')
        xml.setRootElement(submit_node)

        # Add white board text if set
        wb_node = libxml2.newNode('whiteboard')
        if self.whiteboard is not None:
            wb_node.addChild(libxml2.newText(self.whiteboard))
        submit_node.addChild(wb_node)

        # Add the recipe node ...
        recipe_node = libxml2.newNode('recipe')
        submit_node.addChild(recipe_node)

        # ... and add all the defined arguments
        for key in self.jobargs.GetArgumentKeys():
            if self.jobargs.IsProcessed(key):
                continue
            (tagname, tagnode) = self.jobargs.CreateTag(key)

            arg = self.jobargs.GetNextArgumentOnTag(tagname)
            while arg is not None:
                if arg['value']:
                    recipe_node.addChild(tagnode)
                    if arg['tagvaluetype'] == 'value':
                        tagnode.addChild(libxml2.newText(self.__format_xml_value(arg['argtype'], arg['value'])))
                    elif arg['tagvaluetype'] == 'attribute':
                        tagnode.newProp(arg['tagvaluename'], self.__format_xml_value(arg['argtype'], arg['value']))
                    elif arg['tagvaluetype'] == "list":
                        for listval in arg["value"].split(","):
                            tagchild_n = self.jobargs.CreateChildTag(key)
                            tagchild_n.addChild(libxml2.newText(listval))
                    else:
                        raise Exception("Unknown <tag/> type '%s' found in '%s'"
                                        % (arg['tagvaluetype'], key))

                self.jobargs.SetProcessed()
                arg = self.jobargs.GetNextArgumentOnTag(tagname)

        return xml


    def GenerateXML(self):
        """Generates the internal submit XML document and parses it through
the defined XSLT template.  Returns and libxml2.xmlDoc containing the
result of the XSLT processing"""
        if self.xsltfile is None:
            raise Exception('No XSLT file has been loaded (Have JobConfig::LoadXSLT() been called?)')
        if self.internalxml is None:
            self.internalxml = self.__generate_internal_xml()
        self.beakerxml = self.xslt.applyStylesheet(self.internalxml, None)
        return self.beakerxml


    def GetBeakerXMLasString(self):
        """Returns the XML result of GenerateXML() as a string"""
        if self.beakerxml is None:
            raise Exception('Beaker XML has not been generated yet  - hint: JobConfig::GenerateXML()')
        return self.xslt.saveResultToString(self.beakerxml).decode(self.xslt.encoding())


    def GetBeakerXMLdoc(self):
        """Returns the libxml2.xmlDoc of the XML result from GenerateXML()"""
        if self.beakerxml is None:
            raise Exception('Beaker XML has not been generated yet  - hint: JobConfig::GenerateXML()')
        return self.beakerxml


    def SaveBeakerXML(self, name):
        """Saves the parsed result of GenerateXML() to a given file"""
        self.beakerxml.saveFormatFileEnc(name,'UTF-8', 1)


    def GetInternalXMLdoc(self):
        """Returns the internal XML document as a libxml2.xmlDoc, used for the
XSLT parsing.  This is most useful for debugging only"""
        if self.internalxml is None:
            self.internalxml = self.__generate_internal_xml()
        return self.internalxml


    def GetGlobalJobArguments(self):
        """Returns the global command line arguments as an dictionary"""
        return {'beakerxml': self.savexml,
                'internalxml': self.saveintxml,
                'whiteboard': self.whiteboard,
                'xslt_name': self.xslt_name}


    def GetJobName(self):
        """Returns the job name set in the job configuration XML"""
        return self.name


    def GetXSLTfilename(self):
        """Returns the XSLT template filename defined in the job configuration XML"""
        return self.xsltfile


    def PrintJobArguments(self):
        """Prints all the job specific arguments to the screen"""
        return self.jobargs.PrintArguments()



class JobDefaults(ConfigParser.ConfigParser):
    "Configuration file parser for default settings"

    def __init__(self):
        self.vars = {'profile': None, 'parsed-files': []}
        self.__jobxml_parsed = False
        ConfigParser.ConfigParser.__init__(self)

        deffiles=('%s/.beaker-client/bks-defaults' % os.path.expanduser('~'),
                  'bks-defaults'
                  )
        self.read(deffiles)


    def read(self, fname):
        "A wrapper around ConfigParser.ConfigParser.read()"

        ConfigParser.ConfigParser.read(self, fname)
        self.vars['parsed-files'].append(fname)


    def parserCB_UpdateConfig(self, option, opt_str, value, parser):
        "Used by the optparse object as a callback function for the --defaults argument"
        if not self.__jobxml_parsed:
            try:
                self.read(value)
                setattr(parser.values, option.dest, value)
            except Exception, e:
                raise OptionValueError('Failed to parse configuration file (%s): %s' % (value, e))
        else:
            raise OptionValueError('--defaults cannot be used after --job-xml')


    def SetProfile(self, profile):
        if len(profile) > 0:
            self.vars['profile'] = profile
        else:
            raise OptionValueError('--profile is lacking a profile name')


    def parserCB_SetProfile(self, option, opt_str, value, parser):
        "Used by the optparse object as a callback function for the --profile argument"

        if not self.__jobxml_parsed:
            setattr(parser.values, option.dest, value)
            self.SetProfile(value)
        else:
            raise OptionValueError('--profile cannot be used after --job-xml')


    def parserCBhelper_jobxml_parsed(self):
        self.__jobxml_parsed = True


    def GetDefaultJobXML(self):
        "Returns the configured default Job XML file if configured, otherwise NULL"
        try:
            return self.get('defaults', 'jobxml')
        except ConfigParser.NoOptionError:
            # Ignore if the 'jobxml' setting is not found
            return None
        except ConfigParser.NoSectionError:
            # Ignore if the 'defaults' section is not found
            return None


    def GetJobDefaults(self, jobfname):
        "Extracts the configured job defaults for the defined Job XML and defaults profile"
        jobdefaults = {}
        try:
            fname = os.path.basename(jobfname)
            section = self.vars['profile'] is not None and '%s:%s' % (fname, self.vars['profile']) or fname
            for d in [{k: v} for k,v in self.items(section)]:
                jobdefaults.update(d)
        except ConfigParser.NoSectionError:
            if self.vars['profile'] is not None:
                # if we have a defaults profile set, complain about the miss
                raise OptionValueError("There is no defaults profile '%s' defined for %s" %
                                       (self.vars['profile'], fname))
            else:
                # if not, we don't care about it
                pass

        return jobdefaults



class Workflow_XSLT(BeakerCommand):
    """XSLT workflow - Generates beaker jobs based on XSLT templates"""
    enabled = True

    def __init__(self, parser):
        self.__job_def = JobDefaults()
        self.__job_cfg = JobConfig(parser, self.__job_def)
        self.parser = parser


    def options(self):
        super(Workflow_XSLT, self).options()

        # HACK: Check if --job-xml or --profile is used on the command line
        # If we find --profile - steal the argument to prepare
        # JobDefaults for it.  This improves the --help screen where
        # default values are shown
        defjobxml = None
        jobxml_cmdline = False
        grab_profile = False
        for args in sys.argv:
            if not grab_profile:
                if args.startswith('--job-xml'):
                    jobxml_cmdline = True
                elif args.startswith('--profile='):
                    self.__job_def.SetProfile(args.split('=')[1])
                elif args == '--profile':
                    grab_profile = True
            else:
                self.__job_def.SetProfile(args)
                grab_profile = False

        if grab_profile is True:
            raise OptionValueError('--profile is lacking a profile name')


        # If --job-xml is not in the command line, parse the defaults file
        if defjobxml is None and not jobxml_cmdline:
            defjobxml = self.__job_def.GetDefaultJobXML()
            if defjobxml is not None:
                self.__job_cfg.ParseJobXML(self.parser, defjobxml)

        self.parser.add_option('--defaults', action='callback', callback=self.__job_def.parserCB_UpdateConfig,
                               nargs=1, type='string', metavar='FILENAME',
                               help='Load an additional defaults configuration')

        self.parser.add_option('--profile', action='callback', callback=self.__job_def.parserCB_SetProfile,
                                nargs=1, type='string', metavar='PROFILE-NAME',
                                help='Use a different configured defaults profile')

        self.parser.add_option('--job-xml', action='callback', callback=self.__job_cfg.parserCB_ParseJobXML,
                               nargs=1, type='string', metavar='FILENAME', dest='jobxml',
                               help='Job XML file (Default: %s)' % defjobxml)

        self.parser.add_option('--dry-run', None, dest='dryrun',
                               action='store_true',
                               help='Do not submit the job to beaker')

        self.parser.add_option('--wait', default=False, action='store_true', dest='wait',
                               help='Wait on job completion')

        self.parser.usage = '%%prog %s [options]' % self.normalized_name
    # EOFNC: def option()


    def run(self, *args, **kwargs):

        dryrun = kwargs.get('dryrun', False)
        jobxml = kwargs.get('jobxml', None)
        profile = kwargs.get('profile', None)
        wait = kwargs.get('wait', None)

        self.__job_cfg.ValidateArguments(kwargs)

        # Grab some collected info and parse the requested XSLT file
        globalargs = self.__job_cfg.GetGlobalJobArguments()
        self.__job_cfg.LoadXSLT()

        print '-' * 75
        print 'Generating Beaker XML'
        print '   Job config:       %s' % jobxml
        if profile:
            print '   Defaults profile: %s' % profile
        if globalargs['xslt_name']:
            print '   XSLT name:        %s' % globalargs['xslt_name']
        print '   XSLT template:    %s' % self.__job_cfg.GetXSLTfilename()
        print '   Job name:         %s' % self.__job_cfg.GetJobName()
        print '   Whiteboard:       %s' % globalargs['whiteboard']
        self.__job_cfg.PrintJobArguments()
        print '-' * 75

        # Do we want to save the internal XML used for the XSLT processing?
        saved = False
        if globalargs['internalxml']:
            self.__job_cfg.GetInternalXMLdoc().saveFormatFileEnc(globalargs['internalxml'], 'UTF-8', 1)
            saved = True

        # Do the main work - this does the XSLT processing
        self.__job_cfg.GenerateXML()

        # Fetch the result and do something with it

        # Do we want to save the Beaker XML in addition?
        if globalargs['beakerxml']:
            self.__job_cfg.SaveBeakerXML(globalargs['beakerxml'])
            saved = True

        # Send the job to Beaker, if it's not a dry-run.
        if not dryrun:
            print "** Sending job to Beaker ...",
            sys.stdout.flush()

            self.set_hub(**kwargs)
            submitted_jobs = []
            failed = False

            try:
                submitted_jobs.append(self.hub.jobs.upload(self.__job_cfg.GetBeakerXMLasString()))
                print "Success"
            except Exception, ex:
                print "FAIL"
                failed = True
                print ex

            print '** Submitted: %s' % submitted_jobs
            if wait:
                watch_tasks(self.hub, submitted_jobs)
            if failed:
                sys.exit(1)
        else:
            # If dryrun without saving anything, dump the Beaker XML to stdout
            if not saved:
                print self.__job_cfg.GetBeakerXMLasString()


