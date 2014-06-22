#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# oiseau - scrobble MPD tracks to Last.fm
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

# -------------------------
# Configuration
# -------------------------

LFM_USERNAME = "Last.fm username"
LFM_PASSWORD = "Last.fm password"
MPD_HOST     = "localhost"
MPD_PORT     = 6600
MPD_PASSWORD = None
MPD_UNICODE  = True
DEBUG        = False

# -------------------------
# Here be dragons ...
# -------------------------

VERSION = "oiseau 0.1 - a Last.fm scrobbler for Music Player Daemon.\n\
Copyright (c) 2014, Berk Özbalcı <berkozbalci@gmail.com>"

from mpd import MPDClient, MPDError, CommandError
import pylast
import time
import sys
import os
import atexit
import signal
import argparse
import ConfigParser

class Event(list):
   """ Event subscription system (http://stackoverflow.com/a/2022629/1767963) """
   
   def __call__(self, *args, **kwargs):
      for f in self:
         f(*args, **kwargs)

   def __repr__(self):
      return "Event(%s)" % list.__repr__(self)

class Daemon(object):
   """ A generic daemon class. """
   
   def __init__(self, pidfile, stdin="/dev/null", stdout="/dev/null", stderr="/dev/null"):
      self.stdin = stdin
      self.stdout = stdout
      self.stderr = stderr
      self.pidfile = pidfile

   def daemonize(self):
      """ do the UNIX double-fork magic """

      try:
         pid = os.fork()
         if pid > 0:
            # exit first parent
            sys.exit(0)
      except OSError, e:
         raise OiseauError("Fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))

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
         raise OiseauError("Fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))

      sys.stdout.flush()
      sys.stderr.flush()
      si = file(self.stdin, 'r')
      so = file(self.stdout, 'a+')
      se = file(self.stderr, 'a+', 0)
      os.dup2(si.fileno(), sys.stdin.fileno())
      os.dup2(so.fileno(), sys.stdout.fileno())
      os.dup2(se.fileno(), sys.stderr.fileno())

      # write pidfile
      atexit.register(self.delpid)
      pid = str(os.getpid())
      file(self.pidfile, 'w+').write("%s\n" % pid)

   def delpid(self):
      os.remove(self.pidfile)

   def start(self):
      """ start the daemon """

      # Check for a pidfile to see if the daemon already runs
      try:
         pf = file(self.pidfile, 'r')
         pid = int(pf.read().strip())
         pf.close()
      except IOError:
         pid = None

      if pid:
         raise OiseauError("pidfile %s already exists. Oiseau already running?"
               % self.pidfile)
      
      self.daemonize()
      self.run()

   def stop(self):
      """ stop the daemon """
      
      try:
         pf = file(self.pidfile, 'r')
         pid = int(pf.read().strip())
         pf.close()
      except IOError:
         pid = None

      if not pid:
         raise OiseauError("pidfile %s doesn't exist. Oiseau not running?"
               % self.pidfile)
         return # not an error in a restart

      # Try killing the daemon process
      try:
         while True:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
      except OSError, err:
         err = str(err)
         if err.find("No such process") > 0:
            if os.path.exists(self.pidfile):
               os.remove(self.pidfile)
         else:
            raise OiseauError(err)

   def restart(self):
      """ restart the daemon """

      self.stop()
      self.start()

   def run(self):
      """ this method will be overridden when Daemon is subclassed. """

      pass

class OiseauError(Exception):
   """ An error in the scrobbler """

class MPDConnection:
   """ Connects and disconnects to a MPD server """

   def __init__(self, host, port, password=None, use_unicode=True):
      self.host = host
      self.port = port
      self.password = password
      self.use_unicode = use_unicode
      self.client = MPDClient(use_unicode=use_unicode)

   def connect(self):
      """ Connect to the MPD server """

      try:
         self.client.connect(self.host, self.port)
      except IOError as err:
         errno, errstr = err
         raise OiseauError("Could not connect to '%s': %s" % (self.host, errstr))
      except MPDError as e:
         raise OiseauError("Could not connect to '%s': %s" % (self.host, e))

      if self.password:
         try:
            self.client.password(self.password)
         except CommandError as e:
            raise OiseauError("Could not connect to '%s': "
                              "password command failed: %s" % (self.host, e))
         except (MPDError, IOError) as e:
            raise OiseauError("Could not connect to '%s': "
                              "password command failed: %s" % (self.host, e))

   def disconnect(self):
      """ Disconnect from the MPD server """
      
      try:
         self.client.close()
      except (MPDError, IOError):
         # Don't worry, just ignore it, disconnect
         pass
      try:
         self.client.disconnect()
      except (MPDError, IOError):
         # Now this is seriosu. This should never happen on normal usage.
         # The client object should not be trusted to be re-used.
         # One example where this occurs is the daemon stopping process,
         # where the MPDClient() isn't connected and tries to disconnect.
         # So resurrect silently.
         self.client = MPDClient(use_unicode=self.use_unicode)

class MPDWatcher:
   """ Watches MPD track changes and records them into a list """

   def __init__(self, conn):
      self.conn = conn

      # If a track is eligible for scrobbling, it is added to the queue.
      self.queue = []
      self.on_queue_update = Event()

      # The watcher automatically updates the now_playing variable to match the
      # most recently played song.
      self.now_playing = None
      self.on_now_playing_update = Event()
   
   def current_song(self):
      """ Return the current playing song on MPD, empty dictionary if none playing """

      try:
         song = self.conn.client.currentsong()
      except (MPDError, IOError):
         # Try reconnecting and retrying
         self.conn.disconnect()
         try:
            self.conn.connect()
         except OiseauError as e:
            raise OiseauError("Reconnecting failed: %s" % e)
         try:
            song = self.conn.client.currentsong()
         except (MPDError, IOError) as e:
            # Failed again, just give up.
            raise OiseauError("Couldn't retrieve current song: %s" % e)

      return song

   def watch(self):
      """ Add every new song to the queue """

      # As long as this is set True, the watcher will send idle requests to MPD
      # and fetches them. The method MPDWatcher.stop() will set this to False.
      self.watching = True

      # Will be useful when we are recording status changes
      last_status = self.conn.client.status()

      # Start watching by sending an initial idle request.
      self.conn.client.send_idle("player")

      # Watch loop
      while self.watching:
         self.conn.client.fetch_idle()
         status = self.conn.client.status()

         # The songid gets incremented in each track change. Compare it to the previous
         # one to see if the track has been changed
         songid = status.get("songid", None)
         last_songid = last_status.get("songid", None)
         track_changed = songid not in (None, last_songid)

         # If so, process the song
         if track_changed:
            song = self.current_song()
            self.now_playing = song
            self.on_now_playing_update()
            self.schedule_check(song)

         # Update the last_status to the current
         last_status = status

         # Sleep for a while and continue idling
         time.sleep(1)
         self.conn.client.send_idle("player")

   def schedule_check(self, song):
      """ wait until a percentage of the song is finished and proceed """

      # Duration of the song in seconds. Every song has this attritube.
      duration = int(song["time"])

      # If the song is longer than 8 minutes, the first 4 minutes is enough,
      # else, half of the song must be listened before submitted to Last.fm
      if duration >= 480:
         checkpoint = 240
      else:
         checkpoint = duration * 0.5

      # This is going to be helpful when we are going to compare the songids of
      # two statuses. We would be able to detect song changes, and if this occurs,
      # we can stop waiting for the song to reach the required percentage.
      try:
         last_songid = songid = self.conn.client.status()["songid"]
      except KeyError:
         return False

      # Get elapsed time in seconds. Sometimes status() doesn't contain this information.
      # Stop scheduling a check if that occurs.
      try:
         elapsed = int(float(self.conn.client.status()["elapsed"]))
      except KeyError:
         return False

      # Keep listening to the song until we've reached the checkpoint, and if the
      # track changes, cancel this process.
      while last_songid == songid and not elapsed >= checkpoint:
         status = self.conn.client.status()
         try:
            elapsed = int(float(status["elapsed"]))
            songid = status["songid"]
         # Just in case the player stops:
         except KeyError:
            return False
         time.sleep(1)

      # We're out of the loop, but one could also have set the last_songid
      # further than songid, so check again to see if the song can be submitted.
      if elapsed >= checkpoint:
         self.process_song(song)
         return True

      # The song is not eligible for scrobbling. Return false.
      return False

   def process_song(self, song):
      """ If a song is worthy of being scrobbled, add it to the queue. """

      # The minimum requirements for scrobbling: artist, and title.
      try:
         artist = song["artist"]
         title = song["title"]
      except:
         # Song doesn't have enough information to be scrobbled to Last.fm
         return False
      
      # Put in a dictionary format that pylast accepts.
      payload = {
         "artist" : artist,
         "title": title,
         "timestamp": int(time.time())
      }

      # The following are not mandatory, but still nice to be known by Last.fm
      if song["album"]: payload["album"] = song["album"]

      # Often, MPD responds with a list instead of a single string for 'albumartist'.
      # If it's a list, return first element, else, return the string itself.
      if song["albumartist"]:
         if isinstance(song["albumartist"], list) and not isinstance(song["albumartist"], basestring):
            payload["album_artist"] = song["albumartist"][0]
         else:
            payload["album_artist"] = song["albumartist"]

      if song["time"]: payload["duration"] = int(song["time"])

      # Add the song to the list and call the list update event
      self.queue.append(payload)
      self.on_queue_update()

   def stop(self):
      """ Stop watching the MPD server """

      self.watching = False

class Scrobbler:
   """ Submits tracks to Last.fm """

   def __init__(self, username, password_hash):
      API_KEY    = "a76e4f3f6a9e81f45a943509437a125f"
      API_SECRET = "480a8292392dbba520848a3a955e2ec4"

      # password_hash will always be hashed with md5
      self.network = pylast.LastFMNetwork(
            api_key = API_KEY, api_secret = API_SECRET,
            username = username, password_hash = password_hash)

   def scrobble_many(self, tracks):
      """ Submit a batch of tracks at once. """

      self.network.scrobble_many(tracks)

   def now_playing(self, artist, title, album=None, album_artist=None, duration=None):
      """ Update now playing status on Last.fm """

      self.network.update_now_playing(album=album, artist=artist, title=title,
            album_artist=album_artist, duration=duration)

class Oiseau(Daemon):
   """ Binds it all together: the client, the watcher, the scrobbler... """

   def __init__(self, pidfile, conn, watcher, scrobbler,
         stdin="/dev/null", stdout="/dev/null", stderr="/dev/null"):
      # Initializing the daemon
      self.pidfile = pidfile
      self.stdin = stdin
      self.stdout = stdout
      self.stderr = stderr

      # MPD Connection/Watcher, Last.fm Scrobbler
      self.conn = conn
      self.watcher = watcher
      self.scrobbler = scrobbler

      # Connect the events to the functions
      self.watcher.on_queue_update.append(self.scrobble_queue)
      self.watcher.on_now_playing_update.append(self.set_now_playing)

   def scrobble_queue(self):
      """ After receiving a queue update event, attempt to scrobble the tracks. """

      try:
         # (If there is at least one track to scrobble)
         if self.watcher.queue != []:
            self.scrobbler.scrobble_many(self.watcher.queue)
         
         # Reset queue after batch scrobbling, avoid multiple scrobbles.
         # Do not invoke self.watcher.on_queue_update(), as the queue is empty,
         # it will be meaningless to call this function again.
         self.watcher.queue = []
      except Exception as e:
         # TODO: Write the scrobble data to a csv/json file for later reviewal
         # Do not raise OiseauError, instead, cache the scrobbles.
         pass

   def set_now_playing(self):
      """ After receiving a now playing update event, report it to Last.fm """

      # If the now_playing track hasn't been set yet ...
      if self.watcher.now_playing is None:
         return

      last_played = self.watcher.now_playing

      # The minimum requirements for setting the now playing track are artist and title.
      try:
         artist = last_played["artist"]
         title = last_played["title"]
      except:
         # "Now playing" not worthy of being updated.
         return False

      # The following are not mandatory, but still nice to be known by Last.fm
      album = last_played["album"] if last_played["album"] else None

      # Often, MPD responds with a list instead of a single string for 'albumartist'.
      # If it's a list, return first element, else, return the string itself.
      if last_played["albumartist"]:
         if isinstance(last_played["albumartist"], list) and not isinstance(last_played["albumartist"], basestring):
            album_artist = last_played["albumartist"][0]
         else:
            album_artist = last_played["albumartist"]
      else:
         album_artist = None

      duration = int(last_played["time"]) if last_played["time"] else None

      # Report now playing to Last.fm
      self.scrobbler.now_playing(artist=artist, album=album, title=title,
            album_artist=album_artist, duration=duration)

   def run(self):
      """ The main Oiseau procedure. Enter the loop, call events and handle them.
          Overrides Daemon.run() """

      self.conn.connect()
      self.watcher.watch()

   def stop(self, stop_daemon=True):
      """ Stop the entire Oiseau procedure, disconnect from MPD. """

      self.watcher.stop()
      self.conn.disconnect()

      # Stop the daemon, calling the parent function. Note that this function could
      # also be called in the case where Oiseau is not being run as a daemon, so
      # we introduced a boolean parameter.
      if stop_daemon:
         super(Oiseau, self).stop()

def absolute_path(path):
   """ Return the absolute path of the given path. """

   path = os.path.expandvars(path)
   path = os.path.expanduser(path)
   path = os.path.abspath(path)

   return path

def file_readable(path):
   return os.access(path, os.R_OK)

def parse_args():
   """ Parse the arguments passed to Oiseau. """

   parser = argparse.ArgumentParser(
      prog='oiseau',
      description='Last.fm scrobbler for the Music Player Daemon',
      usage='%(prog)s [options]')

   parser.add_argument('-v', '--version', action='store_true', dest='version',
         help='show version and exit')
   parser.add_argument('-F', action='store_true', dest='foreground',
         help='run oiseau in the foreground, rather than as a daemon')
   parser.add_argument('-k', action='store_true', dest='kill',
         help='kill the running oiseau daemon')
   parser.add_argument('-f', type=str, dest='cfgfile',
         help='the location of the configuration file')
   parser.add_argument('-i', type=str, dest='pidfile',
         help='the location of the pid file')

   # Instead of setting the defaults here, we're going to provide a mechanism
   # to allow preferences among CLI args and config file args. 
   args = parser.parse_args()
   return args

def read_config(cfg):
   config = ConfigParser.ConfigParser()
   prefs = {}

   try:
      config.read(cfg)
   except Exception as e:
      raise OiseauError("Could not read configuration file: %s" % e)

   # MPD Connection Information: Default is always localhost:6600 with no password.
   try:
      prefs['mpd_host'] = config.get('mpd', 'host')
   except:
      prefs['mpd_host'] = "localhost"
   try:
      prefs['mpd_port'] = config.getint('mpd', 'port')
   except:
      prefs['mpd_port'] = 6600
   try:
      prefs['mpd_password'] = config.get('mpd', 'password')
   except:
      prefs['mpd_password'] = None

   # Last.fm Connection Information: An username and a password must always be
   # specified. The password is accepted in two formats: a password already hashed
   # with md5, and a plaintext password. The former is the preferred one, and one
   # cannot use the both at the same time.
   try:
      prefs['lfm_username'] = config.get('lastfm', 'username')
   except:
      raise OiseauError("Last.fm username must be specified!")
   try:
      prefs['lfm_password'] = config.get('lastfm', 'password_hash')
   except:
      try:
         prefs['lfm_password'] = pylast.md5(config.get('lastfm', 'password'))
      except:
         raise OiseauError("Last.fm password must be specified!")

   # Oiseau Options: Here are the logging level, log file, pid file, and TODO the
   # cache file options. All of the following options could also be set by
   # passing arguments to the program, and all of the options have default values.
   # To provide a mechanism that makes preferences among the two, we are going to
   # return the preferences in a tuple form, with a boolean as the second element,
   # that indicates whether the option has been explicitly set.
   try:
      prefs['pidfile'] = config.get('oiseau', 'pidfile')
   except:
      prefs['pidfile'] = None

   return prefs

def main():
   """ The entry point of Oiseau """

   # Read the command line arguments.
   args = parse_args()

   # Choose a configuration file.
   if args.config:
      config = absolute_path(args.config)
   else:
      if file_readable(absolute_path("~/.oiseau/config")):
         config = absolute_path("~/.oiseau/config")
      else:
         if file_readable("/usr/local/etc/oiseau.conf"):
            config = "/usr/local/etc/oiseau.conf"
         else:
            raise OiseauError("No configuration file has been detected!")

   # Read the configuration file.
   prefs = read_config(config)

   # Print the program version and copyright information
   if args.version:
      print(VERSION)
      return

   # Create the client/watcher objects to pass to Oiseau
   conn = MPDConnection(
         prefs['mpd_host'],
         prefs['mpd_port'],
         prefs['mpd_password'],
         MPD_UNICODE)
   watcher = MPDWatcher(conn)

   # Try logging in to Last.fm
   try:
      scrobbler = Scrobbler(prefs['lfm_username'], prefs['lfm_password'])
   except pylast.WSError as e:
      # If we're going to kill the running daemon, we don't really care if we
      # can connect to Last.fm. Don't raise an exception if so
      if not args.kill:
         raise OiseauError("Couldn't connect to Last.fm: %s" % e)

      # Just a dummy scrobbler.
      scrobbler = None

   # Choose a pidfile.
   if args.pidfile:
      pidfile = absolute_path(args.pidfile)
   else:
      if prefs['pidfile']:
         pidfile = absolute_path(prefs['pidfile'])
      else:
         pidfile = "/tmp/oiseau.pid"

   # Make it rain!
   oiseau = Oiseau(pidfile, conn, watcher, scrobbler)

   # or don't :p
   if args.kill:
      oiseau.stop()
      return

   # Run as a daemon
   if not args.foreground:
      oiseau.start()

   # Run in the foreground, setting the std{in,out,err} as they were (instead of
   # the ones given in the configuration.) Nothing is printed on the pidfile.
   if args.foreground:
      oiseau.pidfile = None
      oiseau.stdout = sys.stdout
      oiseau.stdin = sys.stdin
      oiseau.stderr = sys.stderr

      try:
         oiseau.run()
      except (KeyboardInterrupt, EOFError):
         oiseau.stop(stop_daemon=False)
         sys.exit()

if __name__ == "__main__":
   if not DEBUG:
      try:
         main()
      except OiseauError as e:
         sys.stderr.write("Error: %s\n" % e)
         sys.exit(1)
      except Exception as e:
         sys.stderr.write("Unexpected exception: %s\n" % e)
         sys.exit(1)
      except:
         sys.exit(0)
   if DEBUG:
      main()
