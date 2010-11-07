.. contents :: :local:

Introduction
--------------

*transmogrifier.ploneremote* is package of transmogrifier blueprints for 
uploading content via Zope XML-RPC API to a Plone site.

Plone site does not need any modifications, but vanilla Zope XML-RPC is used.

Usage
-----

Five different blueprints are provided.

Remote constructor
====================

TODO: How to guess the type and location to be created

Example::

        #
        # Create remote item on Plone site
        #
        [ploneuploader]
        blueprint = transmogrify.ploneremote.remoteconstructor



Remote schema updater
========================================

This will use XML-RPC to call Archetypes setXXX() mutator methods remotely
to set field values.

TODO: How to input schema fields

Example::

        #
        # Update the remote item with new extracted content from Sphinx documentation
        # 
        [schemaupdater]
        blueprint = transmogrify.ploneremote.remoteschemaupdater

Portal transform
====================

TODO: No idea

Workflow updater
====================

Triggers the state transition of the remote item workflow i.e.
publishes the item if it is not public.

Takes the following parameters:

* *path-key*: which blueprint item dictionary key is used to extract the remote path information 
  or the item. Default value *path* . 

* *transitions-key*: which blueprint item dictionary key is used as the transition name
  for the item. 

* *target*: Remote site URL


Redirector
==========

This blueprint adds redirection aliases to those content items that have changed
it's paths during tranmogrification process. It takes into account item's
*_orig_path* key set by webcrawler blueprint. Redirection uses
Products.RedirectionTool Aliases form to add appropriate redirections. So this
is required to install that addon in order to make
*transmogrify.ploneremote.redirector* blueprint work.

If *path* is not equal to *orig_path* then appropriate aliases is being added
to local Plone utility (IRedirectionStorage) using Aliases form.

Takes the following parameters:

* *path-key*: which blueprint item dictionary key is used to extract the remote
  path information or the item. Default value *path* .

Example::

        #
        # Add content aliases for content that changed it's paths
        # 
        [redirector]
        blueprint = transmogrify.ploneremote.remoteredirector


Making remote site URL configurable
-----------------------------------

All blueprints take remote site URL parameter.
Instead of hardcoding this to your *pipeline.cfg*
you can make it configurable from the command line using the following 
*buildout.cfg* snippet to create a helper script::

        #
        # Recipe to create toplone command.
        # 
        # It will walk through all blueprints defined
        # in pipeline.cfg and override their target parameter
        # to be a remote Plone site given on the command line.
        # This all happeins in initialization= magic.
        #
        # Also Python logger is initialized to give us verbose
        # output. Some blueprints use logging module for the output.
        #
        [toplone]
        recipe = zc.recipe.egg
        eggs =
          transmogrify.htmltesting
          transmogrify.webcrawler
          transmogrify.siteanalyser
          transmogrify.htmlcontentextractor
          transmogrify.pathsorter
          transmogrify.ploneremote
          Products.CMFCore
        initialization =
          from urllib import pathname2url as url
          from sys import argv
          import logging
          
          logging.basicConfig(level=logging.INFO)
          args = dict(webcrawler=dict(site_url=url('build')),
              localconstructor=dict(output=url('ploneout')),
              ploneuploader=dict(target=argv[1]),
              schemaupdater=dict(target=argv[1]),
              publish=dict(target=argv[1]),
              redirector=dict(target=argv[1]),
              )
        arguments = 'pipeline.cfg', args
        entry-points = toplone=transmogrify.htmltesting.runner:runner
        extra-paths = ${zope2:location}/lib/python
         


Authors
--------------

In the order of apperance

* Dylan Jay, software@pretaweb.com

* Mikko Ohtamaa, mikko@mfabrik.com, http://mfabrik.com

* Vitaliy Podoba, vitaliypodoba@gmail.com
