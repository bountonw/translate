"""The feature registry: every module in this folder whose name does not start with _ is one feature.

A feature module declares:

    NAME = "english"          # the feature's name: lower-case letters, digits and _, not a core path name
    SETTINGS = {"on": {"type": "bool", "default": False, "help": "..."}}
                              # per-reader and per-group settings, stored as NAME.setting ("english.on")
    ROUTES = []               # (method, sub, handler, auth). sub is a regular expression for the part of the
                              # path after the feature's prefix; the registry builds the path itself:
                              #   "reader"      /api/NAME/<sub>, for readers who have the feature on
                              #   "any_reader"  /api/NAME/<sub>, for every reader with a working link
                              #   "admin"       /api/admin/NAME/<sub>, with the admin token
                              #   None          /api/NAME/<sub>, open to anyone
                              # handler(app, req, *groups) returns (status, payload) like a core route
    MIGRATIONS = []           # (version, [SQL]) for the feature's own tables, named NAME_...; they run
                              # after the core migrations, and feature_schema keeps the version reached
    def me(ctx): ...          # optional: what GET /api/me carries under features.NAME; ctx has conn,
                              # reader (the database row) and settings (this feature's, without the prefix).
                              # Without it, /api/me carries the feature's settings.
    def enabled(settings): ...  # optional: whether the feature is on for a reader, from this feature's
                              # settings; without it, the feature is on when its setting "on" is true

Settings combine a reader's own value with those of the reader's groups that
are switched on. The only type is "bool", combined by "any": on when the
reader's own value or any such group's value is on; with no value at all, the
default. EXTENDING.md says how to add a feature.
"""
import importlib
import json
import pkgutil
import re

NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,30}")
TYPES = {"bool": bool}
# Where each kind of route lies: the registry builds the path, so no pattern can leave its prefix and
# no route under /api/admin/ can do without the admin token.
AUTHS = {"reader": "/api/{name}/", "any_reader": "/api/{name}/", None: "/api/{name}/",
         "admin": "/api/admin/{name}/"}
# The first path segments of the core routes (server/app.py). A feature never takes one as its name.
RESERVED = frozenset({"admin", "health", "me", "chapter", "comments", "place", "finished",
                      "chapters", "readers", "groups", "features", "export", "processed"})


class FeatureError(ValueError):
    """A feature module that declares something the registry cannot use."""


class Setting:
    def __init__(self, feature, name, spec):
        self.key = f"{feature}.{name}"
        self.type = spec.get("type")
        if self.type not in TYPES:
            raise FeatureError(f"{self.key}: the type must be one of {', '.join(TYPES)}")
        self.default = spec.get("default", False)
        self.combine = spec.get("combine", "any")
        if self.combine != "any":
            raise FeatureError(f"{self.key}: the only way to combine settings is any")
        self.help = spec.get("help", "")
        if not self.valid(self.default):
            raise FeatureError(f"{self.key}: the default is not a {self.type}")

    def valid(self, value):
        return isinstance(value, TYPES[self.type])

    def resolve(self, values):
        """The value a reader gets from their own value and their active groups' values."""
        return any(values) if values else self.default

    def describe(self):
        return {"type": self.type, "default": self.default, "combine": self.combine, "help": self.help}


def route_path(name, sub, auth):
    """The full path pattern of a feature route: the prefix of its auth, then sub inside its own group.
    sub must compile alone, so it cannot close the group and reach past the prefix."""
    prefix = AUTHS[auth].format(name=name)
    if not isinstance(sub, str) or sub.startswith("/"):
        raise FeatureError(f"{name}: a route gives only the part of its path after {prefix}, not {sub!r}")
    try:
        re.compile(sub)
    except re.error as e:
        raise FeatureError(f"{name}: the route pattern {sub!r} is not a regular expression on its own ({e})")
    return prefix + f"(?:{sub})"


class Feature:
    def __init__(self, module):
        self.module = module
        self.name = getattr(module, "NAME", None)
        if not isinstance(self.name, str) or not NAME_RE.fullmatch(self.name):
            raise FeatureError(f"{module.__name__}: NAME must be a lower-case word")
        if self.name in RESERVED:
            raise FeatureError(f"{self.name}: a feature may not take the name of a core path "
                               f"({', '.join(sorted(RESERVED))})")
        self.settings = {k: Setting(self.name, k, v) for k, v in getattr(module, "SETTINGS", {}).items()}
        self.routes = []
        for route in getattr(module, "ROUTES", []):
            if not isinstance(route, (tuple, list)) or len(route) != 4:
                raise FeatureError(f"{self.name}: each route is (method, sub, handler, auth)")
            method, sub, handler, auth = route
            if not isinstance(auth, (str, type(None))) or auth not in AUTHS or not callable(handler) \
                    or method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                raise FeatureError(f"{self.name}: the route {method} {sub} needs a method, a handler and auth "
                                   "reader, any_reader, admin or None")
            self.routes.append((method, route_path(self.name, sub, auth), handler, auth))
        self.migrations = list(getattr(module, "MIGRATIONS", []))
        self.me_hook = getattr(module, "me", None)
        self.enabled = getattr(module, "enabled", None)
        if self.enabled is not None and not callable(self.enabled):
            raise FeatureError(f"{self.name}: enabled must be a function of the feature's settings")


def load(package=__name__):
    """Every feature module in the package, sorted by name."""
    pkg = importlib.import_module(package)
    names = sorted(m.name for m in pkgutil.iter_modules(pkg.__path__) if not m.name.startswith("_"))
    return [Feature(importlib.import_module(f"{package}.{n}")) for n in names]


class Context:
    """What a feature's me() hook receives."""

    def __init__(self, conn, reader, settings):
        self.conn, self.reader, self.settings = conn, reader, settings


class Registry:
    """The features in use and their settings, keyed "feature.setting"."""

    def __init__(self, features):
        self.features = {}
        self.settings = {}
        for f in features:
            if f.name in self.features:
                raise FeatureError(f"two features are named {f.name}")
            self.features[f.name] = f
            self.settings.update({s.key: s for s in f.settings.values()})

    def check(self, values):
        """{"english.on": true} from a request, checked against the declared settings."""
        if not isinstance(values, dict):
            raise ValueError('settings must be an object such as {"english.on": true}')
        for key, value in values.items():
            s = self.settings.get(key)
            if s is None:
                raise KeyError(key)
            if not s.valid(value):
                raise ValueError(f"{key} must be {s.type}")
        return values

    def resolve(self, own, from_groups):
        """Effective settings from {key: value} of the reader and [(key, value)] of active groups."""
        out = {}
        for key, s in self.settings.items():
            values = ([own[key]] if key in own else []) + [v for k, v in from_groups if k == key]
            out[key] = s.resolve(values)
        return out

    def effective(self, conn, reader_id):
        """One reader's settings as the reader gets them."""
        own = {r[0]: json.loads(r[1]) for r in conn.execute(
            "SELECT name, value FROM reader_setting WHERE reader = ?", (reader_id,))}
        groups = [(r[0], json.loads(r[1])) for r in conn.execute(
            "SELECT s.name, s.value FROM group_member m JOIN reader_group t ON t.id = m.grp AND t.active = 1"
            " JOIN group_setting s ON s.grp = m.grp WHERE m.reader = ?", (reader_id,))]
        return self.resolve(own, groups)

    @staticmethod
    def own(name, settings):
        """One feature's settings without the prefix: {"on": true} from {"english.on": true, ...}."""
        return {k.split(".", 1)[1]: v for k, v in settings.items() if k.startswith(name + ".")}

    def is_on(self, name, settings):
        """Whether the feature is on for a reader with these effective settings: its enabled() function,
        or else its setting "on". The page decides the same way (web/core/ext.js, isOn)."""
        f = self.features[name]
        mine = self.own(name, settings)
        return bool(f.enabled(mine)) if f.enabled else mine.get("on") is True

    def me(self, conn, reader, settings):
        """features for GET /api/me: each feature's me() hook, or its settings."""
        out = {}
        for name, f in self.features.items():
            mine = self.own(name, settings)
            out[name] = f.me_hook(Context(conn, reader, mine)) if f.me_hook else mine
        return out

    def describe(self):
        return [{"name": n, "settings": {k: s.describe() for k, s in f.settings.items()},
                 "routes": [f"{m} {p} ({a or 'open'})" for m, p, _, a in f.routes]} for n, f in self.features.items()]
