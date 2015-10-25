import re
from config import cfg

flairs_dump = open("flairs.txt").readlines()
flairs = []
re_css = re.compile("\\.flair-(\\w+) \{")
user = "TheHHHRobot"
subject = "flair"
tpl = "* [%s](http://www.reddit.com/message/compose/?to=%s&subject=%s&message=%s)"

for x in flairs_dump:
    match = re_css.match(x)
    if match is not None:
        flairs.append(match.groups()[0])

for x in flairs:
    print(tpl % (x, user, subject x))
