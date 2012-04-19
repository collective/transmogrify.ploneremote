import xmlrpclib
import logging
from zope.interface import classProvides

from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.utils import Condition, Expression


from base import PathBasedAbstractRemoteCommand

logger = logging.getLogger('Plone')


class RemoteNavigationExcluderSection(PathBasedAbstractRemoteCommand):
    """
    Set "Exclude from Navigation" setting for remote Plone content items.
    """
    classProvides(ISectionBlueprint)

    def readOptions(self, options):
        """ Read options give in pipeline.cfg
        """
        # Call parent
        PathBasedAbstractRemoteCommand.readOptions(self, options)
        # Which key we use to read navigation exclusion hint
        self.exclusion = defaultMatcher(options, 'exclude-from-navigation-key',
            self.name, 'exclude-from-navigation')

    def __iter__(self):
        self.checkOptions()
        for item in self.previous:
            keys = item.keys()
            typekey = self.typekey(*keys)[0]
            pathkey = self.pathkey(*keys)[0]
            path = self.extractPath(item)
            type = self.extractType(item)
            exclude_from_nav = self.extractTruthValue(item, self.exclusion)

            if not (typekey and pathkey):             # not enough info
                yield item
                continue
            if (path is None or type is None or exclude_from_nav is None or not
                self.target):
                # The blueprint item did not provide necessary
                # info to perform this pipeline transformation
                yield item
                continue

            proxy = xmlrpclib.ServerProxy(self.constructRemoteURL(item))
            if not self.condition(item, proxy=proxy):
                self.logger.info('%s skipping (condition)'%(path))
                yield item; continue

            logger.debug("Setting exclude from navigation for " + path + " to "
                + str(exclude_from_nav))
            url = self.constructRemoteURL(item)

            proxy = xmlrpclib.ServerProxy(url)
            proxy.setExcludeFromNav(exclude_from_nav)
            # Make sure the change is reflected to portal_catalog
            # TODO: Can't figure out how to pass named arguments to XML-RPC
            # proxy
            # proxy.reindexObject(arguments={"idxs" : ["exclude_from_nav"]})
            proxy.reindexObject()
            yield item
