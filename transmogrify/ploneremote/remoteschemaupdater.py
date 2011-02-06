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
            self.target = self.target.rstrip('/')+'/'
        

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)


    def __iter__(self):
        for item in self.previous:
            if not self.target:
                yield item; continue

            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey:         # not enough info
                yield item; continue

            path = item[pathkey]
            
            url = urllib.basejoin(self.target, path)
            
            changed = False
            errors = []
            
            # support field arguments via 'fieldname.argument' syntax
            # result is dict with tuple (value, fieldarguments)
            # stored in fields variable
            fields = {}
            updated = []
            proxy = xmlrpclib.ServerProxy(url)
            multicall = xmlrpclib.MultiCall(proxy)
            for key, value in item.iteritems():
                if key.startswith('_'):
                    continue
                parts = key.split('.',1)
                fields.setdefault(parts[0], [None,{}])
                if len(parts)==1:
                    fields[parts[0]][0] = value
                else:
                    fields[parts[0]][1][parts[1]] = value
                    
                for key, parts in fields.items():
                    value, arguments = parts

                    if type(value) == type(u''):
                        value = value.encode('utf8')
                    elif getattr(value,'read', None):
                        value = value.read()
                    elif value is None:
                        # Do not update fields for which we have not received
                        # values is transmogrify.htmlextractor
                        self.logger.warning('%s %s=%s'%(path, key, value))
                        continue

                    #getattr(proxy,'set%s'%key.capitalize())(value)
                    arguments.update(dict(value=value))
                    input = urllib.urlencode(arguments)
                    f = urllib.urlopen(url+'/set%s'%key.capitalize(), input)
                    nurl = f.geturl()
                    info = f.info()
                    updated.append(key)
            if fields:
                self.logger.info('%s set fields=%s'%(path, fields.keys()))
            
            for attempt in range(0,3):
                try:
                    if '_defaultpage' in item:
                        proxy.setDefaultPage(item['_defaultpage']) 
                        proxy.update() #does indexing
                        self.logger.info('%s.setDefaultPath=%s'%(path, item['_defaultpage']))
                    break
                except xmlrpclib.ProtocolError,e:
                    if e.errcode == 503:
                        continue
                    else:
                        raise
                except xmlrpclib.Fault,e:
                    pass


            yield item



