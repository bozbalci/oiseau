# -*- coding: utf-8 -*-
#
# This file is a part of oiseau.
#
# Copyright (c) 2014, Berk Özbalcı
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

__author__ = 'Berk Özbalcı <berkozbalci@gmail.com>'
__all__ = ['daemon', 'mpdclient', 'scrobbler', 'cache', 'config', 'misc', 'version']

import daemon
import mpdclient
import scrobbler
import cache
import config
import misc
import version
import traceback
import logging
import signal
import os
import sys

__version__ = version.version

log = misc.LoggerManager().getLogger('oiseau')
if not log.handlers:
   log.addHandler(logging.StreamHandler())

# # Don't propagate to root handler.
# log.propagate = False

class UserError(Exception):
   """ An error which the user is responsible for. """

def _absolute_path(path):
   """ Return the absolute path of the given path. """

   path = os.path.expandvars(path)
   path = os.path.expanduser(path)
   path = os.path.abspath(path)

   return path

def _raw_main(args=None):
   """ A helper function for `main` without top-level exception handling. """

   options = config.Arguments(args).options

   config_files = [
      _absolute_path(options.cfgfile) if options.cfgfile else None,
      _absolute_path("~/.oiseau/config"),
      "/usr/local/etc/oiseau.conf"
   ]

   # Remove empty entries
   config_files = [f for f in config_files if f is not None]

   prefs = config.Configuration(config_files)
   prefs.read()

   if prefs.cache:
      prefs.cache = _absolute_path(prefs.cache)
   
   pidfiles = [
      _absolute_path(options.pidfile) if options.pidfile else None,
      _absolute_path(prefs.pidfile) if prefs.pidfile else None,
      _absolute_path("~/.oiseau/pid") if (
         os.path.isfile(_absolute_path("~/.oiseau/pid"))) else None,
      "/tmp/oiseau.pid"
   ]

   try:
      pidfile = next(pf for pf in pidfiles if pf is not None)
   except StopIteration:
      raise UserError("No pid file could be detected!")

   oiseau = daemon.Oiseau(pidfile)

   if options.kill:
      oiseau.stop()
      return
   
   connection = mpdclient.MPDConnection(prefs.mpd_host, prefs.mpd_port, prefs.mpd_pass)
   watcher = mpdclient.MPDWatcher(connection)
   watcher.connection.connect()

   # a ScrobblerError is raised in failure, and is catched at `main`.
   lfm_scrobbler = scrobbler.Scrobbler(prefs.lfm_user, prefs.lfm_pass)

   signal.signal(signal.SIGTERM, oiseau.sigterm_handler)

   if options.log:
      loglevel = options.log
   else:
      if prefs.loglevel:
         loglevel = prefs.loglevel
      else:
         loglevel = 'warning'

   log.setLevel(getattr(logging, loglevel.upper()))

   if options.logfile:
      for h in log.handlers:
         log.removeHandler(h)
         handler = logging.FileHandler(_absolute_path(options.logfile))
   else:
      if prefs.logfile:
         for h in log.handlers:
            log.removeHandler(h)
            handler = logging.FileHandler(_absolute_path(prefs.logfile))

   formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
      datefmt='%Y-%m-%d %H:%M:%S')

   handler.setFormatter(formatter)
   log.addHandler(handler)

   # Make it rain!
   oiseau.configure(prefs, watcher, lfm_scrobbler)
   oiseau.start()

def main(args=None):
   """ Run the main command-line interface for Oiseau. Includes top-level
   exception handlers that print friendly error messages.
   """
   
   try:
      _raw_main(args)
   except UserError as exc:
      log.error(u'Error: {0}'.format(exc))
      sys.exit(1)
   except mpdclient.MPDConnectionError as exc:
      log.error(u'Error: {0}'.format(exc))
      sys.exit(1)
   except scrobbler.ScrobblerError as exc:
      log.error(u'Error: {0}'.format(exc))
      sys.exit(1)
   except config.ConfigurationError as exc:
      log.error(u'Configuration error: {0}'.format(exc))
      sys.exit(1)
   except misc.DaemonError as exc:
      log.error(u'Error: {0}'.format(exc))
      sys.exit(1)
   except KeyboardInterrupt:
      # Silently ignore ^C except in verbose mode.
      log.debug(traceback.format_exc())
