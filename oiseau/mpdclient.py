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

from mpd import MPDClient, MPDError, CommandError
import misc
import time

log = misc.LoggerManager().getLogger('oiseau')

class MPDConnectionError:
   """ An error in the MPD connection. """

class MPDWatcherError:
   """ An error in the MPD watcher. """

class MPDConnection:
   """ Connects and disconnects to a MPD server """

   def __init__(self, host, port, password=None):
      self.host = host
      self.port = port
      self.password = password

      # Always use Unicode in the MPDClient.
      self.client = MPDClient(use_unicode=True)

   def connect(self):
      """ Connect to the MPD server """

      try:
         log.info('Connecting to the MPD server.')

         self.client.connect(self.host, self.port)
      except IOError as err:
         errno, errstr = err
         raise MPDConnectionError("Could not connect to '%s': %s" % (self.host, errstr))
      except MPDError as e:
         raise MPDConnectionError("Could not connect to '%s': %s" % (self.host, e))

      if self.password:
         log.info('Attempting password command.')

         try:
            self.client.password(self.password)
         except CommandError as e:
            raise MPDConnectionError("Could not connect to '%s': "
                              "password command failed: %s" % (self.host, e))
         except (MPDError, IOError) as e:
            raise MPDConnectionError("Could not connect to '%s': "
                              "password command failed: %s" % (self.host, e))
      
   def disconnect(self):
      """ Disconnect from the MPD server """

      log.info('Disconnecting from the MPD server.')

      try:
         self.client.close()
      except (MPDError, IOError):
         log.debug('Could not close client, disconnecting...')
         # Don't worry, just ignore it, disconnect
         pass
      try:
         self.client.disconnect()
      except (MPDError, IOError):
         log.debug('Could not disconnect, resetting client object.')

         # The client object should not be trusted to be re-used.
         self.client = MPDClient(use_unicode=True)

   def reconnect(self):
      """ Reconnects to the MPD server """

      self.disconnect()
      self.connect()

class MPDWatcher:
   """ Watches MPD track changes and records them into a list """

   def __init__(self, connection):
      self.connection = connection

      # The scrobbling queue, list of dictionaries.
      self.queue = []
      self.queue_updated = misc.Event()

      # The most recent song played in MPD.
      self.now_playing = None
      self.now_playing_updated = misc.Event()

      # The current state of the watcher
      self.watching = False

      # The percentage of a song to wait before submitting
      self.scrobble_point = 0.5

   def disconnect(self):
      """ Disconnect from the MPD server """

      self.connection.disconnect()

   def reconnect(self):
      """ Reconnect to the MPD server """

      self.connection.reconnect()
   
   def start(self):
      """ Start watching the MPD server for track changes """

      log.debug('In watcher loop.')

      # As long as this is set True, the watcher will send idle requests to MPD
      # and fetches them. The method MPDWatcher.stop() will set this to False.
      self.watching = True

      # Will be useful when we are recording status changes
      last_status = self.connection.client.status()

      # Start watching by sending an initial idle request.
      self.connection.client.send_idle("player")
      log.debug('Sent idle() request to MPD.')

      # Watch loop
      while self.watching:
         self.connection.client.fetch_idle()
         log.debug('Fetching idle() from MPD.')

         status = self.connection.client.status()

         # The songid gets incremented in each track change. Compare it to the previous
         # one to see if the track has been changed
         songid = status.get("songid", None)
         last_songid = last_status.get("songid", None)
         track_changed = songid not in (None, last_songid)

         # If so, process the song
         if track_changed:
            log.debug('Track changed.')

            song = self.current_song()
            self.playing(song)
            self.keep_listening(song)

         # Update the last_status to the current
         last_status = status

         # Sleep for a while and continue idling
         time.sleep(1)
         self.connection.client.send_idle("player")
   
   def stop(self):
      """ Stop watching the MPD server """

      self.watching = False
   
   def current_song(self):
      """ Return the current playing song on MPD, empty dictionary if none playing """

      try:
         log.debug('Sending currentsong() to MPD.')

         song = self.connection.client.currentsong()
      except (MPDError, IOError):
         log.debug('currentsong() failed, attempting to reconnect to MPD.')

         # Reconnect and retry
         self.connection.reconnect()

         try:
            log.debug('Sending currentsong() to MPD.')

            song = self.connection.client.currentsong()
         except (MPDError, IOError) as e:
            # Failed again, just give up.
            raise MPDWatcherError("Could not retrieve current song: %s" % e)

      log.debug('Got current song, returning it')

      return song

   def playing(self, song):
      """ Signals a now playing update to the event handlers """

      log.debug('Event now_playing_updated() raised.')

      self.now_playing = song
      self.now_playing_updated()

   def keep_listening(self, song):
      """ Wait until a percentage of the song is finished and proceed """

      log.debug('Started listening to a track.')

      duration = int(song["time"])

      # If the song is longer than 8 minutes, the first 4 minutes is enough,
      # else, a specified portion of the song must be listened before caching.
      if duration >= 480:
         checkpoint = 240
      else:
         checkpoint = duration * self.scrobble_point

      log.debug('Set checkpoint to {} seconds.'.format(checkpoint))

      last_songid = songid = self.connection.client.status()["songid"]
      elapsed = int(float(self.connection.client.status()["elapsed"]))

      log.debug('Waiting for the checkpoint...')

      # Keep listening to the song until we've reached the checkpoint, and if the
      # track changes, cancel this process.
      while last_songid == songid and not elapsed >= checkpoint:
         status = self.connection.client.status()
         try:
            elapsed = int(float(status["elapsed"]))
            songid = status["songid"]
         # Just in case the player stops:
         except KeyError:
            return

         # Listen to one second of the song and continue
         time.sleep(1)

      # We're out of the loop, but one could also have set the last_songid
      # further than songid, so check again to see if the song can be submitted.
      if elapsed >= checkpoint:
         log.debug('Passed the checkpoint, queueing track.')

         self.queue_song(song)
      else:
         log.debug('Track interrupted, aborting.')

   def queue_song(self, song):
      """ If a song is worthy of being scrobbled, add it to the queue. """

      log.debug('A new track is staged for submitting.')

      # The minimum requirements for scrobbling: artist, and title.
      try:
         artist = song["artist"]
         title = song["title"]
      except:
         log.warning('Cannot queue track: missing tag "artist" or "title')

         # Song doesn't have enough information to be scrobbled to Last.fm
         return
      
      payload = { "artist" : artist, "title": title, "timestamp": int(time.time()) }

      # The following are not mandatory, but still nice to be known by Last.fm
      if song["album"]: payload["album"] = song["album"]

      # More often than neglible, MPD will return a list instead of a string when the
      # albumartist tag is requested. Handle each case as pylast doesn't accept lists.
      if song["albumartist"]:
         if not isinstance(song["albumartist"], basestring):
            payload["album_artist"] = song["albumartist"][0]
         else:
            payload["album_artist"] = song["albumartist"]

      if song["time"]: payload["duration"] = int(song["time"])

      # Add the song to the list and call the list update event
      log.debug('The track has been queued for submitting.')
      log.debug('Event queue_updated() raised.')

      self.queue.append(payload)
      self.queue_updated()
