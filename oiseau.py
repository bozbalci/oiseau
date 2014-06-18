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

LFM_USERNAME = "Your Last.fm username"
LFM_PASSWORD = "Your Last.fm password"
MPD_HOST     = "localhost"
MPD_PORT     = 6600
MPD_PASSWORD = None
MPD_UNICODE  = True
DEBUG        = False

# -------------------------
# Here be dragons ...
# -------------------------

API_KEY      = "a76e4f3f6a9e81f45a943509437a125f"
API_SECRET   = '480a8292392dbba520848a3a955e2ec4'

from mpd import MPDClient, MPDError, CommandError
import pylast
import time, logging, sys

class Event(list):
   """ Event subscription system (http://stackoverflow.com/a/2022629/1767963) """
   
   def __call__(self, *args, **kwargs):
      for f in self:
         f(*args, **kwargs)

   def __repr__(self):
      return "Event(%s)" % list.__repr__(self)

class OiseauError(Exception):
   """ An error in the scrobbler """

class MPDConnection:
   """ Connects and disconnects to a MPD server """

   def __init__(self, host, port, password=None, use_unicode=True):
      self.host = host
      self.port = port
      self.password = password
      self.connected = False
      self.client = MPDClient(use_unicode=use_unicode)

   def connect(self):
      """ Connect to the MPD server """

      # If we are already connected, just reconnect
      if self.connected:
         self.disconnect()
         self.connect()

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
            raise OiseauError("Could not connect to '%s': password command failed: %s" %
                  (self.host, e))
         except (MPDError, IOError) as e:
            raise OiseauError("Could not connect to '%s': password command failed: %s" %
                  (self.host, e))

      self.connected = True

   def disconnect(self):
      """ Disconnect from the MPD server """

      # Don't go further if there's no connection
      if not self.connected:
         return

      try:
         self.client.close()
      except (MPDError, IOError):
         # Don't worry, just ignore it, disconnect
         pass
      try:
         self.client.disconnect()
      except (MPDError, IOError):
         # Now this is serious. This should never happen.
         # The client object should not be trusted to be re-used.
         self.client = MPDClient(use_unicode=self.use_unicode)

      self.connected = False

class MPDWatcher:
   """ Watches MPD track changes and records them into a list """

   def __init__(self, conn):
      self.conn = conn
      self.queue = []
      self.on_update = Event()
   
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

      self.watching = True

      # Will be useful when we are recording status changes
      last_status = self.conn.client.status()

      # If there's already a track playing, then add it to the scrobbling queue
      if last_status.get('songid', None) != None:
         song = self.current_song()
         self.process_song(song)
      
      self.conn.client.send_idle('player')
      while self.watching:
         self.conn.client.fetch_idle()
         status = self.conn.client.status()
         songid = status.get('songid', None)
         last_songid = last_status.get('songid', None)
         track_changed = songid not in (None, last_songid)

         if track_changed:
            song = self.current_song()
            self.process_song(song)
         
         last_status = status

         # Continue idling, and sleep for a while.
         time.sleep(1)
         self.conn.client.send_idle('player')

   def process_song(self, song):
      """ If a song is worthy of being scrobbled, add it to the queue. """

      if song == {}:
         return

      try:
         artist = song['artist']
         album = song['album']
         title = song['title']
      except:
         # Song doesn't have enough information to be scrobbled to Last.fm
         return
     
      # Put in a dictionary format that pylast accepts.
      payload = {
         'artist' : artist,
         'album': album,
         'title': title,
         'timestamp': int(time.time())
      }

      self.queue.append(payload)
      self.on_update()

   def stop(self):
      """ Stop watching the MPD server """

      self.watching = False

class Scrobbler:
   """ Submits tracks to Last.fm """

   def __init__(self, username, password):
      password_hash = pylast.md5(password)
      self.network = pylast.LastFMNetwork(
            api_key = API_KEY, api_secret = API_SECRET,
            username = username, password_hash = password_hash)

   def scrobble(self, album, artist, title, timestamp):
      """ Submit a single track to Last.fm """

      self.network.scrobble(artist=artist, title=title, album=album, timestamp=timestamp)

   def scrobble_many(self, tracks):
      """ Submit a batch of tracks at once. """

      self.network.scrobble_many(tracks)

   def now_playing(self, album, artist, title):
      """ Update now playing status on Last.fm """

      self.network.update_now_playing(album=album, artist=artist, title=title)

def main():
   logging.info("Connecting to MPD ...")
   client = MPDConnection(MPD_HOST, MPD_PORT, MPD_PASSWORD, MPD_UNICODE)
   client.connect()
   logging.debug("Connected.")

   logging.info("Initializing MPD watcher ...")
   watcher = MPDWatcher(client)
   logging.debug("Initialized.")

   logging.info("Initializing scrobbler ...")
   scrobbler = Scrobbler(LFM_USERNAME, LFM_PASSWORD)
   logging.debug("Initialized.")

   def watcher_process():
      if watcher.queue != []:
         last_played = watcher.queue[-1]
         
         try:
            artist = last_played['artist']
            album = last_played['album']
            title = last_played['title']
         except:
            # "Now playing" not worthy of being updated.
            pass

         scrobbler.now_playing(artist=artist, album=album, title=title)
         logging.info("Submitted 'now_playing' to Last.fm")
      
      try:
         if watcher.queue != []:
            scrobbler.scrobble_many(watcher.queue)
            logging.info("Scrobbled track to Last.fm")
         
         # Reset queue after batch scrobbling, avoid multiple scrobbles
         watcher.queue = []
      except Exception as e:
         raise OiseauError("Could not scrobble track: %s" % e)
   
   logging.info("Watching for MPD tracks.")
   watcher.on_update.append(watcher_process)

   try:
      watcher.watch()
   except (KeyboardInterrupt, EOFError):
      watcher.stop()
      client.disconnect()
      sys.exit(0)

if __name__ == '__main__':
   if DEBUG:
      logging.getLogger().setLevel(logging.DEBUG)

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
