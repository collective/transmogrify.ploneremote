.. contents :: :local:

Introduction
--------------

*transmogrifier.ploneremote* is package of transmogrifier blueprints for 
uploading content via Zope XML-RPC API to a Plone site.

Plone site does not need any modifications, but vanilla Zope XML-RPC is used.

Usage
-----

Five different blueprints are provided.

Common Options
==============

target
  Url of Plone folder to upload content. You will need to include the username and
  password using the url syntax. e.g. http://user:password@site.com/folder.
  If you'd prefer not to hardcode your password in a pipeline.cfg you can use
  `mr.migrator` which lets you override your pipeline using the commandline.

path-key
  Which blueprint item dictionary key is used to extract the remote path information
  or the item. Default value *path* .


transmogrify.ploneremote.constructor
====================================

Drop in replacement for constructor that will use xmlprc calls to construct content on a remote plone site

Options:

:target:
  see `Common Options`_

:path-key:
  see `Common Options`_

:type-key:
  Key of the field with item type to create. Defaults to 'type','portal_type', 'Type','_type'

:creation-key:
  Key of the field to determine if item should be created. Defaults to '_creation_flag'

:create-condition:
  TAL expression to determine if item should be added. Defaults to 'python:True'

:move-condition:
  If the content has already been uploaded and then moved this TAL expression
  will determine if the content should be moved back. Default is 'python:True'

:remove-condition:
  If the content has already been uploaded and is of a different type this
  TAL expression will determine if the item can be removed and recreated.



transmogrify.ploneremote.remoteschemaupdater
============================================

This will use XML-RPC to call Archetypes setXXX() mutator methods remotely
to set field values.

TODO: How to input schema fields

Options:

:target:
  see `Common Options`_

:path-key:
  see `Common Options`_

:condition:
  TAL Expression to determine to use this blueprint

:skip-existing:
  Default is 'False'

:skip_unmodified:
  if set to true and the items modification date is less than the modification date of
  the remote item then no fields will be updated. The modification date either comes
  from 'modificationDate' key in the item or the 'last-modified' header if item
  was from `transmogrify.webcrawler`.

:headers-key:
  key for dictionary of headers such as added by transmogrify.webcrawler

:skip_fields:
  Fields that won't be updated

:creation_key:
  if skip existing is true and this field is set in the item the remote item is not updated

transmogrify.ploneremote.remoteworkflowupdater
==============================================

Triggers the state transition of the remote item workflow i.e.
publishes the item if it is not public.

Options:

:target:
  see `Common Options`_

:path-key:
  see `Common Options`_

:transitions-key:
  which blueprint item dictionary key is used as the transition name
  for the item. 


transmogrify.ploneremote.remoteredirector
=========================================

This blueprint adds redirection aliases to those content items that have changed
it's paths during tranmogrification process. It takes into account item's
*_orig_path* key set by webcrawler blueprint. Redirection uses
Products.RedirectionTool Aliases form to add appropriate redirections. So this
is required to install that addon in order to make
*transmogrify.ploneremote.redirector* blueprint work.

If *path* is not equal to *orig_path* then appropriate aliases is being added
to local Plone utility (IRedirectionStorage) using Aliases form.


Example::

        #
        # Add content aliases for content that changed it's paths
        # 
        [redirector]
        blueprint = transmogrify.ploneremote.remoteredirector

Options:

:target:
  see `Common Options`_

:path-key:
  see `Common Options`_

transmogrify.ploneremote.remoteprune
====================================

Removes any items from a folder if it's not an item in the pipeline.

Options:

:target:
  see `Common Options`_

:path-key:
  see `Common Options`_

:prune-folder-key:
     which transmogrifier field is read to check
     if the prune folder is run against the remote folder.
     The default value os "_prune-folder"

:trash-path:
  remote folder to set to move content items not specified locally. If empty

transmogrify.ploneremote.remotenavigationexcluder
=================================================

Set "Exclude from Navigation" setting for remote Plone content items.

Options:

:target:
  see `Common Options`_

:path-key:
  see `Common Options`_

:exclude-from-navigation-key:
  Which key we use to read navigation exclusion hint.
  Default is 'exclude-from-navigation'

transmogrify.ploneremote.remoteportlets
=======================================

Set static text portlets. If items contain a key such as '_left_portlet_text_1' it will create
a static text portlet at '_path' as the first portlet on the left.

:left-title-prefix:
  defaults to _left_portlet_title.

:left-text-prefix:
  defaults to _left_portlet_text.

:right-title-prefix:
  defaults to _right_portlet_title.

:right-text-prefix:
  defaults to _right_portlet_text.

Authors
--------------

In the order of apperance

* Dylan Jay, software@pretaweb.com

* Mikko Ohtamaa, mikko@mfabrik.com, http://mfabrik.com

* Vitaliy Podoba, vitaliypodoba@gmail.com
