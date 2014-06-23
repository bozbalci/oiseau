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

import misc
import json, os

log = misc.LoggerManager().getLogger('oiseau')

class CacheError(Exception):
   """ An error which occurs during the process of caching tracks. """

def load_json(name):
   """ Deserializes a file containing a JSON document into a Python object,
   and empties the file afterwards. If the cache file is empty, or nonexistent,
   do not raise an error.
   """

   log.debug('load_json() called.')

   if name == None:
      log.debug('Filename is not specified, aborting.')

      return []

   if not os.path.isfile(name):
      log.debug('The file does not exist, aborting.')

      return []

   # Check if the file is empty
   try:
      log.debug('Attempting to stat the file.')

      if os.stat(name).st_size == 0:
         log.debug('The file is empty, aborting.')

         return []
   except IOError as e:
      raise CacheError("Cannot stat the cache file" % e)

   try:
      with open(name, 'r') as fp:
         data = json.load(fp)

         log.debug('Successfully read JSON data from file.')
   except IOError as e:
      raise CacheError("Could not read from the cache file: %s" % e)

   try:
      open(name, 'w').close()

      log.debug('Successfully emptied the cache file.')
   except IOError as e:
      raise CacheError("Could not empty the cache file: %s" % e)

   return data

def write_json(name, data):
   """ Attempts to append JSON objects into a file which may be containing
   JSON data. If the file doesn't exist or is empty, it creates/fills the file.
   """
   
   log.debug('write_json() called.')

   if name == None:
      log.debug('Filename not specified, aborting.')

      return

   if data == []:
      log.debug('Nothing to write to cache, aborting.')

      return

   if not os.path.isfile(name):
      log.debug('File is nonexistent, will create a new file.')

      existing_data = []
      
      try:
         open(name, 'w+').close()

         log.debug('Created a new file for cache.')
      except IOError as e:
         raise CacheError("Could not create cache file: %s" % e)
   else:
      log.debug('The file exists, running stat.')

      try:
         size = os.stat(name).st_size

         log.debug('Stat successful.')
      except IOError as e:
         raise CacheError("Cannot stat the cache file" % e)

      if size == 0:
         log.debug('Cache file is empty.')

         existing_data = []
      else:
         log.debug('Cache file is nonempty, will attempt to load the JSON.')

         existing_data = load_json(name)

   try:
      with open(name, 'w') as fp:
         json.dump(existing_data + data, fp)

         log.info('Successfully wrote cache to the file.')
   except IOError as e:
      raise CacheError("Could not write to cache file: %s" % e)
