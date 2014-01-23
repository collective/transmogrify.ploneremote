
import unittest2 as unittest
import sys
import  zope.app.component

#from zope.testing import doctest
import doctest
from zope.component import provideUtility
from Products.Five import zcml
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint, ISection

from Testing import ZopeTestCase as ztc
from Products.Five import fiveconfigure

from collective.transmogrifier.tests import setUp as baseSetUp
from collective.transmogrifier.tests import tearDown
#from collective.transmogrifier.sections.tests import PrettyPrinter
import logging

from plone.app.testing import PLONE_FIXTURE, \
    PLONE_FUNCTIONAL_TESTING, PLONE_INTEGRATION_TESTING




class HTMLSource(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.items = []
        for order,item in zip(range(0,len(options)),options.items()):
            path,text = item 
            if path in ['blueprint']:
                continue
            item_ = dict(
#                _mimetype="text/html",
#                 _site_url="http://test.com/",
                 _path=path,
                 text=text,
#                        _sortorder=order,
                 )
            self.items.append(item_)

    def __iter__(self):
        for item in self.previous:
            yield item

        for item in self.items:
            yield item




class TestExample(unittest.TestCase):

    layer = PLONE_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']

        from collective.transmogrifier.transmogrifier import Transmogrifier
        from collective.transmogrifier.tests import registerConfig
        self.transmogrifier = Transmogrifier(self.portal)
        self.registerConfig = registerConfig

        import zope.component
        import collective.transmogrifier.sections
        zcml.load_config('meta.zcml', zope.app.component)
        zcml.load_config('configure.zcml', collective.transmogrifier.sections)
        zcml.load_config('configure.zcml', collective.transmogrifier.sections.tests)
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)



        provideUtility(PrettyPrinter,
            name=u'collective.transmogrifier.sections.tests.pprinter')
        provideUtility(TemplateFinder,
            name=u'transmogrify.htmlcontentextractor')
        provideUtility(HTMLSource,
            name=u'transmogrify.htmlcontentextractor.test.htmlsource')

    def test_product_is_installed(self):
        """
        Validate that our products GS profile has been run and the product
        installed
        """
        pid = 'collective.listingviews'
        installed = [p['id'] for p in self.qi_tool.listInstalledProducts()]
        self.assertTrue(pid in installed,
                        'package appears not to have been installed')


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


