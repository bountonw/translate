"""Tests for the SSH route: review.py reaches the live site only through an SSH tunnel it opens itself.

This machine cannot reach the droplet, so a stand-in named ssh goes first on PATH. It records its arguments,
listens on the Unix socket that -L names (or the port, where this system lets no program make a Unix socket),
and passes each connection on to the port after it, where a dev server of the test runs, as ssh -L would pass it
to waitress on the droplet."""
import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from helpers import sample_chapter

import review
from server import dev
from server.app import App

STAND_IN = r'''#!/usr/bin/env python3
"""A stand-in for ssh -N -L NEAR:127.0.0.1:API ... HOST: it forwards NEAR to API on this machine. NEAR is a Unix
socket's path, or 127.0.0.1:PORT where the system lets no program make a Unix socket (review.py, Tunnel). With
FAKE_SSH_DELAY it waits that many seconds first, as ssh does while it asks for a passphrase. With
FAKE_SSH_UNIX_OVER_TCP it serves a Unix socket's path on a port of 127.0.0.1 instead and writes that port to
PATH.port, for a test whose own process stands in for the Unix socket."""
import json, os, socket, sys, threading, time
args = sys.argv[1:]
log = os.environ["FAKE_SSH_LOG"]
runs = sum(1 for _ in open(log)) if os.path.exists(log) else 0
with open(log, "a") as f:
    f.write(json.dumps({"args": args, "pid": os.getpid()}) + "\n")
mode = os.environ.get("FAKE_SSH_MODE", "ok")
if mode == "deny":
    sys.stderr.write("tester@droplet.example: Permission denied (publickey).\n")
    sys.exit(255)
time.sleep(float(os.environ.get("FAKE_SSH_DELAY") or 0))
local = args[args.index("-L") + 1]
near, rhost, rport = local.rsplit(":", 2)
if near.startswith("/"):
    if os.environ.get("FAKE_SSH_UNIX_OVER_TCP"):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        with open(near + ".port", "w") as f:
            f.write(str(server.getsockname()[1]))
    else:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(near)
else:
    lhost, lport = near.rsplit(":", 1)
    if mode == "busy-once" and runs == 0:
        sys.stderr.write(f"bind [{lhost}]:{lport}: Address already in use\nchannel_setup_fwd_listener_tcpip: cannot listen to port: {lport}\nCould not request local forwarding.\n")
        sys.exit(255)
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((lhost, int(lport)))
server.listen(16)

def pipe(a, b):
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

def handle(client):
    try:
        upstream = socket.create_connection((rhost, int(rport)))
    except OSError:
        client.close()
        return
    threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
    pipe(upstream, client)

while True:
    c, _ = server.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
'''


def gone(pid):
    """True when the process pid has ended (or is a zombie no one waits for)."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().split(") ", 1)[1].startswith("Z")
    except OSError:
        return True


class Tunnel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.data = root / "data"
        code, out, err = cls.run_cli([], "setup", "--data", str(cls.data), "--public-url", "https://review.example.org")
        assert code == 0, err
        cls.app = App(cls.data)
        cls.httpd = dev.make(cls.app, root, 0, quiet=True)
        cls.api_port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.bin = root / "bin"
        cls.bin.mkdir()
        ssh = cls.bin / "ssh"
        ssh.write_text(STAND_IN.replace("#!/usr/bin/env python3", f"#!{sys.executable}", 1))
        ssh.chmod(ssh.stat().st_mode | stat.S_IXUSR)
        cls.log = root / "ssh.log"
        cls.target = f"ssh://tester@droplet.example?api_port={cls.api_port}"
        # The live site's token folder: the token and the file server that names its SSH target.
        cls.conf = root / "config-review"
        cls.conf.mkdir()
        (cls.conf / "admin-token").write_text((cls.data / "admin-token").read_text())
        (cls.conf / "server").write_text(cls.target + "\n")
        review.Client(f"http://127.0.0.1:{cls.api_port}", cls.data / "admin-token").call(
            "PUT", "/api/admin/chapters/SC/SC01", sample_chapter(1))

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    @staticmethod
    def run_cli(env, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, dict(env)), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = review.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def ssh_env(self, mode="ok"):
        if self.log.exists():
            self.log.unlink()
        return {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "FAKE_SSH_LOG": str(self.log),
                "FAKE_SSH_MODE": mode}

    def runs(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_a_command_goes_through_the_tunnel_and_closes_it(self):
        code, out, err = self.run_cli(self.ssh_env(), "--token-file", str(self.conf / "admin-token"), "chapters")
        self.assertEqual(code, 0, err)
        self.assertIn(f"Server: {self.target}", err)
        self.assertIn("SC01  published  3 paragraphs", out)
        (run,) = self.runs()
        args = run["args"]
        self.assertEqual(args[0], "-N")
        self.assertIn("ExitOnForwardFailure=yes", args)
        local = args[args.index("-L") + 1]
        if review.Tunnel.unix_sockets():
            self.assertRegex(local, rf"^/.+/api\.sock:127\.0\.0\.1:{self.api_port}$")
            # The socket's private folder is gone with the tunnel.
            self.assertFalse(Path(local.rsplit(":", 2)[0]).parent.exists())
        else:
            self.assertRegex(local, rf"^127\.0\.0\.1:\d+:127\.0\.0\.1:{self.api_port}$")
        self.assertEqual(args[-2:], ["--", "tester@droplet.example"])
        for _ in range(100):
            if gone(run["pid"]):
                break
            time.sleep(0.02)
        self.assertTrue(gone(run["pid"]), "the tunnel stays open after the command")

    def test_no_other_program_can_take_the_tunnel_before_ssh_opens_it(self):
        """While ssh still asks for a passphrase, its forward does not exist yet. The near end is a Unix socket in
        a new folder of mode 700, so no program can listen there first, as one could on a free port. Where this
        system lets no program make a Unix socket, as in a sandbox, the test stands in for it: review.py's
        connection to the socket's path goes to the port that the stand-in for ssh writes beside that path."""
        unix = review.Tunnel.unix_sockets()
        real = review.Tunnel.connect

        def connect(near, timeout=None):
            if unix or not isinstance(near, Path):
                return real(near, timeout)
            try:
                port = int(Path(str(near) + ".port").read_text())
            except (OSError, ValueError):
                raise FileNotFoundError(str(near))
            return real(port, timeout)

        seen = {}
        start = review.Tunnel.start

        def watch(tunnel):
            near = start(tunnel)
            seen.update(near=near, mode=stat.S_IMODE(tunnel.folder.stat().st_mode))
            return near

        env = dict(self.ssh_env(), FAKE_SSH_DELAY="0.5", FAKE_SSH_UNIX_OVER_TCP="" if unix else "1")
        with mock.patch.object(review.Tunnel, "connect", staticmethod(connect)), \
                mock.patch.object(review.Tunnel, "unix_sockets", staticmethod(lambda: True)), \
                mock.patch.object(review.Tunnel, "start", watch):
            code, out, err = self.run_cli(env, "--token-file", str(self.conf / "admin-token"), "chapters")
        self.assertEqual(code, 0, err)
        self.assertIn("SC01  published", out)
        self.assertEqual((seen["near"].name, seen["mode"]), ("api.sock", 0o700))
        self.assertFalse(seen["near"].parent.exists())

    def test_a_port_taken_meanwhile_is_tried_again(self):
        """Where the near end is a port: a port another program took before ssh is given up for another."""
        with mock.patch.object(review.Tunnel, "unix_sockets", staticmethod(lambda: False)):
            code, out, err = self.run_cli(self.ssh_env("busy-once"), "--token-file", str(self.conf / "admin-token"),
                                          "chapters")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.runs()), 2)

    def test_the_export_records_the_ssh_target_and_goes_to_the_live_folder(self):
        client = review.Client(self.target, self.conf / "admin-token")
        self.assertEqual(client.export_dir(), review.PROD_EXPORT)
        out = Path(self.tmp.name) / "export" / "one.json"
        code, _, err = self.run_cli(self.ssh_env(), "--token-file", str(self.conf / "admin-token"), "export",
                                    "--out", str(out))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out.read_text())["server"], self.target)

    def test_ssh_options_and_port(self):
        t = review.Tunnel("ssh://translator@review.laoegw.com:2222")
        self.assertEqual(t.api_port, 8087)
        cmd = t.command(Path("/run/x/api.sock"))
        self.assertEqual(cmd[0:2], ["ssh", "-N"])
        self.assertEqual(cmd[cmd.index("-L") + 1], "/run/x/api.sock:127.0.0.1:8087")
        self.assertEqual(t.command(40001)[cmd.index("-L") + 1], "127.0.0.1:40001:127.0.0.1:8087")
        self.assertEqual(cmd[cmd.index("-p") + 1], "2222")
        self.assertEqual(cmd[-2:], ["--", "translator@review.laoegw.com"])
        self.assertEqual(review.Tunnel("ssh://droplet").dest, "droplet")
        for bad in ("ssh://", "ssh://host/path", "ssh://a:b@host", "ssh://host?other=1", "ssh://-oProxyCommand=x",
                    "ssh://-oProxyCommand", "ssh://-l@host", "ssh://host?api_port=x"):
            with self.assertRaises(review.CLIError, msg=bad):
                review.Tunnel(bad)

    def test_ssh_refusing_stops_with_its_message(self):
        code, _, err = self.run_cli(self.ssh_env("deny"), "--token-file", str(self.conf / "admin-token"), "chapters")
        self.assertEqual(code, 1)
        self.assertIn("Cannot open the SSH tunnel to tester@droplet.example: tester@droplet.example: Permission "
                      "denied (publickey).", err)
        self.assertIn("ssh tester@droplet.example true", err)
        self.assertNotIn("Traceback", err)

    def test_the_api_down_behind_the_tunnel(self):
        target = "ssh://tester@droplet.example?api_port=1"
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "admin-token").write_text("x" * 43)
            (Path(folder) / "server").write_text(target)
            code, _, err = self.run_cli(self.ssh_env(), "--token-file", str(Path(folder) / "admin-token"), "chapters")
        self.assertEqual(code, 1)
        self.assertIn("the site's API did not answer", err)
        self.assertIn("sudo systemctl status review", err)

    def test_the_live_site_is_never_named_by_https(self):
        code, _, err = self.run_cli({}, "--server", "https://review.laoegw.com", "--token-file",
                                    str(self.data / "admin-token"), "chapters")
        self.assertEqual(code, 1)
        self.assertIn("only through SSH", err)
        # The token's own server file names the SSH target; another address with that token is refused.
        code, _, err = self.run_cli(self.ssh_env(), "--server", f"http://127.0.0.1:{self.api_port}", "--token-file",
                                    str(self.conf / "admin-token"), "chapters")
        self.assertEqual(code, 1)
        self.assertIn(f"belongs to {self.target}", err)

    def test_apache_traffic_never_reaches_the_admin_routes(self):
        """Apache marks what it passes on; the API refuses a marked admin request even with the right token."""
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{self.api_port}/api/admin/chapters", headers={
            "Authorization": "Bearer " + (self.data / "admin-token").read_text().strip(), "X-Review-Proxy": "1"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with self.assertRaises(urllib.error.HTTPError) as e:
            opener.open(req, timeout=10)
        with e.exception as r:
            self.assertEqual((r.code, json.loads(r.read())["error"]), (403, "admin_local_only"))


if __name__ == "__main__":
    unittest.main()
