
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from decimal import Decimal
import urllib
from itertools import chain
from rdflib.namespace import Namespace, RDF, RDFS, XSD
import rdflib.term
from rdflib.term import URIRef, Literal, BNode
from bkr.server.util import absolute_url

DC = Namespace('http://purl.org/dc/terms/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
INV = Namespace('https://fedorahosted.org/beaker/rdfschema/inventory#')

# rdflib maps python int to xsd:integer and python long to xsd:long, 
# which is completely wrong -- xsd:integer has no range constraint, whereas 
# xsd:long is a subtype of xsd:integer constrained to 64 bits 
# (python int has platform-dependent width, and python long has unbounded width).
# So we fix up the mapping table used by rdflib, but it's private data 
# so this is a nasty hack :-(
def _fixup(item):
    (py_type, (conversion, datatype)) = item
    if py_type is long:
        datatype = XSD.integer
    return (py_type, (conversion, datatype))
rdflib.term._PythonToXSD = map(_fixup, rdflib.term._PythonToXSD)
del _fixup

def bind_namespaces(graph):
    """
    Modifies the given graph's namespace mappings, so that all of the 
    namespaces we use are bound to sensible prefixes.
    """
    graph.namespace_manager.bind('dcterms', DC)
    graph.namespace_manager.bind('foaf', FOAF)
    graph.namespace_manager.bind('inv', INV)

def describe_lab_controller(lab_controller, graph):
    concept = URIRef(
            absolute_url('/lc/%s' % urllib.quote(lab_controller.fqdn.encode('utf8'), ''))
            + '#lc')
    graph.add((concept, RDF.type, INV.LabController))
    return concept

def describe_user(user, graph):
    concept = URIRef(
            absolute_url('/users/%s' % urllib.quote(user.user_name.encode('utf8'), ''))
            + '#user')
    graph.add((concept, RDF.type, FOAF.User))
    graph.add((concept, FOAF.name, Literal(user.display_name)))
    graph.add((concept, FOAF.mbox, URIRef('mailto:' + user.email_address)))
    return concept

def describe_key(key, graph):
    concept = URIRef(
            absolute_url('/keys/%s' % urllib.quote(key.key_name.encode('utf8'), ''))
            + '#key')
    graph.add((concept, RDF.type, RDF.Property))
    graph.add((concept, RDFS.label, Literal(key.key_name)))
    return concept

def describe_arch(arch, graph):
    concept = URIRef(
            absolute_url('/arch/%s' % urllib.quote(arch.arch.encode('utf8'), ''))
            + '#arch')
    graph.add((concept, RDF.type, INV.Arch))
    graph.add((concept, RDFS.label, Literal(arch.arch)))
    return concept

def describe_device(device, graph):
    concept = BNode()
    graph.add((concept, RDF.type, INV.Device))
    if device.driver and device.driver != u'Unknown':
        graph.add((concept, INV.usingDriver, Literal(device.driver)))
    if device.device_class:
        graph.add((concept, INV.ofDeviceClass,
                describe_device_class(device.device_class, graph)))
    if device.bus:
        graph.add((concept, INV.attachedToBus,
                describe_bus_type(device.bus, graph)))
    if device.bus == u'pci':
        graph.add((concept, INV.pciVendorId, Literal(device.vendor_id)))
        graph.add((concept, INV.pciDeviceId, Literal(device.device_id)))
        graph.add((concept, INV.pciSubsysVendorId, Literal(device.subsys_vendor_id)))
        graph.add((concept, INV.pciSubsysDeviceId, Literal(device.subsys_device_id)))
    if device.description:
        graph.add((concept, DC.description, Literal(device.description)))
    return concept

def describe_device_class(device_class, graph):
    concept = URIRef(
            absolute_url('/devices/%s' % urllib.quote(device_class.device_class.encode('utf8'), ''))
            + '#class')
    graph.add((concept, RDF.type, INV.DeviceClass))
    graph.add((concept, RDFS.label, Literal(device_class.device_class)))
    return concept

def describe_bus_type(bus_type, graph):
    concept = URIRef(
            absolute_url('/devices/bus/%s' % urllib.quote(bus_type.encode('utf8'), ''))
            + '#bus')
    graph.add((concept, RDF.type, INV.BusType))
    graph.add((concept, RDFS.label, Literal(bus_type)))
    return concept

def describe_system(system, graph):
    """
    Appends an RDF description of a system to the given graph.
    """
    concept = URIRef(absolute_url(system.href) + '#system')
    graph.add((concept, RDF.type, INV.System))
    graph.add((concept, INV.fqdn, Literal(system.fqdn)))
    if system.lab_controller:
        graph.add((concept, INV.controlledBy,
                describe_lab_controller(system.lab_controller, graph)))
    if system.vendor:
        graph.add((concept, INV.vendor, Literal(system.vendor)))
    if system.model:
        graph.add((concept, INV.model, Literal(system.model)))
    if system.location:
        graph.add((concept, INV.location, Literal(system.location)))
    if system.mac_address:
        graph.add((concept, INV.macAddress, Literal(system.mac_address)))
    if system.owner:
        graph.add((concept, INV.owner, describe_user(system.owner, graph)))
    for arch in system.arch:
        graph.add((concept, INV.supportsArch, describe_arch(arch, graph)))
    if system.memory:
        graph.add((concept, INV.memory, Literal(system.memory)))
    if system.numa:
        graph.add((concept, INV.numaNodes, Literal(system.numa.nodes)))
    if system.cpu:
        if system.cpu.vendor:
            graph.add((concept, INV.cpuVendor, Literal(system.cpu.vendor)))
        if system.cpu.model_name:
            graph.add((concept, INV.cpuModelName, Literal(system.cpu.model_name)))
        if system.cpu.family:
            graph.add((concept, INV.cpuFamilyId, Literal(system.cpu.family)))
        if system.cpu.model:
            graph.add((concept, INV.cpuModelId, Literal(system.cpu.model)))
        if system.cpu.stepping:
            graph.add((concept, INV.cpuStepping, Literal(system.cpu.stepping)))
        if system.cpu.speed:
            graph.add((concept, INV.cpuSpeed, Literal(Decimal(str(system.cpu.speed)))))
        if system.cpu.processors:
            graph.add((concept, INV.cpuCount, Literal(system.cpu.processors)))
        if system.cpu.cores:
            graph.add((concept, INV.cpuCoreCount, Literal(system.cpu.cores)))
        if system.cpu.sockets:
            graph.add((concept, INV.cpuSocketCount, Literal(system.cpu.sockets)))
        if system.cpu.hyper:
            graph.add((concept, INV.cpuHyperthreading, Literal(system.cpu.hyper)))
        for flag in system.cpu.flags:
            graph.add((concept, INV.cpuFlag, Literal(flag.flag)))
    for device in system.devices:
        graph.add((concept, INV.hasDevice, describe_device(device, graph)))
    for kv in chain(system.key_values_int, system.key_values_string):
        if kv.key: # ugh
            graph.add((concept, describe_key(kv.key, graph), Literal(kv.key_value)))
