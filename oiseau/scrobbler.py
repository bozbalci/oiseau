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

import pylast
import misc

log = misc.LoggerManager().getLogger('oiseau')

class ScrobblerError:
   """ An error in the Scrobbler class """

class Scrobbler:
   """ Submits tracks to Last.fm """

   def __init__(self, username, password_hash):
      API_KEY = "a76e4f3f6a9e81f45a943509437a125f"
      API_SECRET = "480a8292392dbba520848a3a955e2ec4"

      # password_hash will always be hashed with md5
      try:
         self.network = pylast.LastFMNetwork(
               api_key = API_KEY, api_secret = API_SECRET,
               username = username, password_hash = password_hash)
      except pylast.WSError as e:
         raise ScrobblerError("Could not log in to Last.fm: %s" % e)

   def scrobble_many(self, tracks):
      """ Submit a batch of tracks at once. """

      log.debug('scrobble_many() called, submitting tracks...')

      try:
         self.network.scrobble_many(tracks)
      except (pylast.NetworkError, pylast.MalformedResponseError,
            pylast.ScrobblingError) as e:
         raise ScrobblerError("Could not scrobble batch of tracks: %s" % e)

   def now_playing(self, artist, title, album=None, album_artist=None, duration=None):
      """ Update now playing status on Last.fm """
      
      log.debug('now_playing() called, updating Now Playing...')

      try:
         self.network.update_now_playing(album=album, artist=artist, title=title,
               album_artist=album_artist, duration=duration)
      except (pylast.NetworkError, pylast.MalformedResponseError) as e:
         raise ScrobblerError("Could not update now playing track: %s" % e)
