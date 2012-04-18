"""

    Remove remove Plone content items which are no longer present locally.

"""

import urllib
import xmlrpclib
import logging

from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException

from base import AbstractRemoteCommand, PathBasedAbstractRemoteCommand
import xmlrpclib


logger = logging.getLogger('remoteprune')

class RemotePruneSection(PathBasedAbstractRemoteCommand):
    """
    
    Parameters:
    
    * prune-folder-key: which transmogrifier field is read to check 
      if the prune folder is run against the remote folder. 
      The default value os "_prune-folder"
      
    
    Also handle special root object created by treeserializer.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def readOptions(self, options):
        """ Read options give in pipeline.cfg. 
        """
        
        # Call parent 
        PathBasedAbstractRemoteCommand.readOptions(self, options)

        # Remote site / object URL containing HTTP Basic Auth username and password 
        self.prune_folder_matcher = defaultMatcher(options, 'prune-folder-key', self.name, 'prune-folder')

    def getRemoteObjectIds(self, item):
        """ Fetch the folder listing from the remote site """
        url = self.constructRemoteURL(item)              
        proxy = xmlrpclib.ServerProxy(url)
        ids = proxy.contentIds()
        return ids
    
    def deleteRemoteObject(self, item, id):
        """ Perform object deletion over XML-RPC """        
        url = self.constructRemoteURL(item)            
        proxy = xmlrpclib.ServerProxy(url)
        proxy.manage_delObjects([id])
        
    def getLocalObjects(self, item):
        """ Fetch the list of item's local childs.
        
        @return: dict local id -> item
        """
        
        mappings = {}
        
        children = item.get("_children", [])
        for child in children:
            path = child.get("_path", None)
            if not path:
                continue
            
            parts = path.split("/")
            id = parts[-1]             
            
            mappings[id] = child
            
        
        return mappings 
            
    def __iter__(self):
    
        self.checkOptions()
                            
                            
        for item in self.previous:            
            
            proxy = xmlrpclib.ServerProxy(self.constructRemoteURL(item))
            path = self.extractPath(item)
            if not path:
                yield item; continue

            if not self.condition(item, proxy=proxy):
                self.logger.info('%s skipping (condition)'%(path))
                yield item; continue

            # See if "prune" flag is set for this tranmogrifier item
            prune = self.extractTruthValue(item, self.prune_folder_matcher)
                    
            if prune:                
                # This folder contains content to be pruned
                                   
                # Make list of ids which are dangling on the remote site
                remote_ids = self.getRemoteObjectIds(item)
                                                
                local_data = self.getLocalObjects(item)
                local_ids = local_data.keys()
                
                for remote_id in remote_ids:

                    if remote_id.startswith("_"):
                        # Don't touch internal stuff
                        continue 

                    if not remote_id in local_ids:                        
                        logger.debug("Removing unneeded remote item:" + remote_id)
                        self.deleteRemoteObject(item, remote_id)
                
            yield item
    