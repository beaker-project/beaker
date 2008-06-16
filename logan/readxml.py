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

class Job(ElementWrapper):
    pass

class RecipeSet(ElementWrapper):
    pass

class Recipe(ElementWrapper):
    pass

class Guest(ElementWrapper):
    pass

class Whiteboard(ElementWrapper):
    def __repr__(self):
        return self.get_text()

class Workflow(ElementWrapper):
    pass

class Submitter(ElementWrapper):
    pass

subclassDict = {
    'workflow' : Workflow,
    'submitter' : Submitter,
    'whiteboard' : Whiteboard,
    'recipeSet' : RecipeSet,
    'recipe' : Recipe,
    'guestrecipe' : Guest,
    }

file = sys.argv[1]
FH = open(file,"r")
xml = FH.read()
FH.close()

myDom = xmltramp.parse(xml)
for elem in myDom:
    print elem._name

#for elem in ElementWrapper(myDom):
#    print elem
