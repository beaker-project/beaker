# Logan - Logan is the scheduling piece of the Beaker project
#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from datetime import datetime
import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
from turbogears.database import metadata, mapper
# import some basic SQLAlchemy classes for declaring the data model
# (see http://www.sqlalchemy.org/docs/04/ormtutorial.html)
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import relation
# import some datatypes for table columns from SQLAlchemy
# (see http://www.sqlalchemy.org/docs/04/types.html for more)
from sqlalchemy import String, Unicode, Integer, DateTime, Boolean, Numeric
from sqlalchemy import and_, or_, not_, select
from turbogears import identity
from turbogears.database import session
import xml.dom.minidom
from xml.dom.minidom import Node


# your data tables

# your_table = Table('yourtable', metadata,
#     Column('my_id', Integer, primary_key=True)
# )

arch = Table('arch', metadata,
	Column('id', Integer, primary_key=True),
	Column('arch', Unicode(256))
)

family = Table('family', metadata,
	Column('id', Integer, primary_key=True),
	Column('name', Unicode(256)),
	Column('alias', Unicode(256))
)

family_arch_map = Table('family_arch_map', metadata,
	Column('family_id', Integer,
		ForeignKey('family.id',onupdate='CASCADE', ondelete='CASCADE')),
	Column('arch_id', Integer,
		ForeignKey('arch.id',onupdate='CASCADE', ondelete='CASCADE')),
)

test = Table('test',metadata,
	Column('id', Integer, primary_key=True),
	Column('name', Unicode(2048)),
	Column('rpm', Unicode(2048)),
	Column('path', Unicode(4096)),
	Column('description', Unicode(2048)),
	Column('repo', Unicode(256)),
	Column('avg_time', Integer),
	Column('destructive', Boolean),
	Column('nda', Boolean),
	Column('family_list', Integer),
	Column('arch_list', Boolean),
	Column('notify', Unicode(2048)),
	Column('creation_date', DateTime, default=datetime.now),
	Column('update_date', DateTime, onupdate=datetime.now),
	Column('owner_id', Integer,
		ForeignKey('tg_user.user_id')),
	Column('version', Unicode(256)),
	Column('license', Unicode(256)),
	Column('valid', Boolean)
)

test_packages_runfor_map = Table('test_packages_runfor_map', metadata,
	Column('test_id', Integer,
		ForeignKey('test.id', onupdate='CASCADE',
                                      ondelete='CASCADE')),
	Column('package_id', Integer,
		ForeignKey('test_package.id',onupdate='CASCADE', 
                                             ondelete='CASCADE')),
)

test_packages_required_map = Table('test_packages_required_map', metadata,
	Column('test_id', Integer,
		ForeignKey('test.id', onupdate='CASCADE',
                                      ondelete='CASCADE')),
	Column('package_id', Integer,
		ForeignKey('test_package.id',onupdate='CASCADE', 
                                             ondelete='CASCADE')),
)

test_property_needed = Table('test_property_needed', metadata,
	Column('id', Integer, primary_key=True),
	Column('test_id', Integer,
		ForeignKey('test.id')),
	Column('property', Unicode(2048))
)

test_package = Table('test_package',metadata,
	Column('id', Integer, primary_key=True),
	Column('package', Unicode(2048))
)

test_type = Table('test_type',metadata,
	Column('id', Integer, primary_key=True),
	Column('type', Unicode(256))
)

test_type_map = Table('test_type_map',metadata,
	Column('test_id', Integer,
		ForeignKey('test.id',onupdate='CASCADE', 
                                     ondelete='CASCADE')),
	Column('test_type_id', Integer,
		ForeignKey('test_type.id', onupdate='CASCADE', 
                                           ondelete='CASCADE')),
)

test_arch_map = Table('test_arch_map',metadata,
	Column('test_id', Integer,
		ForeignKey('test.id',onupdate='CASCADE', 
                                     ondelete='CASCADE')),
	Column('arch_id', Integer,
		ForeignKey('arch.id',onupdate='CASCADE', 
                                     ondelete='CASCADE')),
)

test_family_map = Table('test_family_map',metadata,
	Column('test_id', Integer,
		ForeignKey('test.id',onupdate='CASCADE', ondelete='CASCADE')),
	Column('family_id', Integer,
		ForeignKey('family.id',onupdate='CASCADE', ondelete='CASCADE')),
)

test_bugzilla = Table('test_bugzilla',metadata,
	Column('id', Integer, primary_key=True),
	Column('bugzilla_id', Integer),
	Column('test_id', Integer,
		ForeignKey('test.id')),
)

status = Table('status',metadata,
	Column('id', Integer, primary_key=True),
	Column('status', Unicode(20))
)

result = Table('result',metadata,
	Column('id', Integer, primary_key=True),
	Column('result', Unicode(20))
)

priority = Table('priority',metadata,
	Column('id', Integer, primary_key=True),
	Column('priority', Unicode(20))
)

job = Table('job',metadata,
	Column('id', Integer, primary_key=True),
	Column('owner_id', Integer, 
		ForeignKey('tg_user.user_id'), index=True),
	Column('whiteboard',Unicode(2000)),
	Column('result_id', Integer,
		ForeignKey('result.id')),
	Column('status_id', Integer,
		ForeignKey('status.id'), default=select([status.c.id], limit=1).where(status.c.status=='Queued').correlate(None))
)

recipe_set = Table('recipe_set',metadata,
	Column('id', Integer, primary_key=True),
	Column('job_id',Integer,
		ForeignKey('job.id')),
	Column('priority_id', Integer,
		ForeignKey('priority.id'), default=select([priority.c.id], limit=1).where(priority.c.priority==u'Normal').correlate(None)),
	Column('queue_time',DateTime, nullable=False, default=datetime.now),
	Column('result_id', Integer,
		ForeignKey('result.id')),
	Column('status_id', Integer,
		ForeignKey('status.id'), default=select([status.c.id], limit=1).where(status.c.status==u'Queued').correlate(None))
)

recipe = Table('recipe',metadata,
	Column('id', Integer, primary_key=True),
	Column('recipe_set_id', Integer,
		ForeignKey('recipe_set.id')),
	Column('arch', Unicode(25)),
	Column('distro', Unicode(255)),
	Column('family', Unicode(255)),
	Column('variant', Unicode(25)),
	Column('machine', Unicode(255)),
	Column('result_id', Integer,
		ForeignKey('result.id')),
	Column('status_id', Integer,
		ForeignKey('status.id'),default=select([status.c.id], limit=1).where(status.c.status=='Queued').correlate(None)),
	Column('lab_server',Unicode(255)),
	Column('start_time',DateTime),
	Column('finish_time',DateTime),
	Column('host_requires',Unicode()),
	Column('distro_requires',Unicode()),
	Column('kickstart',Unicode()),
	Column('possible_machines', Unicode()),
	# type = recipe, machine_recipe or guest_recipe
	Column('type', String(30), nullable=False)
)

machine_recipe = Table('machine_recipe', metadata,
	Column('id', Integer, ForeignKey('recipe.id'), primary_key=True)
)

guest_recipe = Table('guest_recipe', metadata,
	Column('id', Integer, ForeignKey('recipe.id'), primary_key=True),
	Column('guestname', Unicode()),
	Column('guestargs', Unicode())
)

#callback = Table('callback', metadata,
#	Column('id', Integer, ForeignKey('recipe.id'), primary_key=True)
#)

recipe_tag = Table('recipe_tag',metadata,
	Column('id', Integer, primary_key=True),
	Column('recipe_id', Integer, ForeignKey('recipe.id')),
	Column('tag', Unicode(255))
)

machine_guest_map =Table('machine_guest_map',metadata,
	Column('machine_recipe_id', Integer,
		ForeignKey('machine_recipe.id'),
		nullable=False),
	Column('guest_recipe_id', Integer,
		ForeignKey('recipe.id'),
		nullable=False)
)

recipe_rpm =Table('recipe_rpm',metadata,
	Column('recipe_id', Integer,
		ForeignKey('recipe.id'), primary_key=True),
	Column('package',Unicode(255)),
	Column('version',Unicode(255)),
	Column('release',Unicode(255)),
	Column('epoch',Integer),
	Column('arch',Unicode(255)),
	Column('running_kernel', Boolean)
)

recipe_test =Table('recipe_test',metadata,
	Column('id', Integer, primary_key=True),
	Column('recipe_id',Integer,
		ForeignKey('recipe.id')),
	Column('test_id',Integer,
		ForeignKey('test.id')),
	Column('start_time',DateTime),
	Column('finish_time',DateTime),
	Column('result_id', Integer,
		ForeignKey('result.id')),
	Column('status_id', Integer,
		ForeignKey('status.id'),default=select([status.c.id], limit=1).where(status.c.status=='Queued').correlate(None)),
	Column('role', Unicode(255)),
)

recipe_test_param = Table('recipe_test_param', metadata,
	Column('id', Integer, primary_key=True),
	Column('recipe_test_id', Integer,
		ForeignKey('recipe_test.id')),
        Column('name',Unicode(255)),
        Column('value',Unicode())
)

recipe_test_comment = Table('recipe_test_comment',metadata,
	Column('id', Integer, primary_key=True),
	Column('recipe_test_id', Integer,
		ForeignKey('recipe_test.id')),
	Column('comment', Unicode()),
	Column('created', DateTime),
	Column('user_id', Integer, 
		ForeignKey('tg_user.user_id'), index=True)
)

recipe_test_bugzilla = Table('recipe_test_bugzilla',metadata,
	Column('id', Integer, primary_key=True),
	Column('recipe_test_id', Integer,
		ForeignKey('recipe_test.id')),
	Column('bugzilla_id', Integer)
)

recipe_test_rpm =Table('recipe_test_rpm',metadata,
	Column('recipe_test_id', Integer,
		ForeignKey('recipe_test.id'), primary_key=True),
	Column('package',Unicode(255)),
	Column('version',Unicode(255)),
	Column('release',Unicode(255)),
	Column('epoch',Integer),
	Column('arch',Unicode(255)),
	Column('running_kernel', Boolean)
)

recipe_test_result = Table('recipe_test_result',metadata,
	Column('id', Integer, primary_key=True),
	Column('recipe_test_id', Integer,
		ForeignKey('recipe_test.id')),
	Column('path', Unicode(2048)),
	Column('result_id', Integer,
		ForeignKey('result.id')),
	Column('score', Numeric(10)),
	Column('log', Unicode()),
)

# the identity schema

visits_table = Table('visit', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('expiry', DateTime)
)

visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True)
)

groups_table = Table('tg_group', metadata,
    Column('group_id', Integer, primary_key=True),
    Column('group_name', Unicode(16), unique=True),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.now)
)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(16), unique=True),
    Column('email_address', Unicode(255), unique=True),
    Column('display_name', Unicode(255)),
    Column('password', Unicode(40)),
    Column('created', DateTime, default=datetime.now)
)

permissions_table = Table('permission', metadata,
    Column('permission_id', Integer, primary_key=True),
    Column('permission_name', Unicode(16), unique=True),
    Column('description', Unicode(255))
)

user_group_table = Table('user_group', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)


# the identity model

class Visit(object):
    """
    A visit to your site
    """
    def lookup_visit(cls, visit_key):
        return cls.query.get(visit_key)
    lookup_visit = classmethod(lookup_visit)


class VisitIdentity(object):
    """
    A Visit that is link to a User object
    """
    pass


class Group(object):
    """
    An ultra-simple group definition.
    """
    pass


class User(object):
    """
    Reasonably basic User definition.
    Probably would want additional attributes.
    """

    def permissions(self):
        p = set()
        for g in self.groups:
            p |= set(g.permissions)
        return p
    permissions = property(permissions)

    def by_email_address(cls, email):
        """
        A class method that can be used to search users
        based on their email addresses since it is unique.
        """
        return cls.query.filter_by(email_address=email).first()
    by_email_address = classmethod(by_email_address)

    def by_user_name(cls, username):
        """
        A class method that permits to search users
        based on their user_name attribute.
        """
        return cls.query.filter_by(user_name=username).first()
    by_user_name = classmethod(by_user_name)

    def _set_password(self, password):
        """
        encrypts password on the fly using the encryption
        algo defined in the configuration
        """
        self._password = identity.encrypt_password(password)

    def _get_password(self):
        """
        returns password
        """
        return self._password

    password = property(_get_password, _set_password)


class Permission(object):
    """
    A relationship that determines what each Group can do
    """
    pass

# your model classes

class MappedObject(object):

    doc = xml.dom.minidom.Document()

    @classmethod
    def lazy_create(cls, **kwargs):
        try:
            item = cls.query.filter_by(**kwargs).one()
        except:
            item = cls(**kwargs)
            session.save(item)		
            session.flush([item])
        return item

    def node(self, element, value):
        node = self.doc.createElement(element)
        node.appendChild(self.doc.createTextNode(value))
        return node

    def __repr__(self):
        # pretty-print the attributes, so we can see what's getting autoloaded for us:
        attrStr = ""
        numAttrs = 0
        for attr in self.__dict__:
            if attr[0] != '_':
                if numAttrs>0:
                    attrStr += ', '
                attrStr += '%s=%s' % (attr, repr(self.__dict__[attr]))
                numAttrs += 1
        return "%s(%s)" % (self.__class__.__name__, attrStr)
        #return "%s()" % (self.__class__.__name__)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

class Arch(MappedObject):
    """
    Holds a list of Arches the system knows about
    """

    def __init__(self, arch=None):
        self.arch = arch

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(arch=name).one()

    @classmethod
    def get_arches(cls):
        arches = cls.query()
        return [(arch.id, arch.arch) for arch in arches]

class Family(MappedObject):
    """
    Holds a list of Families the system knows about
    """
    def __init__(self, name=None, alias=None):
        self.name = name
        self.alias = alias

    @classmethod
    def by_name_alias(cls, name_alias):
        return cls.query.filter(or_(Family.name==name_alias,
                                    Family.alias==name_alias)).one()

class Test(MappedObject):
    """
    Tests that are available to schedule
    """

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(name=name).one()

    @classmethod
    def by_family_arch(cls, wantedFamily, wantedArch):
        return cls.query.outerjoin('families').outerjoin('arches').\
               filter(
                  and_(
                    or_(
                       # Select tests that are not whitelisting by ARCH
                       Test.arch_list==False,
                       # White listing.
                       # Only show tests that have a matching arch
                       and_(Test.arch_list==True,
                            Arch.arch==wantedArch)
                       ),
                    or_(
                       # Select tests that are not 
                       #   whitelisting/blacklisting by family
                       Test.family_list==0,

                       # White listing.
                       # Only show tests that have a matching family
                       and_(Test.family_list==1,
                            or_(Family.name==wantedFamily,
                                Family.alias==wantedFamily)),

                       # Black listing.
                       # Only show tests that don't have a matching family
                       and_(Test.family_list==2,
                           not_(Test.id.in_(
                             select([test.c.id]).
                                where(test.c.family_list==2).
                                where(test.c.id==test_family_map.c.test_id).
                                where(test_family_map.c.family_id==family.c.id).
                                where(or_(Family.name==wantedFamily,
                                          Family.alias==wantedFamily)).
                                correlate(None))))
                       )
                      )
                     )

    @classmethod
    def by_type(cls, type, query=None):
        if not query:
            query=cls.query
        return query.join('types').filter(TestType.type==type)

    @classmethod
    def by_package(cls, package, query=None):
        if not query:
            query=cls.query
        return query.join('runfor').filter(TestPackage.package==package)

    def elapsed_time(self, suffixes=[' year',' week',' day',' hour',' minute',' second'], add_s=True, separator=', '):
        """
        Takes an amount of seconds and turns it into a human-readable amount of 
        time.
        """
        seconds = self.avg_time
        # the formatted time string to be returned
        time = []
       
        # the pieces of time to iterate over (days, hours, minutes, etc)
        # - the first piece in each tuple is the suffix (d, h, w)
        # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
        parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
                (suffixes[1], 60 * 60 * 24 * 7),
                (suffixes[2], 60 * 60 * 24),
                (suffixes[3], 60 * 60),
                (suffixes[4], 60),
                (suffixes[5], 1)]
       
        # for each time piece, grab the value and remaining seconds, 
        # and add it to the time string
        for suffix, length in parts:
            value = seconds / length
            if value > 0:
                seconds = seconds % length
                time.append('%s%s' % (str(value),
                            (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
            if seconds < 1:
                break
      
        return separator.join(time)
       
class TestType(MappedObject):
    """
    A test can be classified into serveral test types which can be used to
    select tests for batch runs
    """
    pass

class TestPackage(MappedObject):
    """
    A list of packages that a test should be run for.
    """
    def __repr__(self):
        return self.package

class TestPropertyNeeded(MappedObject):
    """
    Tests can have requirements on the systems that they run on.
         *not currently implemented*
    """
    pass

class TestBugzilla(MappedObject):
    """
    Bugzillas that apply to this Test.
    """
    pass

class Job(MappedObject):
    """
    Container to hold like recipe sets.
    """
    def to_xml(self):
        job = self.doc.createElement("job")
        job.setAttribute("id", "%s" % self.id)
        job.setAttribute("owner", "%s" % self.owner.email_address)
        job.setAttribute("result", "%s" % self.result)
        job.setAttribute("status", "%s" % self.status)
        job.appendChild(self.node("Scheduler", "FIXME"))
        job.appendChild(self.node("whiteboard", self.whiteboard))
        for rs in self.recipesets:
            job.appendChild(rs.to_xml())
        return job

class Priority(MappedObject):
    """
    Holds a list of Priorities the system knows about.
    """
    def __init__(self, priority=None):
        self.priority = priority

class RecipeSet(MappedObject):
    """
    A Collection of Recipes that must be executed at the same time.
    """
    def to_xml(self):
        recipeSet = self.doc.createElement("recipeSet")
        recipeSet.setAttribute("id", "%s" % self.id)
        for r in self.recipes:
            recipeSet.appendChild(r.to_xml())
        return recipeSet

    @classmethod
    def by_status(cls, status, query=None):
        if not query:
            query=cls.query
        return query.join('status').filter(Status.status==status)

    @classmethod
    def by_datestamp(cls, datestamp, query=None):
        if not query:
            query=cls.query
        return query.filter(RecipeSet.queue_time <= datestamp)

    @classmethod
    def iter_recipeSets(self, status=u'Queued'):
        self.recipeSets = []
        while True:
            recipeSet = RecipeSet.by_status(status).join('priority')\
                            .order_by(priority.c.priority)\
                            .filter(not_(RecipeSet.id.in_(self.recipeSets)))\
                            .first()
            if recipeSet:
                self.recipeSets.append(recipeSet.id)
            else:
                return
            yield recipeSet

class Recipe(MappedObject):
    """
    Contains requires for host selection and distro selection.
    Also contains what tests will be executed.
    """
    def to_xml(self, recipe):
        recipe.setAttribute("id", "%s" % self.id)
	recipe.setAttribute("job_id", "%s" % self.recipeset.job_id)
	recipe.setAttribute("recipe_set_id", "%s" % self.recipe_set_id)
	if self.result:
            recipe.setAttribute("result", "%s" % self.result)
	if self.status:
            recipe.setAttribute("status", "%s" % self.status)
	if self.arch:
	    recipe.setAttribute("arch", "%s" % self.arch)
	if self.distro:
	    recipe.setAttribute("distro", "%s" % self.distro)
	if self.family:
	    recipe.setAttribute("family", "%s" % self.family)
	if self.variant:
	    recipe.setAttribute("variant", "%s" % self.variant)
	if self.machine:
	    recipe.setAttribute("machine", "%s" % self.machine)
        drs = xml.dom.minidom.parseString(self.distro_requires)
        hrs = xml.dom.minidom.parseString(self.host_requires)
        for dr in drs.getElementsByTagName("distroRequires"):
            recipe.appendChild(dr)
        for hr in hrs.getElementsByTagName("hostRequires"):
            recipe.appendChild(hr)
        for t in self.tests:
            recipe.appendChild(t.to_xml())
        return recipe

class GuestRecipe(Recipe):
    def to_xml(self):
        recipe = self.doc.createElement("guestrecipe")
        recipe.setAttribute("guestname", "%s" % self.guestname)
        recipe.setAttribute("guestargs", "%s" % self.guestargs)
        return Recipe.to_xml(self,recipe)

class MachineRecipe(Recipe):
    """
    Optionally can contain guest recipes which are just other recipes
      which will be executed on this system.
    """
    def to_xml(self):
        recipe = self.doc.createElement("recipe")
        for guest in self.guests:
            recipe.appendChild(guest.to_xml())
        return Recipe.to_xml(self,recipe)

class RecipeTag(MappedObject):
    """
    Each recipe can be tagged with information that identifies what is being
    tested.  This is helpful when generating reports.
    """
    pass

class RecipeRpm(MappedObject):
    """
    A list of rpms that were installed at the time of testing.
    """
    pass

class RecipeTest(MappedObject):
    """
    This holds the results/status of the test being executed.
    """
    def to_xml(self):
        test = self.doc.createElement("test")
        test.setAttribute("id", "%s" % self.id)
        test.setAttribute("name", "%s" % self.test.name)
        test.setAttribute("avg_time", "%s" % self.test.avg_time)
        test.setAttribute("role", "%s" % self.role)
        test.setAttribute("result", "%s" % self.result)
        test.setAttribute("status", "%s" % self.status)
        if self.params:
            params = self.doc.createElement("params")
            for p in self.params:
                params.appendChild(p.to_xml())
            test.appendChild(params)
        rpm = self.doc.createElement("rpm")
        rpm.setAttribute("name", "%s" % self.test.rpm)
        test.appendChild(rpm)
        return test

    def _get_duration(self):
        try:
            return self.finish_time - self.start_time
        except:
            return None
    duration = property(_get_duration)

class RecipeTestParam(MappedObject):
    """
    Parameters for test execution.
    """
    def to_xml(self):
        param = self.doc.createElement("param")
        param.setAttribute("name", "%s" % self.name)
        param.setAttribute("value", "%s" % self.value)
        return param

class RecipeTestComment(MappedObject):
    """
    User comments about the test execution.
    """
    pass

class RecipeTestBugzilla(MappedObject):
    """
    Any bugzillas filed/found due to this test execution.
    """
    pass

class RecipeTestRpm(MappedObject):
    """
    the versions of the RPMS listed in the tests runfor list.
    """
    pass

class RecipeTestResult(MappedObject):
    """
    Each test can report multiple results
    """
    pass

class Status(MappedObject):
    """
    Holds the status keys the system knows about.
    """
    def __init__(self, status=None):
        self.status = status

    def __repr__(self):
        return self.status

class Result(MappedObject):
    """
    Holds the results keys the system knows about.
    """
    def __init__(self, result=None):
        self.result = result

    def __repr__(self):
        return self.result

# set up mappers between your data tables and classes

mapper(Arch, arch)
mapper(Family, family,
	properties = {'arches':relation(Arch,
					secondary=family_arch_map)})
mapper(Test, test,
	properties = {'types':relation(TestType,
					secondary=test_type_map, 
					backref='tests'),
		      'arches':relation(Arch,
					secondary=test_arch_map),
		      'families':relation(Family,
					secondary=test_family_map),
		      'runfor':relation(TestPackage,
                                        secondary=test_packages_runfor_map,
                                        backref='tests'),
		      'required':relation(TestPackage,
                                        secondary=test_packages_required_map),
		      'needs':relation(TestPropertyNeeded),
		      'bugzillas':relation(TestBugzilla, backref='tests',
                                            cascade='all, delete-orphan'),
		      'owner':relation(User, uselist=False, backref='tests')})
mapper(TestPackage, test_package)
mapper(TestPropertyNeeded, test_property_needed)
mapper(TestType, test_type)
mapper(TestBugzilla, test_bugzilla)
mapper(Job, job,
	properties = {'recipesets':relation(RecipeSet, backref='job'),
		      'owner':relation(User, uselist=False, backref='jobs'),
		      'result':relation(Result, uselist=False),
                      'status':relation(Status, uselist=False)})
mapper(RecipeSet, recipe_set,
	properties = {'recipes':relation(Recipe, backref='recipeset'),
		      'priority':relation(Priority, uselist=False),
		      'result':relation(Result, uselist=False),
                      'status':relation(Status, uselist=False)})
mapper(Recipe, recipe, 
	polymorphic_on=recipe.c.type, polymorphic_identity='recipe',
	properties = {'tests':relation(RecipeTest, backref='recipe'),
		      'tags':relation(RecipeTag, backref='recipes'),
		      'rpms':relation(RecipeRpm, backref='recipes'),
		      'result':relation(Result, uselist=False),
		      'status':relation(Status, uselist=False)})
mapper(GuestRecipe, guest_recipe, inherits=Recipe, 
	polymorphic_identity='guest_recipe')
mapper(MachineRecipe, machine_recipe, inherits=Recipe, 
	polymorphic_identity='machine_recipe',
	properties = {'guests':relation(Recipe, backref='hostmachine',
					secondary=machine_guest_map)})
mapper(RecipeTag, recipe_tag)
mapper(RecipeRpm, recipe_rpm)
mapper(RecipeTest, recipe_test,
	properties = {'results':relation(RecipeTestResult, backref='test'),
                      'rpms':relation(RecipeTestRpm),
		      'comments':relation(RecipeTestComment, backref='test'),
                      'params':relation(RecipeTestParam),
		      'bugzillas':relation(RecipeTestBugzilla, backref='test'),
		      'test':relation(Test, uselist=False, backref='runs'),
		      'result':relation(Result, uselist=False),
		      'status':relation(Status, uselist=False)})
mapper(RecipeTestParam, recipe_test_param)
mapper(RecipeTestComment, recipe_test_comment,
	properties = {'user':relation(User, uselist=False, backref='comments')})
mapper(RecipeTestBugzilla, recipe_test_bugzilla)
mapper(RecipeTestRpm, recipe_test_rpm)
mapper(RecipeTestResult, recipe_test_result,
	properties = {'result':relation(Result, uselist=False)})
mapper(Priority, priority)
mapper(Status, status)
mapper(Result, result)

# set up mappers between identity tables and classes

mapper(Visit, visits_table)

mapper(VisitIdentity, visit_identity_table,
        properties=dict(users=relation(User, backref='visit_identity')))

mapper(User, users_table,
        properties=dict(_password=users_table.c.password))

mapper(Group, groups_table,
        properties=dict(users=relation(User,
                secondary=user_group_table, backref='groups')))

mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group,
                secondary=group_permission_table, backref='permissions')))
