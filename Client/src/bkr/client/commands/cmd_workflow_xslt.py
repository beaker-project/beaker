# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import re
import sys
from optparse import OptionValueError, OptionGroup

from lxml import etree
from six.moves import configparser

from bkr.client import BeakerCommand
from bkr.client.task_watcher import *


def get_node_text(node):
    """
    Always return string representation for node text
    """
    if not node.text:
        return ''
    return node.text


class JobArguments(object):
    """
    Internal object for the JobConfiguration class - A simple argument container
    """

    def __init__(self):
        self.arguments = {}
        self.current = None
        self.current_node = None
        self.re_tag = re.compile('(.*)(\[@(.*)=(.*)\])')

    def add_argument(self, name, argtype, tagname, tagvaltype, tagvalname,
                     tagnamelmnt, value, optional):
        """
        Registers a new argument with a unique name
        """

        self.arguments[name] = {'argtype': argtype,
                                'optional': optional,
                                'tagname': tagname,
                                'tagvaluetype': tagvaltype,
                                'tagvaluename': tagvalname,
                                'tagname_childs': tagnamelmnt,
                                'value': value,
                                'processed': False}

    def get_argument_keys(self):
        """
        Returns all the unique argument keys
        """

        return self.arguments.keys()

    def get_next_argument_on_tag(self, tag_name):
        """
        Returns an argument setup for a specific XML tag which has
        not yet been processed.  When all arguments for the given
        tag_name are processed, None will be returned
        """

        for key in self.arguments.keys():
            if (self.arguments[key]['processed'] is False
                    and self.arguments[key]['tagname'] == tag_name):
                self.current = key
                return self.arguments[key]
        return None

    def create_tag(self, key):
        """
        Creates an etree.Element for a given argument key.
        It returns the tag name and the created Element.
        """

        tagname = self.arguments[key]['tagname']
        rxp = self.re_tag.match(tagname)
        if rxp:
            res = rxp.groups()
            if len(res) != 4:
                raise Exception("Error in <tag/> - value '%s' is not parsable" % tagname)

            tagnode = etree.Element(res[0])
            tagnode.set(res[2].strip("\"'"), res[3].strip("\"'"))
        else:
            tagnode = etree.Element(tagname)

        self.current_node = tagnode
        return tagname, tagnode

    def create_child_tag(self, key):
        """
        Create a child node for a node created by create_tag(), used by lists
        """

        tagname = self.arguments[key]['tagname_childs']
        tagnode = etree.Element(tagname)

        self.current_node.append(tagnode)
        return tagnode

    def is_valid(self, key):
        """
        Returns True if the argument has a value if it is not an optional argument
        """
        return not (self.arguments[key]['optional'] is False
                    and self.arguments[key]['value'] is None)

    def is_processed(self, key):
        """
        Returns True if the argument has been processed
        """
        return self.arguments[key]['processed']

    def set_value(self, key, value):
        """
        Sets a new value for an argument
        """
        self.arguments[key]['value'] = value

    def set_processed(self):
        """
        Marks the argument returned by get_next_argument_on_tag() as processed
        """
        self.arguments[self.current]['processed'] = True

    def print_arguments(self):
        """
        Dumps the registered arguments which are set to stdout
        """
        print('   Job arguments:')
        for key in self.arguments.keys():
            if self.arguments[key]['value'] is not None:
                print('     - %s: %s' % (key, self.arguments[key]['value']))


class JobConfig(object):
    """
    Class which parses the job configuration XML and validates the script arguments parameters
    """

    def __init__(self, argpars, jobdefaults):
        """
        Needs a optparse.OptionParser object and a JobDefaults object
        """

        self.argpars = argpars
        self.grparser = OptionGroup(argpars, 'XSLT Job Config Specific Options',
                                    'These options are specific to and defined in '
                                    'the Job Configuration XML')
        self.defaults = jobdefaults

        self.jobargs = JobArguments()
        self.internalxml = None
        self.beakerxml = None
        self.whiteboard = None
        self.savexml = None
        self.saveintxml = None
        self.xslt = None
        self.xsltfile = None
        self.xslt_nodes = None
        self.xslt_override = None
        self.xslt_name = None
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
        globgrp.add_option('-W', '--whiteboard', dest='whiteboard',
                           type='string', default=None, metavar='TEXT', action='store',
                           help='Whiteboard text for the job')
        globgrp.add_option('--save-xml', None, dest='savexml',
                           type='string', metavar='FILENAME', action='store',
                           help='Save Beaker XML to FILENAME')
        globgrp.add_option('--save-internal-xml', None, dest='saveintxml',
                           type='string', metavar='FILENAME', action='store',
                           help='Save raw submission XML to FILENAME')
        argpars.add_option_group(globgrp)

    def parse_job_xml_callback(self, option, opt_str, value, parser):
        """
        Callback function used by optparse for parsing the given job XML file
        """

        # Check that not more --job-xml arguments are used
        if parser.values.jobxml is not None:
            raise OptionValueError('You cannot use %s multiple times' % opt_str)

        if value is None:
            return

        # Parse the Job XML
        try:
            self.parse_job_xml(parser, value)
            setattr(parser.values, option.dest, value)
            self.defaults.job_xml_parsed_callback()
        except Exception as e:
            # Re-throw the exception as optparse.OptionValueError instead
            raise OptionValueError(str(e))

    def parse_job_xml(self, parser, jobxml):
        """
        Parses the given --job-xml file and extends the group
        option parser with the configured arguments
        """

        if jobxml is None:
            raise Exception('No Job XML file given')

        try:
            job_cfg = etree.parse(jobxml)
        except Exception as e:
            raise Exception('Failed to parse Job XML (%s): %s' % (jobxml, str(e)))

        # Extract job config name and XSLT file to use
        try:
            self.name = get_node_text(job_cfg.xpath('/jobConfig/name')[0])
            self.xslt_nodes = job_cfg.xpath('/jobConfig/xslt')
            if len(self.xslt_nodes) < 1:
                raise Exception('Job XML (%s) is missing <xslt/> tag(s)' % jobxml)
        except IndexError:
            # TODO : This raise can be removed (possibly)
            # missing <xslt> is raised before this line
            raise Exception('Job XML (%s) is missing <name/> and/or <xslt/> tags' % jobxml)

        # Parse /jobConfig/arguments/arg tags
        jobdefaults = self.defaults.get_job_defaults(jobxml)

        for xnode in job_cfg.xpath('/jobConfig/arguments/arg'):
            if xnode.attrib.get('section') != 'recipe':
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
            argtype = xnode.attrib.get('type') or 'string'
            argoptional = xnode.attrib.get('optional') == '1'
            argaction = (argtype == 'bool') and 'store_true' or 'store'
            arglong = None
            argshort = None
            argmetavar = None
            argdefault = None
            tagname = None
            tagvaltype = None
            tagnamelmnt = None
            descr = None

            # Parse the <arg/> children nodes
            for node in xnode.getchildren():
                if node.tag == 'text':
                    # We ignore pure text nodes - should not be processed here
                    continue
                elif node.tag == 'name':
                    # <name short='{short arg}'/> tag
                    # - Defines the long option name in the text node and the short option
                    #   is defined via the 'short' attribute.
                    arglong = get_node_text(node).strip()
                    if node.attrib.get('short'):
                        argshort = node.attrib['short'].strip()
                elif node.tag == 'tag':
                    # <tag type='{string, attribute}' [attrname='attribute name']/>
                    # - Defines the XML tag name for the internal XML this option will set.  If
                    #   type is 'string' the given tag content value will be used for as the
                    #   tag name.  If type is 'attribute' it will be added as an XML tag attribute
                    #   to the tag defined by the (text node) value.  The name of the attribute
                    #   variable is set by a required 'attrname' attribute in the <tag/>.
                    tagname = get_node_text(node).strip()
                    tagvaltype = ('type' in node.attrib and node.attrib['type'].strip() or None)
                    tagvalname = ('attrname' in node.attrib
                                  and node.attrib['attrname'].strip() or None)
                    tagnamelmnt = None
                    if tagvaltype == "list":
                        tagnamelmnt = ('element_tag' in node.attrib
                                       and node.attrib['element_tag'] or 'value')
                elif node.tag == 'description':
                    # <description/>
                    # - Describes the option in plain English, used by the --help screen
                    node_text = get_node_text(node)
                    descr = ' '.join([s.strip()
                                      for s in node_text.expandtabs(1).split(' ')
                                      if len(s.strip()) > 0])
                elif node.tag == 'metavar':
                    # <metavar/>
                    # - Defines a illustrative option value, used by the --help screen
                    argmetavar = get_node_text(node).strip()

                elif node.tag == 'default':
                    # <default/>
                    # - Will give a default value to the option if the option is not given
                    #   via the command line
                    argdefault = get_node_text(node).strip()


            # Some quick sanity checks on important tags
            if arglong is None or len(arglong) < 1:
                raise Exception('The <name/> tag must be present with a value.')

            # We need tagname and tag-value-type
            if tagname is None or tagvaltype is None:
                raise Exception("The <tag/> tag on '%s' must be present with a "
                                "value and must have a 'type' attribute" % arglong)

            # Make sure tag-value-type is of a known type
            if tagvaltype != 'value' and tagvaltype != 'attribute' and tagvaltype != 'list':
                raise Exception("The <tag/> type attribute on '%s' must be either "
                                "'value', 'attribute' or 'list'" % arglong)

            # If 'attribute' we need an attribute name too
            if tagvaltype == 'attribute' and tagvalname is None:
                raise Exception("The <tag/> on '%s' is missing a 'name' attribute" % arglong)

            # If we have another default value from the bks-defaults file, use that instead
            if arglong in jobdefaults:
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
                                              (argoptional and 'Optional, ' or 'Required, ', descr,
                                               argdefault)
                                         )
            else:
                self.grparser.add_option('--%s' % arglong,
                                         dest=arglong,
                                         type=op_argtype,
                                         default=argdefault,
                                         metavar=argmetavar,
                                         action=argaction,
                                         help='%s%s (default: %s)' %
                                              (argoptional and 'Optional, ' or 'Required, ', descr,
                                               argdefault)
                                         )

            # Save some important information about this option
            self.jobargs.add_argument(arglong, argtype, tagname, tagvaltype, tagvalname, tagnamelmnt,
                                      argdefault, argoptional)

        parser.add_option_group(self.grparser)
        self.__jobxml_parsed = True
        del job_cfg

    # EOFNC: def ParseJobXML()

    def validate_arguments(self, kwargs):
        """
        Validates command line arguments,
        and checks if all required arguments are set
        """
        if self.__jobxml_parsed is False:
            self.argpars.error('Missing --job-xml <filename>.  See --help for more information.')

        # Validate the input from the command line
        # against what the XML jobConfig defines
        for optkey in self.jobargs.get_argument_keys():
            try:
                optval = kwargs.get(optkey, None)
            except AttributeError as e:
                raise e

            if optval is None:
                if not self.jobargs.is_valid(optkey):
                    raise Exception('Missing required argument: --%s' % optkey)
            else:
                self.jobargs.set_value(optkey, optval)

        # Save global arguments we need
        self.whiteboard = kwargs.get('whiteboard', None)
        self.savexml = kwargs.get('savexml', None)
        self.saveintxml = kwargs.get('saveintxml', None)
        self.xslt_override = kwargs.get('xslt_override', None)
        self.xslt_name = kwargs.get('xslt_name', None)

    def load_xslt(self):
        """
        Loads the XSLT file configured in the Job XML or overridden by the command line.
        """

        no_error_print = False
        try:
            if self.xslt_override is None:
                # Which XSLT file should we load?
                # TODO: Possibly whole if can be removed and values sanitized
                if len(self.xslt_nodes) > 1:
                    for n in self.xslt_nodes:
                        if self.xslt_name is None and n.attrib.get('name') is None:
                            # If no named XSLT template is given, grab the <xslt/>
                            # without a name attribute
                            self.xsltfile = get_node_text(n)
                            break
                        elif self.xslt_name is not None and n.attrib.get('name') is not None:
                            # If looking for a named XSLT template
                            if n.prop('name') == self.xslt_name:
                                self.xsltfile = get_node_text(n)
                                break
                else:
                    self.xsltfile = get_node_text(self.xslt_nodes[0])
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
            style_doc = etree.parse(self.xsltfile)
            self.xslt = etree.XSLT(style_doc)
            del self.xslt_nodes

        except Exception as e:
            if not no_error_print:
                print('** ERROR ** Failed to parse the XSLT template: %s' % self.xsltfile)
            raise e

    @staticmethod
    def __format_xml_value(argtype, argvalue):
        """
        Formats an argument value for XML tags according to the argument type
        """

        if argtype == 'bool':
            # Convert Python True/False value to 'true' or 'false' string
            return argvalue is True and 'true' or 'false'
        else:
            # Pass through on all other types, using the native type
            return argvalue

    def __generate_internal_xml(self):
        """
        Generates the internal XML needed for XSLT template
        """

        # Generate new XML document and set <submit/> to be the root tag
        submit_node = etree.Element('submit')
        tree = etree.ElementTree(submit_node)

        # Add white board text if set
        wb_node = etree.Element('whiteboard')
        wb_node.text = self.whiteboard
        submit_node.append(wb_node)

        # Add the recipe node ...
        recipe_node = etree.Element('recipe')
        submit_node.append(recipe_node)

        # ... and add all the defined arguments
        for key in self.jobargs.get_argument_keys():
            if self.jobargs.is_processed(key):
                continue
            tag_name, tag_element = self.jobargs.create_tag(key)

            arg = self.jobargs.get_next_argument_on_tag(tag_name)
            while arg is not None:
                if arg['value']:
                    recipe_node.append(tag_element)
                    if arg['tagvaluetype'] == 'value':
                        tag_element.text = self.__format_xml_value(arg['argtype'], arg['value'])
                    elif arg['tagvaluetype'] == 'attribute':
                        tag_element.set(arg['tagvaluename'],
                                        self.__format_xml_value(arg['argtype'], arg['value']))
                    elif arg['tagvaluetype'] == "list":
                        for listval in arg["value"].split(","):
                            tagchild_n = self.jobargs.create_child_tag(key)
                            tagchild_n.text = listval
                    else:
                        raise Exception("Unknown <tag/> type '%s' found in '%s'"
                                        % (arg['tagvaluetype'], key))

                self.jobargs.set_processed()
                arg = self.jobargs.get_next_argument_on_tag(tag_name)

        return tree

    def generate_xml(self):
        """
        Generates the internal submit XML document and parses it through
        the defined XSLT template.

        Returns _XSLTResultTree containing the result of the XSLT processing
        """
        if self.xsltfile is None:
            raise Exception(
                'No XSLT file has been loaded (Have JobConfig::LoadXSLT() been called?)')
        if self.internalxml is None:
            self.internalxml = self.__generate_internal_xml()
        self.beakerxml = self.xslt(self.internalxml)
        return self.beakerxml

    def get_beaker_xml_string(self):
        """
        Returns the XML result of generate_xml() as a string
        """
        if self.beakerxml is None:
            raise Exception(
                'Beaker XML has not been generated yet  - hint: JobConfig::GenerateXML()')
        # TODO: str can return invalid XML. Instead of str we should use etree.tostring
        # Result will be None in case of invalid XML
        return str(self.beakerxml)

    def get_beaker_xml_doc(self):
        """
        Returns the _XSLTResultTree of the XML result from generate_xml()
        """
        if self.beakerxml is None:
            raise Exception(
                'Beaker XML has not been generated yet  - hint: JobConfig::GenerateXML()')
        return self.beakerxml

    def save_beaker_xml(self, filename):
        """
        Saves Beaker tree to a given file
        """
        with open(filename, 'wb') as fd:
            # TODO: Invalid XML can be returned without using etree.tostring
            self.beakerxml.write_output(fd)

    def save_internal_xml(self, filename):
        """
        Saves Internal tree to a given file
        """
        self.get_internal_xml_doc()  # Make sure Internal XML doc is generated
        with open(filename, 'wb') as fd:
            fd.write(etree.tostring(self.internalxml, encoding='utf-8', pretty_print=True))

    def get_internal_xml_doc(self):
        """
        Returns the internal XML document as a etree.ElementTree, used for the
        XSLT parsing.  This is most useful for debugging only
        """
        if self.internalxml is None:
            self.internalxml = self.__generate_internal_xml()
        return self.internalxml

    def get_global_job_args(self):
        """
        Returns the global command line arguments as an dictionary
        """
        return {
            'beakerxml': self.savexml,
            'internalxml': self.saveintxml,
            'whiteboard': self.whiteboard,
            'xslt_name': self.xslt_name
        }

    def get_job_name(self):
        """
        Returns the job name set in the job configuration XML
        """
        return self.name

    def get_xslt_filename(self):
        """
        Returns the XSLT template filename defined in the job configuration XML
        """
        return self.xsltfile

    def print_job_args(self):
        """
        Prints all the job specific arguments to the screen
        """
        return self.jobargs.print_arguments()


class JobDefaults(configparser.ConfigParser):
    """
    Configuration file parser for default settings
    """

    def __init__(self):
        self.vars = {'profile': None, 'parsed-files': []}
        self.__jobxml_parsed = False
        configparser.ConfigParser.__init__(self)

        deffiles = ('%s/.beaker-client/bks-defaults' % os.path.expanduser('~'),
                    'bks-defaults'
                    )
        self.read(deffiles)

    def read(self, fname):
        """
        Wrapper around ConfigParser.ConfigParser.read()
        """

        configparser.ConfigParser.read(self, fname)
        self.vars['parsed-files'].append(fname)

    def update_config_callback(self, option, opt_str, value, parser):
        """
        Used by the optparse object as a callback function for the --defaults argument
        """

        if not self.__jobxml_parsed:
            try:
                self.read(value)
                setattr(parser.values, option.dest, value)
            except Exception as e:
                raise OptionValueError('Failed to parse configuration file (%s): %s' % (value, e))
        else:
            raise OptionValueError('--defaults cannot be used after --job-xml')

    def set_profile(self, profile):
        if len(profile) > 0:
            self.vars['profile'] = profile
        else:
            raise OptionValueError('--profile is lacking a profile name')

    def set_profile_callback(self, option, opt_str, value, parser):
        """
        Used by the optparse object as a callback function for the --profile argument
        """

        if not self.__jobxml_parsed:
            setattr(parser.values, option.dest, value)
            self.set_profile(value)
        else:
            raise OptionValueError('--profile cannot be used after --job-xml')

    def job_xml_parsed_callback(self):
        self.__jobxml_parsed = True

    def get_default_job_xml(self):
        """
        Returns the configured default Job XML file if configured, otherwise NULL
        """

        try:
            return self.get('defaults', 'jobxml')
        except configparser.NoOptionError:
            # Ignore if the 'jobxml' setting is not found
            return None
        except configparser.NoSectionError:
            # Ignore if the 'defaults' section is not found
            return None

    def get_job_defaults(self, job_file_name):
        """
        Extracts the configured job defaults for the defined Job XML and defaults profile
        """

        job_defaults = {}

        try:
            file_name = os.path.basename(job_file_name)
            section = self.vars['profile'] is not None and '%s:%s' % (
            file_name, self.vars['profile']) or file_name

            for d in [{k: v} for k, v in self.items(section)]:
                job_defaults.update(d)
        except configparser.NoSectionError:
            if self.vars['profile'] is not None:
                # if we have a defaults profile set, complain about the miss
                raise OptionValueError("There is no defaults profile '%s' defined for %s" %
                                       (self.vars['profile'], file_name))
            else:
                # if not, we don't care about it
                pass

        return job_defaults


class Workflow_XSLT(BeakerCommand):
    """
    XSLT workflow - Generates beaker jobs based on XSLT templates
    """

    enabled = True

    def __init__(self, parser):
        self.job_def = JobDefaults()
        self.job_cfg = JobConfig(parser, self.job_def)
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
                    self.job_def.set_profile(args.split('=')[1])
                elif args == '--profile':
                    grab_profile = True
            else:
                self.job_def.set_profile(args)
                grab_profile = False

        if grab_profile is True:
            raise OptionValueError('--profile is lacking a profile name')

        # If --job-xml is not in the command line, parse the defaults file
        if defjobxml is None and not jobxml_cmdline:
            defjobxml = self.job_def.get_default_job_xml()
            if defjobxml is not None:
                self.job_cfg.parse_job_xml(self.parser, defjobxml)

        self.parser.add_option('--defaults', action='callback',
                               callback=self.job_def.update_config_callback,
                               nargs=1, type='string', metavar='FILENAME',
                               help='Load an additional defaults configuration')

        self.parser.add_option('--profile', action='callback',
                               callback=self.job_def.set_profile_callback,
                               nargs=1, type='string', metavar='PROFILE-NAME',
                               help='Use a different configured defaults profile')

        self.parser.add_option('--job-xml', action='callback',
                               callback=self.job_cfg.parse_job_xml_callback,
                               nargs=1, type='string', metavar='FILENAME', dest='jobxml',
                               help='Job XML file (Default: %s)' % defjobxml)

        self.parser.add_option('--dry-run', None, dest='dryrun',
                               action='store_true',
                               help='Do not submit the job to beaker')

        self.parser.add_option('--wait', default=False, action='store_true', dest='wait',
                               help='Wait on job completion')

        self.parser.usage = '%%prog %s [options]' % self.normalized_name

    def run(self, *args, **kwargs):

        dryrun = kwargs.get('dryrun', False)
        jobxml = kwargs.get('jobxml', None)
        profile = kwargs.get('profile', None)
        wait = kwargs.get('wait', None)

        self.job_cfg.validate_arguments(kwargs)

        # Grab some collected info and parse the requested XSLT file
        globalargs = self.job_cfg.get_global_job_args()
        self.job_cfg.load_xslt()

        print('-' * 75)
        print('Generating Beaker XML')
        print('   Job config:       %s' % jobxml)
        if profile:
            print('   Defaults profile: %s' % profile)
        if globalargs['xslt_name']:
            print('   XSLT name:        %s' % globalargs['xslt_name'])
        print('   XSLT template:    %s' % self.job_cfg.get_xslt_filename())
        print('   Job name:         %s' % self.job_cfg.get_job_name())
        print('   Whiteboard:       %s' % globalargs['whiteboard'])
        self.job_cfg.print_job_args()
        print('-' * 75)

        # Do we want to save the internal XML used for the XSLT processing?
        saved = False
        if globalargs['internalxml']:
            self.job_cfg.save_internal_xml(globalargs['internalxml'])
            saved = True

        # Do the main work - this does the XSLT processing
        self.job_cfg.generate_xml()

        # Fetch the result and do something with it

        # Do we want to save the Beaker XML in addition?
        if globalargs['beakerxml']:
            self.job_cfg.save_beaker_xml(globalargs['beakerxml'])
            saved = True

        # Send the job to Beaker, if it's not a dry-run.
        if not dryrun:
            print("** Sending job to Beaker ...", )
            sys.stdout.flush()

            self.set_hub(**kwargs)
            submitted_jobs = []
            failed = False

            try:
                submitted_jobs.append(self.hub.jobs.upload(self.job_cfg.get_beaker_xml_string()))
                print("Success")
            except Exception as ex:
                print("FAIL")
                failed = True
                print(ex)

            print('** Submitted: %s' % submitted_jobs)
            if wait:
                watch_tasks(self.hub, submitted_jobs)
            if failed:
                sys.exit(1)
        else:
            # If dryrun without saving anything, dump the Beaker XML to stdout
            if not saved:
                print(self.job_cfg.get_beaker_xml_string())
