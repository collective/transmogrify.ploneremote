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
    Do remote workflow state transition using ZPublisher (Not XML-RPC).
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
    
    def split_zclient_url(self, url):
        """Split URL to ZPublisher.Client compatible format
        
        @param url: URL containing embedded HTTP Basic auth info, e.g. http://admin:admin@localhost:8080/yoursite
        
        @return: url, username, password
        """
        from urlparse import urlparse, urlunparse
        import ZPublisher.Client
        
        # ('http', 'admin:admin@localhost:8080', '/gomobile/refman/', '', '', '')
        parts = urlparse(url)
        netloc = parts[1]
        
        auth, netloc = netloc.split("@")
        username, password = auth.split(":")
        
        # Reconstruct URL without auth data
        parts = [parts[0], netloc, parts[2], parts[3], parts[4], parts[5] ]
        url = urlunparse(parts)
        
        # No ending slash allowed
        if url.endswith("/"):
            url = url[0:-1]
            
        return url, username, password
           
    def __iter__(self):
                
        # Resolve remote workflow tool.
        # We can do remote XML-RPC traversing by using the dotted notation in the object graph 

             
        import ZPublisher.Client
    
        base_url, username, password = self.split_zclient_url(self.target)
        
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
            
            remote_url = remote_url.replace(".html", "")
            
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
