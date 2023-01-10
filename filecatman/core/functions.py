import os
import shutil
import re
from filecatman.core.namespace import FCM
from filecatman.core import const
import requests


def chunksgen(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    chunkList = list()
    for i in range(0, len(lst), n):
        chunkList.append(lst[i:i + n])
    return chunkList

def createLink(filePath, linkPath, overwriteLinks=False):
    linkDir = os.path.dirname(linkPath)
    if not os.path.exists(linkDir): os.makedirs(linkDir)
    if os.path.lexists(linkPath):
        if overwriteLinks:
            os.unlink(linkPath)
            os.symlink(filePath, linkPath)
    else:
        os.symlink(filePath, linkPath)
    return True

def desktopFileExt():
    import platform
    if platform.system() in ("Windows", "Darwin"): return "url"
    return "desktop"

def _createLinuxDesktopFile(linkPath, itemName, itemSource):
    overwriteLinks = True
    linkDir = os.path.dirname(linkPath)
    if not os.path.exists(linkDir): os.makedirs(linkDir)
    if os.path.exists(linkPath):
        if overwriteLinks:
            with open(linkPath, 'w') as fp:
                fp.write("[Desktop Entry]\n")
                fp.write("Encoding=UTF-8\n")
                fp.write("Name=" + itemName + "\n")
                fp.write("Type=Link\n")
                fp.write("URL=" + itemSource + "\n")
            os.chmod(linkPath, 0o755)
    else:
        with open(linkPath, 'x') as fp:
            fp.write("[Desktop Entry]\n")
            fp.write("Encoding=UTF-8\n")
            fp.write("Name=" + itemName + "\n")
            fp.write("Type=Link\n")
            fp.write("URL=" + itemSource + "\n")
        os.chmod(linkPath, 0o755)
    return True

def _createMacDesktopFile(linkPath, itemName, itemSource):
    overwriteLinks = True
    linkDir = os.path.dirname(linkPath)
    if not os.path.exists(linkDir): os.makedirs(linkDir)
    if os.path.exists(linkPath):
        if overwriteLinks:
            with open(linkPath, 'w') as fp:
                fp.write('[InternetShortcut]\n')
                fp.write('URL=%s\n' % itemSource)
                fp.write('IconIndex=0')
            os.chmod(linkPath, 0o755)
    else:
        with open(linkPath, 'x') as fp:
            fp.write('[InternetShortcut]\n')
            fp.write('URL=%s\n' % itemSource)
            fp.write('IconIndex=0')
        os.chmod(linkPath, 0o755)
    return True

def _createWinDesktopFile(linkPath, itemName, itemSource):
    overwriteLinks = True
    linkDir = os.path.dirname(linkPath)
    if not os.path.exists(linkDir): os.makedirs(linkDir)
    if os.path.exists(linkPath):
        if overwriteLinks:
            with open(linkPath, 'w') as fp:
                fp.write('[InternetShortcut]\n')
                fp.write('URL=%s' % itemSource)
            os.chmod(linkPath, 0o755)
    else:
        with open(linkPath, 'x') as fp:
            fp.write('[InternetShortcut]\n')
            fp.write('URL=%s' % itemSource)
        os.chmod(linkPath, 0o755)
    return True

def createDesktopFile(linkPath, itemName, itemSource):
    import platform
    if platform.system() == "Windows": return _createWinDesktopFile(linkPath, itemName, itemSource)
    elif platform.system() == "Darwin": return _createMacDesktopFile(linkPath, itemName, itemSource)
    return _createLinuxDesktopFile(linkPath, itemName, itemSource)

def getPythonFileDir(): return os.path.dirname(os.path.realpath(__file__))
def getCwd(): return os.getcwd()

def getPrintColourFromName(_colour):
    from filecatman.core.printcolours import bcolours
    colour =  str(_colour).upper()
    try: bcoloursColour = getattr(bcolours, colour)
    except AttributeError: return ""
    if bcoloursColour: return bcoloursColour
    return ""

def convToBool(boolStr, fallbackBool=False):
    if isinstance(boolStr, str):
        if boolStr.lower() == "true": return True
        elif boolStr.lower() == "false": return False
        else: return fallbackBool
    elif isinstance(boolStr, bool): return boolStr
    elif isinstance(boolStr, int): return bool(boolStr)
    else: return fallbackBool

def timeStampToString(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def formatBytes(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if -1024.0 < num < 1024.0:
            return "%3.0f%s" % (num, x)
        num /= 1024.0
    return "%3.0f%s" % (num, 'TB')

def unformatBytes(size):
    if size.isnumeric(): return int(size)
    units = {"B": 1, "KB": 2 ** 10, "MB": 2 ** 20, "GB": 2 ** 30, "TB": 2 ** 40}
    size = size.upper()
    #print("parsing size ", size)
    if not re.match(r' ', size):
        size = re.sub(r'([KMGT]?B)', r' \1', size)
    number, unit = [string.strip() for string in size.split()]
    return int(float(number)*units[unit])

def getDataFilePath(dataDir, dataType, fileID=''):
    return os.path.join(dataDir, dataType, fileID)

def getTmpPath():
    import string, random, tempfile
    letters = string.ascii_lowercase + string.digits
    fileName = ''.join(random.choice(letters) for i in range(50))
    tmpDir = os.path.join(tempfile.gettempdir(), "filecatman")
    if not os.path.exists(tmpDir): os.makedirs(tmpDir)
    return os.path.join(tmpDir, fileName)

def _getUserConfigDir():
    """Returns a platform-specific root directory for user config settings."""
    if os.name == "nt":
        appdata = os.getenv("LOCALAPPDATA")
        if appdata: return appdata
        appdata = os.getenv("APPDATA")
        if appdata: return appdata
        return None
    # On non-windows, use XDG_CONFIG_HOME if set, else default to ~/.config.
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home: return xdg_config_home
    return os.path.join(os.path.expanduser("~"), ".config")

def getUserConfigDir():
    if const.PORTABLEMODE: return ""
    confDir = os.path.join(_getUserConfigDir(), "filecatman")
    if not os.path.exists(confDir): os.makedirs(confDir)
    return confDir

def getMD5FromPath(path):
    if isURL(path):
        fileDestination = getTmpPath()
        if downloadFile(path, fileDestination):
            return getMD5FromFile(fileDestination)
    elif os.path.isfile(path): return getMD5FromFile(path)
    return False

def deepCopy(data):
    import copy
    return copy.deepcopy(data)

def printProgressBar(progress, barLength=40, progressMessage="Progress", status="", enabled=True):
    import sys
    # progress = (self.itemsLinkedCount/self.totalItemsCount)
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    if enabled:
        block = int(round(barLength*progress))
        text = "\r{0}: [{1}] {2}% {3}".format(progressMessage,"#"*block + "-"*(barLength-block), round(progress*100, 2), status)
        sys.stdout.write(text)
        sys.stdout.flush()
    elif progress == 1: print(progressMessage+": Done")

def getMD5FromFile(filePath):
    import hashlib
    md5_hash = hashlib.md5()
    with open(filePath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
        return md5_hash.hexdigest()

def uploadFile(config, fileSource, fileDestination, fileType=None):
    baseFilename = os.path.basename(fileSource)
    fileName = os.path.splitext(baseFilename)[0]
    baseFileID = os.path.basename(fileDestination)
    fileID = os.path.splitext(baseFileID)[0]
    if fileType in config['itemTypes'].nounNames(FCM.IsWebpages):
            destDir = os.path.dirname(fileDestination)
            if not os.path.exists(destDir):
                os.makedirs(destDir)
            sourceDir = os.path.dirname(fileSource)
            folderSource = os.path.join(sourceDir, fileName+"_files")
            if os.path.exists(folderSource):
                folderDestination = os.path.join(destDir, fileID+"_files")
                if os.path.exists(folderDestination):
                    shutil.rmtree(folderDestination)
                shutil.copytree(folderSource, folderDestination)

            # shutil.copyfile(fileSource, fileDestination)
            shutil.copy2(fileSource, fileDestination)
    else:
        destDir = os.path.dirname(fileDestination)
        if not os.path.exists(destDir):
            os.makedirs(destDir)
        # shutil.copyfile(fileSource, fileDestination)
        shutil.copy2(fileSource, fileDestination)
    return True

def pluralize(noun):
    import re
    if re.search('[sxz]$', noun):
         return re.sub('$', 'es', noun)
    elif re.search('[^aeioudgkprt]h$', noun):
        return re.sub('$', 'es', noun)
    elif re.search('[aeiou]y$', noun):
        return re.sub('y$', 'ies', noun)
    else:
        return noun + 's'

def downloadFile(fileSource, fileDestination):
    destDir = os.path.dirname(fileDestination)
    if not os.path.exists(destDir): os.makedirs(destDir)
    headers = {'user-agent': 'Mozilla/5.0 (Linux; Android 7.0; SM-G892A Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/67.0.3396.87 Mobile Safari/537.36'}
    r = requests.get(fileSource, headers=headers)
    if r.status_code == 200:
        with open(fileDestination, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
        return True
    return False

def deleteFile(parent, filePath, folderPath=None):
    if folderPath and os.path.exists(folderPath):
        shutil.rmtree(folderPath)
    if os.path.exists(filePath):
        os.remove(filePath)
        parent.logger.debug("{} deleted.".format(filePath))
        return True
    return False


def escape(string, chars=("'", '"', '`', '$'), replacement=""):
    string = re.sub("[{}]".format(''.join(chars)), replacement, string)
    return string


def renameFolder(parent, filePath):
    try:
        os.remove(filePath)
        parent.logger.debug("{} deleted.".format(filePath))
        return True
    except BaseException as e:
        # warningMsgBox(parent, e, title="Error Deleting File")
        return False

def isURL(url):
    import re
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url)