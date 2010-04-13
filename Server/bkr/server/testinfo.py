#
# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or 
# redistribute it subject to the terms and conditions of the GNU General 
# Public License v.2.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: David Malcolm, Bill Peck

import re
import unittest
import os
import sys

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
        self.test_archs = None
        self.owner = None
        self.testversion = None
        self.releases = []
        self.test_archs = []
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

    def output_string_field(self, file, fileFieldName, dictFieldName):
        value = self.__dict__[dictFieldName]
        if value:
            file.write('%s: %s\n'%(fileFieldName, value))            

    def output_string_list_field(self, file, fileFieldName, dictFieldName):
        value = self.__dict__[dictFieldName]
        if value:
            file.write('%s: %s\n'%(fileFieldName, ' '.join(value)))

    def output_bool_field(self, file, fileFieldName, dictFieldName):        
        value = self.__dict__[dictFieldName]
        if value is not None:
            if value:
                strValue = "yes"
            else:
                strValue = "no"
            file.write('%s: %s\n'%(fileFieldName, strValue))

    def output(self, file):
        """
        Write out a testinfo.desc to the file object
        """
        self.output_string_field(file, 'Name', 'test_name')
        self.output_string_field(file, 'Description', 'test_description')
        self.output_string_list_field(file, 'Architectures', 'test_archs')
        self.output_string_field(file, 'Owner', 'owner')
        self.output_string_field(file, 'TestVersion', 'testversion')
        self.output_string_list_field(file, 'Releases', 'releases')
        self.output_string_field(file, 'Priority', 'priority')
        self.output_bool_field(file, 'Destructive', 'destructive')
        self.output_string_field(file, 'License', 'license')
        self.output_bool_field(file, 'Confidential', 'confidential')
        self.output_string_field(file, 'TestTime', 'avg_test_time')
        self.output_string_field(file, 'Path', 'test_path')
        self.output_string_list_field(file, 'Requires', 'requires')
        self.output_string_list_field(file, 'RhtsRequires', 'rhtsrequires')
        self.output_string_list_field(file, 'RunFor', 'runfor')
        self.output_string_list_field(file, 'Bugs', 'bugs')
        self.output_string_list_field(file, 'Type', 'types')
        for (name, op, value) in self.need_properties:
            file.write('NeedProperty: %s %s %s\n'%(name, op, value))
        file.write(self.generate_siteconfig_lines())
        
    def generate_siteconfig_lines(self):
        result = ""
        for (arg, description) in self.siteconfig:
            if self.test_name:
                if arg.startswith(self.test_name):
                    # Strip off common prefix:
                    arg = arg[len(self.test_name)+1:]
            result += 'SiteConfig(%s): %s\n'%(arg, description)
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

class BoolValidator(Validator):
    def __init__(self):
        pass

    def is_valid(self, value):
        if re.match("y|yes|1", value):
            return True

        if re.match("n|no|0", value):
            return True

        return False
    
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
            'ISV'
            ]
        
        self.root_ns_with_mnt_tests_subtree = ['distribution', 'kernel']
        
        self.valid_architectures = [
            'ia64', 
            'x86_64', 
            'ppc', 
            'ppc64', 
            's390', 
            's390x', 
            'i386'
            ]
        
        self.valid_priorities = [
            'Low', 
            'Medium', 
            'Normal', 
            'High', 
            'Manual'
            ]
        
        self.valid_properties = [
            'HOSTNAME', 
            'ARCH', 
            'PCIID', 
            'USBID', 
            'MODULE', 
            'CPUSPEED', 
            'CPUVENDOR', 
            'PROCESSORS', 
            'VENDOR', 
            'MODEL'
            ]
        
        self.valid_releases = [
            'RHEL2.1', 
            'RHEL3', 
            'RHEL4',
            'RHELServer5',
            'RHELClient5',
            'RHEL6',
            'FC4',
            'FC5',
            'FC6',
            'F7',
            'F8',
            'F9',
            'F10',
            'F11',
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

    def handle_name(self, key, value):
        self.__unique_field(key, 'test_name', value)

        if not re.match('^/', value):
            self.handle_error("Name field does not begin with a forward-slash")
            return
                
        name_frags= value.split('/')
        
        # Check root namespace:
        #print name_frags
        root_ns = name_frags[1]
        if not root_ns in self.valid_root_ns:
            self.handle_error("%s is not a valid root namespace (within %s)"%(root_ns, value))
        
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
        self.__unique_field(key, 'owner', value, RegexValidator(r'([A-Za-z ]*) <([-a-z\._]*)@[-a-z\.]*>', 'should be of the form "John Doe <jdoe@somedomain.org>"'))

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
            self.error_if_not_in_array("Architecture", arch, self.valid_architectures)
            archs.append(arch)
        self.info.test_archs = archs

    def handle_priority(self, key, value):
        self.__unique_field(key, 'priority', value, ListValidator(self.valid_priorities))

    def handle_destructive(self, key, value):
        self.__unique_field(key, 'destructive', value, BoolValidator())

    def handle_confidential(self, key, value):
        self.__unique_field(key, 'confidential', value, BoolValidator())

    def handle_testtime(self, key, value):
        if self.info.avg_test_time:
            self.handle_error("%s field already defined"%key)
            return

        # TestTime is an integer with an optional minute (m) or hour (h) suffix
        m = re.match('^(\d+)', value)
        if m:
            self.info.avg_test_time = int(m.group(1))
            if re.match('.*m$', value):
                self.info.avg_test_time *= 60
            if re.match('.*h$', value):
                self.info.avg_test_time *= 3600

            if self.info.avg_test_time<60:
                self.handle_warning("TestTime should not be less than a minute")

        else:
            self.handle_error("Malformed %s field"%key)

    def handle_type(self, key, value):
        for type in value.split(" "):
            self.info.types.append(type)
    
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

#			$absolute_path =~ /^\/mnt\/tests\/(.*)$/;
#			my $test_path_under_mnt_tests = $1;
#
#			# Deal with trailing slashes:
#			chop $test_path_under_mnt_tests if $test_path_under_mnt_tests =~ m/\/$/;
#
#			$test{test_path_under_mnt_tests} = $test_path_under_mnt_tests;
#
#			# FIXME: ensure that the path value is sane...
#			# with the /mnt/tests stripped off it ought to be equal to 
#

    def handle_runfor(self, key, value):
        for pkgname in value.split(" "):
            self.info.runfor.append(pkgname)

    def handle_requires(self, key, value):
        for pkgname in value.split(" "):
            self.info.requires.append(pkgname)

    def handle_rhtsrequires(self, key, value):
        for pkgname in value.split(" "):
            self.info.rhtsrequires.append(pkgname)

    def handle_needproperty(self, key, value):
        m = re.match(r'^([A-Za-z0-9]*)\s+(=|>|>=|<|<=)\s+([A-Za-z0-9]*)$', value)
        if m:
            self.info.needs.append(value)
            self.info.need_properties.append((m.group(1), m.group(2), m.group(3)))
        else:
            self.handle_error('"%s" is not a valid %s field; %s'%(value, key, "must be of the form PROPERTYNAME {=|>|>=|<|<=} PROPERTYVALUE"))
        

    def handle_deprecated_for_needproperty(self, key, value):
        self.handle_error("%s field is deprecated.  Use WantProperty instead"%key)

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
            m = re.match('(.*)\((.*)\):(.*)', line)
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

#
#	my $expected_path_under_mnt_tests = $test{test_name_under_root_ns};
#
#	# Some root namespaces seem to expect tests to live under /mnt/tests/ROOT_NS_NAME:
#    foreach my $root_ns (@root_ns_with_mnt_tests_subtree) {
#		if ($test{test_name_root_ns} eq $root_ns) {
#			$expected_path_under_mnt_tests = "$root_ns/$expected_path_under_mnt_tests";
#		}
#	}
#
#	#print "Name: $test{test_name}\n";
#	#print "Path: $test{test_path}\n\n";
#	#print "                  root_ns: $test{test_name_root_ns}\n";
#	#print "       name_under_root_ns: $test{test_name_under_root_ns}\n";
#	#print "test_path_under_mnt_tests: $test{test_path_under_mnt_tests}\n";
#	#print "            expected path: $test{expected_path_under_mnt_tests_from_name}\n";
#
#	if (!($test{test_path_under_mnt_tests} eq $expected_path_under_mnt_tests)) {
#		# Disable for now: a few true positives, but many false positives:
#		#&handle_error($filename, "Path below /mnt/tests (\"$test{test_path_under_mnt_tests}\") does not match expected value (\"$expected_path_under_mnt_tests\") based on Name ", $line_num);
#	}
#
#
#	# FIXME: warn about RunFor: in conjunction with Priority: Manual
#
#	# FIXME: warn about Requires: not containing RunFor: ?
#	# FIXME: warn about RunFor: not containing Requires: ?
#	# FIXME: warn about a test against a specific package (via the Name and/or Path ?) not containing RunFor: and Requires: lines ? (if not manual???)
#	# FIXME: warn about mismatch between Name and Path ?
#	# FIXME: warn about NeedProperty names,values, operators
#	# FIXME: blank RunFor: lines
#	
#	# Server side FIXMEs:
#	# query the tree for Requires/RunFor package names to ensure these are sane
#
#	# Stuff we could lint for in the runtest.sh:
#	# - that it exists
#	# - that it's syntactically valid
#	# - that you use report_result specifically with $result when using startup_test (special var)
#
#	# Stuff we could lint for in the Makefile:
#	# - that it's syntactically valid?
#	# - the usual tab issues in Makefiles
#	# - must contain an install target
#	# - not having install as the top-most target ????
#
##lintable stuff from actual cleanups:
##-       export result="FAIL:"
##+       export result="FAIL"
#
#
#
#    # Do some post processing, like turning lists into strings
#    # Only do the processing if we found the field while parsing
#    # Remove the temporary key if it existed
#    if (exists $test{RunFor}) {
#        #$test{relevant_packages} = $db->quote(join ' ', @{$test{RunFor}});
#        #delete $test{RunFor};
#    }
#    if (exists $test{Requires}) {
#        #$test{packages_needed} = $db->quote(join ' ', @{$test{Requires}});
#        #delete $test{Requires};
#    }
#    if (exists $test{Need}) {
#        #foreach my $prop (@{$test{Need}}) {
#        #    $test{need_property} .= "NeedProperty $prop\n";
#        #}
#        #delete $test{Need};
#        #$test{need_property} = $db->quote($test{need_property});
#    }
#    if (exists $test{Want}) {
#        #foreach my $prop (@{$test{Want}}) {
#        #    $test{want_property} .= "WantProperty $prop\n";
#        #}
#        #delete $test{Want};
#        #$test{want_property} = $db->quote($test{want_property});
#    }
#    # All values should be properly quoted by this point.
#
#    # build up a list to use with SQL "WHERE x in list"
#    #my $testtype = join "', '", @testtypes;
#    #$testtype = "('$testtype')";
#}

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
    p = StrictParser(raise_errors)
    p.parse(string.split("\n"))
    return p.info

def parse_file(filename, raise_errors = True):
    p = StrictParser(raise_errors)
    p.parse(open(filename).readlines())
    return p.info

#class ParserTests(unittest.TestCase):
#    def test_key_value(self):
#        raise NotImplementedError
#
#    def test_decl_arg_value(self):
#        raise NotImplementedError

class NamespaceTests(unittest.TestCase):
    def test_package_not_found(self):
        "Ensure that we get None for the namespace of an unrecognized package"
        self.assertEquals(None, get_namespace_for_package('foobar'))

    def test_simple_packages(self):
        "Ensure that we get expected namespaces back for some simple packages"
        self.assertEquals('desktop', get_namespace_for_package('evolution'))
        self.assertEquals('tools', get_namespace_for_package('gcc'))

class NameFieldTests(unittest.TestCase):
    def test_name(self):
        "Ensure Name field is parsed correctly"
        ti = parse_string("Name: /CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_name, "/CoreOS/cups/foo/bar")

class PathFieldTests(unittest.TestCase):
    def test_path_absolute(self):
        "Ensure absolute Path field is parsed correctly"
        ti = parse_string("Path: /mnt/tests/CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_path, "/mnt/tests/CoreOS/cups/foo/bar")

    def test_path_relative(self):
        "Ensure relative Path field is parsed correctly"
        ti = parse_string("Path: CoreOS/cups/foo/bar", raise_errors=False)
        self.assertEquals(ti.test_path, "/mnt/tests/CoreOS/cups/foo/bar")

class DescriptionFieldTests(unittest.TestCase):
    def test_description(self):
        "Ensure Description field is parsed correctly"
        ti = parse_string("Description: Ensure that the thingummy frobnicates the doohickey", raise_errors=False)
        self.assertEquals(ti.test_description, "Ensure that the thingummy frobnicates the doohickey")

    def test_description_with_colon(self):
        "Ensure Description field containing a colon is parsed correctly"
        ti = parse_string("Description: This test is from http://foo/bar", raise_errors=False)
        self.assertEquals(ti.test_description, "This test is from http://foo/bar")

class ReleasesFieldTests(unittest.TestCase):
    def test_releases(self):
        "Ensure Releases field is parsed correctly"
        ti = parse_string("Releases: FC5 FC6", raise_errors=False)
        self.assertEquals(ti.releases, "FC5 FC6")

class ArchitecturesFieldTests(unittest.TestCase):
    def test_architectures(self):
        "Ensure Architectures field is parsed correctly"
        ti = parse_string("Architectures: i386 x86_64", raise_errors=False)
        self.assertEquals(ti.test_archs, ["i386", "x86_64"])

    def test_architectures_after_releases(self):
        "Ensure that an Architectures field following a Releases field is parsed correctly"
        ti = parse_string("""
        Releases: FC5 FC6
        Architectures: i386 x86_64""", raise_errors=False)
        self.assertEquals(ti.releases, "FC5 FC6")
        self.assertEquals(ti.test_archs, ["i386", "x86_64"])

class NotifyFieldTests(unittest.TestCase):
    def test_notify(self):
        "Ensure Notify field is deprecated"
        self.assertRaises(ParserWarning, parse_string, "Notify: everyone in a 5-mile radius", raise_errors=True)

class OwnerFieldTests(unittest.TestCase):
    def test_owner_example(self):
        "Ensure that the example Owner field is parsed correctly"
        ti = parse_string("Owner: John Doe <jdoe@redhat.com>", raise_errors=False)
        self.assertEquals(ti.owner, "John Doe <jdoe@redhat.com>")

    def test_owner_example2(self):
        "Ensure that other Owner fields are parsed correctly"
        ti = parse_string("Owner: Jane Doe <jdoe@fedoraproject.org>", raise_errors=False)
        self.assertEquals(ti.owner, "Jane Doe <jdoe@fedoraproject.org>")

class PriorityFieldTests(unittest.TestCase):
    def test_priority(self):
        "Ensure Priority field is parsed correctly"
        ti = parse_string("Priority: Manual", raise_errors=False)
        self.assertEquals(ti.priority, "Manual")

class BugFieldTests(unittest.TestCase):
    def test_single_bug(self):
        "Ensure a single Bug field works"
        ti = parse_string("Bug: 123456", raise_errors=False)
        self.assertEquals(ti.bugs, [123456])

    def test_single_bugs(self):
        "Ensure a single Bugs field works"
        ti = parse_string("Bugs: 123456", raise_errors=False)
        self.assertEquals(ti.bugs, [123456])

    def test_multiple_bugs(self):
        "Ensure that multiple values for a Bugs field work"
        ti = parse_string("Bugs: 123456 456123", raise_errors=False)
        self.assertEquals(ti.bugs, [123456, 456123])

    def test_multiple_bug_lines(self):
        "Ensure that multiple Bug and Bugs lines work"
        ti = parse_string("""Bugs: 123456 456123
        Bug: 987654 456789""", raise_errors=False)
        self.assertEquals(ti.bugs, [123456, 456123, 987654, 456789])

    def test_blank_bug(self):
        "Ensure a blank Bug field is handled"
        ti = parse_string("Bug: ", raise_errors=False)
        self.assertEquals(ti.bugs, [])

class TestVersionFieldTests(unittest.TestCase):
    def test_testversion(self):
        "Ensure TestVersion field is parsed correctly"
        ti = parse_string("TestVersion: 1.1", raise_errors=False)
        self.assertEquals(ti.testversion, "1.1")

class LicenseFieldTests(unittest.TestCase):
    def test_license(self):
        "Ensure License field is parsed correctly"
        ti = parse_string("License: GPL", raise_errors=False)
        self.assertEquals(ti.license, "GPL")

class TestTimeFieldTests(unittest.TestCase):
    def test_testtime_seconds(self):
        "Ensure TestTime field can handle seconds"
        ti = parse_string("TestTime: 5", raise_errors=False)
        self.assertEquals(ti.avg_test_time, 5)

    def test_testtime_minutes(self):
        "Ensure TestTime field can handle minutes"
        ti = parse_string("TestTime: 10m", raise_errors=False)
        self.assertEquals(ti.avg_test_time, 600)

    def test_testtime_hours(self):
        "Ensure TestTime field can handle hours"
        ti = parse_string("TestTime: 2h", raise_errors=False)
        self.assertEquals(ti.avg_test_time, (2*60*60))

class RequiresFieldTests(unittest.TestCase):
    def test_single_line_requires(self):
        "Ensure Requires field is parsed correctly"
        ti = parse_string("Requires: evolution dogtail", raise_errors=False)
        self.assertEquals(ti.requires, ['evolution', 'dogtail'])

    def test_multiline_requires(self):
        "Ensure we can handle multiple Requires lines"
        ti = parse_string("""Requires: evolution dogtail
        Requires: foo bar""", raise_errors=False)
        self.assertEquals(ti.requires, ['evolution', 'dogtail', 'foo', 'bar'])

class RunForFieldTests(unittest.TestCase):
    def test_single_line_runfor(self):
        "Ensure RunFor field is parsed correctly"
        ti = parse_string("RunFor: evolution dogtail", raise_errors=False)
        self.assertEquals(ti.runfor, ['evolution', 'dogtail'])

    def test_multiline_runfor(self):
        "Ensure we can handle multiple RunFor lines"
        ti = parse_string("""RunFor: evolution dogtail
        RunFor: foo bar""", raise_errors=False)
        self.assertEquals(ti.runfor, ['evolution', 'dogtail', 'foo', 'bar'])

class TypeFieldTests(unittest.TestCase):
    def test_single_line_type(self):
        "Ensure Type field is parsed correctly"
        ti = parse_string("Type: Crasher Regression", raise_errors=False)
        self.assertEquals(ti.types, ['Crasher', 'Regression'])

    def test_multiline_type(self):
        "Ensure we can handle multiple Type lines"
        ti = parse_string("""Type: Crasher Regression
        Type: Performance Stress""", raise_errors=False)
        self.assertEquals(ti.types, ['Crasher', 'Regression', 'Performance', 'Stress'])

class NeedPropertyFieldTests(unittest.TestCase):
    def test_single_line_needproperty(self):
        "Ensure NeedProperty field is parsed correctly"
        ti = parse_string("NeedProperty: PROCESSORS > 1", raise_errors=False)
        self.assertEquals(ti.need_properties, [("PROCESSORS", ">", "1")])
                          
    def test_multiline_needproperty(self):
        "Ensure we can handle multiple NeedProperty lines"
        ti = parse_string("""
        NeedProperty: CAKE = CHOCOLATE
        NeedProperty: SLICES > 3
        """, raise_errors=False)
        self.assertEquals(ti.need_properties, [("CAKE", "=", "CHOCOLATE"), ("SLICES", ">", "3")])

class SiteConfigDeclarationTests(unittest.TestCase):
    """Unit tests for the SiteConfig declaration"""
    
    def test_relative_siteconfig_without_name(self):
        "Ensure that a relative SiteConfig declaration without a Name is handled with a sane error"
        self.assertRaises(ParserError, parse_string, "SiteConfig(server): Hostname of server", raise_errors=True)

    def test_flat_relative_siteconfig(self):
        "Ensure that relative SiteConfig declarations without nesting work"
        ti = parse_string("""
        Name: /desktop/evolution/mail/imap/authentication/ssl
        SiteConfig(server): Hostname of server
        SiteConfig(username): Username to use
        SiteConfig(password): Password to use
        """, raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/desktop/evolution/mail/imap/authentication/ssl/server', "Hostname of server"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/username', "Username to use"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/password', "Password to use")
                                          ])

    def test_nested_relative_siteconfig(self):
        "Ensure that a relative SiteConfig declaration containing a path works"
        ti = parse_string("""
        Name: /desktop/evolution/mail/imap/authentication
        SiteConfig(ssl/server): Hostname of server to try SSL auth against
        SiteConfig(ssl/username): Username to use for SSL auth
        SiteConfig(ssl/password): Password to use for SSL auth
        SiteConfig(tls/server): Hostname of server to try TLS auth against
        SiteConfig(tls/username): Username to use for TLS auth
        SiteConfig(tls/password): Password to use for TLS auth
        """, raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/desktop/evolution/mail/imap/authentication/ssl/server', "Hostname of server to try SSL auth against"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/username', "Username to use for SSL auth"),
                                          ('/desktop/evolution/mail/imap/authentication/ssl/password', "Password to use for SSL auth"),
                                          ('/desktop/evolution/mail/imap/authentication/tls/server', "Hostname of server to try TLS auth against"),
                                          ('/desktop/evolution/mail/imap/authentication/tls/username', "Username to use for TLS auth"),
                                          ('/desktop/evolution/mail/imap/authentication/tls/password', "Password to use for TLS auth")
                                          ])

    def test_absolute_siteconfig(self):
        "Ensure that an absolute SiteConfig declaration works"
        ti = parse_string("""SiteConfig(/stable-servers/ldap/hostname): Location of stable LDAP server to use""", raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/stable-servers/ldap/hostname', 'Location of stable LDAP server to use')])

    #def test_siteconfig_comment(self):
    #    "Ensure that comments are stripped as expected from descriptions"
    #    ti = parse_string("SiteConfig(/foo/bar): Some value # hello world", raise_errors=False)
    #    self.assertEquals(ti.siteconfig, [('/foo/bar', "Some value")])

    def test_siteconfig_whitespace(self):
        "Ensure that whitespace is stripped as expected from descriptions"
        ti = parse_string("SiteConfig(/foo/bar):        Some value    ", raise_errors=False)
        self.assertEquals(ti.siteconfig, [('/foo/bar', "Some value")])

    def test_output_relative_siteconfig(self):
        "Ensure that the output methods collapse redundant paths in relative SiteConfig declarations"
        ti = TestInfo()
        ti.test_name = '/foo/bar'
        ti.siteconfig = [('/foo/bar/baz/fubar', 'Dummy value')]
        self.assertEquals(ti.generate_siteconfig_lines(), "SiteConfig(baz/fubar): Dummy value\n")
        

class IntegrationTests(unittest.TestCase):
    def test_example_file(self):
        "Ensure a full example file is parsed correctly"
        ti = parse_string("""\
# Test comment
Owner:        Jane Doe <jdoe@redhat.com>
Name:         /examples/coreutils/example-simple-test
Path:         /mnt/tests/examples/coreutils/example-simple-test
Description:  This test ensures that md5sums are generated and validated correctly
TestTime:     1m
TestVersion:  1.1
License:      GPL
RunFor:       coreutils
Requires:     coreutils python
        """, raise_errors=True)
        self.assertEquals(ti.owner, "Jane Doe <jdoe@redhat.com>")
        self.assertEquals(ti.test_name, "/examples/coreutils/example-simple-test")
        self.assertEquals(ti.test_path, "/mnt/tests/examples/coreutils/example-simple-test")
        self.assertEquals(ti.test_description, "This test ensures that md5sums are generated and validated correctly")
        self.assertEquals(ti.avg_test_time, 60)
        self.assertEquals(ti.testversion, "1.1")
        self.assertEquals(ti.license, "GPL")
        self.assertEquals(ti.runfor, ["coreutils"])
        self.assertEquals(ti.requires, ["coreutils", "python"])

    def test_output_testinfo(self):
        "Output an example file, then ensure it is parsed succesfully"
        ti1 = parse_string("""\
# Test comment
Owner:        Jane Doe <jdoe@redhat.com>
Name:         /examples/coreutils/example-simple-test
Path:         /mnt/tests/examples/coreutils/example-simple-test
Description:  This test ensures that md5sums are generated and validated correctly
TestTime:     1m
TestVersion:  1.1
License:      GPL
RunFor:       coreutils
Requires:     coreutils python
NeedProperty: CAKE = CHOCOLATE
NeedProperty: SLICES > 3
SiteConfig(server): Hostname of server
SiteConfig(username): Username to use
SiteConfig(password): Password to use
SiteConfig(ssl/server): Hostname of server to try SSL auth against
SiteConfig(ssl/username): Username to use for SSL auth
SiteConfig(ssl/password): Password to use for SSL auth
SiteConfig(tls/server): Hostname of server to try TLS auth against
SiteConfig(tls/username): Username to use for TLS auth
SiteConfig(tls/password): Password to use for TLS auth
SiteConfig(/stable-servers/ldap/hostname): Location of stable LDAP server to use
        """, raise_errors=True)
        filename = os.tmpnam()
        file = open(filename, 'w')
        ti1.output(file)
        file.close()

        p = StrictParser(raise_errors=True)
        p.parse(open(filename, "r").readlines())
        ti2= p.info
        self.assertEquals(ti2.owner, "Jane Doe <jdoe@redhat.com>")
        self.assertEquals(ti2.test_name, "/examples/coreutils/example-simple-test")
        self.assertEquals(ti2.test_path, "/mnt/tests/examples/coreutils/example-simple-test")
        self.assertEquals(ti2.test_description, "This test ensures that md5sums are generated and validated correctly")
        self.assertEquals(ti2.avg_test_time, 60)
        self.assertEquals(ti2.testversion, "1.1")
        self.assertEquals(ti2.license, "GPL")
        self.assertEquals(ti2.runfor, ["coreutils"])
        self.assertEquals(ti2.requires, ["coreutils", "python"])
        self.assertEquals(ti2.need_properties, [('CAKE', '=', 'CHOCOLATE'), ('SLICES', '>', '3')])
        self.assertEquals(ti2.siteconfig, [('/examples/coreutils/example-simple-test/server', 'Hostname of server'),
                                           ('/examples/coreutils/example-simple-test/username', 'Username to use'),
                                           ('/examples/coreutils/example-simple-test/password', 'Password to use'),
                                           ('/examples/coreutils/example-simple-test/ssl/server', 'Hostname of server to try SSL auth against'),
                                           ('/examples/coreutils/example-simple-test/ssl/username', 'Username to use for SSL auth'),
                                           ('/examples/coreutils/example-simple-test/ssl/password', 'Password to use for SSL auth'),
                                           ('/examples/coreutils/example-simple-test/tls/server', 'Hostname of server to try TLS auth against'),
                                           ('/examples/coreutils/example-simple-test/tls/username', 'Username to use for TLS auth'),
                                           ('/examples/coreutils/example-simple-test/tls/password', 'Password to use for TLS auth'),
                                           ('/stable-servers/ldap/hostname', 'Location of stable LDAP server to use')])

#etc


if __name__=='__main__':
    unittest.main()
    
    
