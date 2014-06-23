========
L'oiseau
========

A `Last.fm <http://www.last.fm/>`_ scrobbler for Music Player Daemon, written in Python.

Features
========

* Scrobbling (obviously)

* Updates "Now Playing" on Last.fm when it can

* No duplicate scrobbles (almost guaranteed)

* Waits for a portion of the song to be finished before scrobbling

* Can set "scrobble after N tracks"

* Can cache tracks for later scrobbling

* Configuration file

* Run as a daemon

Installation
============

**NOTE:** You can try *oiseau* without installing it, by running the command::

    $ python oiseau.py -f <config_file>

where *config_file* is the location of your Oiseau configuration file.

Getting the latest source code
------------------------------

If you would like to use the latest source code, you can grab a copy of the development version from Git by running the command::

    $ git clone git://github.com/berkoz/oiseau.git

Installing from source
----------------------

To install *oiseau* from source, simply run the command::

    $ python setup.py install

You can also use the *--help* switch on *setup.py* for a complete list of commands and their options.

After installing, you must fill out a configuration file. An example has been provided in the distribution. The recommended (and the default) configuration file locations are one of the following:

1. :code:`$HOME/.oiseau/config`

2. :code:`/usr/local/etc/oiseau.conf`

Usage
=====

::

    usage: oiseau [options]
    
    Last.fm scrobbler for the Music Player Daemon
    
    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -f CFGFILE            configuration file location
      -i PIDFILE            pid file location
      -l LOGFILE            log file location
      -k                    kill the running oiseau daemon
      --log {debug,info,warning,error,critical}
                            logging level

Command line arguments will always take precedence over configuration options.

Requirements
============

* Tested on Python 2.7.6, will not work in Python 3.x

* Requires MPD >= 0.15, tested on MPD 0.18.11

* `python-mpd <https://github.com/Mic92/python-mpd2>`_ >= 0.5.3

* `pylast <https://code.google.com/p/pylast/>`_  0.5.11
