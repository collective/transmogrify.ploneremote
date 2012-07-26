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
import datetime
import DateTime


""" Simple blueprint to upload static text portlets to a page """



class RemotePortlets(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.target = options['target']
        self.logger = logging.getLogger(name)
        self.condition=Condition(options.get('condition','python:True'), transmogrifier, name, options)
        self.prefixes = [
                ('left','title', options.get('left-title-prefix','_left_portlet_title')),
                ('left','text', options.get('left-text-prefix','_left_portlet_text')),
                ('right','title', options.get('right-title-prefix','_right_portlet_title')),
                ('right','text', options.get('right-text-prefix','_right_portlet_text')),
        ]

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
            url = self.target + path

            portlets = {}
            for key, value in item.items():
                for side, part, prefix in self.prefixes:
                    if key.startswith(prefix):
                        pos = key.lstrip(prefix)
                        portlets.setdefault(side,{}).setdefault(pos,{})[part] = value

            for side,sideportlets in portlets.items():
                for pos, portlet in sorted(sideportlets.items()):
                    proxy = xmlrpclib.ServerProxy(url+'/++contextportlets++plone.%scolumn'%side)
                    addurl = url+'/++contextportlets++plone.%scolumn/+/plone.portlet.static.Static'%side
                    if 'title' not in portlet:
                        title = 'static'
                    else:
                        title = portlet['title']

                    # HACK to delete portlet
                    try:
                        getattr(proxy, '@@delete-portlet')(title.lower().replace(' ','-'))
                    except xmlrpclib.ProtocolError:
                        # 302 means it worked
                        pass
                    except xmlrpclib.Fault:
                        # it wasn't there
                        pass

                    input = urllib.urlencode({'form.header':title,
                                              'form.text':portlet['text'],
                                              'form.omit_border':'checked',
                                              'form.portlet_style': ' ',
                                              'form.actions.save': 'Save'})
                    f = None
                    try:
                        f = urllib.urlopen(addurl, input)
                        if f.url != addurl:
                            #success!
                            self.logger.debug('%s add %s portlet "%s"'%(path, side, title))
                        else:
                            self.logger.debug('%s FAILED to add %s portlet "%s"'%(path, side, title))
                    except IOError, e:
                        #import pdb; pdb.set_trace()
                        self.logger.warning("%s.set%s() raised %s"%(path,method,e))



            yield item
