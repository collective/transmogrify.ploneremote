from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher
from transmogrify.pathsorter.treeserializer import TreeSerializer

from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
import xmlrpclib
import urllib
from urlparse import urlparse, urljoin
import logging

class RemoteConstructorSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    "Drop in replacement for constructor that will use xmlprc calls to construct content on a remote plone site"

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = TreeSerializer(transmogrifier, name, options, previous)
        self.context = transmogrifier.context
        #self.ttool = getToolByName(self.context, 'portal_types')

        self.typekey = defaultMatcher(options, 'type-key', name, 'type',
                                      ('portal_type', 'Type','_type'))
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.target = options.get('target','')
        self.logger = logging.getLogger(name)
        if self.target:
            self.target = self.target.rstrip('/')+'/'

    def __iter__(self):
        if self.target:
            basepath = xmlrpclib.ServerProxy(self.target).getPhysicalPath()
        for item in self.previous:
            if not self.target:
                yield item
                continue
            keys = item.keys()
            type_, path = item.get(self.typekey(*keys)[0]), item.get(self.pathkey(*keys)[0])

            if not (type_ and path):             # not enough info
                yield item; continue

            path = path.encode('ascii')


            #fti = self.ttool.getTypeInfo(type_)
            #if fti is None:                           # not an existing type
            #    msg = "constructor: no type found %s:%s" % (type_,path)
            #    logger.log(logging.ERROR, msg)
            #    yield item; continue

            elems = path.strip('/').rsplit('/', 1)
            
            for attempt in range(0, 3):
                try:
                
                    url = urllib.basejoin(self.target, path)
                    proxy = xmlrpclib.ServerProxy(url)
                    container, id = (len(elems) == 1 and ('', elems[0]) or elems)
                    #if id == 'index.html':
                    try:
                        #test paths in case of acquition
                        rpath = proxy.getPhysicalPath()
                        #TODO: should check type to see if it's correct?
                        rpath = rpath[len(basepath):]
                        typeinfo = proxy.getTypeInfo()
                        existingtype = typeinfo.get('id')
                        if existingtype != type_:
                            self.logger.info("%s already exists. but is %s instead of %s. Deleting"% (path,existingtype, type_) )
                            parentpath =  '/'.join(path.split('/')[:-1])
                            parent = xmlrpclib.ServerProxy(urllib.basejoin(self.target,parentpath))
                            parent.manage_delObjects([id])

                        elif path == '/'.join(rpath):
                            self.logger.debug("%s already exists. Not creating"% (path) )
                            break
                    except xmlrpclib.Fault, e:
                        # Doesn't already exist
                        pass
                    purl = urllib.basejoin(self.target,container)
                    pproxy = xmlrpclib.ServerProxy(purl)
                    try:
                        pproxy.invokeFactory(type_, id)
                        self.logger.info("%s Created with type=%s"% (path, type_) )
                    except xmlrpclib.ProtocolError,e:
                        if e.errcode == 302:
                            pass
                        else:
                            raise
                    except xmlrpclib.Fault, e:
                        self.logger.warning("Failuire while creating '%s' of type '%s: %s'"% (path, type_, e) )
                        pass
                    break
                except xmlrpclib.ProtocolError,e:
                    if e.errcode == 503:
                        continue
                    else:
                        raise
            
            yield item
            
