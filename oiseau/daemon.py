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

from mpdclient import MPDConnectionError, MPDWatcherError
import misc
import cache

log = misc.LoggerManager().getLogger('oiseau')

class OiseauError(Exception):
   """ An error in the relation between the watcher and the scrobbler. """

class Oiseau(misc.Daemon):
   """ A daemon which connects the watcher and the scrobbler. """

   def configure(self, prefs, watcher, scrobbler):
      """ Loads the program configurations into Oiseau. """

      self.prefs = prefs
      self.set_watcher(watcher)
      self.set_scrobbler(scrobbler)
   
   def run(self):
      """ Runs the Oiseau procedure as a daemon. """
         
      if self.watcher and self.scrobbler:
         log.info('Starting oiseau daemon...')

         try:
            log.debug('Entering watcher loop.')

            self.watcher.start()
         except OiseauError as exc:
            log.error(u'Error: {}'.format(exc))
         except MPDWatcherError as exc:
            log.error(u'MPD error: {}'.format(exc))
            self.stop()

   def sigterm_handler(self, signal, frame):
      """ Final clean-up before processing SIGTERM. """

      if self.watcher:
         log.info('Stopping oiseau daemon...')

         try:
            if len(self.watcher.queue) > 0:
               log.debug('Attempting to write to cache...')

               cache.write_json(self.prefs.cache, self.watcher.queue)
         except CacheError as exc:
            log.error('Could not cache tracks: {}'.format(exc))
         finally:
            self.watcher.stop()
            self.watcher.disconnect()

   def set_watcher(self, watcher):
      self.watcher = watcher

      # Bind the events to the corresponding methods
      self.watcher.queue_updated.append(self.queue_updated)
      
      if self.prefs.now_playing:
         self.watcher.now_playing_updated.append(self.now_playing_updated)

      self.watcher.scrobble_point = self.prefs.point

   def set_scrobbler(self, scrobbler):
      self.scrobbler = scrobbler

   def queue_updated(self):
      """ The queue of tracks has been updated. Attempt to submit the tracks. """

      log.debug('Track queue updated.')

      try:
         log.debug('Attempting to load cache...')

         self.watcher.queue += cache.load_json(self.prefs.cache)

         log.debug('Successfully loaded cache.')
      except CacheError as e:
         raise OiseauError("Could not load tracks from cache file: %s" % e)

      if self.watcher.queue == []:
         log.debug('Queue empty, aborting.')
         return

      log.debug('Proceeding to submit tracks to Last.fm.')

      if self.prefs.after not in [0, 1]:
         log.debug('Will wait for {} tracks before submitting.'.format(self.prefs.after))

         if len(self.watcher.queue) >= self.prefs.after:
            log.debug('Collected {} tracks, submitting.'.format(len(self.watcher.queue)))

            try:
               self.scrobbler.scrobble_many(self.watcher.queue)
               log.info('Submitted {} tracks to Last.fm.'.format(len(self.watcher.queue)))
               
               self.watcher.queue = []
            except:
               try:
                  log.debug('Could not submit tracks, writing to scrobble cache...')

                  cache.write_json(self.prefs.cache, self.watcher.queue)
                  log.info('Wrote {} tracks into cache.'.format(len(self.watcher.queue)))

                  self.watcher.queue = []
               except CacheError as e:
                  raise OiseauError("Could not cache tracks: %s" % e)
      else:
         log.debug('Will not wait for any other tracks before submitting.')

         try:
            self.scrobbler.scrobble_many(self.watcher.queue)
            log.info('Submitted 1 track to Last.fm.')

            self.watcher.queue = []
         except:
            try:
               cache.write_json(self.prefs.cache, self.watcher.queue)
               log.info('Wrote {} tracks into cache.'.format(len(self.watcher.queue)))

               self.watcher.queue = []
            except CacheError as e:
               raise OiseauError("Could not cache tracks: %s" % e)

   def now_playing_updated(self):
      """ The currently playing song has been updated, broadcast it. """
      
      log.debug('Now playing updated, broadcasting it...')

      if self.watcher.now_playing is None:
         log.debug('No track is playing. Abort.')

         # Not playing a track at the moment.
         return

      np = self.watcher.now_playing

      try:
         artist = np['artist']
         title = np['title']
      except KeyError:
         log.warning('Cannot update Now Playing: missing tag "artist" or "title"')

         # The song doesn't have artist/title information.
         return

      album = np['album'] if np['album'] else None

      # More often than neglible, MPD will return a list instead of a string when the
      # albumartist tag is requested. Handle each case as pylast doesn't accept lists.
      if np['albumartist']:
         if not isinstance(np['albumartist'], basestring):
            album_artist = np['albumartist'][0]
         else:
            album_artist = np['albumartist']
      else:
         album_artist = None

      duration = int(np['time'])

      try:
         self.scrobbler.now_playing(artist=artist, album=album, title=title,
               album_artist=album_artist, duration=duration)

         log.info('Broadcasted Now Playing to Last.fm')
      except ScrobblerError as exc:
         raise OiseauError("Could not update now playing: {}".format(exc))
