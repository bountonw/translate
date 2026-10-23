# Putting the proofreading site on the droplet

These steps put the site on the DigitalOcean droplet that already serves the Lao GC website with Apache 2.4 on Debian 13 (trixie). The site gets its own host name, review.laoegw.com. If you choose another name, replace review.laoegw.com everywhere below and on the ServerName line of deploy/review-apache.conf.

In the commands, `USER@DROPLET` is how you log in to the droplet with ssh, as in `root@203.0.113.7`, and `USER` alone is that login name. Commands marked "on your machine" run from the folder that holds review.py (in the repository: `assets/review/`). Every other command runs on the droplet. If you log in as root, leave out `sudo`.

The finished layout on the droplet:

| Path | What it holds | Owner |
|---|---|---|
| /srv/review/app | the code: review.py, server/, parsers/, books.json, web/, deploy/ | root, readable by all |
| /srv/review/app.prev | the code before the last update, for rolling back | root |
| /var/lib/review | the database, the admin token's hash, config.json, backups/ | review, private (0700) |
| /etc/systemd/system/review.service | runs the API on 127.0.0.1:8087 | root |
| /etc/apache2/sites-available/review.conf | the http site; it includes /srv/review/app/deploy/review-site.conf | root |
| /etc/apache2/sites-available/review-le-ssl.conf | the https site, written by certbot in step 8; it includes the same file | root |

## 1. Add the DNS record

At the company that holds the DNS for laoegw.com (in DigitalOcean: Networking, Domains, laoegw.com), add one record:

| Type | Hostname | Value | TTL |
|---|---|---|---|
| A | review | the droplet's IPv4 address, the same one laoegw.com uses | 3600 |

If laoegw.com also has an AAAA record, add an AAAA record for review with the droplet's IPv6 address. Check the record on your machine; it prints the droplet's address once the record is live:

    getent hosts review.laoegw.com

## 2. Install the packages

    sudo apt update
    sudo apt install python3-waitress sqlite3 rsync certbot python3-certbot-apache

python3-waitress runs the API. sqlite3 lets you look inside the database. certbot gets the HTTPS certificate.

## 3. Make the system user and the folders

    sudo adduser --system --group --home /nonexistent --no-create-home review
    sudo install -d -o root -g root -m 0755 /srv/review /srv/review/app
    sudo install -d -o review -g review -m 0700 /var/lib/review

## 4. Copy the code

On your machine:

    rsync -a --delete --exclude tests/ --exclude __pycache__/ ./ USER@DROPLET:review-app/

This puts the code in review-app/ in your home folder on the droplet. On the droplet:

    sudo rsync -a --delete ~/review-app/ /srv/review/app/
    sudo chown -R root:root /srv/review/app
    sudo chmod -R u=rwX,go=rX /srv/review/app

## 5. Create the database and the admin token

    sudo -u review python3 /srv/review/app/review.py setup --data /var/lib/review --public-url https://review.laoegw.com

This prints the path of the admin token file, /var/lib/review/admin-token. Show the token:

    sudo cat /var/lib/review/admin-token

On your machine, save it in a private folder outside ~/claude-sandbox, so that no Claude session can read it. Paste the token, press Enter, then Ctrl-D:

    install -d -m 0700 ~/.config/review
    (umask 077; cat > ~/.config/review/admin-token)

Then tie the token to its server. review.py reads this file whenever it uses that token: it talks to that address when no server is named, and refuses any other, so the token never goes to another address, such as a program listening on port 8087 of your machine. The address is an SSH one: for each command review.py opens an SSH tunnel to the droplet, sends the token through it to the API on the droplet's own 127.0.0.1, and closes the tunnel, so the token never crosses the internet. Write your own login name in place of USER:

    echo ssh://USER@review.laoegw.com > ~/.config/review/server

`ssh USER@review.laoegw.com true` must work in a terminal on your machine, with your key, as it does for the commands in these steps. If you log in through a Host entry of ~/.ssh/config, write `ssh://` and that Host's name instead. If the droplet's ssh listens on another port, add it, as `ssh://USER@review.laoegw.com:2222`.

Back on the droplet, delete the plain token. The server keeps only its hash.

    sudo rm /var/lib/review/admin-token

## 6. Start the API

    sudo cp /srv/review/app/deploy/review.service /srv/review/app/deploy/review-backup.service /srv/review/app/deploy/review-backup.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now review.service review-backup.timer
    curl -s --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:8087/api/health

The last command prints `{"ok":true}`. If it does not, read the log with `sudo journalctl -u review -n 50`. If the log shows "Bad system call", delete the line `SystemCallFilter=~@privileged @resources` from /etc/systemd/system/review.service, then run `sudo systemctl daemon-reload` and `sudo systemctl restart review`. The same line in review-backup.service is removed the same way if `sudo journalctl -u review-backup -n 50` shows that error.

## 7. Turn on the Apache site

    sudo cp /srv/review/app/deploy/review-apache.conf /etc/apache2/sites-available/review.conf
    sudo a2enmod proxy proxy_http headers deflate ssl rewrite http2
    sudo a2ensite review
    sudo apache2ctl configtest
    sudo systemctl reload apache2
    curl -s http://review.laoegw.com/api/health

configtest prints "Syntax OK". The last command prints `{"ok":true}`. Apache refuses the admin routes from the internet; this command prints 403:

    curl -s -o /dev/null -w '%{http_code}\n' http://review.laoegw.com/api/admin/chapters

## 8. Turn on HTTPS

    sudo certbot --apache -d review.laoegw.com

When certbot asks, choose to redirect http to https. certbot writes /etc/apache2/sites-available/review-le-ssl.conf with the same Include line, adds the redirect to review.conf, and renews the certificate by itself through certbot.timer. Check both:

    curl -s https://review.laoegw.com/api/health
    systemctl list-timers certbot.timer

From now on, never copy review-apache.conf to the droplet again: that would remove the redirect. Every setting of the site is in deploy/review-site.conf, which both sites include.

## 9. Publish the chapters and invite yourself

You run every server command yourself, on your machine. Claude never holds the production admin token; it reads only the export files. Point review.py at the site's token once per terminal; the file ~/.config/review/server from step 5 gives the address:

    export REVIEW_TOKEN_FILE=~/.config/review/admin-token

Every server command prints `Server: ssh://USER@review.laoegw.com` first, so you can see which site it acted on. Check the SSH route once: the first command lists the chapters through the tunnel (none yet), and the second prints `allowtcpforwarding yes` on the droplet. If the first fails, it names the reason ssh gave.

    python3 review.py chapters
    ssh USER@DROPLET 'sudo sshd -T | grep -i allowtcpforwarding'

Then:

    python3 review.py publish SC 01-08
    python3 review.py invite "Translator" --grant SC01-08 --english

invite prints the reader's link once. Open it on your phone.

To invite many readers, put them in a CSV file (README.md, "Inviting many readers") and run:

    python3 review.py invite --from readers.csv

The links go to a new file of mode 600 in ~/.config/review/, beside the admin token, and the command prints only that file's path and the count. Send each reader their own link, then delete the file. Groups (`group create`, `group add`, `group off`) open and close chapters for many readers at once; README.md lists the commands.

To hand the comments to Claude, run `python3 review.py export`. It writes the comments new or changed since the last export, and `export --all` writes every comment. The files go to ~/claude-sandbox/review-prod/export/, where Claude can read them. Exports from the dev server go to ~/claude-sandbox/review-dev/export/ instead.

Each time you open SC for a new review, start a round, so that readers see only the comments of that round: `python3 review.py round start SC NAME`. A link works on the first two devices that open it; `python3 review.py devices` lists a further device that waits for your approval, and `python3 review.py device approve NUMBER` lets it in.

The admin page does all of this in the browser. It opens the SSH tunnel once and keeps it open until you stop it with Ctrl-C:

    python3 review.py admin

The limits on what readers write, and the number of devices a link works on (README.md, "Limits"), are settings. To change one, add it to /var/lib/review/config.json, as `"limits": {"comments_per_day": 1000}`, and restart the API with `sudo systemctl restart review`. If the API does not start, `sudo journalctl -u review -n 50` names the setting it refused.

## Daily backup

review-backup.timer copies the database at about 03:30 each day to /var/lib/review/backups/review-YYYY-MM-DD-HHMMSS.sqlite3, named with the UTC date and time, so no backup is ever written over, not even two on one day. Copies older than 14 days are deleted, but the newest 14 always stay. To make one now and list them, newest first:

    sudo systemctl start review-backup
    sudo ls -lt /var/lib/review/backups/

Those copies are lost if the droplet is lost. Once a week, on your machine, make a fresh backup and copy home the newest one:

    mkdir -p ~/claude-sandbox/review-prod
    ssh USER@DROPLET 'sudo -n systemctl start review-backup && sudo -n sh -c "cat \"\$(ls -t /var/lib/review/backups/review-*.sqlite3 | head -n 1)\""' > ~/claude-sandbox/review-prod/latest.part && mv ~/claude-sandbox/review-prod/latest.part ~/claude-sandbox/review-prod/review-$(date -u +%F).sqlite3 && sqlite3 ~/claude-sandbox/review-prod/review-$(date -u +%F).sqlite3 "PRAGMA integrity_check"

The command ends by printing `ok`. Any other output, or an error such as "a password is required", means the copy failed and no dated file was written; log in as root for this command, or allow your droplet user to run sudo without a password. DigitalOcean's paid droplet backups are a second copy you can turn on in the droplet's Backups tab.

## Updating the code

On your machine:

    rsync -a --delete --exclude tests/ --exclude __pycache__/ ./ USER@DROPLET:review-app/

On the droplet:

    sudo systemctl start review-backup
    sudo rm -rf /srv/review/app.prev
    sudo cp -a /srv/review/app /srv/review/app.prev
    sudo rsync -a --delete ~/review-app/ /srv/review/app/
    sudo chown -R root:root /srv/review/app
    sudo chmod -R u=rwX,go=rX /srv/review/app
    sudo systemctl restart review
    curl -s --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:8087/api/health

The restart applies any change to the database that the new code brings, after the backup that the first command took. Readers keep their links and their comments through an update. A change to web/ alone needs no restart, except a change to web/languages.json, which the server reads when it starts.

The update that adds groups brings database version 3 and a change to deploy/review-site.conf (admin requests may now carry up to 4.5 MiB, for hundreds of readers at once). After it, run the Apache reload below. Code from before that update cannot open a version 3 database, so rolling back past it needs the backup as well, as "Rolling back" says.

The update that adds each book's title in its own language brings database version 4, a new column that the code before it still opens. It also changes deploy/review-site.conf (Apache refuses an admin request without a bearer token before reading its body, and stops using an idle connection to waitress after 20 s), deploy/review.service (MALLOC_ARENA_MAX=2, which keeps the API near 110 MB after large exports instead of 260 MB) and deploy/review-backup.service (backups by age). After it, run all three sets of commands below.

The update that adds the SSH route brings database version 5, which keeps every published version of a chapter; code of version 4 still opens it. It changes deploy/review-site.conf: Apache refuses /api/admin/ from the internet and marks what it passes on to the API. After it, write the SSH address into ~/.config/review/server as in step 5, run the Apache reload below, and check the route as in step 9. It replaces the admin-request settings of the two updates above.

The update that adds review rounds and the device count brings database version 6, which gives the fields that hold the translation's text neutral names. Code of version 5 cannot open it, so rolling back past it needs the backup that the update takes first, as "Rolling back" says. A config.json that names the retired limit `comments` starts as before. The update changes no file of deploy/. Readers keep their links; each link then works on the first two devices that open it after the update, and a third waits for your approval (`review.py devices`).

The update that keeps two readers from sharing a name brings database version 7, which records the client_id of each comment deleted; code of version 6 still opens it. From this update on, the server refuses to start on a database of a version newer than its own code, and its journal names the backup to put back. The update changes no file of deploy/. Commands to the live site now reach the API through a Unix socket in a private folder, which needs no change on the droplet.

To check that the site answers quickly, run this on your machine. It prints the seconds the health check took, which should be well under one second; a slower answer at a quiet time means something to look into, with `sudo journalctl -u review -n 50`.

    curl -s -o /dev/null -w '%{time_total}\n' https://review.laoegw.com/api/health

The log does not hold waitress's line "Task queue depth is N", which it writes whenever a request waits a moment for a thread: at normal load that is thousands of lines an hour, which says nothing about speed and could crowd an error out of the journal.

If deploy/review-site.conf changed:

    sudo apache2ctl configtest && sudo systemctl reload apache2

If deploy/review.service changed:

    sudo cp /srv/review/app/deploy/review.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart review

If deploy/review-backup.service or deploy/review-backup.timer changed:

    sudo cp /srv/review/app/deploy/review-backup.service /srv/review/app/deploy/review-backup.timer /etc/systemd/system/ && sudo systemctl daemon-reload

## Rolling back

To go back to the code before the last update:

    sudo rsync -a --delete /srv/review/app.prev/ /srv/review/app/
    sudo systemctl restart review

Going back past the update that brings database version 3, or the one that brings version 6, always needs the backup taken before that update as well, as below: code older than those updates cannot read the database they made. The health check of "Updating the code" still answers ok on such a database while every reader's request fails, so after a rollback check the site with this command on your machine, which must list the chapters:

    python3 review.py chapters

Code from the version 7 update on stops at its start on a database newer than its own, and `sudo journalctl -u review -n 20` then names the backup to put back.

To go back to a database backup, which loses every comment made after that backup, first list the backups, newest first. Each name holds the UTC date and time it was taken. After an update, the one you want is the newest taken before the update, which the update's first command made:

    sudo ls -lt /var/lib/review/backups/

Then, with that file's name in place of review-YYYY-MM-DD-HHMMSS.sqlite3:

    sudo systemctl stop review
    sudo -u review mv /var/lib/review/review.sqlite3 /var/lib/review/review.sqlite3.replaced
    sudo -u review rm -f /var/lib/review/review.sqlite3-wal /var/lib/review/review.sqlite3-shm
    sudo -u review cp /var/lib/review/backups/review-YYYY-MM-DD-HHMMSS.sqlite3 /var/lib/review/review.sqlite3
    sudo systemctl start review

## Turning the site off

    sudo a2dissite review review-le-ssl
    sudo systemctl reload apache2
    sudo systemctl disable --now review.service review-backup.timer

The data stays in /var/lib/review. To turn the site back on:

    sudo systemctl enable --now review.service review-backup.timer
    sudo a2ensite review review-le-ssl
    sudo systemctl reload apache2

## What is secret

The code holds no secrets, so it can sit in the repository and on GitHub. The secrets are the admin token, kept only in ~/.config/review/admin-token on your machine beside the file server that ties it to the site and travels only inside SSH, and the reader links, which invite prints once and invite --from and relink --group write to links files in ~/.config/review/. The server stores only SHA-256 hashes of both, in /var/lib/review. Never put /var/lib/review, a backup or the token file in the repository. If the admin token leaks, make a new one on the droplet with `sudo -u review python3 /srv/review/app/review.py setup --data /var/lib/review --new-token`, save it as in step 5, and delete the plain file again.
