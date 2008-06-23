#!/usr/bin/python

import xmltramp
import os
import sys

class ElementWrapper:
    @classmethod
    def get_subclass(cls, element):
        #print element
        
        name = element._name

        #print name
        #print type(name)

        #print subclassDict

        if name in subclassDict:
            return subclassDict[name]
        return UnknownElement
    
    def __init__(self, wrappedEl):
        self.wrappedEl = wrappedEl

    def __repr__(self):
        return '%s("%s")' % (self.__class__, repr(self.wrappedEl))

    def __iter__(self):
        for child in self.wrappedEl:
            if isinstance(child, xmltramp.Element):
                yield ElementWrapper.get_subclass(child)(child)
            else:
                yield child

    def __getitem__(self, n):
        child = self.wrappedEl[n]
        if isinstance(child, xmltramp.Element):
            return ElementWrapper.get_subclass(child)(child)
        else:
            return child
        

    def recurse(self, visitor):
        visitor.visit(self)
        for child in self:
            child.recurse(visitor)

    def get_text(self):
        # Simple API for extracting textual content below this node, stripping
        # out any markup
        #print 'get_text: %s' % self
        result = ''
        for child in self:
            if isinstance(child, ElementWrapper):
                # Recurse:
                result += child.get_text()
            else:
                #print child
                result += child

        return result

    def get_xml_attr(self, attr, typeCast, defaultValue):
        if attr in self.wrappedEl._attrs:
            return typeCast(self.wrappedEl(attr))
        else:
            return defaultValue

class UnknownElement(ElementWrapper):
    pass

class XmlJob(ElementWrapper):
    def iter_recipeSets(self):
        for recipeSet in self.wrappedEl['recipeSet':]:
            yield XmlRecipeSet(recipeSet)

    def __getattr__(self, attrname):
        try:
            return self.wrappedEl[attrname]
        except: 
            raise AttributeError, attrname

class XmlRecipeSet(ElementWrapper):
    def iter_recipes(self):
        for recipe in self.wrappedEl['recipe':]:
            yield XmlRecipeMachine(recipe)

class XmlRecipe(ElementWrapper):
    def iter_tests(self):
        for test in self.wrappedEl['test':]:
            yield XmlTest(test)

    def distroRequires(self):
        return ["%s" % distroRequire for distroRequire in self.wrappedEl['distroRequires':]]

    def hostRequires(self):
        return ["%s" % hostRequire for hostRequire in self.wrappedEl['hostRequires':]]

class XmlRecipeMachine(XmlRecipe):
    def iter_guests(self):
        for guest in self.wrappedEl['guestrecipe':]:
            yield XmlRecipeGuest(guest)

class XmlRecipeGuest(XmlRecipe):
    def __getattr__(self, attrname):
        if attrname == 'guestargs':
            return self.get_xml_attr('guestargs', unicode, 'None')
        else: raise AttributeError, attrname

class XmlTest(ElementWrapper):
    def iter_params(self):
        for params in self.wrappedEl['params':]:
            for param in params['param':]:
                yield XmlParam(param)

    def __getattr__(self, attrname):
        if attrname == 'role':
            return self.get_xml_attr('role', unicode, u'None')
        elif attrname == 'name': 
            return self.get_xml_attr('name', unicode, u'None')
        else: raise AttributeError, attrname

class XmlParam(ElementWrapper):
    def __getattr__(self, attrname):
        if attrname == 'name':
            return self.get_xml_attr('name', unicode, u'None')
        elif attrname == 'value': 
            return self.get_xml_attr('value', unicode, u'None')
        else: raise AttributeError, attrname

subclassDict = {
    'job'         : XmlJob,
    'recipeSet'   : XmlRecipeSet,
    'recipe'      : XmlRecipe,
    'guestrecipe' : XmlRecipe,
    'test'        : XmlTest,
    }

if __name__=='__main__':
    file = sys.argv[1]
    FH = open(file,"r")
    xml = FH.read()
    FH.close()

    myJob = xmltramp.parse(xml)
    job   = XmlJob(myJob)

    print job.workflow
    print job.whiteboard
    print job.submitter
    for recipeSet in job.iter_recipeSets():
        for recipe in recipeSet.iter_recipes():
            print recipe.hostRequires()
            for guest in recipe.iter_guests():
                print guest.guestargs
                for test in guest.iter_tests():
                    for params in test.iter_params():
                        print "%s = %s" % (params.name, params.value)
                    print "%s %s" % (test.role, test.name)
            for test in recipe.iter_tests():
                for params in test.iter_params():
                    print "%s = %s" % (params.name, params.value)
                print "%s %s" % (test.role, test.name)
