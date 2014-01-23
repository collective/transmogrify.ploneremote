from Products.Five.testbrowser import Browser
from Products.PloneTestCase import PloneTestCase
PloneTestCase.setupPloneSite()


class RedirectorTestCase(PloneTestCase.PloneTestCase):
    pass


class RedirectorFunctionalTestCase(PloneTestCase.FunctionalTestCase):

    def getBrowser(self, loggedIn=True):
        """ instantiate and return a testbrowser for convenience """
        browser = Browser()
        if loggedIn:
            user = PloneTestCase.default_user
            pwd = PloneTestCase.default_password
            browser.addHeader('Authorization', 'Basic %s:%s' % (user, pwd))
        return browser
