oiseau
------

Extremely hacky [Last.fm][lfm] scrobbler for MPD that I wrote for myself (because every other scrobbler sucked).

Pros:

- Makes sure to submit each track "at most" once.
- Supports submitting the currently playing track as "Now Playing" on Last.fm

Cons:

- Scrobbles a track immediately after the song starts.
- Doesn't have arguments/configs/documents/help etc, you have to modify the source code.
- Doesn't support the album artist tag (who cares)
- Doesn't cache tracks for later scrobbling

TODO:

- Cache tracks for later scrobbling

Usage
-----

Open `oiseau.py` and edit the following lines:

    # -------------------------
    # Configuration
    # -------------------------
    
    API_KEY      = "Your API key"
    API_SECRET   = "Your API secret"
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

- Tested on Python 2.7.6
- [python-mpd2][py27-mpd2] >= 0.5.3
- [pylast][pylast] >= 0.5.11


[lfm]: http://www.last.fm
[py27-mpd2]: https://github.com/Mic92/python-mpd2
[pylast]: https://code.google.com/p/pylast/
