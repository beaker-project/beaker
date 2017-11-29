
# encoding: utf8

# Copyright (c) 2006 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#
# Author: David Malcolm

# IMPORTANT. This file (testinfo.py) still remains in rhts as well.
# When making any changes to this file, please assess what changes (if any) are needed
# to be made in the corresponding file in rhts.
import re
import sys
import codecs

namespaces = [ ('desktop', ['evolution', 'openoffice.org', 'poppler', 'shared-mime-info']),
               ('tools', ['gcc']),
               ('CoreOS', ['rpm']),
               ('cluster', []),
               ('rhn', []) ]

def get_namespace_for_package(packageName):
    for (namespace, packages) in namespaces:
        if packageName in packages:
            return namespace

    # not found:
    return None
    
class TestInfo:
    """Class representing metadata about a test, suitable for outputting as a
    testinfo.desc file"""
    def __init__(self):
        self.test_name = None
        self.test_description = None
        self.test_archs = []
        self.owner = None
        self.testversion = None
        self.releases = []
        self.priority = None
        self.destructive = None
        self.license = None
        self.confidential = None
        self.avg_test_time = None
        self.test_path = None
        self.requires = []
        self.rhtsrequires = []
        self.runfor = []
        self.bugs = []
        self.types = []
        self.needs = []
        self.need_properties = []
        self.siteconfig = []
        self.kickstart = None
        self.options = []
        self.environment = {}
        self.provides = []

    def output_string_field(self, file, fileFieldName, dictFieldName):
        value = self.__dict__[dictFieldName]
        if value:
            file.write(u'%s: %s\n'%(fileFieldName, value))

    def output_string_list_field(self, file, fileFieldName, dictFieldName):
        value = self.__dict__[dictFieldName]
        if value:
            file.write(u'%s: %s\n'%(fileFieldName, u' '.join(value)))

    def output_string_dict_field(self, file, fileFieldName, dictFieldName):
        value = self.__dict__[dictFieldName]
        if value:
            for key, val in value.items():
                if val:
                    file.write(u'%s: %s=%s\n'%(fileFieldName, key, val))

    def output_bool_field(self, file, fileFieldName, dictFieldName):        
        value = self.__dict__[dictFieldName]
        if value is not None:
            if value:
                strValue = u"yes"
            else:
                strValue = u"no"
            file.write(u'%s: %s\n'%(fileFieldName, strValue))

    def output(self, file):
        """
        Write out a testinfo.desc to the file object
        """
        file = codecs.getwriter('utf8')(file)
        self.output_string_field(file, u'Name', u'test_name')
        self.output_string_field(file, u'Description', u'test_description')
        self.output_string_list_field(file, u'Architectures', u'test_archs')
        self.output_string_field(file, u'Owner', u'owner')
        self.output_string_field(file, u'TestVersion', u'testversion')
        self.output_string_list_field(file, u'Releases', u'releases')
        self.output_string_field(file, u'Priority', u'priority')
        self.output_bool_field(file, u'Destructive', u'destructive')
        self.output_string_field(file, u'License', u'license')
        self.output_bool_field(file, u'Confidential', u'confidential')
        self.output_string_field(file, u'TestTime', u'avg_test_time')
        self.output_string_field(file, u'Path', u'test_path')
        self.output_string_list_field(file, u'Requires', u'requires')
        self.output_string_list_field(file, u'RhtsRequires', u'rhtsrequires')
        self.output_string_list_field(file, u'RunFor', u'runfor')
        self.output_string_list_field(file, u'Bugs', u'bugs')
        self.output_string_list_field(file, u'Type', u'types')
        self.output_string_list_field(file, u'RhtsOptions', u'options')
        self.output_string_dict_field(file, u'Environment', u'environment')
        self.output_string_list_field(file, u'Provides', u'provides')
        for (name, op, value) in self.need_properties:
            file.write(u'NeedProperty: %s %s %s\n'%(name, op, value))
        file.write(self.generate_siteconfig_lines())
        
    def generate_siteconfig_lines(self):
        result = ""
        for (arg, description) in self.siteconfig:
            if self.test_name:
                if arg.startswith(self.test_name):
                    # Strip off common prefix:
                    arg = arg[len(self.test_name)+1:]
            result += u'SiteConfig(%s): %s\n'%(arg, description)
        return result
        
class Validator:
    """
    Abstract base class for validating fields
    """
    pass

class RegexValidator(Validator):
    def __init__(self, pattern, message):
        self.pattern = pattern
        self.msg = message

    def is_valid(self, value):
        return re.match(self.pattern, value)

    def message(self):
        return self.msg

class UnicodeRegexValidator(RegexValidator):
    """
    Validates against a regexp pattern but with the re.UNICODE flag applied
    so that character classes like \w have their "Unicode-aware" meaning.
    """
    def is_valid(self, value):
        return re.match(self.pattern, value, re.UNICODE)

# This is specified in RFC2822 Section 3.4, 
# we accept only the most common variations
class NameAddrValidator(UnicodeRegexValidator):

    ATOM_CHARS = r"\w!#$%&'\*\+-/=?^_`{|}~"
    PHRASE = r' *[%s][%s ]*' % (ATOM_CHARS, ATOM_CHARS)
    ADDR_SPEC = r'[%s.]+@[%s.]+' % (ATOM_CHARS, ATOM_CHARS)
    NAME_ADDR = r'%s<%s> *' % (PHRASE, ADDR_SPEC)

    def __init__(self):
        RegexValidator.__init__(self, self.NAME_ADDR,
                'should be a valid RFC2822 name_addr, '
                'such as John Doe <jdoe@somedomain.org>')

class ListValidator(Validator):
    def __init__(self, validValues):
        self.validValues = validValues

    def is_valid(self, value):
        return value in self.validValues

    def message(self):
        errorMsg = 'valid values are'
        for value in self.validValues:
            errorMsg += ' "%s"'%value
        return errorMsg

class DashListValidator(ListValidator):
    def is_valid(self, value):
        if value.startswith('-'):
            value = value[1:]
        return ListValidator.is_valid(self, value)

    def message(self):
        return ListValidator.message(self) + " optionally prefixed with '-'"

class BoolValidator(Validator):
    def __init__(self):
        pass

    def convert(self, value):
        if re.match("y|yes|1", value):
            return True

        if re.match("n|no|0", value):
            return False

        return None

    def is_valid(self, value):
        return self.convert(value) is not None

    def message(self):
        return "boolean value expected"


class Parser:
    """
    Parser for testinfo.desc files
    """
    def __init__(self):
        self.info = TestInfo()

        # All of these could be populated based on a DB query if we wanted to structure things that way:
        self.valid_root_ns = [
            'distribution', 
            'installation', 
            'kernel', 
            'desktop', 
            'tools', 
            'CoreOS', 
            'cluster', 
            'rhn', 
            'examples',
            'performance',
            'ISV',
            'virt'
            ]
        
        self.root_ns_with_mnt_tests_subtree = ['distribution', 'kernel']
        
        self.valid_architectures = [
            'ia64', 
            'x86_64', 
            'ppc', 
            'ppc64', 
            'ppc64le',
            's390', 
            's390x', 
            'i386',
            'aarch64',
            'arm',
            'armhfp',
            ]
        
        self.valid_priorities = [
            'Low', 
            'Medium', 
            'Normal', 
            'High', 
            'Manual'
            ]

        self.valid_options = [
            'Compatible',
            'CompatService',
            'StrongerAVC',
            ]
        
    def handle_error(self, message):
        raise NotImplementedError

    def handle_warning(self, message):
        raise NotImplementedError

    def error_if_not_in_array(self, fieldName, value, validValues):
        if not value in validValues:
            errorMsg = '"%s" is not a valid value for %s; valid values are'%(value, fieldName);
            for validValue in validValues:
                errorMsg += ' "%s"'%validValue
            self.handle_error(errorMsg)

    def __mandatory_field(self, fileFieldName, dictFieldName):
        if not self.info.__dict__[dictFieldName]:
            self.handle_error("%s field not defined"%fileFieldName)

    def __unique_field(self, fileFieldName, dictFieldName, value, validator=None):
        if self.info.__dict__[dictFieldName]:
            self.handle_error("%s field already defined"%fileFieldName)

        self.info.__dict__[dictFieldName] = value

        if validator:
            if not validator.is_valid(value):
                self.handle_error('"%s" is not a valid %s field (%s)'%(value, fileFieldName, validator.message()))

    def __bool_field(self, fileFieldName, dictFieldName, raw_value):
        validator = BoolValidator()
        if not validator.is_valid(raw_value):
            self.handle_error('"%s" is not a valid %s field (%s)'
                    % (raw_value, fileFieldName, validator.message()))
        value = validator.convert(raw_value)
        self.__unique_field(fileFieldName, dictFieldName, value)

    def _handle_dict(self, fileFieldName, dictFieldName, value, validator=None, key_validator=None):
        kv = value.split("=", 1)
        if len(kv) < 2:
            self.handle_error("Malformed %s field not matching KEY=VALUE pattern" % fileFieldName)
            return
        k, v = kv
        d = getattr(self.info, dictFieldName)
        if d.has_key(k):
            self.handle_error("%s: Duplicate entry for %r" % (fileFieldName, k))
            return
        if key_validator and not key_validator.is_valid(k):
            self.handle_error('"%s" is not a valid key for %s field (%s)'%(k, fileFieldName, key_validator.message()))
            return
        if validator and not validator.is_valid(v):
            self.handle_error('"%s" is not a valid %s field (%s)'%(v, fileFieldName, validator.message()))
            return
        d[k] = kv[1]

    def _handle_unique_list(self, fileFieldName, dictFieldName, value, validator=None, split_at=" "):
        l = getattr(self.info, dictFieldName)
        if l:
            self.handle_error("%s field already defined"%fileFieldName)
            return
        items = value.split(split_at)
        if validator:
            for item in items:
                if not validator.is_valid(item):
                    self.handle_error('"%s" is not a valid %s field (%s)'%(item, fileFieldName, validator.message()))
                    continue
                l.append(item)
        else:
            l.extend(items)

    def handle_name(self, key, value):
        self.__unique_field(key, 'test_name', value)

        if not re.match('^/', value):
            self.handle_error("Name field does not begin with a forward-slash")
            return
                
        name_frags= value.split('/')
        
        #print name_frags
        root_ns = name_frags[1]
        
        self.info.test_name_root_ns = root_ns
        self.info.test_name_under_root_ns = "/".join(name_frags[2:])
        self.info.expected_path_under_mnt_tests_from_name = self.info.test_name_under_root_ns
        # print "name_under_root_ns: %s"%self.info.test_name_under_root_ns            
        self.info.test_name_frags = name_frags

    def handle_desc(self, key, value):
        self.__unique_field(key, 'test_description', value)

    def handle_owner(self, key, value):
        # Required one-only email addresses "John Doe <someone@some.domain.org>"
        # In theory this could be e.g. memo-list@redhat.com; too expensive to check for that here
        self.__unique_field(key, 'owner', value, NameAddrValidator())

    def handle_testversion(self, key, value):
        self.__unique_field(key, 'testversion', value, RegexValidator(r'^([A-Za-z0-9\.]*)$', 'can only contain numbers, letters and the dot symbol'))
        # FIXME: we can probably support underscores as well

    def handle_license(self, key, value):
        self.__unique_field(key, 'license', value)

    def handle_deprecated(self, key, value):
        self.handle_warning("%s field is deprecated"%key)

    def handle_releases(self, key, value):
        self.__unique_field(key, 'releases', value)

        num_negative_releases = 0
        num_positive_releases = 0

        releases = []
        for release in value.split(" "):
            #print "Got release: release"

            releases.append(release)
            m = re.match('^-(.*)', release)
            if m:
                cleaned_release = m.group(1)
                # print "Got negative release: %s"%cleaned_release
                num_negative_releases+=1
            else:
                cleaned_release = release
                # print "Got positive release: %s"%release
                num_positive_releases+=1

            if num_negative_releases>0 and num_positive_releases>0:
                self.handle_warning("Releases field lists both negated and non-negated release names (should be all negated, or all non-negated)")
        self.info.releases = releases

    def handle_archs(self, key, value):
        self.__unique_field(key, 'test_archs', value)

        archs = []
        for arch in value.split(" "):
            self.error_if_not_in_array("Architecture", arch.lstrip('-'), self.valid_architectures)
            archs.append(arch)
        if any(arch.startswith('-') for arch in archs) and not all(arch.startswith('-') for arch in archs):
            self.handle_warning("Architectures field lists both negated and non-negated architectures (should be all negated, or all non-negated)")
        self.info.test_archs = archs

    def handle_options(self, key, value):
        self._handle_unique_list(key, 'options', value, DashListValidator(self.valid_options))

    def handle_environment(self, key, value):
        self._handle_dict(key, 'environment', value, key_validator=RegexValidator(r'^([A-Za-z_][A-Za-z0-9_]*)$', 'Can contain only letters, numbers and underscore.'))

    def handle_priority(self, key, value):
        self.__unique_field(key, 'priority', value, ListValidator(self.valid_priorities))

    def handle_destructive(self, key, value):
        self.__bool_field(key, 'destructive', value)

    def handle_confidential(self, key, value):
        self.__bool_field(key, 'confidential', value)

    def handle_testtime(self, key, value):
        if self.info.avg_test_time:
            self.handle_error("%s field already defined"%key)
            return

        # TestTime is an integer with an optional minute (m) or hour (h) suffix
        m = re.match('^(\d+)(.*)$', value)
        if m:
            self.info.avg_test_time = int(m.group(1))
            suffix = m.group(2)
            if suffix == '':
                pass # no units means seconds
            elif suffix == 'm':
                self.info.avg_test_time *= 60
            elif suffix == 'h':
                self.info.avg_test_time *= 3600
            else:
                self.handle_warning("TestTime unit is not valid, should be m (minutes) or h (hours)")
                return

            if self.info.avg_test_time<60:
                self.handle_warning("TestTime should not be less than a minute")

        else:
            self.handle_error("Malformed %s field"%key)

    def handle_type(self, key, value):
        for type in value.split(" "):
            self.info.types.append(type)
    
    def handle_kickstart(self, key, value):
        self.info.kickstart = value
    
    def handle_bug(self, key, value):
        for bug in value.split(" "):
            # print "Got bug: %s"%bug

            m = re.match('^([1-9][0-9]*)$', bug)
            if m:
                self.info.bugs.append(int(m.group(1)))
            else:
                self.handle_error('"%s" is not a valid Bug value (should be numeric)'%bug)
                
    def handle_path(self, key, value):
        if self.info.test_path:
            self.handle_error("Path field already defined")

        if re.match(r'^\/mnt\/tests\/', value):
            absolute_path = value
        else:
            if re.match(r'^\/', value):
                self.handle_error("Path field is absolute but is not below /mnt/tests")

            # Relative path:

            absolute_path = "/mnt/tests/"+value

        self.info.test_path = absolute_path

    def handle_runfor(self, key, value):
        for pkgname in value.split(" "):
            self.info.runfor.append(pkgname)

    def handle_requires(self, key, value):
        for pkgname in value.split(" "):
            self.info.requires.append(pkgname)

    def handle_rhtsrequires(self, key, value):
        for pkgname in value.split(" "):
            self.info.rhtsrequires.append(pkgname)

    def handle_provides(self, key, value):
        for pkgname in value.split(" "):
            self.info.provides.append(pkgname)

    def handle_needproperty(self, key, value):
        m = re.match(r'^([A-Za-z0-9]*)\s+(=|>|>=|<|<=)\s+([A-Z:a-z0-9]*)$', value)
        if m:
            self.info.needs.append(value)
            self.info.need_properties.append((m.group(1), m.group(2), m.group(3)))
        else:
            self.handle_error('"%s" is not a valid %s field; %s'%(value, key, "must be of the form PROPERTYNAME {=|>|>=|<|<=} PROPERTYVALUE"))

    def handle_deprecated_for_needproperty(self, key, value):
        self.handle_error("%s field is deprecated.  Use NeedProperty instead"%key)

    def __handle_siteconfig(self, arg, value):
        if re.match('^/.*', arg):
            # Absolute path:
            absPath = arg
        else:
            # Relative path:
            if self.info.test_name:
                absPath = self.info.test_name + '/' + arg
            else:
                self.handle_error("A relative SiteConfig(): declaration appeared before a Name: field")
                return
        self.info.siteconfig.append( (absPath, value) )
    
    def __handle_declaration(self, decl, arg, value):
        # print 'decl:  "%s"'%decl
        # print 'arg:   "%s"'%arg
        # print 'value: "%s"'%value

        if decl=="SiteConfig":
            self.__handle_siteconfig(arg, value)
        else:
            self.handle_error('"%s" is not a valid declaration"')
        
    def parse(self, lines):
        # Map from field names to value-parsing methods:
        fields = {'Name' : self.handle_name,
                  'Description' : self.handle_desc,
                  'Notify' : self.handle_deprecated,
                  'Owner' : self.handle_owner,
                  'TestVersion' : self.handle_testversion,
                  'License' : self.handle_license,
                  'Releases': self.handle_releases,
                  'Architectures': self.handle_archs,
                  'RhtsOptions': self.handle_options,
                  'Environment': self.handle_environment,
                  'Priority': self.handle_priority,
                  'Destructive': self.handle_destructive,
                  'Confidential': self.handle_confidential,
                  'TestTime': self.handle_testtime,
                  'Type': self.handle_type,
                  'Bug': self.handle_bug,
                  'Bugs': self.handle_bug,
                  'Path': self.handle_path,
                  'RunFor': self.handle_runfor,
                  'Requires': self.handle_requires,
                  'RhtsRequires': self.handle_rhtsrequires,
                  'NeedProperty': self.handle_needproperty,
                  'Need': self.handle_deprecated_for_needproperty,
                  'Want': self.handle_deprecated_for_needproperty,
                  'WantProperty': self.handle_deprecated_for_needproperty,
                  'Kickstart': self.handle_kickstart,
                  'Provides': self.handle_provides,
                  }

        self.lineNum = 0;
        for line in lines:
            self.lineNum+=1

            # print $line_num," ",$line;

            # Skip comment lines:
            if re.match('^#', line):
                continue

            line = line.strip()
 
            # Skip pure whitespace:
            if line=='':
                continue

            # Handle declarations e.g. "SiteConfig(server):  hostname of server"
            m = re.match('([^:]*)\((.*)\):(.*)', line)
            if m:
                (decl, arg, value) = (m.group(1), m.group(2), m.group(3))

                # Deal with it, stripping whitespace:
                self.__handle_declaration(decl, arg.strip(), value.strip())
                continue

            # Handle key/value pairs e.g.: "Bug: 123456"
            m = re.match('([^:]*):(.*)', line)
            if not m:
                self.handle_error("Malformed \"Key: value\" line")
                continue
            
            (key, value) = (m.group(1), m.group(2))
            
            # Strip leading and trailing whitespace:
            value = value.strip()

            # Note that I'm not quoting the values; this isn't talking direct to a DB
            if key in fields:
                handler = fields[key]
                handler(key, value)

        # Postprocessing:
	# Ensure mandatory fields have values:
        self.__mandatory_field('Name', 'test_name')
        self.__mandatory_field('Description', 'test_description')
        self.__mandatory_field('Path', 'test_path')
        self.__mandatory_field('TestTime', 'avg_test_time')
        self.__mandatory_field('TestVersion', 'testversion')
        self.__mandatory_field('License', 'license')
        self.__mandatory_field('Owner', 'owner')


class PrintingParser(Parser):
    """
    A parser which handles errors/warnings by printing messages to a file object
    """
    def __init__(self, outputFileObj, inputFilename):
        Parser.__init__(self)
        self.outputFileObj = outputFileObj
        self.inputFilename = inputFilename
        self.numErrors = 0
        self.numWarnings = 0

    def handle_message(self, message, severity):
        # Try to mimic the format of a GCC output line, e.g.:
        # tmp.c:1: error: your code sucks
        print >> self.outputFileObj, "%s:%i: %s: %s"%(self.inputFilename, self.lineNum, severity, message)

    def handle_error(self, message):
        self.handle_message(message, "error")
        self.numErrors+=1

    def handle_warning(self, message):
        self.handle_message(message, "warning")
        self.numWarnings+=1

class StdoutParser(PrintingParser):
    """
    A parser which handles errors/warnings by printing messages to stdout
    """
    def __init__(self, inputFilename):
        PrintingParser.__init__(self, sys.stdout, inputFilename)
    
class StderrParser(PrintingParser):
    """
    A parser which handles errors/warnings by printing messages to stderr
    """
    def __init__(self, inputFilename):
        PrintingParser.__init__(self, sys.stderr, inputFilename)


class ParserError(Exception):
    pass

class ParserWarning(Exception):
    pass

class StrictParser(Parser):
    def __init__(self, raise_errors):
        Parser.__init__(self)
        self.raise_errors = raise_errors
    
    def handle_error(self, message):
        if self.raise_errors:
            raise ParserError(message)

    def handle_warning(self, message):
        if self.raise_errors:
            raise ParserWarning(message)

def parse_string(string, raise_errors = True):
    assert isinstance(string, unicode)
    p = StrictParser(raise_errors)
    p.parse(string.split("\n"))
    return p.info

def parse_file(filename, raise_errors = True):
    p = StrictParser(raise_errors)
    p.parse(codecs.open(filename, 'r', 'utf8').readlines())
    return p.info
