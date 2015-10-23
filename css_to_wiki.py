import re
from config import cfg

flairs_dump = open("flairs.txt").readlines()
flairs = []
re_css = re.compile("\\.flair-(\\w+) \{")

for x in flairs_dump:
    match = re_css.match(x)
    if match is not None:
        flairs.append(match.groups()[0])

for x in flairs:
    print("* [%s](http://www.reddit.com/message/compose/?to=wizzo&subject=flair&message=%s)" % (x, x))
