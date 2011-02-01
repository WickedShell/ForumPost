# fourmPostPlugin.py
# By spaz (a.k.a. WickedShell)
# 
# This is a B3 plugin designed for WildCat's Clan (wildcatsclan.net)
# The idea of this plugin is when a permanant ban is issued, the plugin will
# automatically publish the releavent information on the forms
# While this plugin may be generalized for other sites, at the moment
# it works specifically with WC and not other sites.

__version__ = '0.0.2'
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
        #should need this once (with cookies that are always logged in)
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
        self._adminPlugin.registerCommand(self, 'permban', 1, self.cmd_permban, 'permban')
        self._adminPlugin.registerCommand(self, 'pb', 1, self.cmd_permban, 'permban')

        # Register our events
        #self.verbose('Registering events')

        self.verbose('Logging into forum\'s')
        self.login()

        self.verbose('Logged in')

    #TODO: dynamic post fields
    def post(self, url, formIndex, subject, message):
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

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        #don't believe we handle anything yet. This could be false


    def cmd_permban(self, data, client=None, cmd=None):
        """\
        <name> [<reason>] - ban a player permanently
        """
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False

        cid, keyword = m
        reason = self._adminPlugin.getReason(keyword)

        #TODO: the no reason level should be loaded from config
        if not reason and client.maxLevel < self.config.getint('settings', 'noreason_level'):
            client.message('^1ERROR: ^7You must supply a reason')
            return False

        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if sclient:
            if sclient.cid == client.cid:
                self.console.say(self._adminPlugin.getMessage('ban_self', client.exactName))
                return True
            elif sclient.maxLevel >= client.maxLevel:
                if sclient.maskGroup:
                    client.message('^7%s ^7is a masked higher level player, can\'t ban' % client.exactName)
                else:
                    self._adminPlugin.console.say(self.getMessage('ban_denied', client.exactName, sclient.exactName))
                return True
            else:
                sclient.groupBits = 0
                sclient.save()

                sclient.ban(reason, keyword, client)
                if self.postToForums:
                    self.verbose("Posting to the forums!")
                    #set up the future contents of the substitution dictonary
                    bannedName  = sclient.exactName[0:len(sclient.exactName) - 2]
                    bannedIP    = sclient.ip
                    bannedB3id  = str(sclient.id)
                    bannedLevel = sclient.maxLevel
                    bannerName  = client.exactName[0:len(client.exactName) - 2]
                    bannerIP    = client.ip
                    bannerB3id  = str(client.id)
                    bannerLevel = client.maxLevel
                    serverName  = str(self.console.getCvar('sv_hostname'))
                    serverName  = serverName[33:len(serverName) - 20]
                    reason
                    keyword
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
                    self.verbose(subject)
                    self.verbose(message)
                    self.post(self.postURL, self.postIndex, subject, message)
                    client.message('^1Created a post on the forums of this ban')
                return True
        elif re.match('^[0-9]+$', cid):
            # failsafe, do a manual client id ban
            self._adminPlugin.console.ban(cid, reason, client)

