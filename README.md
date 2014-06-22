oiseau
------

Extremely hacky [Last.fm][lfm] scrobbler for MPD that I wrote for myself. Still in active development.

Features
--------

- No duplicate scrobbles
- Updates 'now playing' on Last.fm when it can
- Waits for the half of the track to be listened before submitting (except if the track is longer than 8 minutes, it only requires the first 4 minutes)
- **NEW:** Can be run as a daemon now!

TODO
----

- Introduce a configuration file
- Cache tracks for later scrobbling

Usage
-----

    usage: oiseau [options]
    
    Last.fm scrobbler for the Music Player Daemon
    
    optional arguments:
      -h, --help     show this help message and exit
      -v, --version  show version and exit
      -F             run oiseau in the foreground, rather than as a daemon
      -k             kill the running oiseau daemon
      -i PIDFILE     the location of the pid file

For connection details, open `oiseau.py` and edit the following lines:

    # -------------------------
    # Configuration
    # -------------------------
    
    LFM_USERNAME = "Your Last.fm username"
    LFM_PASSWORD = "Your Last.fm password"
    MPD_HOST     = "MPD hostname"
    MPD_PORT     = MPD port
    MPD_PASSWORD = None  | If you have a password, write it in quotation marks
    MPD_UNICODE  = True  | Use unicode on MPD
    DEBUG        = False | Speaks for itself
    
    # -------------------------
    # Here be dragons ...
    # -------------------------

Mark the file as executable, move it into somewhere in the $PATH and you're ready.

Requirements
------------

- Tested on Python 2.7.6, will not work in Python 3.x
- Requires MPD >= 0.15, tested on MPD 0.18.11
- [python-mpd2][py27-mpd2] >= 0.5.3
- [pylast][pylast] >= 0.5.11

[lfm]: http://www.last.fm
[py27-mpd2]: https://github.com/Mic92/python-mpd2
[pylast]: https://code.google.com/p/pylast/
