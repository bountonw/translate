# Putting the proofreading site on the droplet

These steps put the site on the DigitalOcean droplet that already serves the Lao GC website with Apache 2.4 on Debian 13 (trixie). The site gets its own host name, review.laoegw.com. If you choose another name, replace review.laoegw.com everywhere below and on the ServerName line of deploy/review-apache.conf.

In the commands, `USER@DROPLET` is how you log in to the droplet with ssh, as in `root@203.0.113.7`. Commands marked "on your machine" run from the folder that holds review.py (in the repository: `assets/review/`). Every other command runs on the droplet. If you log in as root, leave out `sudo`.

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
    sudo a2enmod proxy proxy_http headers deflate ssl rewrite
    sudo a2ensite review
    sudo apache2ctl configtest
    sudo systemctl reload apache2
    curl -s http://review.laoegw.com/api/health

configtest prints "Syntax OK". The last command prints `{"ok":true}`.

## 8. Turn on HTTPS

    sudo certbot --apache -d review.laoegw.com

When certbot asks, choose to redirect http to https. certbot writes /etc/apache2/sites-available/review-le-ssl.conf with the same Include line, adds the redirect to review.conf, and renews the certificate by itself through certbot.timer. Check both:

    curl -s https://review.laoegw.com/api/health
    systemctl list-timers certbot.timer

From now on, never copy review-apache.conf to the droplet again: that would remove the redirect. Every setting of the site is in deploy/review-site.conf, which both sites include.

## 9. Publish the chapters and invite yourself

You run every server command yourself, on your machine. Claude never holds the production admin token; it reads only the export files. Point review.py at the site once per terminal:

    export REVIEW_SERVER=https://review.laoegw.com
    export REVIEW_TOKEN_FILE=~/.config/review/admin-token

Every server command prints `Server: https://review.laoegw.com` first, so you can see which site it acted on. Then:

    python3 review.py publish SC 01-08
    python3 review.py invite "Translator" --grant SC01-08 --english

invite prints the reader's link once. Open it on your phone.

To hand the comments to Claude, run `python3 review.py export`. The files go to ~/claude-sandbox/review-prod/export/, where Claude can read them. Exports from the dev server go to ~/claude-sandbox/review-dev/export/ instead.

## Daily backup

review-backup.timer copies the database to /var/lib/review/backups/review-YYYY-MM-DD.sqlite3 at about 03:30 each day and keeps the newest 14 copies. To make one now and list them:

    sudo systemctl start review-backup
    sudo ls -l /var/lib/review/backups/

Those copies are lost if the droplet is lost. Once a week, on your machine, make a fresh backup and copy it home:

    mkdir -p ~/claude-sandbox/review-prod
    ssh USER@DROPLET 'sudo -n systemctl start review-backup && sudo -n cat /var/lib/review/backups/review-$(date -u +%F).sqlite3' > ~/claude-sandbox/review-prod/latest.part && mv ~/claude-sandbox/review-prod/latest.part ~/claude-sandbox/review-prod/review-$(date -u +%F).sqlite3 && sqlite3 ~/claude-sandbox/review-prod/review-$(date -u +%F).sqlite3 "PRAGMA integrity_check"

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

The restart applies any change to the database that the new code brings, after the backup that the first command took. Readers keep their links and their comments through an update. A change to web/ alone needs no restart.

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

If that update changed the database and the old code fails with it, also go back to the backup taken before the update, as below.

To go back to a database backup, which loses every comment made after that backup:

    sudo systemctl stop review
    sudo -u review mv /var/lib/review/review.sqlite3 /var/lib/review/review.sqlite3.replaced
    sudo -u review rm -f /var/lib/review/review.sqlite3-wal /var/lib/review/review.sqlite3-shm
    sudo -u review cp /var/lib/review/backups/review-YYYY-MM-DD.sqlite3 /var/lib/review/review.sqlite3
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

The code holds no secrets, so it can sit in the repository and on GitHub. The secrets are the admin token, kept only in ~/.config/review/admin-token on your machine, and the reader links. The server stores only SHA-256 hashes of both, in /var/lib/review. Never put /var/lib/review, a backup or the token file in the repository. If the admin token leaks, make a new one on the droplet with `sudo -u review python3 /srv/review/app/review.py setup --data /var/lib/review --new-token`, save it as in step 5, and delete the plain file again.
