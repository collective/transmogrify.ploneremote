#from zope import event
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import urllib
import xmlrpclib
import logging
from collective.transmogrifier.utils import Condition, Expression



class RemoteSchemaUpdaterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.target = options['target']
        self.logger = logging.getLogger(name)
        self.condition=Condition(options.get('condition','python:True'), transmogrifier, name, options)
        self.skip_existing = options.get('skip-existing','False').lower() in ['true','yes']
        if self.target:
            self.target = self.target.rstrip('/') + '/'

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)

    def __iter__(self):
        for item in self.previous:
            if not self.target:
                yield item
                continue

            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey:         # not enough info
                yield item
                continue


            path = item[pathkey]
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
            multicall = xmlrpclib.MultiCall(proxy)

            if not self.condition(item, proxy=proxy):
                self.logger.info('%s skipping (condition)'%(path))
                yield item; continue

            #if self.skip_existing:
            #    import pdb; pdb.set_trace()
            #    if proxy.CreationDate() != proxy.ModificationDate():
            #        self.logger.info('%s skipping existing'%(path))
            #        yield item; continue


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
            if '_defaultpage' in item:
                fields['DefaultPage'] = (item['_defaultpage'], {})
            if '_mimetype' in item:
                # Without this plone 4.1 doesn't update html correctly
                fields['ContentType'] = (item['_mimetype'], {})

            for key, parts in fields.items():
                value, arguments = parts

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

                method = key[0].upper() + key[1:]
                if arguments:
                    #need to use urllib for keywork arguments
                    arguments.update(dict(value=value))
                    input = urllib.urlencode(arguments)
                    f = None
                    for attempt in range(0,3):
                        try:
                            f = urllib.urlopen(url + '/set%s'%key.capitalize(), input)
                            break
                        except IOError, e:
                            #import pdb; pdb.set_trace()
                            self.logger.warning("%s.set%s() raised %s"%(path,method,e))
                    if f is None:
                        self.logger.warning("%s.set%s() raised too many errors. Giving up"%(path,method))
                        break


                    nurl = f.geturl()
                    info = f.info()
                    #print method + str(arguments)
                    if info.status != '':
                        e = str(f.read())
                        f.close()
                        self.logger.error("%s.set%s(%s) raised %s" % (
                            path, method, arguments, e))
                else:
                    # setModificationDate doesn't use 'value' keyword
                    try:
                        # XXX Better way than catching method names?
                        if method == 'Image':    # wrap binary image data
                            value = xmlrpclib.Binary(value)  

                        getattr(proxy, 'set%s' % method)(value)

                    except xmlrpclib.Fault, e:
                        self.logger.error("%s.set%s(%s) raised %s"%(path,method,value,e))
                    except xmlrpclib.ProtocolError, e:
                        self.logger.error("%s.set%s(%s) raised %s"%(path,method,value,e))
                    updated.append(key)
            if fields:
                self.logger.info('%s set fields=%s'%(path, fields.keys()))
                try:
                    proxy.update() #does indexing
                except xmlrpclib.Fault, e:
                    self.logger.error("%s.update() raised %s"%(path,e))
                except xmlrpclib.ProtocolError, e:
                    self.logger.error("%s.update() raised %s"%(path,e))
            yield item
