import urllib
import xmlrpclib
import logging

from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException

from 

logger = logging.getLogger('Plone')

class RemoteWorkflowUpdaterSection(object):
    """
    Do remote workflow state transition using ZPublisher (Not XML-RPC).
    """
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        


    def readOptions(self, options):
        """ Read options give in pipeline.cfg. 
        """
        
        # Remote site / object URL containing HTTP Basic Auth username and password 
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.transitionskey = defaultMatcher(options, 'transitions-key', name,
                                             'transitions')

               
    def __iter__(self):
    
        self.checkOptions()
                
        # Resolve remote workflow tool.
        # We can do remote XML-RPC traversing by using the dotted notation in the object graph     
        workflow_url = urllib.basejoin(base_url, "portal_workflow")            
        wf_tool = ZPublisher.Client.Object(workflow_url, 
                                       username=username, 
                                       password=password,
                                       )
        
        for item in self.previous:
            keys = item.keys()
            
            # Apply defaultMatcher() function to extract necessary data
            pathkey = self.pathkey(*keys)[0]
            transitionskey = self.transitionskey(*keys)[0]

            if not (pathkey and transitionskey): # not enough info
                yield item
                continue
            
            path, transitions = item[pathkey], item[transitionskey]
            if isinstance(transitions, basestring):
                transitions = (transitions,)
            
            #remote_url = urllib.basejoin(base_url, path)
            remote_url = base_url + "/" + path
            

            remote_object = ZPublisher.Client.Object(remote_url, 
                                       username=username, 
                                       password=password,
                                       )

                    
    
            for transition in transitions:
            
                logger.info("Performing transition %s for item %s" % (transition, remote_url))
                
                try:
                
                    # workflow_tool.doActionFor() cannot be called
                    # for some reason using remote object traversing.
                    # We do it in painful way.
                    wf_tool.doActionFor(ob=remote_object, action=transition)
                    
                    print "Da?"
                except:
                    logger.error("fail")
                    msg = "Remote workflow transition failed %s->%s" %(path,transition)
                    logger.log(logging.ERROR, msg, exc_info=True)
            
            yield item
