oiseau
------

Extremely hacky [Last.fm][lfm] scrobbler for MPD that I wrote for myself. Still in active development.

Requirements
------------

- Tested on Python 2.7.6, will not work in Python 3.x
- Requires MPD >= 0.15, tested on MPD 0.18.11
- [python-mpd2][py27-mpd2] >= 0.5.3
- [pylast][pylast] >= 0.5.11

Features
--------

- Scrobbling (obviously)
- Updates 'now playing' on Last.fm when it can
- No duplicate scrobbles (almost guaranteed)
- Waits for a portion of the song to be finished before scrobbling
- **NEW:** Configuration file!
- **NEW:** Can be run as a daemon now!

TODO
----

- Cache tracks for later scrobbling
- Code cleaning

Usage
-----

oiseau requires a configuration file before using. An example configuration file has been provided with the package. The preference order for the configuration file is as follows:

1. If specified in the arguments, `-f <config_file>`
2. If it exists, `~/.oiseau/config`
3. If it exists, `/usr/local/etc/oiseau.conf`
4. No configuration file found, raise an error

oiseau also requires a temporary pid file, which defaults to `/tmp/oiseau.pid` if not another one is supplied in the arguments or the configuration file.

The command line usage:

    usage: oiseau [options]
    
    Last.fm scrobbler for the Music Player Daemon
    
    optional arguments:
      -h, --help     show this help message and exit
      -v, --version  show version and exit
      -F             run oiseau in the foreground, rather than as a daemon
      -k             kill the running oiseau daemon
      -f CFGFILE     the location of the configuration file
      -i PIDFILE     the location of the pid file
      -l LOGFILE     the location of the log file
      -d             log everything

The recommended installation is to move oiseau somewhere in `$PATH` and mark it as an executable. Create a directory in `~` named `.oiseau` and fill in a configuration file named `config`. You may now run oiseau as a daemon by simply running `oiseau` in your terminal. You may start oiseau from your `.xinitrc`.

License
-------

    Copyright (c) 2014, Berk Özbalcı
    All rights reserved.
    
    Redistribution and use in source and binary forms, with or without modification,
    are permitted provided that the following conditions are met:
    
    * Redistributions of source code must retain the above copyright notice, this
      list of conditions and the following disclaimer.
    
    * Redistributions in binary form must reproduce the above copyright notice, this
      list of conditions and the following disclaimer in the documentation and/or
      other materials provided with the distribution.
    
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
    ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

[lfm]: http://www.last.fm
[py27-mpd2]: https://github.com/Mic92/python-mpd2
[pylast]: https://code.google.com/p/pylast/
