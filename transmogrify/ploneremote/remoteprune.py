"""

    Remove remove Plone content items which are no longer present locally.

"""

import xmlrpclib
import logging

from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher


import xmlrpclib
from base import PathBasedAbstractRemoteCommand
from collections import OrderedDict


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

    plone4 = False

    def readOptions(self, options):
        """ Read options give in pipeline.cfg
        """

        # Call parent
        PathBasedAbstractRemoteCommand.readOptions(self, options)

        # Remote site / object URL containing HTTP Basic Auth username and
        # password
        self.prune_folder_matcher = defaultMatcher(options, 'prune-folder-key',
            self.name, 'prune-folder')

        self.trash = options.get('trash-path','trash')

    def getRemoteObjectIds(self, item):
        """ Fetch the folder listing from the remote site """
        url = self.constructRemoteURL(item)
        proxy = xmlrpclib.ServerProxy(url)

        contents = proxy.listFolderContents()
        # gives us list like [{'locallyAllowedTypes': ['Document',...], 'description': '',
        # 'modification_date': <DateTime '2012-07-21T17:40:42+10:00' at 3ae5558>, 'title': 'Resources',
        # 'demarshall_hook': None, 'portal_type': 'Folder', 'creation_date': <DateTime '2012-07-21T17:40:41+10:00' at 3adb760>,
        # 'marshall_hook': None, 'default_page': 'index', 'at_references': {},
        # 'immediatelyAddableTypes': ['Document', ...], 'id': 'resources',
        # 'workflow_history': {'data': {'simple_publication_workflow': [{'action': None, 'review_state':
        # 'private', 'comments': '', 'actor': 'djay', 'time': <DateTime '2012-07-21T17:40:41+10:00' at 3adb238>},
        # {'action': 'publish', 'review_state': 'published', 'comments': '', 'actor': 'djay',
        # 'time': <DateTime '2012-07-21T17:40:42+10:00' at 3adb0f8>}]}}, 'constrainTypesMode': -1},
        return [item['id'] for item in contents]



    def deleteRemoteObjects(self, item, ids):
        """ Perform object deletion over XML-RPC """
        path = item.get('_path')
        if not len(ids):
            self.logger.debug("'%s' nothing to prune" % (path))
            return

        url = self.constructRemoteURL(item)
        proxy = xmlrpclib.ServerProxy(url, allow_none=True)
        if self.trash:
            # we have a trash path so we'll move items to here instead of del (prevents linkintegrity errors)
            self.logger.debug("'%s' moving to %s: %s" % (path, self.trash, ids))
            trash_url = self.target+self.trash
            trash = xmlrpclib.ServerProxy(trash_url, allow_none=True)
            if url == self.target:
                #special case to prevent trash being moved to trash
                trash_id = self.trash.split('/')[0]
                ids = [id for id in ids if id != trash_id]
            try:
                cp_data = proxy.manage_cutObjects(ids, None)
            except:
                self.logger.warning("'%s' Error trying to cut %s: %s" % (path, self.trash, ids))
                return
            try:
                trash.manage_pasteObjects(cp_data, None)
            except:
                self.logger.warning("'%s' Error trying to paste %s: %s" % (path, self.trash, ids))
                return


        else:
            self.logger.debug("removing uneeded in '%s' %s" % (item['_path'],ids))
            try:
                proxy.manage_delObjects(ids)
            except:
                self.logger.warning("Error trying to delete %s: %s" % (self.trash, ids))
                return



    def __iter__(self):
        self.checkOptions()

        children = OrderedDict()
        items = []

        for item in self.previous:
            if not self.target:
                yield item
                continue

            path = self.extractPath(item)
            if path is None:
                yield item; continue

            # we need to build up a tree structure since items don't know their children
            parentpath = '/'.join(path.split('/')[:-1])
            if parentpath != path:
                children.setdefault(parentpath,[]).append(item)

            proxy = xmlrpclib.ServerProxy(self.constructRemoteURL(item))
            if not self.condition(item, proxy=proxy):
                self.logger.debug('%s skipping (condition)'%(path))
                yield item; continue

            items.append(item)

        for item in items:

            # See if "prune" flag is set for this tranmogrifier item
            #prune = self.extractTruthValue(item, self.prune_folder_matcher)
            # Not working on plone4
            prune = True
            if prune:
                # This folder contains content to be pruned
                # Make list of ids which are dangling on the remote site
                remote_ids = self.getRemoteObjectIds(item)
                path = self.extractPath(item)
                local_ids = [i['_path'].split('/')[-1] for i in children.get(path,[])]
                # Don't touch internal stuff
                remove_ids = [id for id in remote_ids if not id.startswith("_") and id not in local_ids]
                self.deleteRemoteObjects(item, remove_ids)
            yield item
