from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.utils import Condition, Expression
from transmogrify.siteanalyser.treeserializer import TreeSerializer

import xmlrpclib
import urllib
import urlparse
import logging
import httplib
import base64
import string

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
        self.alias_key = options.get('alias-key', '_origin_path').strip()
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
            self.basepath = proxy.getPhysicalPath()
            virtualpath = proxy.virtual_url_path()
            portal_url = self.target[:-len(virtualpath)-1]
            _,host,targetpath,_,_,_ = urlparse.urlparse(self.target)

        # record subjects of a folder (indexed by path) so we can set position
        subobjects = {}

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
            parenturl = urllib.basejoin(self.target, parentpath.lstrip('/'))
            parent = xmlrpclib.ServerProxy(parenturl)

            subobjects.setdefault(parentpath,[]).append(item)


            #fti = self.ttool.getTypeInfo(type_)
            #if fti is None:                           # not an existing type
            #    msg = "constructor: no type found %s:%s" % (type_,path)
            #    logger.log(logging.ERROR, msg)
            #    yield item; continue

            elems = path.strip('/').rsplit('/', 1)
            container, id = (len(elems) == 1 and ('', elems[0]) or elems)

            #if id == 'index.html':
            #see if content already uploaded to another location
            moved = False
            if self.alias_key in item:
                orig_path = item[self.alias_key]
            else:
                orig_path = item.get(self.pathkey(*keys)[0])

            # oldpath is where item is now on the remote
            redir = self.checkRedir(orig_path)
            if redir is None:
                oldpath = targetpath+orig_path
            else:
                oldpath = redir
            parts = oldpath.split('/')
            oldparentpath,oldid = parts[:-1],parts[-1]
            oldparentpath = '/'.join(oldparentpath)
            oldparenturl = urllib.basejoin(self.target, oldparentpath)
            if '_origin' not in item:
                item['_origin'] = item.get(self.pathkey(*keys)[0])

            if oldid and redir and oldparenturl != parenturl and self.move(item):
                # previous uploaded contentn needs to be moved to new location
                self.logger.debug("%s previously uploaded to %s, moving"% (path,oldpath) )
                oldparent = xmlrpclib.ServerProxy(oldparenturl, allow_none=True)
                cp_data = oldparent.manage_cutObjects([oldid], None)
                parent.manage_pasteObjects(cp_data)
                moved = True
            else:
                #parentpath = oldparentpath
                #parenturl = oldparenturl
                #parent = xmlrpclib.ServerProxy(parenturl)
                pass

            if oldid and redir and oldid != id and self.move(item):
                self.logger.debug("%s previously uploaded to %s, renaming"% (path,oldpath) )
                try:
                    parent.manage_renameObject(oldid, id)
                except:
                    # something already has that id. need to delete it
                    for i in range(1,20):
                        try:
                            parent.manage_renameObject(id, "%s-%s"%(id,i))
                            break
                        except:
                            pass
                    parent.manage_renameObject(oldid, id)
                moved = True
            else:
                #id = oldid
                pass

            if parentpath:
                path = '/'.join([parentpath, id])
            item[self.pathkey(*keys)[0]] = path

            existingtype = self.checkType(path)

            if existingtype and existingtype != type_ and self.remove(item):
                self.logger.info("%s already exists. but is %s instead of %s. Deleting"% (path,existingtype, type_) )
                parent.manage_delObjects([id])
                existingtype = None
            elif existingtype and existingtype != type_ and self.move(item):
                self.logger.info("%s already exists. but is %s instead of %s. Moving"% (path,existingtype, type_) )
                for i in range(1,20):
                    try:
                        parent.manage_renameObject(id, id+'-%s'%i)
                        break
                    except xmlrpclib.Fault:
                        pass
                existingtype = None

            elif existingtype:
                # path == '/'.join(rpath):
                if moved:
                    self.logger.debug("%s moved existing item"% (path) )
                else:
                    self.logger.debug("%s already exists. Not creating"% (path) )
            #purl = urllib.basejoin(self.target,container)
            #pproxy = xmlrpclib.ServerProxy(purl)
            try:
                if not existingtype and self.create(item):
                    self.logger.debug("%s creating as %s" % (path, type_))
                    try:
                        parent.invokeFactory(type_, id)
                    except xmlrpclib.ProtocolError, e:
                        # 302 means content was created correctly
                        if e.errcode != 302:
                            raise
                    self.logger.debug("%s Created with type=%s" % (path, type_))
                    item[self.creation_key] = True
            except xmlrpclib.ProtocolError, e:
                self.logger.warning("Failuire while creating '%s' of type '%s: %s'" % (path, type_, e))
                pass
            except xmlrpclib.Fault, e:
                self.logger.warning("Failuire while creating '%s' of type '%s: %s'" % (path, type_, e))
                pass

            # now try setting position
            position = len(subobjects[parentpath])-1
            self.logger.debug("'%s' setting position=%s"%(path,position))
            parent.moveObjectToPosition(id, position)

            yield item

    def checkRedir(self, orig_path):
        # old_url = portal_url+item['_orig_path']
        # XXX: referers to target and not portal
        old_url = self.target  + orig_path

        # this downloads file. We need a way to do this without the download
        _,host,targetpath,_,_,_ = urlparse.urlparse(self.target)
        if '@' in host:
            auth,host = host.split('@')
        else:
            auth = None

        conn = httplib.HTTPConnection(host)
        headers = {}
        if auth:
            auth = 'Basic ' + string.strip(base64.encodestring(auth))
            headers['Authorization'] = auth
        # /view is a hack as zope seems to send all content on head request
        conn.request("HEAD", targetpath+orig_path, headers=headers)
        res = conn.getresponse()
        redir = res.status == 301
        if redir and res.getheader('location'):
            _,_,oldpath,_,_,_ = urlparse.urlparse(res.getheader('location'))
            parts = oldpath.split('/')
            if parts[-1] == 'view':
                parts = parts[:-1]
            return '/'.join(parts)
        if res.status == 200:
            return orig_path
        return None

    def checkType(self, path):


        try:
            #test paths in case of acquition. ie. /publicationsandresources/faq might return 'Folder' but really be /faq
            url = '/'.join([self.target, path])
            proxy = xmlrpclib.ServerProxy(url)
            rpath = proxy.getPhysicalPath()
            # be sure to begin with a "/"
            rpath = "/"+'/'.join(rpath[len(self.basepath):]).lstrip('/')

            if rpath != '/'+path:
                # Doesn't already exist
                existingtype = None
            else:
                typeinfo = proxy.getTypeInfo()
                existingtype = typeinfo.get('id')
        except xmlrpclib.Fault, e:
            # Doesn't already exist
            #self.logger.error("%s raised %s"%(path,e))
            existingtype = None
        return existingtype