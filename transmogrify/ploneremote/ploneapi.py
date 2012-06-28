"""
Wraps XMLRPC and http get and post to provide a single api for manipulating folders
and AT Content in Plone
"""
from httplib import HTTPException

class RemoteApi():
    """ TODO: unfinished
    """

    def __init__(self, url, username=None, password=None):
        self.proxy = xmlrpclib.ServerProxy(url)
        self.multicall = xmlrpclib.MultiCall(proxy)
        self.url = url

    def update(self, **fields):


        for key, parts in fields.items():
            value, arguments = parts

            if type(value) == type(u''):
                value = value.encode('utf8')
            elif getattr(value,'read', None):
                file = value
                value = file.read()
                try:
                    file.seek(0)
                except AttributeError:
                    file.close()
            elif value is None:
                # Do not update fields for which we have not received
                # values is transmogrify.htmlextractor
                self.logger.warning('%s %s=%s'%(path, key, value))
                continue

            method = key[0].upper()+key[1:]
            if arguments:
                #need to use urllib for keywork arguments
                arguments.update(dict(value=value))
                input = urllib.urlencode(arguments)
                f = None
                for attempt in range(0,3):
                    try:
                        f = urllib.urlopen(url+'/set%s'%key.capitalize(), input)
                        break
                    except IOError, e:
                        self.logger.warning("%s.set%s() raised %s"%(path,method,e))
                if f is None:
                    self.logger.warning("%s.set%s() raised too many errors. Giving up"%(path,method))
                    break


            nurl = f.geturl()
            info = f.info()
            #print method + str(arguments)
            if info.status != '':
                e = str(f.read())
                f.close()
                self.logger.error("%s.set%s(%s) raised %s"%(path,method,arguments,e))
        else:
            # setModificationDate doesn't use 'value' keyword
            try:
                getattr(proxy,'set%s'%method)(value)
            except xmlrpclib.Fault, e:
                self.logger.error("%s.set%s(%s) raised %s"%(path,method,value,e))
        updated.append(key)
    if fields:
        self.logger.info('%s set fields=%s'%(path, fields.keys()))
        try:
            proxy.update() #does indexing
        except xmlrpclib.Fault, e:
            self.logger.error("%s.update() raised %s"%(path,e))


    def getPhysicalPath(self):
        return self.proxy.getPhysicalPath()

    def getTypeInfo(self):
        return self.proxy.getTypeInfo()

    def Type(self)
        return self.getTypeInfo().get('id')

    def manage_delObjects(ids):
        return self.proxy.manage_delObjects(ids)

    def parent(self):
        parentpath =  '/'.join(self.path.split('/')[:-1])
        return RemoteApi(self.url, self.path, self.username, self.password)

    def invokeFactory(self, type_, id):
        return self.proxy.invokeFactory(type_, id)

    def updateWorkflow(self, transition):

        url = urllib.basejoin(self.url, "content_status_modify?workflow_action=" + transition)
        self.logger.info("%s performing transition '%s'" % (path, transition))
        try:
            f= urllib.urlopen(transition_trigger_url)
        except HTTPException, e:
            # Other than HTTP 200 OK should end up here,
            # unless URL is broken in which case Plone shows
            # "Your content was not found page"
            self.logger.error("fail")
            msg = "Remote workflow transition failed %s->%s" %(path,transition)
            self.logger.log(logging.ERROR, msg, exc_info=True)
            return

        data = f.read()

        # Use Plone not found page signature to detect bad URLs
        if "Please double check the web address" in data:
            import pdb ; pdb.set_trace()
            raise RuntimeError("Bad remote URL:" + transition_trigger_url)

