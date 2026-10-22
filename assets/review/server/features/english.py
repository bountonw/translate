"""English: shows the English source beside the translation.

When english.on is on for a reader, GET /api/chapter sends each paragraph's
English ("en") and its ETag ends in ".en"; otherwise it sends no English.
/api/me carries the setting as features.english.on. The setting is on when
the reader's own setting or that of any of the reader's groups that is
switched on turns it on. review.py sets it with `english NAME on`, `group
english G on`, or the general `feature NAME english on`.
"""
NAME = "english"
SETTINGS = {"on": {"type": "bool", "default": False, "help": "show the English source beside the translation"}}
ROUTES = []
MIGRATIONS = []
