import logging
import copy
from filecatman.core.printcolours import bcolours
from filecatman.core.namespace import FCM

class ColoredFormatter(logging.Formatter):
    LEVELCOLOR = {
        'INFO': bcolours.BOLD,
        'DEBUG': bcolours.BLUE,
        'WARNING': bcolours.WARNING,
        'ERROR': bcolours.FAIL,
        'CRITICAL': bcolours.CRITICAL,
        'ENDC': bcolours.ENDC
    }

    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)

    def format(self, record):
        record = copy.copy(record)
        levelname = record.levelname
        if levelname in self.LEVELCOLOR:
            record.levelname = "["+self.LEVELCOLOR[levelname]+levelname+self.LEVELCOLOR['ENDC']+"]"
            record.name = bcolours.HEADER+record.name+bcolours.ENDC
        return logging.Formatter.format(self, record)

class TaxonomyList:
    data = list()
    index = 0

    def __init__(self, data=None):
        if data:
            self.data = data

    def __next__(self):
        if self.index == len(self.data):
            raise StopIteration
        else:
            taxonomy = self.data[self.index]
            self.index += 1
        return taxonomy

    def __iter__(self):
        self.index = 0
        return self

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.data[item]
        elif isinstance(item, str):
            for taxonomy in self.data:
                if taxonomy.nounName == item:
                    return taxonomy
                elif taxonomy.pluralName == item:
                    return taxonomy
                elif taxonomy.tableName == item:
                    return taxonomy
                elif taxonomy.dirName == item:
                    return taxonomy

    def get(self,item):
        result = self.__getitem__(item)
        if not result: return False
        return result

    def __len__(self):
        return len(self.data)

    def append(self, typeObj):
        self.data.append(typeObj)

    def pop(self, index):
        self.data.pop(index)

    def clear(self):
        try:
            self.data.clear()
        except AttributeError:
            del self.data[:]

    def remove(self, objOrName):
        if isinstance(objOrName, Taxonomy):
            self.data.remove(objOrName)
            return True
        elif isinstance(objOrName, str):
            for taxonomy in self.data:
                if taxonomy.nounName == objOrName:
                    self.data.remove(taxonomy)
                    return True
                elif taxonomy.pluralName == objOrName:
                    self.data.remove(taxonomy)
                    return True
                elif taxonomy.tableName == objOrName:
                    self.data.remove(taxonomy)
                    return True
                elif taxonomy.dirName == objOrName:
                    self.data.remove(taxonomy)
                    return True
        return False

    def tableFromPlural(self, pluralName):
        for taxonomy in self.data:
            if taxonomy.pluralName == pluralName:
                return taxonomy.tableName
        return False

    def tableFromNoun(self, nounName):
        for taxonomy in self.data:
            if taxonomy.nounName == nounName:
                return taxonomy.tableName
        return False

    def nounFromPlural(self, pluralName):
        for taxonomy in self.data:
            if taxonomy.pluralName == pluralName:
                return taxonomy.nounName
        return False

    def nounFromTable(self, tableName):
        for taxonomy in self.data:
            if taxonomy.tableName == tableName:
                return taxonomy.nounName
        return False

    def dirFromTable(self, tableName):
        for taxonomy in self.data:
            if taxonomy.tableName == tableName:
                return taxonomy.dirName
        return False

    def dirFromNoun(self, nounName):
        for taxonomy in self.data:
            if taxonomy.nounName == nounName:
                return taxonomy.dirName
        return False

    def dirFromPlural(self, pluralName):
        for taxonomy in self.data:
            if taxonomy.pluralName == pluralName:
                return taxonomy.dirName
        return False

    def pluralFromTable(self, tableName):
        for taxonomy in self.data:
            if taxonomy.tableName == tableName:
                return taxonomy.pluralName
        return False

    def nounNames(self):
        nounList = list()
        for taxonomy in self.data:
            if taxonomy.nounName:
                nounList.append(taxonomy.nounName)
        return nounList

    def tableNames(self, flag=None):
        tableList = list()
        for taxonomy in self.data:
            if flag == FCM.OnlyDisabled:
                if taxonomy.tableName and not taxonomy.enabled:
                    tableList.append(taxonomy.tableName)
            elif flag == FCM.OnlyEnabled:
                if taxonomy.tableName and taxonomy.enabled:
                    tableList.append(taxonomy.tableName)
            elif flag == FCM.NoChildren:
                if taxonomy.tableName and not taxonomy.hasChildren:
                    tableList.append(taxonomy.tableName)
            elif flag == FCM.IsTags:
                if taxonomy.tableName and taxonomy.isTags:
                    tableList.append(taxonomy.tableName)
            elif flag == FCM.NoTags:
                if taxonomy.tableName and not taxonomy.isTags:
                    tableList.append(taxonomy.tableName)
            else:
                if taxonomy.tableName:
                    tableList.append(taxonomy.tableName)
        return tableList

    def pluralNames(self, flag=None):
        pluralList = list()
        for taxonomy in self.data:
            if flag == FCM.OnlyEnabled:
                if taxonomy.pluralName and taxonomy.enabled:
                    pluralList.append(taxonomy.pluralName)
            elif flag == FCM.NoChildren:
                if taxonomy.pluralName and not taxonomy.hasChildren:
                    pluralList.append(taxonomy.pluralName)
            elif flag == FCM.IsTags:
                if taxonomy.pluralName and taxonomy.isTags:
                    pluralList.append(taxonomy.pluralName)
            elif flag == FCM.NoTags:
                if taxonomy.pluralName and not taxonomy.isTags:
                    pluralList.append(taxonomy.pluralName)
            else:
                if taxonomy.pluralName:
                    pluralList.append(taxonomy.pluralName)
        return pluralList


class Taxonomy:
    pluralName = None
    nounName = None
    dirName = None
    tableName = None
    enabled = True
    hasChildren = True
    isTags = False
    colour = ""

    def __init__(self, data=None):
        if data:
            self.pluralName = data[0]
            self.nounName = data[1]
            self.tableName = data[2]
            self.extensions = data[3]

    def setPluralName(self, name):
        self.pluralName = name

    def setNounName(self, name):
        self.nounName = name
        if not self.dirName:
            self.dirName = name

    def setDirName(self, name):
        if name not in ("", None):
            self.dirName = name
        else:
            self.dirName = self.nounName

    def setTableName(self, name):
        self.tableName = name

    def setEnabled(self, setBool):
        if isinstance(setBool, str):
            if setBool.lower().strip() == "true":
                self.enabled = True
            else:
                self.enabled = False
        elif isinstance(setBool, bool):
            self.enabled = setBool
        elif isinstance(setBool, int):
            if setBool == 1:
                self.enabled = True
            else:
                self.enabled = False

    def setHasChildren(self, setBool):
        if isinstance(setBool, str):
            if setBool.lower().strip() == "true":
                self.hasChildren = True
            else:
                self.hasChildren = False
        elif isinstance(setBool, bool):
            self.hasChildren = setBool
        elif isinstance(setBool, int):
            if setBool == 1:
                self.hasChildren = True
            else:
                self.hasChildren = False

    def setIsTags(self, setBool):
        if isinstance(setBool, str):
            if setBool.lower().strip() == "true":
                self.isTags = True
            else:
                self.isTags = False
        elif isinstance(setBool, bool):
            self.isTags = setBool
        elif isinstance(setBool, int):
            if setBool == 1:
                self.isTags = True
            else:
                self.isTags = False

    def setColour(self, colour):
        self.colour = colour

    def printDetails(self):
        print(bcolours.HEADER+"Noun Name: "+bcolours.ENDC+self.nounName)
        print(bcolours.HEADER+"Plural Name: "+bcolours.ENDC+self.pluralName)
        print(bcolours.HEADER+"Dir Name: "+bcolours.ENDC+self.dirName)
        print(bcolours.HEADER+"Table Name: "+bcolours.ENDC+self.tableName)
        print(bcolours.HEADER+"Enabled: "+bcolours.ENDC+str(self.enabled))
        print(bcolours.HEADER+"Has Children: "+bcolours.ENDC+str(self.hasChildren))
        print(bcolours.HEADER+"Is Tags: "+bcolours.ENDC+str(self.isTags))


class ItemTypeList:
    data = list()
    index = 0

    def __init__(self, data=None):
        if data:
            self.data = data

    def __next__(self):
        if self.index == len(self.data):
            raise StopIteration
        else:
            itemType = self.data[self.index]
            self.index += 1
        return itemType

    def __iter__(self):
        self.index = 0
        return self

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.data[item]
        elif isinstance(item, str):
            for itemType in self.data:
                if itemType.nounName == item:
                    return itemType
                elif itemType.pluralName == item:
                    return itemType
                elif itemType.tableName == item:
                    return itemType
                elif itemType.dirName == item:
                    return itemType
        return False

    def get(self,item):
        result = self.__getitem__(item)
        if not result: return False
        return result

    def __len__(self):
        return len(self.data)

    def append(self, typeObj):
        self.data.append(typeObj)

    def pop(self, index):
        self.data.pop(index)

    def clear(self):
        try:
            self.data.clear()
        except AttributeError:
            del self.data[:]

    def remove(self, objOrName):
        if isinstance(objOrName, ItemType):
            self.data.remove(objOrName)
            return True
        elif isinstance(objOrName, str):
            for itemType in self.data:
                if itemType.nounName == objOrName:
                    self.data.remove(itemType)
                    return True
                elif itemType.pluralName == objOrName:
                    self.data.remove(itemType)
                    return True
                elif itemType.tableName == objOrName:
                    self.data.remove(itemType)
                    return True
                elif itemType.dirName == objOrName:
                    self.data.remove(itemType)
                    return True
        return False

    def tableFromPlural(self, pluralName):
        for itemType in self.data:
            if itemType.pluralName == pluralName:
                return itemType.tableName
        return False

    def tableFromNoun(self, nounName):
        for itemType in self.data:
            if itemType.nounName == nounName:
                return itemType.tableName
        return False

    def nounFromPlural(self, pluralName):
        for itemType in self.data:
            if itemType.pluralName == pluralName:
                return itemType.nounName
        return False

    def nounFromTable(self, tableName):
        for itemType in self.data:
            if itemType.tableName == tableName:
                return itemType.nounName
        return False

    def nounFromExtension(self, ext):
        for itemType in self.data:
            if itemType.hasExtension(ext):
                return itemType.nounName
        return False

    def dirFromTable(self, tableName):
        for itemType in self.data:
            if itemType.tableName == tableName:
                return itemType.dirName
        return False

    def dirFromNoun(self, nounName):
        for itemType in self.data:
            if itemType.nounName == nounName:
                return itemType.dirName
        return False

    def dirFromPlural(self, pluralName):
        for itemType in self.data:
            if itemType.pluralName == pluralName:
                return itemType.dirName
        return False

    def pluralFromTable(self, tableName):
        for itemType in self.data:
            if itemType.tableName == tableName:
                return itemType.pluralName
        return False

    def nounNames(self, flag=None):
        nounList = list()
        for itemType in self.data:
            if flag == FCM.OnlyEnabled:
                if itemType.nounName and itemType.enabled:
                    nounList.append(itemType.nounName)
            elif flag == FCM.OnlyDisabled:
                if itemType.nounName and not itemType.enabled:
                    nounList.append(itemType.nounName)
            elif flag == FCM.IsWeblinks:
                if itemType.nounName and itemType.isWeblinks:
                    nounList.append(itemType.nounName)
            elif flag == FCM.NoWeblinks:
                if itemType.nounName and not itemType.isWeblinks:
                    nounList.append(itemType.nounName)
            elif flag == FCM.IsWebpages:
                if itemType.nounName and itemType.isWebpages:
                    nounList.append(itemType.nounName)
            elif flag == FCM.NoWebpages:
                if itemType.nounName and not itemType.isWebpages:
                    nounList.append(itemType.nounName)
            else:
                if itemType.nounName:
                    nounList.append(itemType.nounName)
        return nounList

    def tableNames(self, flag=None):
        tableList = list()
        for itemType in self.data:
            if flag == FCM.OnlyEnabled:
                if itemType.tableName and itemType.enabled:
                    tableList.append(itemType.tableName)
            elif flag == FCM.OnlyDisabled:
                if itemType.tableName and not itemType.enabled:
                    tableList.append(itemType.tableName)
            elif flag == FCM.IsWeblinks:
                if itemType.tableName and itemType.isWeblinks:
                    tableList.append(itemType.tableName)
            elif flag == FCM.NoWeblinks:
                if itemType.tableName and not itemType.isWeblinks:
                    tableList.append(itemType.tableName)
            else:
                if itemType.tableName:
                    tableList.append(itemType.tableName)
        return tableList

    def validateIcons(self, icons, backupName):
        for itemType in self.data:
            if not icons.get(itemType.iconName):
                itemType.setIconName(backupName)


class ItemType:
    pluralName = None
    nounName = None
    dirName = None
    tableName = None
    enabled = True
    isWeblinks = False
    isWebpages = False

    def __init__(self, data=None):
        self.extensions = list()

        if data:
            self.pluralName = data[0]
            self.nounName = data[1]
            self.tableName = data[2]
            self.extensions = data[3]

    def setPluralName(self, name):
        self.pluralName = name
        if not self.dirName:
            self.dirName = name

    def setNounName(self, name):
        self.nounName = name

    def setDirName(self, name):
        if name not in ("", None):
            self.dirName = name
        else:
            self.dirName = self.pluralName

    def setTableName(self, name):
        self.tableName = name

    def setExtensions(self, exts):
        self.clearExtensions()
        for ext in exts:
            if ext not in self.extensions:
                self.extensions.append(ext)

    def addExtension(self, ext):
        if ext not in self.extensions:
            self.extensions.append(ext)

    def hasExtension(self, ext):
        if ext in self.extensions:
            return True
        else:
            return False

    def removeExtension(self, ext):
        self.extensions.remove(ext)

    def clearExtensions(self):
        try:
            self.extensions.clear()
        except AttributeError:
            del self.extensions[:]

    def extensionCount(self):
        return len(self.extensions)

    def setEnabled(self, setBool):
        if isinstance(setBool, str):
            if setBool.lower().strip() == "true":
                self.enabled = True
            else:
                self.enabled = False
        elif isinstance(setBool, bool):
            self.enabled = setBool
        elif isinstance(setBool, int):
            if setBool == 1:
                self.enabled = True
            else:
                self.enabled = False

    def printDetails(self):
        print(bcolours.HEADER+"Noun Name: "+bcolours.ENDC+self.nounName)
        print(bcolours.HEADER+"Plural Name: "+bcolours.ENDC+self.pluralName)
        print(bcolours.HEADER+"Dir Name: "+bcolours.ENDC+self.dirName)
        print(bcolours.HEADER+"Table Name: "+bcolours.ENDC+self.tableName)
        print(bcolours.HEADER+"Enabled: "+bcolours.ENDC+str(self.enabled))
        print(bcolours.HEADER+"Is Weblinks: "+bcolours.ENDC+str(self.isWeblinks))
        print(bcolours.HEADER+"Is Webpages: "+bcolours.ENDC+str(self.isWebpages))
        print(bcolours.HEADER+"Extensions: "+bcolours.ENDC)
        print(self.extensions)

