import os
import sys
import logging
from filecatman.core import const
from filecatman.core.objects import ColoredFormatter
from filecatman.core.functions import getUserConfigDir

levels = dict(
    info=logging.INFO,
    warning=logging.WARNING,
    error=logging.ERROR,
    none=logging.CRITICAL,
    debug=logging.DEBUG
)


def initializeLogger(level):
    logPath = os.path.join(getUserConfigDir(), "filecatman.log")

    if not level or level not in levels:
        level = "error"

    rootLogger = logging.getLogger('')
    rootLogger.setLevel(logging.DEBUG)

    console = logging.StreamHandler(stream=sys.stdout)
    if os.name == "nt":
        console.setFormatter(logging.Formatter('%(lineno)-s %(name)-s: %(levelname)-s %(message)s'))
    else:
        console.setFormatter(ColoredFormatter('%(lineno)-s %(name)-s: %(levelname)-s %(message)s'))
    console.setLevel(levels[level])
    rootLogger.addHandler(console)

    fh = logging.FileHandler(logPath, 'w')
    fh.setFormatter(logging.Formatter('[%(asctime)-s] %(lineno)s %(name)-s: %(levelname)-8s %(message)s',
                                      datefmt='%m-%d %H:%M'))
    fh.setLevel(logging.DEBUG)
    rootLogger.addHandler(fh)

logger = logging.getLogger("Filecatman")