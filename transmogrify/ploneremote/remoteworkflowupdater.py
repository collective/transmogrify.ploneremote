import urllib
import xmlrpclib
import logging

from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException

logger = logging.getLogger('Plone')

class RemoteWorkflowUpdaterSection(object):
    """
    Do remote workflow state transition using Plone HTTP API.
    
    Trigger the same HTTP GET query as Workflow menu does in the user interface.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.transitionskey = defaultMatcher(options, 'transitions-key', name,
                                             'transitions')
        
        # Remote site urL
        self.target = options.get('target','http://localhost:8080/plone')
    
           
    def __iter__(self):
                

        # URL of the Plone container we are populating which 
        target = self.target
        if not target.endwith("/"):            
            target += "/"
            
        for item in self.previous:
            keys = item.keys()
            
            # Apply defaultMatcher() function to extract necessary data
            # 1) which item will be transitioned
            # 2) with which transition
            pathkey = self.pathkey(*keys)[0]
            transitionskey = self.transitionskey(*keys)[0]

            if not (pathkey and transitionskey): # not enough info
                yield item
                continue
            
            path, transitions = item[pathkey], item[transitionskey]
            if isinstance(transitions, basestring):
                transitions = (transitions,)
            
                
            remote_url = urllib.basejoin(target, path)
            if not remote_url.endswith("/"):
                remote_url += "/"
                
            #remote_url = remote_url.replace(".html", "")
    
            for transition in transitions:
    
                
                transition_trigger_url = urllib.basejoin(remote_url, "content_status_modify?workflow_action=" + transition)
                logger.info("Performing transition %s for item %s" % (transition, transition_trigger_url))
                
                try:
                
                    f= urllib.urlopen(transition_trigger_url)
                    data = f.read()
                    print data
                except:
                    # Other than HTTP 200 OK should end up here,
                    # unless URL is broken in which case Plone shows
                    # "Your content was not found page"
                    logger.error("fail")
                    msg = "Remote workflow transition failed %s->%s" %(path,transition)
                    logger.log(logging.ERROR, msg, exc_info=True)
            
            yield item
