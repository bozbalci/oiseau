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

import argparse, ConfigParser, hashlib
from version import version

class ConfigurationError(Exception):
   """ An error in the configuration file system. """

class Configuration(argparse.Namespace):
   """ Namespace for preferences which will be used in Oiseau. """

   def __init__(self, config_files):
      self.config_files = config_files

   def read(self):
      """ Read the configuration file(s). """

      parser = ConfigParser.ConfigParser()
      if parser.read(self.config_files) == []:
         raise ConfigurationError("No configuration file found!")

      if not parser.has_section('mpd'):
         self.mpd_host = 'localhost'
         self.mpd_port = 6600
         self.mpd_pass = None

      if not parser.has_section('lastfm'):
         raise ConfigurationError("Last.fm username must be specified!")

      if not parser.has_section('oiseau'):
         self.now_playing = True
         self.after = 0
         self.point = 0.5
         self.cache = None
         self.pidfile = None
         self.logfile = None
         self.loglevel = None

      # [mpd] host: The MPD hostname as a string. Defaults to "localhost".
      try:
         self.mpd_host = parser.get('mpd', 'host')
      except ConfigParser.NoOptionError:
         self.mpd_host = "localhost"
      except ConfigParser.NoSectionError:
         pass

      # [mpd] port: The MPD port as an integer. Defaults to 6600.
      try:
         self.mpd_port = parser.getint('mpd', 'port')
      except ConfigParser.NoOptionError:
         self.mpd_port = 6600
      except ConfigParser.NoSectionError:
         pass

      # [mpd] port: The MPD password as a string. No default value.
      try:
         self.mpd_pass = parser.get('mpd', 'password')
      except ConfigParser.NoOptionError:
         self.mpd_pass = None
      except ConfigParser.NoSectionError:
         pass

      # [lastfm] username: Last.fm username. Must be specified for Oiseau to
      # function properly.
      try:
         self.lfm_user = parser.get('lastfm', 'username')
      except ConfigParser.NoOptionError:
         raise ConfigurationError("Last.fm username must be specified!")

      # [lastfm] password_hash: The Last.fm password, hashed in MD5.
      # [lastfm] password: The Last.fm password, in plaintext format.
      # When password_hash is supplied, it is preferred over password.
      # Either must be specified for Oiseau to function properly.
      try:
         self.lfm_pass = parser.get('lastfm', 'password_hash')
      except ConfigParser.NoOptionError:
         try:
            self.lfm_pass = hashlib.md5(parser.get('lastfm', 'password')).hexdigest()
         except ConfigParser.NoOptionError:
            raise ConfigurationError("Last.fm password must be specified!")

      # [oiseau] now_playing: A boolean value which specifies whether Oiseau should
      # broadcast the currently playing track on MPD to Last.fm. Defaults to True.
      try:
         self.now_playing = parser.getboolean('oiseau', 'now_playing')
      except ConfigParser.NoOptionError:
         self.now_playing = True
      except ConfigParser.NoSectionError:
         pass

      # [oiseau] scrobble_after: An integer number of tracks to keep in queue before
      # having them submitted to Last.fm in batch. Defaults to 0, which makes Oiseau
      # scrobble after every track.
      try:
         self.after = parser.getint('oiseau', 'scrobble_after')
      except ConfigParser.NoOptionError:
         self.after = 0
      except ConfigParser.NoSectionError:
         pass

      # [oiseau] scrobble_point: A float f which satisfies (1.0 >= f >= 0.5).
      # It configures Oiseau to queue a song after (duration * f) seconds pass.
      # Defaults to 50%.
      try:
         self.point = parser.getfloat('oiseau', 'scrobble_point')
         if not (1.0 >= self.point >= 0.5):
            raise ConfigurationError('scrobble_point must be between 0.5 and 1.0')
      except ConfigParser.NoOptionError:
         self.point = 0.5
      except ConfigParser.NoSectionError:
         pass

      # [oiseau] cache: A file to store the track queue to prevent losing
      # scrobbles in case of scrobbling errors, connectivity issues, etc.
      # Setting this None will disable the feature and that is the default one.
      try:
         self.cache = parser.get('oiseau', 'cache')
      except ConfigParser.NoOptionError:
         self.cache = None
      except ConfigParser.NoSectionError:
         pass

      # [oiseau] pidfile: A file to store the currently running Oiseau daemon's pid.
      # No default value.
      try:
         self.pidfile = parser.get('oiseau', 'pidfile')
      except ConfigParser.NoOptionError:
         self.pidfile = None
      except ConfigParser.NoSectionError:
         pass

      # [oiseau] logfile: A file to write the Oiseau logs. No default value.
      try:
         self.logfile = parser.get('oiseau', 'logfile')
      except ConfigParser.NoOptionError:
         self.logfile = None
      except ConfigParser.NoSectionError:
         pass

      # [oiseau] loglevel: String among the 5 options below, determines the
      # verbosity level on the logs. Defaults to 'warning'.
      try:
         self.loglevel = parser.get('oiseau', 'loglevel')
         if not self.loglevel in ['debug', 'info', 'warning', 'error', 'critical']:
            raise ConfigurationError('Loglevel must be any of the following: '
                  'debug, info, warning, error, critical')
      except ConfigParser.NoOptionError:
         self.loglevel = None
      except ConfigParser.NoSectionError:
         pass

class Arguments:
   def __init__(self, argv):
      self.argv = argv
      self.parse()

   def parse(self):
      """ Parse the arguments passed to Oiseau. """

      parser = argparse.ArgumentParser(
         prog='oiseau',
         usage='%(prog)s [options]',
         description='Last.fm scrobbler for the Music Player Daemon')

      parser.add_argument('-v', '--version', action='version',
            version='oiseau-{}'.format(version))

      parser.add_argument('-f', dest='cfgfile', help='configuration file location')
      parser.add_argument('-i', dest='pidfile', help='pid file location')
      parser.add_argument('-l', dest='logfile', help='log file location')
      parser.add_argument('-k', action='store_true', dest='kill',
            help='kill the running oiseau daemon')
      parser.add_argument('--log',
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='logging level')

      # Instead of setting the defaults here, we're going to provide a mechanism
      # to allow preferences among CLI args and config file args. 
      self.options = parser.parse_args(self.argv)
