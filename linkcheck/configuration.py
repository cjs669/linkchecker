# -*- coding: iso-8859-1 -*-
# Copyright (C) 2000-2005  Bastian Kleineidam
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""
Store metadata and options.
"""

import ConfigParser
import sys
import os
import logging
import logging.config
import re
import urllib

import _linkchecker_configdata
import linkcheck
import linkcheck.log
import linkcheck.containers

Version = _linkchecker_configdata.version
AppName = u"LinkChecker"
App = AppName+u" "+Version
Author =  _linkchecker_configdata.author
HtmlAuthor = Author.replace(u' ', u'&nbsp;')
Copyright = u"Copyright � 2000-2005 "+Author
HtmlCopyright = u"Copyright &copy; 2000-2005 "+HtmlAuthor
AppInfo = App+u"              "+Copyright
HtmlAppInfo = App+u", "+HtmlCopyright
Url = _linkchecker_configdata.url
Email = _linkchecker_configdata.author_email
UserAgent = u"%s/%s (%s; %s)" % (AppName, Version, Url, Email)
Freeware = AppName+u""" comes with ABSOLUTELY NO WARRANTY!
This is free software, and you are welcome to redistribute it
under certain conditions. Look at the file `LICENSE' within this
distribution."""


def normpath (path):
    """
    Norm given system path with all available norm funcs in os.path.
    """
    return os.path.normcase(os.path.normpath(os.path.expanduser(path)))


# dynamic options
class Configuration (dict):
    """
    Storage for configuration options. Options can both be given from
    the command line as well as from configuration files.
    """

    def __init__ (self):
        """
        Initialize the default options.
        """
        super(Configuration, self).__init__()
        self["verbose"] = False
        self["warnings"] = False
        self["anchors"] = False
        self["anchorcaching"] = True
        self["externstrictall"] = False
        self["externlinks"] = []
        self["internlinks"] = []
        self["denyallow"] = False
        self["interactive"] = False
        # on ftp, password is set by Pythons ftplib
        self["authentication"] = []
        self["proxy"] = urllib.getproxies()
        self["recursionlevel"] = -1
        self["wait"] = 0
        self['cookies'] = False
        self["status"] = False
        self["fileoutput"] = []
        # Logger configurations
        self["text"] = {
            "filename": "linkchecker-out.txt",
            'colorparent':  "default",
            'colorurl':     "default",
            'colorname':    "default",
            'colorreal':    "default",
            'colorbase':    "default",
            'colorvalid':   "default",
            'colorinvalid': "default",
            'colorinfo':    "default",
            'colorwarning': "default",
            'colordltime':  "default",
            'colordlsize':  "default",
            'colorreset':   "default",
        }
        self['html'] = {
            "filename":        "linkchecker-out.html",
            'colorbackground': '#fff7e5',
            'colorurl':        '#dcd5cf',
            'colorborder':     '#000000',
            'colorlink':       '#191c83',
            'colorwarning':    '#e0954e',
            'colorerror':      '#db4930',
            'colorok':         '#3ba557',
        }
        self['gml'] = {
            "filename": "linkchecker-out.gml",
        }
        self['sql'] = {
            "filename": "linkchecker-out.sql",
            'separator': ';',
            'dbname': 'linksdb',
        }
        self['csv'] = {
            "filename": "linkchecker-out.csv",
            'separator': ',',
            "quotechar": '"',
        }
        self['blacklist'] = {
            "filename": "~/.linkchecker/blacklist",
        }
        self['xml'] = {
            "filename": "linkchecker-out.xml",
        }
        self['dot'] = {
            "filename": "linkchecker-out.dot",
            "encoding": "ascii",
        }
        self['none'] = {}
        self['logger'] = self.logger_new('text')
        self["warningregex"] = None
        self["warnsizebytes"] = None
        self["nntpserver"] = os.environ.get("NNTP_SERVER", None)
        self["threads"] = 10

    def init_logging (self, debug=None):
        """
        Load logging.conf file settings to set up the
        application logging (not to be confused with check loggers).
        When debug is not None it is expected to be a list of
        logger names for which debugging will be enabled.

        Activating debugging disables threading.
        """
        config_dir = _linkchecker_configdata.config_dir
        filename = normpath(os.path.join(config_dir, "logging.conf"))
        logging.config.fileConfig(filename)
        handler = linkcheck.ansicolor.ColoredStreamHandler(strm=sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logging.getLogger(linkcheck.LOG).addHandler(handler)
        if debug is not None:
            self['debug'] = True
            # debugging disables threading
            self['threads'] = 0
            # set debugging on given logger names
            if 'all' in debug:
                debug = linkcheck.lognames.values()
            for name in debug:
                logging.getLogger(name).setLevel(logging.DEBUG)

    def logger_new (self, loggertype, **kwargs):
        """
        Instantiate new logger and return it.
        """
        args = {}
        args.update(self[loggertype])
        args.update(kwargs)
        return linkcheck.Loggers[loggertype](**args)

    def logger_add (self, loggertype, loggerclass, loggerargs=None):
        """
        Add a new logger type to the known loggers.
        """
        if loggerargs is None:
            loggerargs = {}
        linkcheck.Loggers[loggertype] = loggerclass
        self[loggertype] = loggerargs

    def write (self, filename="~/.linkchecker/linkcheckerrc"):
        filename = normpath(filename)
        linkcheck.log.debug(linkcheck.LOG_CHECK,
                            "write configuration into %s", filename)
        fp = open(filename, 'w')
        self.write_output_config(fp)
        self.write_checking_config(fp)
        self.write_authentication_config(fp)
        self.write_filtering_config(fp)
        fp.close()

    def read (self, files=None):
        """
        Read settings from given config files.
        """
        if files is None:
            cfiles = []
        else:
            cfiles = files[:]
        if not cfiles:
            # system wide config settings
            config_dir = _linkchecker_configdata.config_dir
            cfiles.append(normpath(os.path.join(config_dir, "linkcheckerrc")))
            # per user config settings
            cfiles.append(normpath("~/.linkchecker/linkcheckerrc"))
        self.read_config(cfiles)
        # re-init logger
        self['logger'] = self.logger_new('text')

    def read_config (self, files):
        """
        Read all the configuration parameters from the given files.
        """
        linkcheck.log.debug(linkcheck.LOG_CHECK,
                            "reading configuration from %s", files)
        try:
            cfgparser = ConfigParser.ConfigParser()
            cfgparser.read(files)
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
            return
        self.read_output_config(cfgparser)
        self.read_checking_config(cfgparser)
        self.read_authentication_config(cfgparser)
        self.read_filtering_config(cfgparser)

    def read_output_config (self, cfgparser):
        """
        Read configuration options in section "output".
        """
        section = "output"
        for key in linkcheck.Loggers.keys():
            if cfgparser.has_section(key):
                for opt in cfgparser.options(key):
                    try:
                        self[key][opt] = cfgparser.get(key, opt)
                    except ConfigParser.Error, msg:
                        linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
                try:
                    self[key]['fields'] = [f.strip() \
                            for f in cfgparser.get(key, 'fields').split(',')]
                except ConfigParser.Error, msg:
                    linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            logger = cfgparser.get(section, "log")
            if linkcheck.Loggers.has_key(logger):
                self['logger'] = self.logger_new(logger)
            else:
                linkcheck.log.warn(_("invalid log option %r"), logger)
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            if cfgparser.getboolean(section, "verbose"):
                self["verbose"] = True
                self["warnings"] = True
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            if cfgparser.getboolean(section, "quiet"):
                self['logger'] = self.logger_new('none')
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["status"] = cfgparser.getboolean(section, "status")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["warnings"] = cfgparser.getboolean(section, "warnings")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            filelist = cfgparser.get(section, "fileoutput").split(",")
            for arg in filelist:
                arg = arg.strip()
                # no file output for the blacklist and none Logger
                if linkcheck.Loggers.has_key(arg) and \
                   arg not in ["blacklist", "none"]:
                    self['fileoutput'].append(
                                     self.logger_new(arg, fileoutput=1))
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["interactive"] = cfgparser.getboolean(section, "interactive")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)

    def read_checking_config (self, cfgparser):
        """
        Read configuration options in section "checking".
        """
        section = "checking"
        try:
            num = cfgparser.getint(section, "threads")
            self['threads'] = num
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["anchors"] = cfgparser.getboolean(section, "anchors")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["debug"] = cfgparser.get(section, "debug")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            num = cfgparser.getint(section, "recursionlevel")
            self["recursionlevel"] = num
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["externstrictall"] = cfgparser.getboolean(section, "externstrictall")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            wr = cfgparser.get(section, "warningregex")
            if wr:
                self["warningregex"] = re.compile(wr)
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["warnsizebytes"] = int(cfgparser.get(section,
                                                      "warnsizebytes"))
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["nntpserver"] = cfgparser.get(section, "nntpserver")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["anchorcaching"] = cfgparser.getboolean(section,
                                    "anchorcaching")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)

    def read_authentication_config (self, cfgparser):
        """
        Read configuration options in section "authentication".
        """
        section = "authentication"
        try:
            i = 1
            while 1:
                auth = cfgparser.get(section, "entry%d" % i).split()
                if len(auth)!=3:
                    break
                auth[0] = re.compile(auth[0])
                self["authentication"].insert(0, {'pattern': auth[0],
                                                  'user': auth[1],
                                                  'password': auth[2]})
                i += 1
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)

    def read_filtering_config (self, cfgparser):
        """
        Read configuration options in section "filtering".
        """
        section = "filtering"
        try:
            i = 1
            while 1:
                ctuple = cfgparser.get(section, "extern%d" % i).split()
                if len(ctuple)!=2:
                    linkcheck.log.error(
                               _("extern%d: syntax error %s\n")%(i, ctuple))
                    break
                self["externlinks"].append(
                    linkcheck.get_link_pat(ctuple[0], strict=int(ctuple[1])))
                i += 1
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["internlinks"].append(
               linkcheck.get_link_pat(cfgparser.get(section, "internlinks")))
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)
        try:
            self["denyallow"] = cfgparser.getboolean(section, "denyallow")
        except ConfigParser.Error, msg:
            linkcheck.log.debug(linkcheck.LOG_CHECK, msg)

    def write_output_config (self, fp):
        """
        Write configuration options in section "output".
        """
        section = "output"
        # XXX todo

    def write_checking_config (self, fp):
        """
        Write configuration options in section "checking".
        """
        section = "checking"
        # XXX todo

    def write_authentication_config (self, fp):
        """
        Write configuration options in section "authentication".
        """
        section = "authentication"
        # XXX todo

    def write_filtering_config (self, fp):
        """
        Write configuration options in section "filtering".
        """
        section = "filtering"
        # XXX todo

