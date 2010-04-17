"""
    
    Base classes for remote Plone manipulation.
    
    Use XML-RPC / HTTP to call Plone site.

"""

from zope.interface import classProvides, implements

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher


class BadOptionException(RuntimeError):
    """ This is raised if the section blueprint is improperly configured """
    pass

class AbstractRemoteCommand(object):
    """
    Subclasses must override certain functions.
    
    Default options:
    
    * ``target``: Remote Plone site to which upload
    
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    
    def __init__(self, transmogrifier, name, options, previous):
        """ Initialize section blueprint.
        
        @param transmogrifier:  collective.transmogrifier.transmogrifier.Transmogrifier instance
        
        @param name: Section name as given in the blueprint
        
        @param previous: Prior blueprint in the chain. A Python generator object.
        
        @param options: Options as a dictionary as they appear in pipeline.cfg. Parsed INI format.    
        """    
        self.readOptions(options)
        
    def readOptions(self, options):
        """ Read options give in pipeline.cfg. 
        """
        
        # Remote site / object URL containing HTTP Basic Auth username and password 
        self.target = option.get("target", None) 
    
    def checkOptions(self):
        """ See that all necessary options have been set-up.
        
        """
        if not self.target:
            raise BadOptionException("Remote destination site must be externally configured")
                               
                               
        
