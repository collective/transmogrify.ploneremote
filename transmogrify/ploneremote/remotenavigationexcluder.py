import urllib
import xmlrpclib
import logging
from zope.interface import classProvides, implements

from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.interfaces import ISectionBlueprint

from base import PathBasedAbstractRemoteCommand 

logger = logging.getLogger('Plone')

class RemoteNavigationExcluderSection(PathBasedAbstractRemoteCommand):
    """
    Set "Exclude from Navigation" setting for remote Plone content items.
    """
    
    classProvides(ISectionBlueprint)
    
    def readOptions(self, options):
        """ Read options give in pipeline.cfg. 
        """
        
        # Call parent 
        PathBasedAbstractRemoteCommand.readOptions(self, options)
    
        # Which key we use to read navigation exclusion hint 
        self.exclusion = defaultMatcher(options, 'exclude-from-navigation-key', self.name, 'exclude-from-navigation')
    
    def __iter__(self):
    
        self.checkOptions()
                            
        for item in self.previous:
            
            path = self.extractPath(item)
            exclude_from_nav = self.extractTruthValue(item, self.exclusion)
            
            if path is None or exclude_from_nav is None: 
                # The blueprint item did not provide necessary
                # info to perform this pipeline transformation
                yield item
                continue
            
            logger.debug("Setting exclude from navigation for " + path + " to " + str(exclude_from_nav))
                                        
            url = self.constructRemoteURL(item)            

            proxy = xmlrpclib.ServerProxy(url)
            proxy.setExcludeFromNav(exclude_from_nav)
            
            # Make sure the change is reflected to portal_catalog
            # TODO: Can't figure out how to pass named arguments to XML-RPC proxy
            # proxy.reindexObject(arguments={"idxs" : ["exclude_from_nav"]})
            
            proxy.reindexObject()
            
            yield item
