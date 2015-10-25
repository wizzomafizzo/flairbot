#!/usr/bin/env python3

"""Reddit bot for updating user flairs via PM requests"""

import sys
import re
import os
import time
import logging
import logging.handlers

import praw
import OAuth2Util

from config import cfg


def setup_logging():
    """Configure logging module for rotating logs and console output"""
    rotate_cfg = {
        "filename": cfg["log_file"],
        "maxBytes": 1024*1000,
        "backupCount": 5
    }
    rotate_fmt = "%(asctime)s %(levelname)-8s %(message)s"
    console_fmt = "%(levelname)-8s %(message)s"

    if cfg["debug"]:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logger = logging.getLogger()
    logger.setLevel(level)

    rotate = logging.handlers.RotatingFileHandler(**rotate_cfg)
    rotate.setFormatter(logging.Formatter(rotate_fmt))
    logger.addHandler(rotate)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(console_fmt))
    logger.addHandler(console)

def parse_wiki_flairs(content):
    regex = re.compile(cfg["wiki_format"])
    matches = []

    for line in content.splitlines():
        match = regex.match(line)
        if match is not None:
            flair = match.groups()
            matches.append(flair[0])

    return matches


class FlairBot:
    def __init__(self):
        user_agent = cfg["user_agent"] % (cfg["version"],
                                          cfg["subreddit"])
        self.r = praw.Reddit(user_agent=user_agent)
        self.o = OAuth2Util.OAuth2Util(self.r)
        self.processed = 0
        self.flairs = []

        self.login()

    def login(self):
        """Start a new reddit session"""
        logging.info("Logging in...")
        try:
            self.o.refresh()
        except:
            logging.exception("Login failed")
            sys.exit(1)

    def get_requests(self):
        """Fetch and return all new PMs matching configured subject"""
        logging.info("Fetching new messages...")
        pending = []

        try:
            msgs = self.r.get_unread(limit=None)
        except:
            logging.exception("Failed to get new messages")
            return

        for msg in msgs:
            logging.debug(msg)
            if str(msg.subject) == cfg["subject"]:
                pending.append(msg)
            if not cfg["limit_read"]:
                msg.mark_as_read()

        pending.reverse()
        logging.info("Got %i new requests", len(pending))
        return pending

    def process_request(self, subreddit, msg):
        """Read flair request message and set if possible"""
        user = str(msg.author)
        flair = str(msg.body)

        if user in cfg["blacklist"]:
            logging.warning("Skipping blacklisted user: %s", user)
            return

        if flair in self.flairs:
            try:
                subreddit.set_flair(user, "", flair)
            except:
                logging.exception("Error setting flair to %s for %s",
                                  flair, user)
                return
            self.processed += 1
            logging.info("Flair changed to %s for %s", flair, user)
            try:
                self.r.send_message(user,
                                    cfg["msg_subject"],
                                    cfg["msg_success"] % (flair))
            except:
                logging.exception("Error messaging user")
        else:
            logging.warning("Flair %s requested by %s doesn't exist",
                            flair, user)
            wiki = "https://www.reddit.com/r/%s/wiki/%s" % (cfg["subreddit"],
                                                            cfg["wiki_page"])
            try:
                self.r.send_message(user,
                                    cfg["msg_subject"],
                                    cfg["msg_failure"] % (flair, wiki))
            except:
                logging.exception("Error messaging user")

        if cfg["limit_read"]:
            msg.mark_as_read()

    def get_wiki_page(self, subreddit):
        logging.info("Fetching wiki page...")
        if not os.path.exists(cfg["cache_file"]):
            logging.warning("No cache file found")
            modified = 0
        else:
            stat = os.stat(cfg["cache_file"])
            modified = int(stat.st_mtime)

        now = int(time.time())

        if modified > 0 and now - modified < cfg["cache_time"]:
            cache = open(cfg["cache_file"], "r")
            logging.debug("Using valid cache")
            wiki_page = cache.read()
            cache.close()
            return wiki_page

        try:
            logging.debug("Updating cache")
            wiki_page = subreddit.get_wiki_page(cfg["wiki_page"]).content_md
        except (praw.errors.NotFound):
            logging.error("Wiki page %s doesn't exist", cfg["wiki_page"])
            return

        cache = open(cfg["cache_file"], "w")
        logging.debug("Writing cache")
        cache.write(wiki_page)
        cache.close()
        return wiki_page

    def run(self):
        """Process all new flair requests"""
        try:
            requests = self.get_requests()
        except (praw.errors.HTTPException):
            logging.error("OAuth access is invalid")
            return

        subreddit = self.r.get_subreddit(cfg["subreddit"])
        wiki_page = self.get_wiki_page(subreddit)
        if wiki_page is None:
            return

        self.flairs = parse_wiki_flairs(wiki_page)
        logging.debug(self.flairs)

        if requests is None:
            logging.info("No new messages to process")
            return

        for msg in requests:
            self.process_request(subreddit, msg)


setup_logging()


if __name__ == "__main__":
    flair_bot = FlairBot()
    logging.info("Starting new run...")
    flair_bot.run()
    logging.info("Run complete! Processed %i requests.",
                 flair_bot.processed)
