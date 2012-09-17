# fourmPostPlugin.py
# By WickedShell
# 
# This is a B3 plugin
# The idea of this plugin is when a permanant ban is issued, the plugin will
# automatically publish the releavent information on the forums
# The plugin uses html requests and is compatabile with most sites, and uses
# html forms for all actions. The setup is rigid however, and a tool will be
# written to asssist in the initial deployment.
#
# Changelog:
# 0.1.0 09/16/2012 use events to make the ban, strip colors out of the name
#                  attempt to relogin and repost if a post fails, catch failures
# 0.1.1 09/16/2012 don't post if it was a self ban, or a b3 ban

__version__ = '0.1.1'
__author__  = 'WickedShell'

from time import strftime
from string import Template
import re
import b3
import b3.events
import b3.plugin
import mechanize

class ForumpostPlugin(b3.plugin.Plugin):
    requiresConfigFile = True
    subjectTemplate = Template("")
    messageTemplate = Template("")
    postToForums = False
    loginIndex = 1
    userName = ""
    password = ""
    loginURL = ""
    postURL = ""
    postIndex = 1
    loginFormUserName = "user"
    loginFormPassword = "password"
    messageFormSubject = "subject"
    messageFormBody = "body"
    
    #logs into the site for posting
    #this assumes login was succesful
    def login(self):
        try:
            #load the main page to log in from
            mainRequest = mechanize.Request(self.loginURL)
            mainResponse = mechanize.urlopen(mainRequest)
            #generate a list of avalible HTML forms so we can select the desired one
            forms = mechanize.ParseResponse(mainResponse, backwards_compat=False)
            form = forms[self.loginIndex]
            #    print form  # very useful! debug
            #fill in username and password fields and login
            #TODO: move form fields into the config
            #TODO: add dynamic field support
            form[self.loginFormUserName] = self.userName
            form[self.loginFormPassword] = self.password
            loginRequest = form.click()  # mechanize.Request object
            loginResponse = mechanize.urlopen(loginRequest)
            #    print loginResponse.geturl() #debug
            #    print loginResponse.info()   #debug
            #free the rescources on the response page
            mainResponse.close()
            loginResponse.close()
            #TODO: a validation of successful login
        except:
            self.verbose('Failed to login');

    def startup(self):
        """\
        Initialize plugin settings
        """

        # get the admin plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        # Register commands
        self.registerEvent(b3.events.EVT_CLIENT_BAN)

        # Register our events
        #self.verbose('Registering events')

        self.verbose('Logging into forum\'s')
        self.login()

        self.verbose('Logged in')

    #TODO: dynamic post fields
    def post(self, url, formIndex, subject, message):
        try:
            postPageRequest = mechanize.Request(url)
            postPageResponse = mechanize.urlopen(postPageRequest)
            forms = mechanize.ParseResponse(postPageResponse, backwards_compat=False)
            messageForm = forms[int(formIndex)]
            messageForm[self.messageFormSubject] = subject
            messageForm[self.messageFormBody] = message
            submitRequest = messageForm.click()
            submitResponse = mechanize.urlopen(submitRequest)
            #clean up the response's
            postPageResponse.close()
            submitResponse.close()
            return True
        except:
            return False

    def onLoadConfig(self):
        # load our settings
        self.verbose('Loading config')
        self.postToForums = self.config.getboolean('settings', 'enabled')
        subjectStr = str(self.config.get('settings', 'subjectFormat'))
        messageStr = str(self.config.get('settings', 'messageFormat'))
        self.verbose(subjectStr)
        self.verbose(messageStr)
        self.subjectTemplate = Template(subjectStr)
        self.messageTemplate = Template(messageStr)
        self.userName = str(self.config.get('settings', 'userName'))
        self.password = str(self.config.get('settings', 'password'))
        self.loginFormUserName = str(self.config.get('settings', 'loginFormUserName'))
        self.loginFormPassword = str(self.config.get('settings', 'loginFormPassword'))
        self.loginURL = str(self.config.get('settings', 'loginURL'))
        self.postURL = str(self.config.get('settings', 'postURL'))
        self.loginIndex = int(self.config.get('settings', 'loginIndex'))
        self.postIndex = int(self.config.get('settings', 'postIndex'))
        self.messageFormSubject = str(self.config.get('settings', 'messageFormSubject'))
        self.messageFormBody = str(self.config.get('settings', 'messageFormBody'))

    def post_ban(self, event):
        try:
            banned = event.client
            banner = event.data['admin']
        except:
            banner = None
            banned = None
        if self.postToForums:
            if banner == None:
                self.verbose("Ignoring a ban without a banner")
                return
            if banner == banned:
                self.verbose("Ignoring a self ban")
                return
            self.verbose("Posting to the forums!")
            #set up the future contents of the substitution dictonary
            bannedName  = banned.exactName[0:len(banned.exactName) - 2]
            bannedIP    = banned.ip
            bannedB3id  = str(banned.id)
            bannedLevel = banned.maxLevel
            bannerName  = banner.exactName[0:len(banner.exactName) - 2]
            bannerIP    = banner.ip
            bannerB3id  = str(banner.id)
            bannerLevel = banner.maxLevel
            serverName  = str(self.console.getCvar('sv_hostname'))
            serverName  = serverName[35:len(serverName) - 21]
            reason      = event.data['reason']
            duration    = "permanent"
            time        = strftime("%m-%d-%Y-%H:%M")
            mapName     = str(self.console.getCvar('mapname'))
            mapName     = mapName[29:len(mapName)].rsplit('\"')[0]


            #build a substition dictionary that the message will draw on
            substDict = dict(bannedName = bannedName,
                bannedIP = bannedIP, bannedB3id = bannedB3id,
                bannedLevel = bannedLevel, bannerName = bannerName,
                bannerLevel = bannerLevel, bannerIP = bannerIP,
                bannerB3id = bannerB3id, serverName = serverName,
                reason = reason, time = time, mapName = mapName,
                duration = duration)
                    
            subject = self.subjectTemplate.safe_substitute(substDict)
            message = self.messageTemplate.safe_substitute(substDict)
            # strip all color's from names/etc (ie ^1)
            subject = re.sub('\^\d', '', subject)
            message = re.sub('\^\d', '', message)
            self.verbose(subject)
            self.verbose(message)
            success = self.post(self.postURL, self.postIndex, subject, message)
            if success:
                banner.message('^2Created a post on the forums')
            else:
                banner.message('^1Failed to create a post on the forums, attempting to relogin and post')
                self.login()
                success = self.post(self.postURL, self.postIndex, subject, message)
                if success:
                    banner.message('^2Succesfully relogged in and posted')
                else:
                    banner.message('^1Failed to relogin and post, please make a mnaul post')

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_CLIENT_BAN:
            self.post_ban(event);
