from setuptools import setup, find_packages
import os

version = '1.0b4'

setup(name='transmogrify.ploneremote',
      version=version,
      description="Transmogrifier blueprints for uploading content via xmlrpc to a plone site",
      long_description=open('README.txt').read() + '\n' +
                       #open(os.path.join("transmogrify", "ploneremote", "webcrawler.txt")).read() + "\n" +
                       open(os.path.join( "CHANGES.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='transmogrifier blueprint funnelweb source plone import conversion microsoft office',
      author='Dylan Jay',
      author_email='software@pretaweb.com',
      url='http://github.com/djay/transmogrify.ploneremote',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['transmogrify'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'collective.transmogrifier',
          ],
      entry_points="""
            [z3c.autoinclude.plugin]
            target = transmogrify
            """,
            )
