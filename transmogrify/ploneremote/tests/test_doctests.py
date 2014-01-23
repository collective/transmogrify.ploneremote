from unittest import TestSuite
from zope.testing import doctest
from Testing import ZopeTestCase as ztc
from plone.app.redirector.tests.base import RedirectorFunctionalTestCase

optionflags = (doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.ELLIPSIS |
               doctest.NORMALIZE_WHITESPACE)


def test_suite():
    return TestSuite([
        ztc.FunctionalDocFileSuite(
           'browser.txt',
           package='plone.app.redirector.tests',
           test_class=RedirectorFunctionalTestCase,
           optionflags=optionflags),
    ])
