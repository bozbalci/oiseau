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

import sys, os, time, atexit
from signal import SIGTERM
import logging

class Event(list):
   """ Event subscription system (http://stackoverflow.com/a/2022629/1767963) """
   
   def __call__(self, *args, **kwargs):
      for f in self:
         f(*args, **kwargs)

   def __repr__(self):
      return "Event(%s)" % list.__repr__(self)

class DaemonError(Exception):
   """ An error in the generic Daemon class. """

class Daemon(object):
   """ A generic daemon class. """
   
   def __init__(self, pidfile, stdin="/dev/null", stdout="/dev/null",
         stderr="/dev/null"):
      self.stdin = stdin
      self.stdout = stdout
      self.stderr = stderr
      self.pidfile = pidfile

   def daemonize(self):
      """ Do the UNIX double-fork magic, see Stevens' "Advanced Programming
      in the UNIX Environment" for details (ISBN 0201563177)
      http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
      """

      try:
         pid = os.fork()
         if pid > 0:
            # exit first parent
            sys.exit(0)
      except OSError, e:
         raise DaemonError("Fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))

      # decouple from parent environment
      os.chdir("/")
      os.setsid()
      os.umask(0)

      # do second fork
      try:
         pid = os.fork()
         if pid > 0:
            sys.exit(0)
      except OSError, e:
         raise DaemonError("Fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))

      sys.stdout.flush()
      sys.stderr.flush()
      si = file(self.stdin, 'r')
      so = file(self.stdout, 'a+')
      se = file(self.stderr, 'a+', 0)
      os.dup2(si.fileno(), sys.stdin.fileno())
      os.dup2(so.fileno(), sys.stdout.fileno())
      os.dup2(se.fileno(), sys.stderr.fileno())

      # on exit, call delpid
      atexit.register(self.delpid)

      # write pidfile
      pid = str(os.getpid())

      with open(self.pidfile, 'w+') as f:
         f.write("%s\n" % pid)

   def delpid(self):
      """ delete the pidfile """

      os.remove(self.pidfile)

   def start(self):
      """ Start the daemon. """

      # Check for a pidfile to see if the daemon already runs
      try:
         pf = file(self.pidfile, 'r')
         pid = int(pf.read().strip())
         pf.close()
      except IOError:
         pid = None

      if pid:
         raise DaemonError("pidfile %s already exists. Daemon already running?"
               % self.pidfile)
      
      self.daemonize()
      self.run()

   def stop(self):
      """ Stop the daemon. """
      
      try:
         pf = file(self.pidfile, 'r')
         pid = int(pf.read().strip())
         pf.close()
      except IOError:
         pid = None

      if not pid:
         raise DaemonError("pidfile %s does not exist. Daemon not running?"
               % self.pidfile)
         return # not an error in a restart

      # Try killing the daemon process
      try:
         while True:
            os.kill(pid, SIGTERM)
            time.sleep(0.1)
      except OSError, err:
         err = str(err)
         if err.find("No such process") > 0:
            if os.path.exists(self.pidfile):
               os.remove(self.pidfile)
         else:
            raise DaemonError(err)

   def restart(self):
      """ Restart the daemon. """

      self.stop()
      self.start()

   def run(self):
      """ this method will be overridden when Daemon is subclassed. """

      pass

class Singleton(type):
   """ Helper for Logger """

   _instances = {}

   def __call__(cls, *args, **kwargs):
      if cls not in cls._instances.keys():
         cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
      return cls._instances[cls]

class LoggerManager(object):
   """ A simple hack to make loggers available throughout the application. """

   __metaclass__ = Singleton
   _loggers = {}

   def __init__(self, *args, **kwars):
      pass

   @staticmethod
   def getLogger(name=None):
      if not name:
         logging.basicConfig()
         return logging.getLogger()
      elif name not in LoggerManager._loggers.keys():
         LoggerManager._loggers[name] = logging.getLogger(str(name))
      return LoggerManager._loggers[name]
