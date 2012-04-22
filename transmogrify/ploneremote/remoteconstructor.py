from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.utils import Condition, Expression
from transmogrify.siteanalyser.treeserializer import TreeSerializer

import xmlrpclib
import urllib
import logging


class RemoteConstructorSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    """Drop in replacement for constructor that will use xmlprc calls
    to construct content on a remote plone site"""

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = TreeSerializer(transmogrifier, name, options, previous)
        self.context = transmogrifier.context
        #self.ttool = getToolByName(self.context, 'portal_types')

        self.typekey = defaultMatcher(options, 'type-key', name, 'type',
                                      ('portal_type', 'Type', '_type'))
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.creation_key = options.get('creation-key', '_creation_flag').strip()
        self.target = options.get('target','')
        self.logger = logging.getLogger(name)
        if self.target:
            self.target = self.target.rstrip('/')+'/'
        self.create=Condition(options.get('create-condition','python:True'), transmogrifier, name, options)
        self.move=Condition(options.get('move-condition','python:True'), transmogrifier, name, options)
        self.remove=Condition(options.get('remove-condition','python:True'), transmogrifier, name, options)

    def __iter__(self):
        if self.target:
            proxy = xmlrpclib.ServerProxy(self.target)
            basepath = proxy.getPhysicalPath()
            virtualpath = proxy.virtual_url_path()
            portal_url = self.target[:-len(virtualpath)-1]

        for item in self.previous:
            if not self.target:
                yield item
                continue
            keys = item.keys()
            type_, path = item.get(self.typekey(*keys)[0]), \
                          item.get(self.pathkey(*keys)[0])
            item[self.creation_key] = False

            if not (type_ and path):             # not enough info
                yield item
                continue

            path = path.encode('ascii')
            parentpath =  '/'.join(path.split('/')[:-1])
            parenturl = urllib.basejoin(self.target,parentpath)
            parent = xmlrpclib.ServerProxy(parenturl)


            #fti = self.ttool.getTypeInfo(type_)
            #if fti is None:                           # not an existing type
            #    msg = "constructor: no type found %s:%s" % (type_,path)
            #    logger.log(logging.ERROR, msg)
            #    yield item; continue

            elems = path.strip('/').rsplit('/', 1)
            container, id = (len(elems) == 1 and ('', elems[0]) or elems)

            for attempt in range(0, 3):
                try:

                    #if id == 'index.html':
                    #see if content already uploaded to another location
                    moved = False
                    if '_orig_path' in item:
                        old_url = portal_url+item['_orig_path']
                        f = urllib.urlopen(old_url)
                        redir = f.code == 200

                        _,_,oldpath,_,_,_ = urlparse(f.geturl())
                        parts = oldpath.split('/')
                        oldparentpath,oldid = parts[:-1],parts[-1]
                        oldparentpath = '/'.join(oldparentpath)
                        oldparenturl = urllib.basejoin(self.target,oldparentpath)
                        if '_origin' not in item:
                            item['_origin'] = item['_path']
                        #import pdb; pdb.set_trace()

                        if redir and oldparenturl != parenturl and self.move(item):
                            oldparent = xmlrpclib.ServerProxy(oldparenturl, allow_none=True)
                            cp_data = oldparent.manage_cutObjects([oldid], None)
                            parent.manage_pasteObjects(cp_data)
                            moved = True
                        else:
                            #parentpath = oldparentpath
                            #parenturl = oldparenturl
                            #parent = xmlrpclib.ServerProxy(parenturl)
                            pass

                        if redir and oldid != id and self.move(item):
                            parent.manage_renameObject(oldid, id)
                            moved = True
                        else:
                            #id = oldid
                            pass
                        path = '/'.join([parentpath,id])
                        item['_path'] = path
                    #test paths in case of acquition
                    url = urllib.basejoin(self.target, path)
                    proxy = xmlrpclib.ServerProxy(url)
                    #rpath = proxy.getPhysicalPath()
                    #rpath = rpath[len(basepath):]
                    try:
                        typeinfo = proxy.getTypeInfo()
                        existingtype = typeinfo.get('id')
                    except xmlrpclib.Fault, e:
                        existingtype = None
                        # Doesn't already exist
                        #self.logger.error("%s raised %s"%(path,e))
                    if existingtype and existingtype != type_ and self.remove(item):
                        self.logger.info("%s already exists. but is %s instead of %s. Deleting"% (path,existingtype, type_) )
                        parent.manage_delObjects([id])
                    elif existingtype:
                        # path == '/'.join(rpath):
                        if moved:
                            self.logger.info("%s moved existing item"% (path) )
                        else:
                            self.logger.info("%s already exists. Not creating"% (path) )
                        break
                    #purl = urllib.basejoin(self.target,container)
                    #pproxy = xmlrpclib.ServerProxy(purl)
                    try:
                        if self.create(item):
                            parent.invokeFactory(type_, id)
                            self.logger.info("%s Created with type=%s"% (path, type_) )
                            item[self.creation_key] = True
                    except xmlrpclib.ProtocolError,e:
                        if e.errcode == 302:
                            pass
                        else:
                            self.logger.warning("Failuire while creating '%s' of type '%s: %s'"% (path, type_, e) )
                            pass
                    except xmlrpclib.Fault, e:
                        self.logger.warning("Failuire while creating '%s' of type '%s: %s'"% (path, type_, e) )
                        pass
                    break
                except xmlrpclib.ProtocolError, e:
                    if e.errcode == 503:
                        continue
                    else:
                        self.logger.error("%s raised %s"%(path,e))
                        #raise
            yield item
