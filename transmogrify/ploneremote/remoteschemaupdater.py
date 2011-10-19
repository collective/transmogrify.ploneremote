#from zope import event
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import urllib
import xmlrpclib
import logging


class RemoteSchemaUpdaterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.target = options['target']
        self.logger = logging.getLogger(name)
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
            #multicall = xmlrpclib.MultiCall(proxy)
            # handle complex fields e.g. image = ..., image.filename =
            # 'blah.gif', image.mimetype = 'image/gif'
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
                    f = urllib.urlopen(url + '/set%s' % key.capitalize(),
                        input)
                    #nurl = f.geturl()
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
                        # XXX Too noisy?
                        #self.logger.error("%s.set%s(%s) raised %s"%(
                        #path,method,value,e))
                        self.logger.error(
                            "%s.set%s(value) raised xmlrpclib fault error" % (
                                path, method))
                        pass
                    except xmlrpclib.ProtocolError, e:
                        # XXX Too noisy?
                        #self.logger.error("%s.set%s(%s) raised %s"%(
                        #path,method,value,e))
                        self.logger.error(
                            "%s.set%s(value) raised xmlrpclib protocol error" %
                                (path, method))
                        pass
                updated.append(key)
            if fields:
                self.logger.info('%s set fields=%s' % (path, fields.keys()))
                try:
                    proxy.update()  # does indexing
                except:
                    # Keep going!
                    pass

#            for attempt in range(0,3):
#                try:
#                    if '_defaultpage' in item:
#                        proxy.setDefaultPage(item['_defaultpage'])
#                        self.logger.info('%s.setDefaultPath=%s'%(path,
#                           item['_defaultpage']))
#                    break
#                except xmlrpclib.ProtocolError,e:
#                    if e.errcode == 503:
#                        continue
#                    else:
#                        raise
#                except xmlrpclib.Fault,e:
#                    pass
            yield item
