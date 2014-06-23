#from zope import event
import socket
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import urllib
import xmlrpclib
import logging
from collective.transmogrifier.utils import Condition
#import datetime
import DateTime
from ZPublisher.Client import Object, call
from collective.transmogrifier.utils import defaultMatcher


class RemoteSchemaUpdaterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.target = options['target']
        self.logger = logging.getLogger(name)
        self.name = name
        self.condition = Condition(options.get('condition', 'python:True'), transmogrifier, name, options)
        self.skip_existing = options.get('skip-existing', 'False').lower() in ['true', 'yes']
        self.skip_unmodified = options.get('skip-unmodified', 'True').lower() in ['true', 'yes']
        self.skip_fields = set([f.strip() for f in options.get('skip-fields', '').split('\n') if f.strip()])
        self.skip_until_path = options.get('skip-until-path','')
        self.creation_key = options.get('creation-key', '_creation_flag').strip()
        self.headers_key = options.get('headers-key', '_content_info').strip()
        self.defaultpage_key = options.get('defaultpage-key', '_defaultpage').strip()
        self.skipkey = options.get('skip-update-key', '_skip-update')

        if self.target:
            self.target = self.target.rstrip('/') + '/'

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)

    def __iter__(self):

        # We will create a helper Python script on the server to help get around
        # problems in the plone api for updating fields.

        baseproxy=None
        if self.target:
            try:
                baseproxy = xmlrpclib.ServerProxy(self.target)
                baseproxy.manage_addProduct.PythonScripts.manage_addPythonScript('remoteschemaupdater_update')
            except xmlrpclib.ProtocolError:
                # tmp redir after add
                pass
            except xmlrpclib.Fault:
                # it already exists
                pass
            params = "path, values"
            body = "context.restrictedTraverse(path).update(**values); return True"
            baseproxy.remoteschemaupdater_update.ZPythonScriptHTML_editAction(
                False, '', params, body)

        if not self.skip_until_path:
            pathfound = True
        else:
            pathfound = False

        for item in self.previous:
            if not self.target:
                yield item
                continue

            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey:         # not enough info
                yield item
                continue

            path = item[pathkey]

            if not pathfound:
                if path == self.skip_until_path:
                    pathfound = True
                else:
                    self.logger.info('%s skipping (skip-until-path)' % (path))
                    if self.skipkey and self.skipkey not in item:
                        item[self.skipkey] = True
                    yield item
                    continue

            # XXX Why basejoin?
            # url = urllib.basejoin(self.target, path)
            url = self.target + path
            #changed = False
            #errors = []
            # support field arguments via 'fieldname.argument' syntax
            # result is dict with tuple (value, fieldarguments)
            # stored in fields variable
            fields = {}
            updated = []
            proxy = xmlrpclib.ServerProxy(url)
            #multicall = xmlrpclib.MultiCall(proxy)

            if not self.condition(item, proxy=proxy):
                self.logger.info('%s skipping (condition)' % (path))
                if self.skipkey and self.skipkey not in item:
                    item[self.skipkey] = True
                yield item
                continue

            if self.creation_key and str(item.get(self.creation_key, 'True')).lower() in ['false', 'off']:
                created = False
            else:
                created = True

            if self.skip_existing and not created:
                self.logger.info('%s skipping existing' % (path))
                if self.skipkey and self.skipkey not in item:
                    item[self.skipkey] = True
                yield item
                continue

            # handle complex fields e.g. image = ..., image.filename = 'blah.gif', image.mimetype = 'image/gif'
            for key, value in item.iteritems():
                if key.startswith('_'):
                    continue
                parts = key.split('.', 1)
                key = parts[0]
                fields.setdefault(key, [None, {}])
                if len(parts) == 1:
                    fields[key][0] = value
                else:
                    subkey = parts[1]
                    fields[key][1][subkey] = value

            if self.defaultpage_key in item:
                defaultpage = item[self.defaultpage_key]
                self.logger.debug("'%s' setting default page (%s)" % (path, defaultpage))
                fields['DefaultPage'] = (defaultpage, {})
            if '_mimetype' in item:
                # Without this plone 4.1 doesn't update html correctly
                self.logger.debug("'%s' setting content type (%s)" % (path, item['_mimetype']))
                fields['ContentType'] = (item['_mimetype'], {})
            if created:
                modified = None
            elif self.headers_key in item:
                modified = item[self.headers_key].get('last-modified', '')
                if 'modificationDate' not in fields:
                    fields['modificationDate'] = (modified, {})
                #modified = datetime.datetime.strptime(modified, "%Y-%m-%dT%H:%M:%S.Z")
                if modified:
                    modified = DateTime.DateTime(modified)
                else:
                    modified = None

            else:
                modified = None

            while True:
                retry = 0
                try:
                    smodified = proxy.ModificationDate()
                    break
                except:
                    retry += 1
                    if retry == 3:
                        raise
            #smodified = datetime.datetime.strptime(smodified, "%Y-%m-%dT%H:%M:%S.Z")
            if type(smodified) == type(''):
                smodified = DateTime.DateTime(smodified)
            if self.skip_unmodified and modified and smodified and modified <= smodified:
                # Let's double check it at least has a size
                size = float(urllib.urlopen(url + '/getObjSize').read().split()[0])
                if size > 0:
                    self.logger.info('%s skipping (unmodified)' % (path))
                    if self.skipkey and self.skipkey not in item:
                        item[self.skipkey] = True
                    yield item
                    continue

            complex_values = []
            single_update = {}

            for key, parts in fields.items():
                value, arguments = parts
                if not created and key in self.skip_fields:
                    continue

                if type(value) == type(u''):
                    value = value.encode('utf8')
                elif getattr(value, 'read', None):
                    file = value
                    value = file.read()
                    try:
                        file.seek(0)
                    except AttributeError:
                        file.close()
                elif value is None:
                    # Do not update fields for which we have not received
                    # values is transmogrify.htmlextractor
                    self.logger.warning('%s %s=%s' % (path, key, value))
                    continue

                if arguments:
                    #need to use urllib for keywork arguments
                    arguments.update(dict(value=value))
                    complex_values.append( (key, arguments) )
                else:
                    ## XXX Better way than catching method names?
                    #if key.lower() == 'image':    # wrap binary image data
                    #    value = xmlrpclib.Binary(value)

                    # in case user got confused about field names
                    if key == 'modificationDate':
                        key = 'modification_date'
                    elif key == 'creationDate':
                        key = 'creation_date'
                    single_update[key] = value

            for key, input in complex_values:
                method = key[0].upper() + key[1:]
                if self.urlrpc(url + '/set%s' % method, input):
                    updated.append(key)

            if single_update:
                # Problem with using update is it gives no error. Maybe verify fields in schema first?
                # Advantage of update is it works with schemaextender
                retry = 0
                while True:
                    try:
                        if baseproxy.remoteschemaupdater_update(path, single_update):
                        #if Object(url).update(**single_update):
                            updated.extend(single_update.keys())
                        self.logger.info('%s set fields=%s' % (path, updated))
                        break
                    except socket.error:
                        self.logger.warning('RETRY: Socker.error during %s set fields=%s' % (path, updated))
                        retry += 0
                        if retry == 3:
                            raise
            elif updated:
                try:
                    # doesn't set modified
                    proxy.reindexObject(updated)
                except xmlrpclib.Fault, e:
                    self.logger.error("%s.reindexObject() raised %s" % (path, e))
                except xmlrpclib.ProtocolError, e:
                    self.logger.error("%s.reindexObject() raised %s" % (path, e))
                self.logger.info('%s set fields=%s' % (path, updated))
            else:
                self.logger.info('%s no fields to set' % (path))

            yield item

        # finally remove our helper method
        if baseproxy is not None:
            baseproxy.manage_delObjects(['remoteschemaupdater_update'])

    def urlrpc(self, url, args):
        """
        calls urllib open for plone view. returns a status code, or logs error.
        handles retries in case of connection problems.
        """
        input = urllib.urlencode(args)
        f = None
        retry = 0
        while True:
            try:
                f = urllib.urlopen(url, input)
                break
            except IOError, e:
                retry += 1
                #import pdb; pdb.set_trace()
                self.logger.warning("%s raised %s" % (url, e))
                if retry == 3:
                    raise
        if f is None:
            self.logger.warning("%s raised too many errors. Giving up" % url)
            return False

        #nurl = f.geturl()
        info = f.info()
        #print method + str(arguments)
        if info.status != '':
            e = str(f.read())
            f.close()
            self.logger.error("%s %s raised %s" % (
                url, args, e))
            return False
        else:
            return True
