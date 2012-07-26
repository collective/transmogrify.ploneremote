from zope.i18nmessageid import MessageFactory
FunnelwebMessageFactory = MessageFactory('transmogrify.webcrawler')

def monkey_patch_ZPublisher_Client():
    import ZPublisher.Client
    class NotFound(Exception):pass
    ZPublisher.Client.NotFound     = NotFound
    ZPublisher.Client.exceptmap['NotFound'] = ZPublisher.Client.NotFound
    class InternalError(Exception):pass
    ZPublisher.Client.InternalError     = InternalError
    ZPublisher.Client.exceptmap['InternalError'] = ZPublisher.Client.InternalError
    class BadRequest(Exception):pass
    ZPublisher.Client.BadRequest     = BadRequest
    ZPublisher.Client.exceptmap['BadRequest'] = ZPublisher.Client.BadRequest
    class Unauthorized(Exception):pass
    ZPublisher.Client.Unauthorized     = Unauthorized
    ZPublisher.Client.exceptmap['Unauthorized'] = ZPublisher.Client.Unauthorized
    class ServerError(Exception):pass
    ZPublisher.Client.ServerError     = ServerError
    ZPublisher.Client.exceptmap['ServerError'] = ZPublisher.Client.ServerError
    class NotAvailable(Exception):pass
    ZPublisher.Client.NotAvailable     = NotAvailable
    ZPublisher.Client.exceptmap['NotAvailable'] = ZPublisher.Client.NotAvailable

monkey_patch_ZPublisher_Client()
