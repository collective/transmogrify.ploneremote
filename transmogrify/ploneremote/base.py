"""
    
    Base classes for remote Plone manipulation.
    
    Use XML-RPC / HTTP to call Plone site.

"""

import urllib

from zope.interface import classProvides, implements

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultMatcher
import logging
from collective.transmogrifier.utils import Condition, Expression

class BadOptionException(RuntimeError):
    """ This is raised if the section blueprint is improperly configured """
    pass

class AbstractRemoteCommand(object):
    """
    Subclasses must override certain functions.
    
    Default options:
    
    * ``target``: Remote Plone site to which upload
    
    """
    implements(ISection)

    
    def __init__(self, transmogrifier, name, options, previous):
        """ Initialize section blueprint.
        
        @param transmogrifier:  collective.transmogrifier.transmogrifier.Transmogrifier instance
        
        @param name: Section name as given in the blueprint
        
        @param previous: Prior blueprint in the chain. A Python generator object.
        
        @param options: Options as a dictionary as they appear in pipeline.cfg. Parsed INI format.    
        """    
        
        # Initialize common class attributes
        self.name = name
        self.previous = previous
        self.context = transmogrifier.context
        
        self.readOptions(options)
        self.logger = logging.getLogger(name)
        self.condition=Condition(options.get('condition','python:True'), transmogrifier, name, options)

    def readOptions(self, options):
        """ Read options give in pipeline.cfg. 
        
        Initialize all parameters to None if they are not present.
        Then the options can be safely checked in checkOptions() method.
        """
        
        # Remote site / object URL containing HTTP Basic Auth username and password 
        self.target = options.get("target", None) 
        
    
    def checkOptions(self):
        """ See that all necessary options have been set-up.
        
        Note that we might want to modify the blueprint section
        instance attributes in run-time e.g. for setting the remote
        site URL and auth information, so we should not yet call checkOptions()
        during the construction.
        """
        #if not self.target:
        #    raise BadOptionException("Remote destination site must be externally configured")
                               
        # Assume target ends with slash 
        if self.target and not self.target.endswith("/"):            
            self.target += "/"              
            
    def extractKeyValue(self, item, matcher):                 
        """ Try extract key-value information from Blueprint item.
        
        @param item: Blueprint dictionary passed in __iter__()
        
        @param matcher: defaultMatcher() function used to extract key information
        
        @return: Value as a string or None if the information is not available
        """

        # Solve path key
        keys = item.keys()
        key = matcher(*keys)[0]      
        return item.get(key, None)
    
    def extractTruthValue(self, item, matcher):         
        """ Read boolean property from blueprint dictionary. 
        
        Blueprint itself can insert Python True or False object to dictionary::
        
            [mark-image-folders]
            blueprint = collective.transmogrifier.sections.inserter
            key = string:_exclude_from_navigation
            value = python:True
            condition = python:
        
        @return: True or False or None
        """
        value = self.extractKeyValue(item, matcher)
        if value is None:
            return None
        
        if not value in [True,False]:
            raise RuntimeError("Invalid truth value:" + str(value))
        
        return value
    
class PathBasedAbstractRemoteCommand(AbstractRemoteCommand):
    """
    A remote command with the default logic to extract _path hint from blueprint item.
    """
    
    def readOptions(self, options):
        """ Read options give in pipeline.cfg. 
        """
        
        # Call parent 
        AbstractRemoteCommand.readOptions(self, options)
        
        # Remote site / object URL containing HTTP Basic Auth username and password.
        # Note: self.pathkey is a function
        self.pathkey = defaultMatcher(options, 'path-key', self.name, 'path')

        self.typekey = defaultMatcher(options, 'type-key', self.name, 'type',
                                      ('portal_type', 'Type','_type'))
    

    def extractPath(self, item):
        """ Try extract path information from Blueprint item.
        
        @return: Item's path as a string or None if the information is not available
        """
        return self.extractKeyValue(item, self.pathkey)

    def extractType(self, item):
        """ Try extract type information from Blueprint item.
        
        @return: Item's type as a string or None if the information is not available
        """
        return self.extractKeyValue(item, self.typekey)
        
    def constructRemoteURL(self, item, allow_index_html=False):
        """
        @param allow_index_html: if path is index.html it falls back to the default folder
        """
    
        path = self.extractPath(item)
        
        if allow_index_html:
            if path.endswith("index.html"):
                path = path[0:-len("index.html")]        
        
        remote_url = urllib.basejoin(self.target, path)
        if not remote_url.endswith("/"):
            remote_url += "/"
    
        return remote_url