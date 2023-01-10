# Filecatman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Filecatman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Filecatman. If not, see http://www.gnu.org/licenses/.

import csv
import datetime
import os
import pprint
import sys
from urllib.parse import unquote, quote

import filecatman.config as config
from filecatman.core import const
from filecatman.core.database import Database
from filecatman.core.functions import convToBool, getDataFilePath, uploadFile, pluralize, \
    escape, deleteFile, isURL, downloadFile, createLink, createDesktopFile, chunks, \
    formatBytes, unformatBytes, timeStampToString, getMD5FromFile, getMD5FromPath, \
    printProgressBar, getPrintColourFromName, deepCopy, getTmpPath, desktopFileExt
from filecatman.core.objects import ItemType, ItemTypeList, Taxonomy, TaxonomyList, FCM
from filecatman.core.exceptions import FCM_NoDatabaseFile
from filecatman.log import logger

## TODO add category parents

class Filecatman:
    main, config, db = None, None, None
    systemName, logger, portableMode = None, None, None
    organizationname,applicationname, applicationversion = None, None, None
    dataDirOverride = None
    needToPurgeShortcuts, needToCreateShortcuts = False, False
    noIntegration, noShortcuts = False, False
    importedMode = True
    defaultExtensions = dict(
        webpage=('html', 'htm', 'xhtml', 'xht'),
        document=('pdf', 'doc', 'docx', 'txt', 'odt', 'mobi', 'epub', 'rtf', 'abw'),
        image=('jpeg', 'jpg', 'png', 'apng', 'gif', 'bmp', 'svg', 'ico'),
        audio=('mp3', 'flac', 'wav', 'wma', 'mid', 'ogg', 'm4a'),
        video=('flv', 'mp4', 'avi', 'm4v', 'mkv', 'mov', 'mpeg', 'mpg', 'wmv', '3gp')
    )
    defaultItemTypes = (
        ('Webpages', 'Webpage', 'webpage', defaultExtensions['webpage']),
        ('Documents', 'Document', 'document', defaultExtensions['document']),
        ('Images', 'Image', 'image', defaultExtensions['image']),
        ('Weblinks', 'Weblink', 'weblink'),
        ('Audio', 'Audio', 'audio', defaultExtensions['audio']),
        ('Video', 'Video', 'video', defaultExtensions['video'])
    )
    defaultTaxonomies = (
        ('Tags', 'Tag', 'tag', False, True),
    )

    def __init__(self, args=None):
        if not args: args = {}
        if args.get('noImportedMode'): self.importedMode = False
        self.setOrganizationName(const.ORGNAME)
        self.setApplicationName(const.APPNAME)
        self.setApplicationVersion(const.VERSION)
        self.setPortableMode(const.PORTABLEMODE)
        self.getLogger()
        self.getSystemSpecifics()
        self.logger.debug(
            "This is " + self.applicationName() + " " + self.applicationVersion() + " running on " + self.systemName)
        if self.portableMode: self.logger.debug(
            "Running in portable mode. Configuration files are saved in the cwd.")
        self.config = config.Config()

        if args.get('databasePath'):
            self.config['db'] = dict()
            absDbPath = os.path.abspath(args['databasePath'])
            if not os.path.exists(os.path.dirname(absDbPath)): os.makedirs(os.path.dirname(absDbPath))
            self.config['db']['db'] = absDbPath
            self.config['db']['type'] = "sqlite"
            self.config['autoloadDatabase'] = False
            self.confirmConnection()
        elif not self.importedMode and not args.get('closeAutoLoadDatabase') and self.config.get('autoloadDatabase') \
                and self.config['autoloadDatabase'] and self.config.get('db'):
            absDbPath = os.path.abspath(self.config['db']['db'])
            if not os.path.exists(os.path.dirname(absDbPath)): os.makedirs(os.path.dirname(absDbPath))
            self.confirmConnection()
        else:
            if args.get('closeAutoLoadDatabase'):
                self.config['autoloadDatabase'] = False
                self.config.writeConfig()
            raise FCM_NoDatabaseFile("No database file inputted")
        if args.get('dataDirPath'): self.dataDirOverride = args['dataDirPath']
        self.readDatabaseOptions()
        self.readItemTypesAndTaxonomies()

    def getLogger(self):
        # import logging
        # if not logging.getLogger().hasHandlers():
        #     import filecatman.log as log
        #     log.initializeLogger(const.LOGGERLEVEL)
        self.logger = logger

    def executeActions(self, fcmConfig):
        if fcmConfig.get('nointegration'): self.noIntegration = True
        if fcmConfig.get('noshortcuts'): self.noShortcuts = True
        for key in fcmConfig["changes"]:
            match key:
                case "defaulttaxonomy":
                    self.config['options']['default_taxonomy'] = fcmConfig["changes"][key]
                case "shortcutsdir":
                    self.config['options']['default_shortcuts_dir'] = fcmConfig["changes"][key]
                case "integrationdir":
                    self.config['options']['default_integration_dir'] = fcmConfig["changes"][key]
                case "searchresultsdir":
                    self.config['options']['default_results_dir'] = fcmConfig["changes"][key]
                case 'setoption':
                    option = fcmConfig["changes"]['setoption']
                    if option['optionname'] in self.config['options']:
                        self.config['options'][option['optionname']] = option['optionvalue']
                        self.validateOptions()
                    else: self.logger.error("Unrecognised database option: "+ option['optionname'] )

        if self.config['options']['auto_integration'] and not self.noIntegration:
            self.integrateItems()

        for key in fcmConfig['actions']:
            match key:
                case "database":
                    for subkey in fcmConfig['actions']["database"]:
                        match subkey:
                            case "vacuum":
                                self.vacuumDatabase()
                            case "listoptions":
                                import json
                                print(json.dumps(self.config['options'], indent=4))
                            case "listitemtypes":
                                import json
                                self.db.open()
                                print(json.dumps(self.db.selectItemTypes().fetchall(), indent=4))
                                self.db.close()
                            case "listtaxonomies":
                                import json
                                self.db.open()
                                print(json.dumps(self.db.selectAllTaxonomies().fetchall(), indent=4))
                                self.db.close()
                            case "checkfiles":
                                self.checkFilesExistInDatabase()
                            case "info":
                                self.inspectDatabaseInfo()
                case "shortcuts":
                    self.createShortcuts(customPath=fcmConfig['actions'][key], overwriteLinks=True)
                case "integrate":
                    self.integrateItems(fcmConfig['actions'][key])
                case "export":
                    self.exportProject(fcmConfig['actions'][key])
                case "import":
                    self.importProject(fcmConfig['actions'][key])
                case "search":
                    if fcmConfig['actions'][key].get('searchterms'):
                        searchterms = fcmConfig['actions'][key]['searchterms']
                        self.logger.debug("Searching for '"+searchterms+"'")
                    self.searchItems(fcmConfig['actions'][key])
                case "searchcats":
                    if fcmConfig['actions'][key].get('searchterms'):
                        searchterms = fcmConfig['actions'][key]['searchterms']
                        self.logger.debug("Searching for '" + searchterms + "'")
                    self.searchCategories(fcmConfig['actions'][key])
                case "searchtaxs":
                    if fcmConfig['actions'][key].get('searchterms'):
                        searchterms = fcmConfig['actions'][key]['searchterms']
                        self.logger.debug("Searching for '" + searchterms + "'")
                    self.searchTaxonomies(fcmConfig['actions'][key])
                case "item":
                    for subkey in  fcmConfig['actions']["item"]:
                        match subkey:
                            case "synchmd5":
                                self.synchItemMD5WithFiles()
                            case "synchdate":
                                self.synchItemDateWithFiles()
                            case "lastitem":
                                self.printLastItem(fcmConfig['actions']["item"][subkey])
                            case "clone":
                                if not isinstance(fcmConfig['actions']["item"][subkey]['filepath'], list):
                                    fcmConfig['actions']["item"][subkey]['filepath'] = [fcmConfig['actions']["item"][subkey]['filepath'],]
                                self.db.open()
                                print(fcmConfig['actions']["item"][subkey]['filepath'])
                                for filepath in fcmConfig['actions']["item"][subkey]['filepath']:
                                    fileData = fcmConfig['actions']["item"][subkey]
                                    if filepath == "lastitem":
                                        item = self.db.selectLastItem()
                                        if item: filepath = str(item[0])
                                    fileData['filepath'] = filepath
                                    fileData['keepDatabaseOpen'] = True
                                    self.cloneItem(fileData)
                                self.db.commit()
                                self.db.close()
                                self.needToCreateShortcuts = True
                            case  "download":
                                if isinstance(fcmConfig['actions']["item"][subkey]['filepath'], list):
                                    print(fcmConfig['actions']["item"][subkey]['filepath'])
                                    for filepath in fcmConfig['actions']["item"][subkey]['filepath']:
                                        fileData = fcmConfig['actions']["item"][subkey]
                                        fileData['filepath'] = filepath
                                        self.downloadItem(fileData)
                                else:
                                    self.downloadItem(fcmConfig['actions']["item"][subkey])
                                self.needToCreateShortcuts = True
                            case "inspect":
                                if not isinstance(fcmConfig['actions']["item"][subkey]['filepath'], list):
                                    fcmConfig['actions']["item"][subkey]['filepath'] = [fcmConfig['actions']["item"][subkey]['filepath'],]
                                self.db.open()
                                print('{')
                                i = 1
                                for filepath in fcmConfig['actions']["item"][subkey]['filepath']:
                                    fileData = fcmConfig['actions']["item"][subkey]
                                    if filepath == "lastitem":
                                        item = self.db.selectLastItem()
                                        if item: filepath = str(item[0])
                                    fileData['filepath'] = filepath
                                    fileData['keepDatabaseOpen'] = True
                                    item = self.getItemFromPath(filepath)
                                    if not item:
                                        i += 1
                                        continue
                                    print('"' + str(item[FCM.ItemCol['Iden']]) + '": ')
                                    self.inspectItem(fileData)
                                    if i < len(fcmConfig['actions']["item"][subkey]['filepath']):
                                        print(',')
                                    i += 1
                                print('}')
                                self.db.close()
                            case "path":
                                if fcmConfig['actions']["item"][subkey]['filepath'] == "lastitem":
                                    self.db.open()
                                    item = self.db.selectLastItem()
                                    if item: fcmConfig['actions']["item"][subkey]['filepath'] = str(item[0])
                                    self.db.close()
                                self.printItemFilepath(fcmConfig['actions']["item"][subkey])
                            case "rename":
                                if fcmConfig['actions']["item"][subkey]['filepath'] == "lastitem":
                                    self.db.open()
                                    item = self.db.selectLastItem()
                                    if item: fcmConfig['actions']["item"][subkey]['filepath'] = str(item[0])
                                    self.db.close()
                                self.renameItem(fcmConfig['actions']["item"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "launch":
                                if fcmConfig['actions']["item"][subkey]['filepath'] == "lastitem":
                                    self.db.open()
                                    item = self.db.selectLastItem()
                                    if item: fcmConfig['actions']["item"][subkey]['filepath'] = str(item[0])
                                    self.db.close()
                                self.launchItem(fcmConfig['actions']["item"][subkey])
                            case "delete":
                                if not isinstance(fcmConfig['actions']["item"][subkey]['filepath'], list):
                                    fcmConfig['actions']["item"][subkey]['filepath'] = [fcmConfig['actions']["item"][subkey]['filepath'],]
                                for filepath in fcmConfig['actions']["item"][subkey]['filepath']:
                                    fileData = fcmConfig['actions']["item"][subkey]
                                    if filepath == "lastitem":
                                        self.db.open()
                                        item = self.db.selectLastItem()
                                        if item: filepath = str(item[0])
                                        self.db.close()
                                    fileData['filepath'] = filepath
                                    self.deleteItem(fileData)
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "delrel":
                                if isinstance(fcmConfig['actions']["item"][subkey]['filepath'], list):
                                    for filepath in fcmConfig['actions']["item"][subkey]['filepath']:
                                        fileData = fcmConfig['actions']["item"][subkey]
                                        fileData['filepath'] = filepath
                                        self.deleteItemRelations(fileData)
                                else:
                                    self.deleteItemRelations(fcmConfig['actions']["item"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "update":
                                if not isinstance(fcmConfig['actions']["item"][subkey]['filepath'], list):
                                    fcmConfig['actions']["item"][subkey]['filepath'] = [fcmConfig['actions']["item"][subkey]['filepath'],]
                                self.db.open()
                                for filepath in fcmConfig['actions']["item"][subkey]['filepath']:
                                    fileData = fcmConfig['actions']["item"][subkey]
                                    if filepath == "lastitem":
                                        item = self.db.selectLastItem()
                                        if item: filepath = str(item[0])
                                    fileData['filepath'] = filepath
                                    fileData['keepDatabaseOpen'] = True
                                    self.updateItem(fileData)
                                self.db.commit()
                                self.db.close()
                                if fcmConfig['actions']["item"][subkey].get("removecategories") or \
                                        fcmConfig['actions']["item"][subkey].get("setname"):
                                    self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "upload":
                                if isinstance(fcmConfig['actions']["item"][subkey]['filepath'], list):
                                    bulkCommit = fcmConfig['actions']["item"][subkey].get('bulk')
                                    if bulkCommit: self.db.open()
                                    for filepath in fcmConfig['actions']["item"][subkey]['filepath']:
                                        fileData = fcmConfig['actions']["item"][subkey]
                                        fileData['filepath'] = filepath
                                        if bulkCommit: fileData['keepDatabaseOpen'] = True
                                        self.uploadItem(fileData)
                                    if bulkCommit:
                                        self.db.commit()
                                        self.db.close()
                                else:
                                    self.uploadItem(fcmConfig['actions']["item"][subkey])
                                self.needToCreateShortcuts = True
                            case "view":
                                if fcmConfig['actions']["item"][subkey]['filepath'] == "lastitem":
                                    self.db.open()
                                    item = self.db.selectLastItem()
                                    if item: fcmConfig['actions']["item"][subkey]['filepath'] = str(item[0])
                                    self.db.close()
                                self.searchCategories(
                                    {"withitems": [fcmConfig['actions']["item"][subkey]['filepath']]})
                            case "merge":
                                self.mergeItems(fcmConfig['actions']["item"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "copyrel":
                                if fcmConfig['actions']["item"][subkey]['filepath'] == "lastitem":
                                    self.db.open()
                                    item = self.db.selectLastItem()
                                    if item: fcmConfig['actions']["item"][subkey]['filepath'] = str(item[0])
                                    self.db.close()
                                self.copyItemRelations(fcmConfig['actions']["item"][subkey])
                                self.needToCreateShortcuts = True
                            case "mergedupes":
                                self.mergeDuplicateItems(fcmConfig['actions']["item"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True

                case "category":
                    for subkey in fcmConfig['actions']["category"]:
                        match subkey:
                            case "synch":
                                self.synchCategories(fcmConfig['actions']["category"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "launch":
                                searchConf = fcmConfig['actions']["category"][subkey]
                                searchConf['withcategories'] = [searchConf.pop('category')]
                                searchConf['openinmanager'] = True
                                self.searchItems(searchConf)
                            case "create":
                                if isinstance(fcmConfig['actions']["category"][subkey]['category'], list):
                                    self.db.open()
                                    for category in fcmConfig['actions']["category"][subkey]['category']:
                                        fileData = fcmConfig['actions']["category"][subkey]
                                        fileData['category'] = category
                                        fileData['keepDatabaseOpen'] = True
                                        self.createCategory(fileData)
                                    self.db.commit()
                                    self.db.close()
                                else: self.createCategory(fcmConfig['actions']["category"][subkey])
                                self.needToCreateShortcuts = True
                            case "inspect":
                                self.inspectCategory(fcmConfig['actions']["category"][subkey])
                            case "rename":
                                self.renameCategory(fcmConfig['actions']["category"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "delete":
                                if isinstance(fcmConfig['actions']["category"][subkey]['category'], list):
                                    self.db.open()
                                    for category in fcmConfig['actions']["category"][subkey]['category']:
                                        fileData = fcmConfig['actions']["category"][subkey]
                                        fileData['category'] = category
                                        fileData['keepDatabaseOpen'] = True
                                        self.deleteCategory(fileData)
                                    self.db.commit()
                                    self.db.close()
                                else:
                                    self.deleteCategory(fcmConfig['actions']["category"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "delrel":
                                if isinstance(fcmConfig['actions']["category"][subkey]['category'], list):
                                    self.db.open()
                                    for category in fcmConfig['actions']["category"][subkey]['category']:
                                        fileData = fcmConfig['actions']["category"][subkey]
                                        fileData['category'] = category
                                        fileData['keepDatabaseOpen'] = True
                                        self.deleteCategoryRelations(fileData)
                                    self.db.commit()
                                    self.db.close()
                                else:
                                    self.deleteCategoryRelations(fcmConfig['actions']["category"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "copyrel":
                                self.copyCategoryRelations(fcmConfig['actions']["category"][subkey])
                                self.needToCreateShortcuts = True
                            case "update":
                                if isinstance(fcmConfig['actions']["category"][subkey]['category'], list):
                                    self.db.open()
                                    for category in fcmConfig['actions']["category"][subkey]['category']:
                                        fileData = fcmConfig['actions']["category"][subkey]
                                        fileData['category'] = category
                                        fileData['keepDatabaseOpen'] = True
                                        self.updateCategory(fileData)
                                    self.db.commit()
                                    self.db.close()
                                else:
                                    self.updateCategory(fcmConfig['actions']["category"][subkey])
                                if fcmConfig['actions']["category"][subkey].get("removeitems"):
                                    self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "view":
                                searchConf =fcmConfig['actions']["category"][subkey]
                                searchConf['withcategories'] = [searchConf.pop('category')]
                                self.searchItems(searchConf)
                            case "merge":
                                self.mergeCategories(fcmConfig['actions']["category"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                case "taxonomy":
                    for subkey in fcmConfig['actions']["taxonomy"]:
                        match subkey:
                            case "merge":
                                self.mergeTaxonomies(fcmConfig['actions']["taxonomy"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "setcolour":
                                self.setTaxonomyColour(fcmConfig['actions']["taxonomy"][subkey])
                            case "delete":
                                self.deleteTaxonomy(fcmConfig['actions']["taxonomy"][subkey])
                                self.needToPurgeShortcuts = True
                                self.needToCreateShortcuts = True
                            case "view":
                                self.searchCategories(
                                    {"withtaxonomies": [fcmConfig['actions']["taxonomy"][subkey]['taxonomy']]})


    def close(self):
        if self.config['options']['auto_shortcuts'] and not self.noShortcuts:
            if self.needToPurgeShortcuts: self.purgeShortcutsFolder()
            if self.needToPurgeShortcuts or self.needToCreateShortcuts: self.createShortcuts()
        self.writeDatabaseOptions()
        self.config.writeConfig()

    def getItemFromPath(self, path):
        item = None
        if os.path.islink(path):
            ## Multilevel link resolving: # import pathlib # pathlib.Path(filepath).resolve()
            filepath = os.readlink(path)
            fileID = os.path.basename(filepath).rsplit('.', 1)[0]
        elif path.isnumeric():
            fileID = path
        else:
            fileID = os.path.basename(path).rsplit('.', 1)[0]
        if not fileID: return False
        try:
            if not item: item = self.db.selectItem(fileID)
        except IndexError as e:
            self.logger.exception(e)
            return False
        if not item: return False
        return item

    def printLastItem(self, data):
        self.db.open()
        item = self.db.selectLastItem()
        self.db.close()
        if item:
            if self.importedMode: return item
            if data.get('listpaths'):
                dataDir = self.config['options']['default_data_dir']
                typeDir = self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']])
                filePath = os.path.join(dataDir, typeDir, str(item[FCM.ItemCol['Iden']]) + "." + item[FCM.ItemCol['Ext']])
                print(filePath)
            elif data.get('inspect'): self.inspectItem({"filepath": str(item[FCM.ItemCol['Iden']])})
            else: print(item[FCM.ItemCol['Iden']])


    def printItemFilepath(self, data):
        itemData = dict()
        self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item: raise Exception("Item not found")
        for colName in (
        'Iden', 'Name', 'Type', 'Ext', 'Source', 'ModificationTime', 'CreationTime', 'Description', 'PrimaryCategory'):
            itemData[colName] = item[FCM.ItemCol[colName]]
        dataDir = self.config['options']['default_data_dir']
        typeDir = self.config['itemTypes'].dirFromNoun(itemData['Type'])
        filePath = os.path.join(dataDir, typeDir, str(itemData['Iden']) + "." + itemData['Ext'])
        print(filePath)
        self.db.close()

    def importProject(self, data):
        self.logger.debug("Importing project")
        self.db.open()
        if not os.path.exists(data['filepath']): raise Exception('No valid filepath')
        if os.path.isdir(data['filepath']):
            jsonPath = os.path.join(data['filepath'], os.path.basename(data['filepath'])+".json")
            if os.path.exists(jsonPath):
                data['filepath'] = jsonPath
            else: raise Exception('No JSON file found')
        import json
        with open(data['filepath'], "r") as importFile:
            try: importedData = json.load(importFile)
            except json.decoder.JSONDecodeError:
                self.logger.error('Invalid JSON file')
                return
            if not importedData.get("Filecatman Version"): raise Exception('Missing Version Info')
            if importedData.get("Categories"):
                for catIden, cat in importedData['Categories'].items():
                    self.createCategory({ 'category': cat['Taxonomy']+":"+unquote(cat['Name']),
                                          'keepDatabaseOpen': True })
            if importedData.get("Items"):
                for item in importedData['Items']:
                    isWeblink = self.config['itemTypes'].get(item['Type']).isWeblinks
                    if not isWeblink:
                        filePath = os.path.join(os.path.dirname(data['filepath']), "Files", item['Type'], str(item['Iden'])+"."+item['Ext'])
                    else:
                        filePath = unquote(item['Source'])
                        item['Ext'] = desktopFileExt()
                    print(item)
                    itemCategories = list()
                    primaryCategory = None
                    for rel in item['Relations']:
                        if importedData['Categories'].get(str(rel)):
                            itemCategories.append(importedData['Categories'][str(rel)]['Taxonomy']+":"+unquote(importedData['Categories'][str(rel)]['Name']))
                    if item.get('PrimaryCategory'):
                        if importedData['Categories'].get(str(item['PrimaryCategory'])):
                            primaryCategory = importedData['Categories'][str(item['PrimaryCategory'])]['Taxonomy']+":"+unquote(importedData['Categories'][str(item['PrimaryCategory'])]['Name'])
                    if data.get('updateifduplicate') and not isWeblink:
                        existingItems = self.db.selectItems({'item_md5': getMD5FromFile(filePath)})
                        if len(existingItems) > 0:
                            updateData = {
                                'keepDatabaseOpen': True,
                                'filepath': filePath,
                                'setname': unquote(item['Name']),
                                'setext': item['Ext'],
                                'setprimarycategory': primaryCategory,
                                'addcategories': itemCategories
                            }
                            if item.get('Source'): updateData['setsource'] = unquote(item['Source'])
                            if item.get('Description'): updateData['setdescription'] = unquote(item['Description'])
                            if item.get('ModificationTime'): updateData['setdatetime'] = item['ModificationTime']
                            self.updateItem(updateData)
                            continue
                    uploadData = {
                        'keepDatabaseOpen': True,
                        'filepath': filePath,
                        'name': unquote(item['Name']),
                        'ext': item['Ext'],
                        'type': item['Type'],
                        'primarycategory': primaryCategory,
                        'categories': itemCategories
                    }
                    if item.get('Source'): uploadData['source'] = unquote(item['Source'])
                    if item.get('Description'): uploadData['description'] = unquote(item['Description'])
                    if item.get('CreationTime'): uploadData['creationtime'] = item['CreationTime']
                    if item.get('ModificationTime'): uploadData['datetime'] = item['ModificationTime']
                    self.uploadItem(uploadData)
            self.needToCreateShortcuts = True
        self.db.commit()
        self.db.close()

    def exportProject(self,data):
        self.logger.debug("Exporting project")
        if not os.path.exists(data['filepath']): os.makedirs(data['filepath'])

        projectName = os.path.basename(self.db.config['db'])
        dateTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        projectExportPath = os.path.join(data['filepath'], projectName + "_" + dateTime)
        if not os.path.exists(projectExportPath): os.makedirs(projectExportPath)
        projectJsonPath = os.path.join(projectExportPath, projectName + "_" + dateTime + ".json")
        projectDataPath = os.path.join(projectExportPath, "Files")
        if not os.path.exists(projectDataPath): os.makedirs(projectDataPath)

        self.db.open()
        jsonData = dict()
        jsonData['Filecatman Version'] = self.applicationVersion()
        jsonData['Items'] = list()
        jsonData['Categories'] = dict()

        if data.get('exportresults'):
            categories = data['exportresults'][0]
            items = data['exportresults'][1]
        else:
            categories = self.db.selectAllCategories()
            items = self.db.selectAllItems()
        lenItemsCounter = 0
        lenCategories = len(categories)
        for cat in categories:
            jsonData['Categories'][str(cat[FCM.CatCol["Iden"]])] = {
                "Iden": cat[FCM.CatCol["Iden"]],
                "Name": cat[FCM.CatCol["Name"]],
                "Taxonomy": cat[FCM.CatCol["Taxonomy"]],
                "Description": cat[FCM.CatCol["Description"]],
                "Parent": cat[FCM.CatCol["Parent"]],
                "Count": cat[FCM.CatCol["Count"]]
            }
            lenItemsCounter+=1
            printProgressBar(
                progress=lenItemsCounter/lenCategories,
                progressMessage="Exporting categories",
                enabled=self.config['options']['progress_bar']
            )
        lenItemsCounter = 0
        lenCategories = len(items)
        for item in items:
            itemDict = {
                "Iden": item[FCM.ItemCol["Iden"]],
                "Name": item[FCM.ItemCol["Name"]],
                "Type": item[FCM.ItemCol["Type"]],
                "Ext": item[FCM.ItemCol["Ext"]],
                "Source": item[FCM.ItemCol["Source"]],
                "ModificationTime": item[FCM.ItemCol["ModificationTime"]],
                "CreationTime": item[FCM.ItemCol["CreationTime"]],
                "Description": item[FCM.ItemCol["Description"]],
                "PrimaryCategory": item[FCM.ItemCol["PrimaryCategory"]],
                "Relations": [i[0] for i in self.db.selectRelations(itemID=item[FCM.ItemCol["Iden"]])]
            }

            if not self.config['itemTypes'].get(item[FCM.ItemCol['Type']]).isWeblinks:
                filepath = os.path.join(self.config['options']['default_data_dir'],
                                        self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                        str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
                fileDestination = os.path.join(projectDataPath,
                                        item[FCM.ItemCol['Type']],
                                        str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
                if os.path.exists(filepath):
                    itemDict['Md5'] = getMD5FromFile(filepath)
                    uploadFile(self.config, filepath, fileDestination, fileType=self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]))
            jsonData['Items'].append(itemDict)
            lenItemsCounter+=1
            printProgressBar(
                progress=lenItemsCounter / lenCategories,
                progressMessage="Exporting items",
                enabled=self.config['options']['progress_bar']
            )


        import json
        jsonOutput = json.dumps(jsonData, indent=4)

        with open(projectJsonPath, 'x') as fp:
            fp.write(jsonOutput)
        os.chmod(projectJsonPath, 0o755)

    def inspectDatabaseInfo(self, simple=False):
        self.db.open()
        dbInfo = dict()
        dbInfo['Database Path'] = self.db.config['db']
        dbInfo['Data Directory'] = self.config['options']['default_data_dir']
        if not simple:
            dbInfo['Item Count'] = self.db.selectCount("items")[0]
            dbInfo['Category Count']  = self.db.selectCount("terms")[0]
            dbInfo['Relations Count']  = self.db.selectCount("term_relationships")[0]
            dbInfo['SQLite Version']  = self.db.versionInfo()[0]
            dbInfo['Filecatman Version']  = self.applicationVersion()
            totalSize = 0
            for item in self.db.selectAllItems():
                filepath = os.path.join(self.config['options']['default_data_dir'],
                                        self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                        str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
                totalSize+=os.stat(filepath).st_size
            dbInfo['Size'] = formatBytes(totalSize)
            import shutil
            dbInfo['Free Space'] = formatBytes(shutil.disk_usage(self.config['options']['default_data_dir']).free)
            dbInfo['Tables'] =  [a[0] for a in self.db.tables()]
        import json
        print(json.dumps(dbInfo, indent=4))
        self.db.close()

    def inspectItem(self, data):
        self.logger.debug("Inspecting item")
        itemData = dict()
        if not data.get('keepDatabaseOpen'): self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item: raise Exception("Item not found")
        for colName in ('Iden','Name', 'Type', 'Ext', 'Source', 'ModificationTime', 'CreationTime', 'Description','PrimaryCategory','Md5'):
            itemData[colName] = item[FCM.ItemCol[colName]]

        if itemData.get('Name'): itemData['Name'] = unquote(itemData['Name'])
        if itemData.get('Description'): itemData['Description'] = unquote(itemData['Description'])
        if itemData.get('Source'): itemData['Source'] = unquote(itemData['Source'])

        dataDir = self.config['options']['default_data_dir']
        relations = self.db.selectRelations(itemID=itemData['Iden'])

        itemData['Relations'] = list()
        relationsList = list()
        for rel in relations:
            category = self.db.selectCategory(catID=rel[0])
            relationsList.append(category)
        relationsList.sort(key=lambda a: a[1], reverse=False)
        relationsList.sort(key=lambda a: a[2], reverse=False)
        for category in relationsList:
            itemData['Relations'].append(str(category[0])+" = "+str(category[2])+" : "+unquote(category[1]))


        relationsCount = len(relations)
        itemData['RelationCount'] = relationsCount

        typeDir = self.config['itemTypes'].dirFromNoun(itemData['Type'])
        filePath = os.path.join(dataDir, typeDir, str(itemData['Iden']) + "." + itemData['Ext'])
        itemData['Filepath'] = filePath
        # itemData['FileMd5'] = getMD5FromFile(filePath)
        itemData['Size'] = os.stat(filePath).st_size

        if not data.get('keepDatabaseOpen'): self.db.close()

        if self.importedMode or data.get('importedmode'): return itemData

        import json
        print(json.dumps(itemData, indent=4))

    def launchItem(self, data):
        self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item: raise Exception("Item not found")
        isWeblink = self.config['itemTypes'].get(item[FCM.ItemCol['Type']]).isWeblinks
        if not isWeblink:
            filepath = os.path.join(self.config['options']['default_data_dir'],
                                    self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]), str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
            if not os.path.exists(filepath): raise Exception("File not found")
        fileID = item[FCM.ItemCol['Iden']]

        import subprocess, platform
        if not isWeblink:
            dataDir = self.config['options']['default_data_dir']
            typeDir = self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']])
            filePath = os.path.join(dataDir, typeDir, str(fileID) + "." + item[FCM.ItemCol['Ext']])

            searchResultsDir = self.config['options']['default_results_dir']
            if not os.path.exists(searchResultsDir): os.makedirs(searchResultsDir)
            # dateTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # linksDir = os.path.join(searchResultsDir, dateTime)

            linksDir = os.path.join(dataDir, ".launch", str(item[FCM.ItemCol['Iden']]))
            linkPath = os.path.join(linksDir, str(item[FCM.ItemCol['Iden']]) + "." + item[FCM.ItemCol['Ext']])
            createLink(filePath, linkPath, True)

            if platform.system() == "Windows":
                os.startfile(linkPath)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.call(('open', linkPath))
            else:
                subprocess.Popen(['xdg-open', linkPath], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        else:
            source = unquote(item[FCM.ItemCol['Source']])
            if platform.system() == "Windows":
                os.startfile(source)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.call(('open', source))
            else:
                subprocess.Popen(['xdg-open', source], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        self.db.commit()
        self.db.close()

    def integrateItems(self, customPath=None):
        integrationDir = self.config['options']['default_integration_dir']
        if customPath:
            if os.path.exists(customPath) and os.path.isdir(customPath):
                integrationDir = customPath
            else:
                raise Exception('Invalid integration directory path')
        if not os.path.exists(integrationDir): os.mkdir(integrationDir)
        self.db.open()
        directory = os.fsencode(integrationDir)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            filepath = os.path.join(integrationDir, filename)
            if os.path.isfile(filepath):
                self.uploadItem({"filepath": filepath})
                os.remove(filepath)
                self.needToCreateShortcuts = True
            if os.path.isdir(filepath):
                subDir = os.fsencode(filepath)
                folderName = os.path.basename(filepath)
                for subfile in os.listdir(subDir):
                    subFilename = os.fsdecode(subfile)
                    subFilepath = os.path.join(filepath, subFilename)
                    if os.path.islink(subFilepath):
                        linkDestPath = os.readlink(subFilepath)
                        fileID = os.path.basename(linkDestPath).rsplit('.', 1)[0]
                        item =  self.db.selectItem(fileID)
                        if item:
                            self.updateItem({"filepath": fileID, "addcategories":[folderName,]})
                            os.unlink(subFilepath)
                            self.needToCreateShortcuts = True
                    elif os.path.isfile(subFilepath):
                        self.uploadItem({"filepath": subFilepath, "categories":[folderName,]})
                        os.remove(subFilepath)
                        self.needToCreateShortcuts = True
        self.db.close()
        self.logger.debug("Integration folder scan complete")






    def purgeShortcutsFolder(self):
        import shutil
        shortcutsDir = self.config['options']['default_shortcuts_dir']
        try:
            shutil.rmtree(shortcutsDir)
        except FileNotFoundError:
            pass

    def vacuumDatabase(self):
        self.db.close()
        self.db.open()
        self.db.vacuumDatabase()
        self.db.commit()
        self.db.close()

    def synchItemDateWithFiles(self):
        import time
        timerStart = time.perf_counter()
        self.db.open()
        allItems = self.db.selectAllItems()
        allItemsCount = len(allItems)
        allItemsCounter = 0
        for index, item in enumerate(allItems):
            filepath = os.path.join(self.config['options']['default_data_dir'],
                                    self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                    str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
            if os.path.exists(filepath):
                dt = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                fileDate = dt.strftime("%Y-%m-%d %H:%M:%S")
                if not fileDate == item[FCM.ItemCol['ModificationTime']]:
                    self.db.updateMD5(str(item[FCM.ItemCol['Iden']]), getMD5FromFile(filepath))
                    self.db.updateItemDate(str(item[FCM.ItemCol['Iden']]), fileDate)
            allItemsCounter += 1
            printProgressBar(
                progress=allItemsCounter / allItemsCount,
                progressMessage="Synchronizing modification date with files (" + str(allItemsCounter) + "/" + str(
                    allItemsCount) + ")",
                status="",
                enabled=self.config['options']['progress_bar']
            )
        self.db.commit()
        self.db.close()
        timerEnd = time.perf_counter()
        print("Time taken: "+str(round(timerEnd-timerStart,2))+" seconds")

    def synchItemMD5WithFiles(self):
        import time
        timerStart = time.perf_counter()
        self.db.open()
        allItems = self.db.selectAllItems()
        allItemsCount = len(allItems)
        allItemsCounter = 0
        for index, item in enumerate(allItems):
            filepath = os.path.join(self.config['options']['default_data_dir'],
                                    self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                    str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
            if os.path.exists(filepath):
                self.db.updateMD5(str(item[FCM.ItemCol['Iden']]), getMD5FromFile(filepath))
            allItemsCounter += 1
            printProgressBar(
                progress=allItemsCounter / allItemsCount,
                progressMessage="Synchronizing MD5 with files ("+str(allItemsCounter)+"/"+str(allItemsCount)+")",
                status="",
                enabled=self.config['options']['progress_bar']
            )
        self.db.commit()
        self.db.close()
        timerEnd = time.perf_counter()
        print("Time taken: "+str(round(timerEnd-timerStart,2))+" seconds")

    def checkFilesExistInDatabase(self):
        self.db.open()
        missingItemPaths, checkedIdens, duplicateIdens, missingExtensionList, \
        missingFiles = list(), list(), list(), list(), list()
        numItemTypes = len(self.config['itemTypes'])
        numItemTypesCounter = 0
        for itemType in self.config['itemTypes']:
            fileTypePath = os.path.join(self.config['options']['default_data_dir'],
                                itemType.dirName)
            if os.path.isdir(fileTypePath):
                for path in os.listdir(fileTypePath):
                    fullFilePath = os.path.join(fileTypePath, path)
                    if os.path.isfile(fullFilePath):
                        try:
                            fileIden = str(path).split(".")[0]
                            fileExt = str(path).split(".")[1]
                        except IndexError:
                            fileIden = str(path)
                            fileExt = None
                        item = self.getItemFromPath(fileIden)
                        if not item:
                            missingItemPaths.append(str(fullFilePath))
                        else:
                            filepath2 = os.path.join(fileTypePath,
                                 str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
                            if not os.path.exists(filepath2) or not item[FCM.ItemCol['Ext']] == fileExt:
                                missingExtensionList.append(fileIden)
                            if fileIden in checkedIdens:
                                duplicateIdens.append(fileIden)
                            else:
                                checkedIdens.append(fileIden)
                numItemTypesCounter += 1
                printProgressBar(
                    progress=numItemTypesCounter/numItemTypes,
                    progressMessage="Checking items exist",
                    status="",
                    enabled=self.config['options']['progress_bar']
                )


        allItems = self.db.selectAllItems()
        allItemsCount = len(allItems)
        allItemsCounter = 0
        for index, item in enumerate(allItems):
            filepath = os.path.join(self.config['options']['default_data_dir'],
                                    self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                    str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
            if not os.path.exists(filepath):
                missingFiles.append(str(item[FCM.ItemCol['Iden']]))
            # else:
            #     self.db.updateMD5(str(item[FCM.ItemCol['Iden']]), getMD5FromFile(filepath))
            allItemsCounter +=1
            printProgressBar(
                progress=allItemsCounter / allItemsCount,
                progressMessage="Checking files exist",
                status=str(item[0]),
                enabled=self.config['options']['progress_bar']
            )
        if len(missingItemPaths) > 0: print("Item not found for file: "+str(", ".join(missingItemPaths)))
        if len(duplicateIdens) > 0: print("Multiple files found for item: "+str(", ".join(duplicateIdens)))
        if len(missingExtensionList) > 0: print("File extension mismatch: "+str(", ".join(missingExtensionList)))
        if len(missingFiles) > 0: print("File not found for item: "+str(", ".join(missingFiles)))
        self.db.commit()
        self.db.close()

    def createShortcuts(self, customPath=None, overwriteLinks=False):
        shortcutsDir = self.config['options']['default_shortcuts_dir']
        self.db.open()
        if customPath:
            if not os.path.exists(customPath):
                os.makedirs(customPath)
            shortcutsDir = customPath
        elif self.config['options']['purge_shortcuts_folder']: self.purgeShortcutsFolder()
        dataDir = self.config['options']['default_data_dir']
        sqlItems = "SELECT i.item_id, i.item_name, i.type_id, i.item_source, " \
                   "i.item_time, i.item_ext FROM items AS i"
        queryItems = self.db.cur.execute(sqlItems).fetchall()
        lenQueryItems = len(queryItems)
        lenItemsCounter = 0
        if lenQueryItems == 0:
            return False
        for item in queryItems:
            itemIden = item[0]
            itemName = unquote(item[1])
            itemType = item[2]
            itemSource = unquote(item[3])
            itemTime = item[4]
            itemExt = item[5]
            typeDir = self.config['itemTypes'].dirFromNoun(itemType)
            filePath = os.path.join(dataDir,typeDir,str(itemIden)+"."+itemExt)
            if itemType in self.config['itemTypes'].nounNames(FCM.IsWeblinks):
                filePath = os.path.join(dataDir, typeDir, str(itemIden) + "."+desktopFileExt())
                if not createDesktopFile(filePath, itemName, itemSource):
                    self.logger.error("Unable to create desktop file")
                    return False
                pass

            if not os.path.exists(filePath):
                errorMessage = "File Error: File '{}' not found.".format(itemName)
                self.logger.error(errorMessage)
                continue
            else:
                try:
                    linkName = str(itemIden) + "_" + itemName
                    if not linkName.endswith("." + itemExt): linkName += "." + itemExt
                    linkPath = os.path.join(shortcutsDir, 'File Types', typeDir, linkName)
                    if not createLink(filePath, linkPath, overwriteLinks):
                        self.logger.error("Unable to create desktop file")
                        return False
                except (OSError, ) as exc:
                    if exc.errno == 36 or exc.winerror == 123: ## Name too long, Winerror
                        linkName = str(itemIden)
                        if not linkName.endswith("." + itemExt): linkName += "." + itemExt
                        linkPath = os.path.join(shortcutsDir, 'File Types', typeDir, linkName)
                        if not createLink(filePath, linkPath, overwriteLinks):
                            self.logger.error("Unable to create desktop file")
                            return False
                    else:
                        raise
                pass

            sqlRelations = "SELECT t.term_name, t.term_parent, t.term_taxonomy " \
                           "FROM term_relationships AS tr " \
                           "INNER JOIN terms AS t ON (t.term_id = tr.term_id) " \
                           "WHERE (tr.item_id = '{}')".format(itemIden)
            queryRelations = self.db.cur.execute(sqlRelations).fetchall()
            for relation in queryRelations:
                termName = unquote(relation[0])
                termParent = relation[1]
                termTaxonomy = relation[2]
                taxonomyDir = self.config['taxonomies'].dirFromTable(termTaxonomy)


                try:
                    linkName = str(itemIden) + "_" + itemName
                    if not itemName.endswith("." + itemExt): linkName += "." + itemExt
                    if termParent in ("", None, 0):
                        linkPath = os.path.join(shortcutsDir, taxonomyDir, termName, typeDir, linkName)
                    else:
                        termParentRoot, termParentsJoined = self.returnTermParents(termParent, termTaxonomy)
                        linkPath = os.path.join(shortcutsDir, taxonomyDir, termParentRoot, typeDir, termParentsJoined,
                                                termName, linkName)
                    if not createLink(filePath, linkPath, overwriteLinks):
                        return False
                except OSError as exc:
                    if exc.errno == 36 or exc.winerror == 123: ## Name too long, Winerror
                        linkName = str(itemIden)
                        if not itemName.endswith("." + itemExt): linkName += "." + itemExt
                        if termParent in ("", None, 0):
                            linkPath = os.path.join(shortcutsDir, taxonomyDir, termName, typeDir, linkName)
                        else:
                            termParentRoot, termParentsJoined = self.returnTermParents(termParent, termTaxonomy)
                            linkPath = os.path.join(shortcutsDir, taxonomyDir, termParentRoot,
                                                    typeDir, termParentsJoined, termName, linkName)
                        if not createLink(filePath, linkPath, overwriteLinks):
                            return False
                    else:
                        raise
            lenItemsCounter+=1
            printProgressBar(
                progress=lenItemsCounter/lenQueryItems,
                progressMessage="Creating shortcuts",
                enabled=self.config['options']['progress_bar']
            )
        self.logger.debug("Shortcuts created")

    def searchTaxonomies(self, data):
        from filecatman.core.printcolours import bcolours
        self.db.open()

        taxonomyResults =  self.config['taxonomies']
        if data.get('searchterms'): taxonomyResults = [a for a in taxonomyResults if data['searchterms'] in a.tableName]

        colData = list()
        colData.append(
            {'minlength': 5, 'name': "Table Name", 'index': "tableName", 'functions': ()})
        # colourBlock = lambda a : a + "##" + bcolours.ENDC
        colourBlock = lambda a : a.replace("\033", "\\033")
        colData.append(
            {'minlength': 10, 'name': "Colour", 'index': "colour", 'functions': (colourBlock,)})
        countCategories = lambda a : str(self.db.selectCountCategoriesWithTaxonomy(a))
        colData.append(
            {'minlength': 10, 'name': "Categories", 'index': "tableName", 'functions': (countCategories,)})
        isDefaultTaxonomy = lambda a: str(a == self.config['options']['default_taxonomy'])
        colData.append(
            {'minlength': 10, 'name': "Default Taxonomy", 'index': "tableName", 'functions': (isDefaultTaxonomy,)})
        for index, col in enumerate(colData):
            biggestLength = col['minlength']
            for result in taxonomyResults:
                itemRowData = ""
                if col['index']: itemRowData = getattr(result, col['index'])
                for func in col['functions']: itemRowData = func(itemRowData)
                lenCol = len(itemRowData)
                if lenCol > biggestLength: biggestLength = lenCol
            if biggestLength > 50: biggestLength = 50
            biggestLength += 3
            colData[index]["spaces"] = ''.join([char * biggestLength for char in ' '])
            colData[index]["lines"] = ''.join([char * biggestLength for char in '-'])
        columnNamesRow, columnLinesRow = "", ""
        for col in colData:
            columnNamesRow += col['name'] + col['spaces'][len(col['name']):]
            columnLinesRow += col['lines']
        print(columnNamesRow)
        print(columnLinesRow)

        colouredRows = self.config['options']['coloured_taxonomies']
        if colouredRows: from filecatman.core.printcolours import bcolours
        for result in taxonomyResults:
            itemRow = ""
            for col in colData:
                itemRowData = ""
                if col['index']: itemRowData = getattr(result, col['index'])
                for func in col['functions']: itemRowData = func(itemRowData)
                itemRowData = itemRowData[:50]
                printCol = itemRowData + col['spaces'][len(itemRowData):]
                itemRow += printCol
            if colouredRows:
                color = result.colour
                print(color + itemRow + bcolours.ENDC)
            else:
                print(itemRow)
        self.db.close()



    def searchCategories(self, data):
        additionalColumns, withoutColumns = [], []
        if data.get('col'): additionalColumns = data['col']
        if data.get('hidecol'): withoutColumns = data['hidecol']

        self.db.open()
        where = ["( t.term_id is not null )", ]
        itemKeywordsOp = ""
        tableColumns = (('Name', 'term_name', quote),
                        ('Description', 'term_description', quote))
        itemKeywords = data.get('searchterms')
        self.logger.debug(itemKeywords)
        if itemKeywords:
            fieldsWhere = list()
            for nounName, col, wordFunction in tableColumns:
                keywordsWhere = "({0} LIKE '%{1}%'".format(col, wordFunction(itemKeywords))
                keywordsWhere += ") \n"
                fieldsWhere.append(keywordsWhere)
            SQLName = "(" + " OR ".join(fieldsWhere) + ")"
            where.append("{}".format(itemKeywordsOp) + SQLName)
            self.logger.debug(where)

        if data.get('withtaxonomies'):
            fieldsWhere = list()
            for tax in data['withtaxonomies']:
                taxonomy = None
                taxListResult = self.config['taxonomies'].get(tax.capitalize())
                if taxListResult: taxonomy = taxListResult.tableName
                fieldsWhere.append("( t.term_taxonomy = '{}' )".format(taxonomy))
            if len(fieldsWhere) > 0:
                SQLName = "(" + " OR ".join(fieldsWhere) + ")"
                where.append(SQLName)
        elif data.get('withouttaxonomies'):
            fieldsWhere = list()
            for tax in data['withouttaxonomies']:
                taxListResult = self.config['taxonomies'].get(tax.capitalize())
                if taxListResult:
                    taxonomy = taxListResult.tableName
                    fieldsWhere.append("( t.term_taxonomy <> '{}' )".format(taxonomy))
            if len(fieldsWhere) > 0:
                SQLName = "(" + " AND ".join(fieldsWhere) + ")"
                where.append(SQLName)

        _itemcounts = list()
        if data.get("withitemcount"): _itemcounts.append((data['withitemcount'], "="))
        if data.get("withoutitemcount"): _itemcounts.append((data['withoutitemcount'], "<>"))
        if data.get("countmorethan"): _itemcounts.append((data['countmorethan'], ">"))
        if data.get("countlessthan"): _itemcounts.append((data['countlessthan'], "<"))
        if len(_itemcounts) > 0:
            for itemcount, operator in _itemcounts:
                where.append("( t.term_count {} '{}' )".format(operator, itemcount))

        _items = list()
        if data.get("withitems"): _items.append((data['withitems'], "IN"))
        if data.get("withoutitems"): _items.append((data['withoutitems'], "NOT IN"))
        if len(_items) > 0:
            for items, operator in _items:
                for item in items:
                    itemQuery = self.getItemFromPath(item)
                    if itemQuery: itemIden = itemQuery[FCM.ItemCol['Iden']]
                    else: itemIden = None

                    SQLItem = "SELECT tr.term_id \n" \
                              "FROM term_relationships AS tr \n" \
                              "INNER JOIN terms AS t ON (t.term_id = tr.term_id) \n" \
                              "WHERE ( tr.item_id = '{}' )".format(itemIden)
                    where.append("( t.term_id {0} (\n{1}\n) )".format(operator, SQLItem))

        if data.get("withduplicate"):
            duplicateCol = data.get("withduplicate").lower()
            SQLDuplicate = '''
            SELECT a.term_id
            FROM terms as a
            JOIN (SELECT term_{0}, COUNT(*)
            FROM terms 
            GROUP BY term_{0}
            HAVING count(*) > 1 ) as b
            ON a.term_{0} = b.term_{0}
            '''.format(duplicateCol)
            where.append("( t.term_id {0} (\n{1}\n) )".format("IN", SQLDuplicate))

        whereJoined = " AND ".join(where)
        sql = "SELECT {} FROM terms AS t " \
              "WHERE {} \n".format('*', whereJoined)

        if data.get('sortby'):
            sortBy = data['sortby'].lower()
            keys = {"iden": "t.term_id", "name": "t.term_name", "taxonomy": "t.term_taxonomy", "items":"t.term_count"}
            if sortBy in keys:
                directionOrder = "ASC"
                if data.get("desc"): directionOrder = "DESC"
                sql += "ORDER BY {} {}".format(keys[sortBy],directionOrder)
            else:
                sql += "ORDER BY t.term_count ASC"
        else:
            sql += "ORDER BY t.term_count ASC"


        categoriesQuery = self.db.cur.execute(sql).fetchall()
        if len(categoriesQuery) < 1:
            if data.get('count'): print(0)
            return

        # if data.get('sortby'):
        #     sortBy = data['sortby'].lower()
        #     keys = {"iden":0,"name":1,"taxonomy":2,"description":3,"count":5}
        #     if sortBy in keys:
        #         if not data.get("desc"): data['desc'] = False
        #         print(keys[sortBy])
        #         categoriesQuery.sort(key=lambda a: a[keys[sortBy]], reverse = data.get("desc"))
        #         print(categoriesQuery)


        import random
        if data.get("randomorder"): random.shuffle(categoriesQuery)
        if data.get('last'): categoriesQuery = categoriesQuery[-abs(int(data['last'])):]
        elif data.get('first'): categoriesQuery = categoriesQuery[:abs(int(data['first']))]

        if self.importedMode or data.get('importedmode'): return categoriesQuery

        if data.get('count'): print(str(len(categoriesQuery)))
        elif data.get("listids"):
            if len(categoriesQuery) > 0:
                for cat in categoriesQuery: print(cat[0])
        elif data.get('inspect'):
            if len(categoriesQuery) > 0:
                print('{')
                i = 1
                for cat in categoriesQuery:
                    print('"' + str(cat[FCM.ItemCol['Iden']]) + '": ')
                    self.inspectCategory({"category": str(cat[FCM.ItemCol['Iden']])})
                    if i < len(categoriesQuery):
                        print(',')
                    i += 1
                print('}')
        else:
            colData = []
            if not "iden" in withoutColumns: colData.append(
                {'minlength': 5, 'name': "Iden", 'index': 0, 'functions': (str,), 'maxlength':50})
            if not "name" in withoutColumns: colData.append(
                {'minlength': 5, 'name': "Name", 'index': 1, 'functions': (unquote, ), 'maxlength':25})
            if not "taxonomy" in withoutColumns: colData.append(
                {'minlength': 5, 'name': "Taxonomy", 'index': 2, 'functions': (), 'maxlength':50})
            if not "items" in withoutColumns: colData.append(
                {'minlength': 5, 'name': "Items", 'index': 5, 'functions': (str,), 'maxlength':50})
            for index, col in enumerate(colData):
                biggestLength = col['minlength']
                for result in categoriesQuery:
                    itemRowData = result[col['index']]
                    for func in col['functions']: itemRowData = func(itemRowData)
                    lenCol = len(itemRowData)
                    if lenCol > biggestLength: biggestLength = lenCol
                if biggestLength >  col['maxlength']: biggestLength =  col['maxlength']
                biggestLength += 3
                colData[index]["spaces"] = ''.join([char * biggestLength for char in ' '])
                colData[index]["lines"] = ''.join([char * biggestLength for char in '-'])

            columnNamesRow, columnLinesRow = "", ""
            for col in colData:
                columnNamesRow += col['name'] + col['spaces'][len(col['name']):]
                columnLinesRow += col['lines']
            print(columnNamesRow)
            print(columnLinesRow)

            colouredRows = self.config['options']['coloured_taxonomies'] and not data.get('nocolour')
            if colouredRows: from filecatman.core.printcolours import bcolours
            for result in categoriesQuery:
                itemRow = ""
                for col in colData:
                    itemRowData = result[col['index']]
                    for func in col['functions']: itemRowData = func(itemRowData)
                    itemRowData = itemRowData[:col['maxlength']]
                    printCol = itemRowData + col['spaces'][len(itemRowData):]
                    itemRow += printCol
                if colouredRows:
                    color = self.config['taxonomies'].get(result[2].capitalize()).colour
                    print(color+itemRow+bcolours.ENDC)
                else:
                    print(itemRow)
        self.db.close()


    def searchItems(self, data):
        if data.get('timer'):
            import time
            timerStart = time.perf_counter()
        additionalColumns, withoutColumns = [], []
        if data.get('col'): additionalColumns = data['col']
        if data.get('hidecol'): withoutColumns = data['hidecol']
        sizeIndex, fileDateIndex = None, None
        if not data.get('keepDatabaseOpen'): self.db.open()
        itemKeywordsOp = ""
        tableColumns = (('Name', 'item_name', quote),
                        ('Source', 'item_source', quote),
                        ('Description', 'item_description', quote))
        SQLWhere = []
        keywordsWhere = ''
        itemKeywordsType = "Phrase"
        itemKeywords = data.get('searchterms')
        self.logger.debug(itemKeywords)
        if itemKeywords:
            fieldsWhere = list()
            for nounName, col, wordFunction in tableColumns:
                if itemKeywordsType == "Keywords":
                    i = 0
                    for word in itemKeywords.split():
                        i += 1
                        if i == 1:
                            keywordsWhere = "({0} LIKE '%{1}%'".format(col, wordFunction(word))
                        else:
                            keywordsWhere += " AND {0} LIKE '%{1}%'".format(col, wordFunction(word))
                elif itemKeywordsType == "Phrase":
                    keywordsWhere = "({0} LIKE '%{1}%'".format(col, wordFunction(itemKeywords))
                keywordsWhere += ") \n"
                fieldsWhere.append(keywordsWhere)
            SQLName = "(" + " OR ".join(fieldsWhere) + ")"
            SQLWhere.append("{}".format(itemKeywordsOp) + SQLName)
            self.logger.debug(SQLWhere)

        _colsearches = list()
        if data.get("name"): _colsearches.append((data['name'], "", "item_name"))
        if data.get("source"): _colsearches.append((data['source'], "", "item_source"))
        if data.get("description"): _colsearches.append((data['description'], "", "item_description"))
        if data.get("withoutname"): _colsearches.append((data['withoutname'], "NOT ", "item_name"))
        if data.get("withoutsource"): _colsearches.append((data['withoutsource'], "NOT ", "item_source"))
        if data.get("withoutdescription"): _colsearches.append((data['withoutdescription'], "NOT ", "item_description"))
        if len(_colsearches) > 0:
            for colSearchPhrase, operator, column in _colsearches:
                fieldsWhere = list()
                keywordsWhere = "({0} LIKE '%{1}%'".format(column, quote(colSearchPhrase))
                keywordsWhere += ") \n"
                fieldsWhere.append(keywordsWhere)
                SQLName = "(" + " OR ".join(fieldsWhere) + ")"
                SQLWhere.append("{}".format(operator) + SQLName)
                self.logger.debug(SQLWhere)

        _keywords = list()
        if data.get("withkeywords"): _keywords.append((data['withkeywords'],""))
        if data.get("withoutkeywords"): _keywords.append((data['withoutkeywords'], "NOT "))
        if len(_keywords) > 0:
            for keyWords, operator in _keywords:
                fieldsWhere = list()
                for nounName, col, wordFunction in tableColumns:
                    i = 0
                    for word in keyWords:
                        i += 1
                        if i == 1:
                            keywordsWhere = "({0} LIKE '%{1}%'".format(col, wordFunction(word))
                        else:
                            keywordsWhere += " AND {0} LIKE '%{1}%'".format(col, wordFunction(word))
                    keywordsWhere += ") \n"
                    fieldsWhere.append(keywordsWhere)
                SQLName = "(" + " OR ".join(fieldsWhere) + ")"
                SQLWhere.append("{}".format(operator) + SQLName)
                self.logger.debug(SQLWhere)

        if data.get('nullcol'):
            tableNames = dict(name="name", description="description", source="source", md5="md5")
            for nullcol in data['nullcol']:
                if not nullcol in tableNames: continue
                nullSQL = "( i.item_{0} IS NULL) OR (i.item_{0} IS '' )".format(tableNames[nullcol])
                SQLWhere.append(nullSQL)
        if data.get('withoutnullcol'):
            tableNames = dict(name="name", description="description", source="source", md5="md5")
            for nullcol in data['withoutnullcol']:
                if not nullcol in tableNames: continue
                nullSQL = "( (i.item_{0} IS NOT NULL) AND (i.item_{0} IS NOT '') )".format(tableNames[nullcol])
                SQLWhere.append(nullSQL)

        if data.get("withitemtype"):
            itemTypes = list()
            for itemtype in data['withitemtype']:
                typeListResult = self.config['itemTypes'].get(itemtype.capitalize())
                if typeListResult: itemTypes.append(typeListResult.nounName)
            sqlAnyTypesWhere = "( i.type_id = '{0}' )".format(itemTypes.pop(0))
            for itemType in itemTypes: sqlAnyTypesWhere += " OR ( i.type_id = '{0}' )".format(itemType)
            SQLWhere.append("( {} )".format(sqlAnyTypesWhere))

        if data.get("withoutitemtype"):
            for itemtype in data['withoutitemtype']:
                typeListResult = self.config['itemTypes'].get(itemtype.capitalize())
                if typeListResult: itemtype = typeListResult.nounName
                SQLWhere.append("( i.type_id {0} '{1}' )".format("<>", itemtype))
        if data.get("withfileext"):
            for fileext in data['withfileext']:
                SQLWhere.append("( i.item_ext {0} '{1}' )".format("=", fileext))
        if data.get("withoutfileext"):
            for fileext in data['withoutfileext']:
                SQLWhere.append("( i.item_ext {0} '{1}' )".format("<>", fileext))
        if data.get("md5"): SQLWhere.append("( i.item_md5 GLOB '{}*' )".format(str(data['md5'])))
        if data.get("md5file"): SQLWhere.append("( i.item_md5 GLOB '{}*' )".format(getMD5FromPath(data['md5file'])))

        if data.get("withprimarycategory"):
            catResults = self.getCategoryFromInput(data["withprimarycategory"])
            if catResults:
                SQLWhere.append("( i.item_primary_category {0} '{1}' )".format("=", catResults[0][FCM.CatCol['Iden']]))
        if data.get("withoutprimarycategory"):
            catResults = self.getCategoryFromInput(data["withoutprimarycategory"])
            if catResults:
                SQLWhere.append("( i.item_primary_category {0} '{1}' )".format("<>", catResults[0][FCM.CatCol['Iden']]))

        _withdaterange = list()
        if data.get("withdaterange") and (len(data.get('withdaterange')) == 2):
            _withdaterange.append((data['withdaterange'][0],  data['withdaterange'][1], "BETWEEN"))
        if data.get("withoutdaterange") and (len(data.get('withoutdaterange')) == 2):
            _withdaterange.append((data['withoutdaterange'][0], data['withoutdaterange'][1], "NOT BETWEEN"))
        if len(_withdaterange) > 0:
            import dateutil.parser
            for itemDateFrom, itemDateTo, operator in _withdaterange:
                SQLWhere.append("( item_time {0} '{1}' AND '{2}' )".format(operator, itemDateFrom, itemDateTo))
        if data.get('withdategreaterthan'):
            import dateutil.parser
            itemDateFrom = dateutil.parser.parse(data['withdategreaterthan'])
            SQLWhere.append("( item_time {0} '{1}' )".format(">", itemDateFrom))
        if data.get('withdatelessthan'):
            import dateutil.parser
            itemDateFrom = dateutil.parser.parse(data['withdatelessthan'])
            SQLWhere.append("( item_time {0} '{1}' )".format("<", itemDateFrom))

        ## creation date
        _withcdaterange = list()
        if data.get("withcdaterange") and (len(data.get('withcdaterange')) == 2):
            _withcdaterange.append((data['withcdaterange'][0], data['withcdaterange'][1], "BETWEEN"))
        if data.get("withoutcdaterange") and (len(data.get('withoutcdaterange')) == 2):
            _withcdaterange.append((data['withoutcdaterange'][0], data['withoutcdaterange'][1], "NOT BETWEEN"))
        if len(_withcdaterange) > 0:
            import dateutil.parser
            for itemDateFrom, itemDateTo, operator in _withdaterange:
                SQLWhere.append("( item_creation_time {0} '{1}' AND '{2}' )".format(operator, itemDateFrom, itemDateTo))
        if data.get('withcdategreaterthan'):
            import dateutil.parser
            itemDateFrom = dateutil.parser.parse(data['withcdategreaterthan'])
            SQLWhere.append("( item_creation_time {0} '{1}' )".format(">", itemDateFrom))
        if data.get('withcdatelessthan'):
            import dateutil.parser
            itemDateFrom = dateutil.parser.parse(data['withcdatelessthan'])
            SQLWhere.append("( item_creation_time {0} '{1}' )".format("<", itemDateFrom))

        if data.get('withidgreaterthan'): SQLWhere.append("( item_id {0} '{1}' )".format(">", data['withidgreaterthan']))
        if data.get('withidlessthan'): SQLWhere.append("( item_id {0} '{1}' )".format("<", data['withidlessthan']))

        _taxonomies = list()
        if data.get("withtaxonomies"): _taxonomies.append((data['withtaxonomies'], "IN"))
        if data.get("withouttaxonomies"): _taxonomies.append((data['withouttaxonomies'], "NOT IN"))
        if len(_taxonomies) > 0:
            for taxonomies, operator in _taxonomies:
                for taxonomy in taxonomies:
                    tax = None
                    self.logger.debug(taxonomy)
                    taxListResult = self.config['taxonomies'].get(taxonomy.capitalize())
                    if taxListResult: tax = taxListResult.tableName
                    SQLTaxonomy = "SELECT tr.item_id \n" \
                                  "FROM term_relationships AS tr \n" \
                                  "INNER JOIN terms AS t ON (t.term_id = tr.term_id) \n" \
                                  "WHERE ( t.term_taxonomy = '{}' )".format(tax)
                    SQLWhere.append("( i.item_id {0} (\n{1}\n) )".format(operator, SQLTaxonomy))
        _categories = list()
        if data.get("withcategories"): _categories.append((data['withcategories'], "IN"))
        if data.get("withoutcategories"): _categories.append((data['withoutcategories'], "NOT IN"))
        if len(_categories) > 0:
            for categories, operator in _categories:
                for cat in categories:
                    self.logger.debug(cat)
                    catResults, taxonomy = self.getCategoryFromInput(cat)
                    self.logger.debug(catResults)
                    categoryIden = -9999
                    if catResults: categoryIden = catResults[0]
                    else:  self.logger.warning("Category not found")
                    SQLTaxonomy = "SELECT tr.item_id \n" \
                                  "FROM term_relationships AS tr \n" \
                                  "INNER JOIN terms AS t ON (t.term_id = tr.term_id) \n" \
                                  "WHERE ( t.term_taxonomy = '{}' )".format(taxonomy)
                    SQLTaxonomy += " AND ( tr.term_id = '{0}' )".format(categoryIden)
                    SQLWhere.append("( i.item_id {0} (\n{1}\n) )".format(operator, SQLTaxonomy))

        _categories = list()
        if data.get("withanycategories"): _categories.append((data['withanycategories'], "IN"))
        if len(_categories) > 0:
            for categories, operator in _categories:
                __catIdens = list()
                for cat in categories:
                    self.logger.debug(cat)
                    catResults, taxonomy = self.getCategoryFromInput(cat)
                    self.logger.debug(catResults)
                    if catResults: __catIdens.append(catResults[0])
                    else: self.logger.warning("Category not found")
                if len(__catIdens) > 0:
                    sqlAnyCatsWhere = "WHERE ( tr.term_id = '{0}' )".format(__catIdens.pop(0))
                    for cat in __catIdens: sqlAnyCatsWhere += " OR ( tr.term_id = '{0}' )".format(cat)
                    SQLAnyCats = "SELECT tr.item_id \n" \
                                  "FROM term_relationships AS tr \n" \
                                  "INNER JOIN terms AS t ON (t.term_id = tr.term_id) \n"
                    SQLAnyCats += sqlAnyCatsWhere
                    SQLWhere.append("( i.item_id {0} (\n{1}\n) )".format(operator, SQLAnyCats))
                else: SQLWhere.append("( i.item_id == '-999999' )")

        _items = list()
        if data.get("withitems"): _items.append((data['withitems'], "IN"))
        if data.get("withoutitems"): _items.append((data['withoutitems'], "NOT IN"))
        if len(_items) > 0:
            for itemPaths, operator in _items:
                __itemIdens = list()
                for itemPath in itemPaths:
                    self.logger.debug(itemPath)
                    item = self.getItemFromPath(itemPath)
                    if item: __itemIdens.append(item[0])
                    else: self.logger.warning("Item not found")
                if len(__itemIdens) > 0:
                    sqlAnyItemsWhere = "WHERE ( i.item_id = '{0}' )".format(__itemIdens.pop(0))
                    for itemId in __itemIdens: sqlAnyItemsWhere += " OR ( i.item_id = '{0}' )".format(itemId)
                    SQLAnyItems = "SELECT i.item_id \n" \
                                 "FROM items AS i \n"
                    SQLAnyItems += sqlAnyItemsWhere
                    SQLWhere.append("( i.item_id {0} (\n{1}\n) )".format(operator, SQLAnyItems))
                else:
                    SQLWhere.append("( i.item_id == '-999999' )")

        if data.get("withduplicate"):
            duplicateCol = data.get("withduplicate").lower()
            SQLDuplicate = '''
            SELECT a.item_id
            FROM items as a
            JOIN (SELECT item_{0}, COUNT(*)
            FROM items 
            GROUP BY item_{0}
            HAVING count(*) > 1 ) as b
            ON a.item_{0} = b.item_{0}
            '''.format(duplicateCol)
            SQLWhere.append("( i.item_id {0} (\n{1}\n) )".format("IN", SQLDuplicate))
        if len(SQLWhere) > 0:
            whereJoined = "\nWHERE "+" AND \n".join(SQLWhere)
        else:
            whereJoined = ''
        SQL = "SELECT DISTINCT i.item_id AS 'ID', item_name AS 'Name', \n" \
              "type_id AS 'Type', item_time AS 'Time', item_source AS 'Source', item_ext AS 'ext',  \n" \
              "( SELECT COUNT(*) FROM term_relationships WHERE term_relationships.item_id = i.item_id ) AS 'Relations', \n" \
              "item_creation_time as 'CreationTime', item_description as 'Description', \n" \
              "item_md5 as 'Md5' \n" \
              "FROM items AS i {} \n".format(whereJoined)
        if data.get('sortby'):
            sortBy = data['sortby'].lower()
            keys = {"iden": "i.item_id", "name": "i.item_name", "type": "i.type_id", "date": "i.item_time",
                    "source": "i.item_source", "ext": "i.item_ext", "categories":"Relations",
                    "md5": "i.item_md5", "creationdate": "i.item_creation_time"}
            if sortBy in keys:
                directionOrder = "ASC"
                if data.get("desc"): directionOrder = "DESC"
                SQL += "ORDER BY {} {}".format(keys[sortBy],directionOrder)
            else: SQL += "ORDER BY i.item_id ASC"
        else: SQL += "ORDER BY i.item_id ASC"
        self.logger.debug(SQL)
        query = self.db.cur.execute(SQL)
        searchResults = query.fetchall()
        self.logger.debug(searchResults)
        if not data.get('keepDatabaseOpen'): self.db.close()
        if len(searchResults) < 1:
            if data.get('count'): print(0)
            return
        # if sortBy:
        #     sortBy = sortBy.lower()
        #     keys = {"iden":0,"name":1,"type":2,"date":3,"source":4,"ext":5}
        #     if sortBy in keys:
        #         if not data.get("desc"): data['desc'] = False
        #         print(keys[sortBy])
        #         searchResults.sort(key=lambda a: a[keys[sortBy]], reverse = data.get("desc"))
        #         print(searchResults)

        if data.get("withcategorycount"): searchResults = [i for i in searchResults if i[6] == int(data['withcategorycount'])]
        if data.get("withoutcategorycount"): searchResults = [i for i in searchResults if not i[6] == int(data['withoutcategorycount'])]
        if data.get("countmorethan"): searchResults = [i for i in searchResults if i[6] > int(data['countmorethan'])]
        if data.get("countlessthan"): searchResults = [i for i in searchResults if i[6] < int(data['countlessthan'])]

        # if data.get("md5"):
        #     newSearchResults = list()
        #     for index, item in enumerate(searchResults):
        #         print(item[0])
        #         filepath = os.path.join(self.config['options']['default_data_dir'],
        #                                 self.config['itemTypes'].dirFromNoun(item[2]),
        #                                 str(item[0]) + '.' + item[5])
        #         if getMD5FromFile(filepath).startswith(data['md5']):
        #             newSearchResults.append(item)
        #     searchResults = newSearchResults

        if data.get("withmissingfile"):
            newSearchResults = list()
            for index, item in enumerate(searchResults):
                filepath = os.path.join(self.config['options']['default_data_dir'],
                                        self.config['itemTypes'].dirFromNoun(item[2]),
                                        str(item[0]) + '.' + item[5])
                if not os.path.exists(filepath):
                    newSearchResults.append(item)
            searchResults = newSearchResults
        if data.get('sortby') == "size" or data.get('sizemorethan') or data.get('sizelessthan') \
                or "size" in additionalColumns or 'filedate' in additionalColumns or data.get('size'):
            newSearchResults = list()
            for index, item in enumerate(searchResults):
                filepath = os.path.join(self.config['options']['default_data_dir'],
                                        self.config['itemTypes'].dirFromNoun(item[2]),
                                        str(item[0]) + '.' + item[5])
                file_stats = os.stat(filepath)
                if data.get('sizemorethan'):
                    sizeMoreThan = unformatBytes(data.get('sizemorethan'))
                    if file_stats.st_size < sizeMoreThan: continue
                if data.get('sizelessthan'):
                    sizeLessThan = unformatBytes(data.get('sizelessthan'))
                    if file_stats.st_size > sizeLessThan: continue
                newCols = []
                itemIndexLength = len(item) - 1
                if data.get('sortby') == "size" or data.get('sizemorethan') or data.get('sizelessthan') \
                        or "size" in additionalColumns or data.get('size'):
                    newCols.append(file_stats.st_size)
                    itemIndexLength += 1
                    sizeIndex = itemIndexLength
                if data.get('sortby') == "filedate" or 'filedate' in additionalColumns:
                    newCols.append(file_stats.st_mtime)
                    itemIndexLength += 1
                    fileDateIndex = itemIndexLength
                newItem = [*item, *newCols]
                newSearchResults.append(newItem)
            if data.get('sortby') == "size":
                if not data.get("desc"): data['desc'] = False
                newSearchResults.sort(key=lambda a: a[sizeIndex], reverse = data.get("desc"))
            searchResults = newSearchResults


        if data.get("withduplicatefile"):
            from filecmp import cmp
            newSearchResults = list()
            for index, item in enumerate(searchResults):
                print(item)
                if self.config['itemTypes'].get(item[2]).isWeblinks: continue
                filepath = os.path.join(self.config['options']['default_data_dir'],
                                        self.config['itemTypes'].dirFromNoun(item[2]),
                                        str(item[0]) + '.' + item[5])
                if not os.path.exists(filepath): continue
                for index2, item2 in enumerate(searchResults):
                    if self.config['itemTypes'].get(item2[2]).isWeblinks: continue
                    filepath2 = os.path.join(self.config['options']['default_data_dir'],
                                            self.config['itemTypes'].dirFromNoun(item2[2]),
                                            str(item2[0]) + '.' + item2[5])
                    if not os.path.exists(filepath2): continue
                    if item == item2: continue
                    if_dupl = cmp(
                        filepath,
                        filepath2,
                        shallow=False
                    )
                    if if_dupl:
                        newSearchResults.append(item)
                        break
            searchResults = newSearchResults

        import random
        if data.get('randomorder'): random.shuffle(searchResults)
        if data.get('last'): searchResults = searchResults[-abs(int(data['last'])):]
        elif data.get('first'): searchResults = searchResults[:abs(int(data['first']))]
        if data.get('itemsperpage'):
            itemPages = chunks(searchResults,abs(int(data['itemsperpage'])))
            if data.get('page'): searchResults = itemPages[abs(int(data['page']))+1]
            elif data.get('lastpage'): searchResults = itemPages[len(itemPages)-1]
            else: searchResults = itemPages[0]

        if self.importedMode or data.get('importedmode'): return searchResults

        if data.get('openinmanager') or data.get('printresultsdir') or data.get('listnamedpaths'):
            dataDir = self.config['options']['default_data_dir']
            searchResultsDir = self.config['options']['default_results_dir']
            if not os.path.exists(searchResultsDir): os.makedirs(searchResultsDir)
            dateTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            linksDir = os.path.join(searchResultsDir, dateTime)
            self.logger.debug(linksDir)
            for result in searchResults:
                itemName = unquote(result[1])
                itemtype = result[2]
                itemIden = result[0]
                itemExt =  result[5]
                isWeblink = self.config['itemTypes'].get(itemtype).isWeblinks
                typeDir = self.config['itemTypes'].dirFromNoun(itemtype)
                itemName = itemName.replace(" ", "_")
                linkName = str(itemIden) + "_" + itemName
                if isWeblink: itemExt = desktopFileExt()
                if not itemName.endswith("."+itemExt): linkName += "." + itemExt
                filePath = os.path.join(dataDir, typeDir, str(itemIden) + "." + itemExt)
                linkPath = os.path.join(linksDir, linkName)
                try:
                    createLink(filePath, linkPath)
                except OSError as exc:
                    if exc.errno == 36 or exc.winerror == 123: ## Name too long, Winerror
                        linkName = str(itemIden)
                        if isWeblink: itemExt = desktopFileExt()
                        if not itemName.endswith("." + itemExt): linkName += "." + itemExt
                        linkPath = os.path.join(linksDir, linkName)
                        createLink(filePath, linkPath)
                    else:
                        raise
                if data.get('listnamedpaths'): print(linkPath)
            if data.get('printresultsdir'):
                print(linksDir)
            if data.get('openinmanager'):
                import subprocess, platform
                if platform.system() == "Windows":
                    os.startfile(linksDir)
                elif platform.system() == "Darwin":
                    import subprocess
                    subprocess.call(('open', linksDir))
                else:    
                    subprocess.Popen(['xdg-open', linksDir],stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        elif data.get('listids'):
            for result in searchResults:
                itemIden = result[0]
                print(itemIden)
        elif data.get('listpaths'):
            for result in searchResults:
                itemtype = result[2]
                itemIden = result[0]
                itemExt =  result[5]
                dataDir = self.config['options']['default_data_dir']
                typeDir = self.config['itemTypes'].dirFromNoun(itemtype)
                filePath = os.path.join(dataDir, typeDir, str(itemIden) + "." + itemExt)
                print(filePath)
        elif data.get('count'): print(str(len(searchResults)))
        elif data.get('size'):
            totalSize = 0
            for searchItem in searchResults:
                totalSize += searchItem[sizeIndex]
            print(str(totalSize))
            # print(formatBytes(totalSize))
        elif data.get('timer'):
                import time
                timerEnd = time.perf_counter()
                timerDiff = timerEnd - timerStart
                print(timerDiff)
        elif data.get('inspectitems'):
            if len(searchResults) > 0:
                print('{')
                i = 1
                for item in searchResults:
                    print('"'+str(item[FCM.ItemCol['Iden']])+'": ')
                    self.inspectItem({"filepath": str(item[FCM.ItemCol['Iden']])})
                    if i < len(searchResults):
                        print(',')
                    i+=1
                print('}')
        elif data.get('export'):
            if not data.get('keepDatabaseOpen'): self.db.open()
            exportItems = list()
            exportCategories = list()
            for item in searchResults:
                exportItems.append(self.db.selectItem(itemID=item[FCM.ItemCol['Iden']]))
                relations = self.db.selectRelations(itemID=item[FCM.ItemCol['Iden']])
                for rel in relations:
                    category = self.db.selectCategory(catID=rel[0])
                    exportCategories.append(category)
            exportCategories = [*set(exportCategories)]
            self.exportProject({'filepath': data['export'], 'exportresults': (exportCategories, exportItems)})
            if not data.get('keepDatabaseOpen'): self.db.close()
        else:
            colData =  []
            if not "iden" in withoutColumns: colData.append({'minlength':5, 'name':"Iden", 'index':0, 'functions':(str,), 'maxlength':50})
            if not "name" in withoutColumns:
                nameFuncs = [unquote,]
                if data.get('noemoji'):
                    import cleantext
                    nameFuncs.append(cleantext.remove_emoji)
                colData.append({'minlength':10, 'name':"Name", 'index':1, 'functions':nameFuncs, 'maxlength':50})
            if not "type" in withoutColumns: colData.append({'minlength':5, 'name':"Type", 'index':2, 'functions':(), 'maxlength':50})
            if "date" in additionalColumns:
                colData.append({'minlength':10, 'name':"Date", 'index':3, 'functions':(), 'maxlength':50})
            if not "cats" in withoutColumns: colData.append( {'minlength':5, 'name':"Cats", 'index':6, 'functions':(str,), 'maxlength':50})
            if data.get('sortby') == "source" or "source" in additionalColumns:
                colData.append({'minlength': 10, 'name': "Source", 'index': 4, 'functions': (unquote,), 'maxlength':50})
            if data.get('sortby') == "description" or "description" in additionalColumns:
                colData.append({'minlength': 10, 'name': "Description", 'index': 8, 'functions': (unquote,), 'maxlength':50})
            if not "md5" in withoutColumns:
                colData.append({'minlength': 10, 'name': "Md5", 'index': 9, 'functions': (lambda a:a[:12]+"..",), 'maxlength':14})
            if data.get('sortby') == "creationdate" or data.get('withcdaterange') \
                    or data.get('withoutcdaterange') or data.get('withcdategreaterthan') or \
                    data.get('withcdatelessthan') or "creationdate" in additionalColumns:
                colData.append({'minlength': 10, 'name': "Creation Date", 'index': 7, 'functions': (), 'maxlength':50})
            if data.get('sortby') == "size" or data.get('sizemorethan') or data.get('sizelessthan') or "size" in additionalColumns:
                colData.append({'minlength': 10, 'name': "Size", 'index': sizeIndex, 'functions': (formatBytes,), 'maxlength':50})
            if data.get('sortby') == "filedate" or "filedate" in additionalColumns:
                colData.append({'minlength': 10, 'name': "File Modification Date", 'index': fileDateIndex, 'functions': (timeStampToString,), 'maxlength':50})
            if data.get('sortby') == "ext" or "ext" in additionalColumns:
                colData.append({'minlength': 3, 'name': "Ext", 'index': 5, 'functions': (), 'maxlength':12})

            for index, col in enumerate(colData):
                biggestLength = col['minlength']
                for result in searchResults:
                    itemRowData = result[col['index']]
                    for func in col['functions']: itemRowData = func(itemRowData)
                    lenCol = len(itemRowData)
                    if lenCol > biggestLength: biggestLength = lenCol
                if biggestLength > col['maxlength']: biggestLength = col['maxlength']
                biggestLength += 3
                colData[index]["spaces"] = ''.join([char * biggestLength for char in ' '])
                colData[index]["lines"] = ''.join([char * biggestLength for char in '-'])

            columnNamesRow, columnLinesRow = "", ""
            for col in colData:
                columnNamesRow+= col['name']+col['spaces'][len(col['name']):]
                columnLinesRow+= col['lines']
            print(columnNamesRow)
            print(columnLinesRow)

            for result in searchResults:
                itemRow = ""
                for col in colData:
                    itemRowData = result[col['index']]
                    for func in col['functions']: itemRowData = func(itemRowData)
                    itemRowData = itemRowData[:col['maxlength']]
                    printCol = itemRowData+col['spaces'][len(itemRowData):]
                    itemRow += printCol
                print(itemRow)

        if data.get('launch'):
            import subprocess, platform
            dataDir = self.config['options']['default_data_dir']
            for result in searchResults:
                itemName = unquote(result[1])
                itemtype = result[2]
                itemIden = result[0]
                itemExt =  result[5]
                typeDir = self.config['itemTypes'].dirFromNoun(itemtype)
                filePath = os.path.join(dataDir, typeDir, str(itemIden) + "." + itemExt)
                if platform.system() == "Windows":
                    os.startfile(filePath)
                elif platform.system() == "Darwin":
                    import subprocess
                    subprocess.call(('open', filePath))
                else:
                    subprocess.Popen(['xdg-open', filePath],stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)




    def createCategory(self, data):
        if not data.get('keepDatabaseOpen'): self.db.open()
        catResults, taxonomy = self.getCategoryFromInput(data['category'])
        self.logger.debug(catResults)
        if not catResults:
            if ":" in data['category']:
                term = data['category'].split(":",1)[1]
                if len(term) == 0: return False
            else:
                term = data['category']
            self.createTaxonomyIfNotExisting(taxonomy)
            self.db.newCategory({"name": quote(term), "taxonomy": taxonomy})
            catID = self.db.lastInsertId
        else: self.logger.warning("Category already exists")

        if not data.get('keepDatabaseOpen'): self.db.commit()
        if not data.get('keepDatabaseOpen'): self.db.close()


    def downloadItem(self, _data):
        data = deepCopy(_data)
        if not isURL(data['filepath']): raise Exception('Not a valid URL')
        destPath = getTmpPath()
        if not downloadFile(data['filepath'],destPath): raise Exception('Unable to download')
        if not data.get('name'):
            urlName = os.path.basename(data['filepath'])
            if urlName: data['name'] = urlName
        data['filepath'] = destPath
        self.uploadItem(data)

    def uploadItem(self, _data):
        import copy
        data = copy.deepcopy(_data)
        keepDatabaseOpen = data.get('keepDatabaseOpen')
        if not keepDatabaseOpen: self.db.open()
        isWeblink = False
        fileType, fileExtension = None, None
        if os.path.exists(data['filepath']):
            pass
        elif isURL(data['filepath']):
            isWeblink = True
            fileExtension = desktopFileExt()
            fileType = "Weblink"
            data['source'] = data['filepath']

        if data.get('datetime'):
            import dateutil.parser
            try:
                data['datetime'] = dateutil.parser.parse(data['datetime']).strftime("%Y-%m-%d %H:%M:%S")
            except dateutil.parser.ParserError:
                data.pop("datetime")
        else:
            if not isWeblink:
                self.logger.debug(os.path.getmtime(data['filepath']))
                dt = datetime.datetime.fromtimestamp(os.path.getmtime(data['filepath']))
                self.logger.debug(dt.strftime("%Y-%m-%d %H:%M:%S"))
                data['datetime'] = dt.strftime("%Y-%m-%d %H:%M:%S")
        if not data.get('creationtime'):
            data['creationtime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not data.get('name'):
            if not isWeblink: data['name'] = quote(os.path.basename(data['filepath']))
            else: data['name'] = "Weblink"
        else:  data['name'] = quote(data['name'])
        if not isWeblink:
            fileExtension = os.path.splitext(data['filepath'])[1][1:].lower().strip()
            fileType = self.config['itemTypes'].nounFromExtension(fileExtension)
        if not fileType:
            import magic
            magicFileType = magic.from_file(data['filepath'], mime=True)
            self.logger.debug(magicFileType)
            magicFileExtension = magicFileType.split("/")[1]
            if magicFileExtension == "jpeg": magicFileExtension = "jpg"
            if not fileExtension: fileExtension = magicFileExtension

            fileType = self.config['itemTypes'].nounFromExtension(fileExtension)
            if not fileType:
                fileType = self.config['itemTypes'].nounFromExtension(magicFileExtension)
            if not fileType:
                magicTypeName = magicFileType.split("/")[0]
                self.logger.debug(magicTypeName)
                # tableName = self.config['itemTypes'].tableFromNoun(magicTypeName)
                if magicTypeName in self.config['itemTypes'].tableNames():
                    fileTypeObj = self.config['itemTypes'][magicTypeName]
                    fileTypeObj .addExtension(fileExtension)
                    fileType = fileTypeObj.nounName
                else:
                    newItemTypeObj = ItemType()
                    newItemTypeObj.setNounName(str(magicTypeName).capitalize())
                    newItemTypeObj.setPluralName(pluralize(str(magicTypeName).capitalize()))
                    newItemTypeObj.setDirName(pluralize(str(magicTypeName).capitalize()))
                    newItemTypeObj.setTableName(str(magicTypeName))
                    newItemTypeObj.setEnabled(True)
                    if fileExtension:
                        newItemTypeObj.addExtension(fileExtension)
                    elif magicFileExtension:
                        newItemTypeObj.addExtension(magicFileExtension)
                    self.config['itemTypes'].append(newItemTypeObj)
                    fileType = newItemTypeObj.nounName
        if fileType:
            if not data.get('type'): data['type'] = fileType
            if not data.get('ext'): data['ext'] = fileExtension
        else:
            raise Exception("File type not recognised")
        self.logger.debug(data)

        if data.get('updateifduplicate') and not isWeblink:
            existingItems = self.db.selectItems({"item_md5": getMD5FromFile(data['filepath'])})
            if len(existingItems) > 0:
                updateData = dict()
                updateData['filepath'] = str(existingItems[0][0])
                if data.get('categories'): updateData['addcategories'] = data['categories']
                if data.get('source'): updateData['setsource'] = data['source']
                if data.get('description'): updateData['setdescription'] = data['description']
                if data.get('primarycategory'): updateData['setprimarycategory'] = data['primarycategory']
                if data.get('datetime'): updateData['setdatetime'] = data['datetime']
                if data.get('name'): updateData['setname'] = data['name']
                return self.updateItem(updateData)

        self.db.newItem(data)
        fileID = self.db.lastInsertId
        if fileID:
            if data.get('primarycategory'):
                if data.get('categories'):
                    data['categories'].insert(0, data['primarycategory'])
                else:
                    data['categories'] = [data['primarycategory'], ]
            if data.get('categories'):
                primaryCategoryCreated = False
                for cat in data['categories']:
                    self.logger.debug(cat)
                    catResults, taxonomy = self.getCategoryFromInput(cat)
                    self.logger.debug(catResults)
                    if not catResults:
                        if ":" in cat:
                            term = cat.split(":",1)[1]
                            if len(term) == 0: return False
                        else:
                            term = cat
                        self.createTaxonomyIfNotExisting(taxonomy)
                        self.db.newCategory({"name": quote(term), "taxonomy": taxonomy})
                        catID = self.db.lastInsertId
                        self.db.newRelation({'item': fileID, 'term': catID})
                    else:
                        catID = catResults[0]
                        relationExists = self.db.checkRelation(itemID=fileID, termID=catID).fetchall()
                        if len(relationExists) == 0:
                            self.db.newRelation({'item': fileID, 'term': catID})
                        else:
                            self.logger.info("Item already has relation for '" + taxonomy + ":" + catResults[
                                FCM.CatCol['Name']] + "'")
                    if not primaryCategoryCreated:
                        self.db.updatePrimaryCategory(itemID=fileID, newPrimaryCategory=catID)
                        primaryCategoryCreated = True
        else:
            self.logger.error("Unable to insert item.")
            self.db.rollback()
            raise Exception("Unable to insert item.")
        dataDir = self.config['options']['default_data_dir']
        dirType = self.config['itemTypes'].dirFromNoun(data['type'])
        if not isWeblink:
            newFileName = str(fileID)+'.'+fileExtension
            fileDestination = getDataFilePath(dataDir, dirType, newFileName)
            if not os.path.exists(getDataFilePath(dataDir, dirType, newFileName)):
                if uploadFile(self.config, data['filepath'], fileDestination, data['type']):
                    self.db.updateMD5(itemID=fileID, newMD5=getMD5FromFile(fileDestination))
                else:
                    self.logger.error("Error Uploading File")
            else:
                self.logger.error("File with ID already exists")
        else:
            dataDir = self.config['options']['default_data_dir']
            dirType = self.config['itemTypes'].dirFromNoun(data['type'])
            filePath = os.path.join(dataDir, dirType, str(fileID)+"."+desktopFileExt())
            if not createDesktopFile(filePath, unquote(data['name']), unquote(data['source'])):
                self.logger.error("Unable to create desktop file")
        if not keepDatabaseOpen:
            self.db.commit()
            self.db.close()
        if self.importedMode: return fileID

    def inspectCategory(self, data):
        catData = dict()
        if not data.get('category'): return False
        self.db.open()
        category, taxonomy = self.getCategoryFromInput(data.get("category"))
        if not category: raise Exception("Category not found")
        for colName in ('Iden','Name', 'Taxonomy', 'Description', 'Parent', 'Count'):
            catData[colName] = category[FCM.CatCol[colName]]
        if catData.get('Name'): catData['Name'] = unquote(catData['Name'])
        relations = self.db.selectCategoryRelations(termID=catData['Iden'])
        catData['Relations'] = list()
        for rel in relations:
            item = self.db.selectItem(rel[0])
            catData['Relations'].append(item)

        self.db.commit()
        self.db.close()

        import json
        print(json.dumps(catData, indent=4))

    def deleteTaxonomy(self, _data):
        if not _data.get('taxonomy'): return False
        import copy
        data = copy.deepcopy(_data)
        self.db.open()
        taxInput = data.get("taxonomy")
        taxListResult = self.config['taxonomies'].get(taxInput.capitalize())
        if taxListResult: taxParent = taxListResult.tableName
        else: raise Exception("Taxonomy not found")
        catResults = self.db.selectCategories(
            {"term_taxonomy": taxParent}).fetchall()
        if len(catResults) > 0:
            for cat in catResults: self.db.deleteCategory(cat[FCM.CatCol['Iden']])
        self.config['taxonomies'].remove(taxListResult)
        self.db.commit()
        self.db.close()

    def deleteCategory(self, _data):
        if not _data.get('category'): return False
        import copy
        data = copy.deepcopy(_data)
        keepDatabaseOpen = data.get('keepDatabaseOpen')
        if not keepDatabaseOpen: self.db.open()
        category, taxonomy = self.getCategoryFromInput(data.get("category"))
        if not category: raise Exception("Category not found")
        self.db.deleteCategory(category[FCM.CatCol['Iden']])
        if not keepDatabaseOpen:
            self.db.commit()
            self.db.close()

    def deleteItemRelations(self, data):
        if not data.get("filepath"): return False
        self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item: raise Exception("Item not found")
        self.db.deleteRelations(item[FCM.ItemCol['Iden']])
        self.db.commit()
        self.db.close()

    def deleteCategoryRelations(self, data):
        if not data.get("category"): return False
        if not data.get('keepDatabaseOpen'): self.db.open()
        category, taxonomy = self.getCategoryFromInput(data.get("category"))
        if not category: raise Exception("Category not found")
        self.db.deleteRelations(iden=category[FCM.ItemCol['Iden']], col="term_id")
        if not data.get('keepDatabaseOpen'):
            self.db.commit()
            self.db.close()

    def deleteItem(self, _data):
        import copy
        data = copy.deepcopy(_data)
        self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item:
            self.logger.error("Item not found")
            return False
        filepath = os.path.join(self.config['options']['default_data_dir'],
                                self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
        fileID = item[FCM.ItemCol['Iden']]
        if self.db.deleteItem(fileID):
            if os.path.exists(filepath): deleteFile(self, filepath)
        self.db.commit()
        self.db.close()

    def getCategoryFromInput(self, _categoryInput):
        category = None
        categoryInput = str(_categoryInput)
        if ":" in categoryInput:
            taxonomy = categoryInput.split(":",1)[0]
            taxListResult = self.config['taxonomies'].get(taxonomy.capitalize())
            if taxListResult: taxonomy = taxListResult.tableName
            term = categoryInput.split(":",1)[1]
            if len(taxonomy) == 0: taxonomy = self.config['options']['default_taxonomy']
            if len(term) == 0: return False, taxonomy
        else:
            term = categoryInput
            taxonomy = self.config['options']['default_taxonomy']

        catResults = self.db.selectCategories(
            {"term_name": quote(term), "term_taxonomy": taxonomy}).fetchall()
        self.logger.debug(catResults)
        if len(catResults) > 0:
            if len(catResults) > 1:
                self.logger.warning("Multiple categories resolved from Input")
            category = catResults[0]
        elif categoryInput.isnumeric():
            category = self.db.selectCategory(catID=int(categoryInput))
            if category: taxonomy = category[2]
            else: return False, taxonomy
        if not category: return False, taxonomy
        return category, taxonomy


    def renameCategory(self, data):
        self.db.open()
        category, taxonomy = self.getCategoryFromInput(data.get("category"))
        if not category: raise Exception("Category not found")
        self.db.renameCategory(category[FCM.CatCol['Iden']], quote(data['newname']))
        self.db.commit()
        self.db.close()

    def renameItem(self, data):
        self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item: raise Exception("Item not found")
        self.db.renameItem(item[FCM.ItemCol['Iden']], quote(data['newname']))
        self.db.commit()
        self.db.close()

    def createTaxonomyIfNotExisting(self, taxonomy):
        if taxonomy not in self.config['taxonomies'].tableNames():
            taxonomyObj = Taxonomy()
            taxonomyObj.setNounName(str(taxonomy).capitalize())
            taxonomyObj.setPluralName(pluralize(str(taxonomy).capitalize()))
            taxonomyObj.setDirName(str(taxonomy).capitalize())
            taxonomyObj.setTableName(str(taxonomy))
            taxonomyObj.setEnabled(True)
            taxonomyObj.setHasChildren(True)
            taxonomyObj.setIsTags(False)
            self.config['taxonomies'].append(taxonomyObj)

    def setTaxonomyColour(self, data):
        print(data)
        if not data.get("taxonomy"): return False
        taxInput = data.get("taxonomy")
        printColour = getPrintColourFromName(data.get("colour"))
        parentTaxListResult = self.config['taxonomies'].get(taxInput.capitalize())
        if parentTaxListResult:
            parentTaxListResult.colour = printColour
            self.config['options']['coloured_taxonomies'] = True
        else: raise Exception("Taxonomy not found")

    def mergeTaxonomies(self, data):
        print(data)
        if not data.get("taxonomy"): return False
        taxInput = data.get("taxonomy")
        parentTaxListResult = self.config['taxonomies'].get(taxInput.capitalize())
        if parentTaxListResult: taxParent = parentTaxListResult.tableName
        else: raise Exception("Taxonomy not found")
        self.db.open()
        if data.get('with'):
            for taxToMerge in data['with']:
                childTaxListResult = self.config['taxonomies'].get(taxToMerge.capitalize())
                if not childTaxListResult: continue
                if childTaxListResult == parentTaxListResult: continue
                taxChild = childTaxListResult.tableName
                childCatResults = self.db.selectCategories(
                    {"term_taxonomy": taxChild}).fetchall()
                print(childCatResults)
                for childCat in childCatResults:
                    parentCat = self.db.selectCategories(
                        {"term_name": childCat[FCM.CatCol['Name']],
                         "term_taxonomy": taxParent}).fetchone()
                    if parentCat:
                        self.logger.debug("term already exists for")
                        self.mergeCategories(
                            {"category": parentCat[FCM.CatCol['Iden']], "with": [childCat[FCM.CatCol['Iden']],],
                             'keepDatabaseOpen': True})
                    else:
                        self.logger.debug("term not existing for")
                        self.db.newCategory({"name": childCat[FCM.CatCol['Name']], "taxonomy": taxParent})
                        catID = self.db.lastInsertId
                        self.mergeCategories(
                            {"category": catID, "with": [childCat[FCM.CatCol['Iden']], ],
                             'keepDatabaseOpen': True})
                self.config['taxonomies'].remove(childTaxListResult)
        self.db.commit()
        self.db.close()

    def mergeDuplicateItems(self, data):
        self.db.open()
        searchResults = self.searchItems({
            "keepDatabaseOpen": True,
            "withduplicate": "md5",
            "importedmode": True,
            "sortby": "md5"
        })
        if not searchResults: return
        duplicatesList = dict()
        for item in searchResults:
            filepath = os.path.join(self.config['options']['default_data_dir'],
                                    self.config['itemTypes'].dirFromNoun(item[2]),
                                    str(item[0]) + '.' + item[5])
            fileMd5 = getMD5FromFile(filepath)
            itemMd5 = item[9]
            if not fileMd5 == itemMd5:
                self.db.updateMD5(item[0], fileMd5)
                itemMd5 = fileMd5
            if itemMd5 not in duplicatesList:
                duplicatesList[itemMd5] = list()
                duplicatesList[itemMd5].append(item)
            else: duplicatesList[itemMd5].append(item)
        _duplicatesList = dict()
        for key, dupList in duplicatesList.items():
            if len(dupList) > 1:
                _duplicatesList[key] = dupList
        duplicatesList = _duplicatesList
        for md5Key, dupeList in duplicatesList.items():
            parentIndex = 0
            if data.get("intolastitem"): parentIndex = len(dupeList)-1
            parentItem = dupeList.pop(parentIndex)
            mergeWith = list()
            for index, item in enumerate(dupeList):
                mergeWith.append(str(item[0]))
            self.mergeItems({
                "keepDatabaseOpen": True,
                "filepath": str(parentItem[0]),
                "with": mergeWith
            })
        self.db.commit()
        self.db.close()

    def copyCategoryRelations(self, data):
        keepDatabaseOpen = data.get('keepDatabaseOpen')
        if not keepDatabaseOpen: self.db.open()
        if not data.get('from'): Exception("No categories specified")
        category, taxonomy = self.getCategoryFromInput(data.get("category"))
        if not category:
            if ":" in data.get("category"):
                term = data.get("category").split(":", 1)[1]
                if len(term) == 0: return False
            else:
                term = data.get("category")
            self.createTaxonomyIfNotExisting(taxonomy)
            self.db.newCategory({"name": quote(term), "taxonomy": taxonomy})
            catID = self.db.lastInsertId
            category, taxonomy = self.getCategoryFromInput(str(catID))
            if not category: raise Exception("Category not found")
        existingIdensList = list()
        existingRelations = self.db.selectCategoryRelations(termID=category[FCM.CatCol['Iden']])
        if existingRelations:
            for rel in existingRelations: existingIdensList.append(rel[0])
        if data.get('from'):
            itemIdensList = list()
            for catToMerge in data['from']:
                categoryMerge, taxonomyMerge = self.getCategoryFromInput(catToMerge)
                if categoryMerge == category: continue
                if not categoryMerge: continue
                relations = self.db.selectCategoryRelations(termID=categoryMerge[FCM.CatCol['Iden']])
                for rel in relations:
                    itemIdensList.append(rel[0])
            itemIdensList = [*set(itemIdensList)]
            newIdensList = [i for i in itemIdensList if i not in existingIdensList]
            for itemIden in newIdensList:
                relationExists = self.db.checkRelation(
                    itemID=itemIden, termID=category[FCM.CatCol['Iden']]).fetchall()
                if len(relationExists) == 0:
                    self.db.newRelation({'item': itemIden, 'term': category[FCM.CatCol['Iden']]})
                else:
                    self.logger.info("Category already has relation for Item: " + itemIden)
        if not keepDatabaseOpen: self.db.commit()
        if not keepDatabaseOpen: self.db.close()

    def copyItemRelations(self, data):
        if not data.get('from'): Exception("No items specified")
        if not data.get('keepDatabaseOpen'): self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item: raise Exception("Item not found")
        existingIdensList = list()
        existingRelations = self.db.selectRelations(itemID=item[FCM.ItemCol['Iden']])
        if existingRelations:
            for rel in existingRelations: existingIdensList.append(rel[0])
        catIdensList = list()
        for mergeItemPath in data['from']:
            item2 = self.getItemFromPath(mergeItemPath)
            if not item2: continue
            if item == item2: continue
            relations = self.db.selectRelations(itemID=item2[FCM.ItemCol['Iden']])
            for rel in relations:
                if data.get("withtaxonomies"):
                    category, taxonomy = self.getCategoryFromInput(str(rel[0]))
                    print(data['withtaxonomies'])
                    if not category: continue
                    if taxonomy in data['withtaxonomies']:
                        catIdensList.append(rel[0])
                elif data.get("withouttaxonomies"):
                    category, taxonomy = self.getCategoryFromInput(str(rel[0]))
                    print(data['withouttaxonomies'])
                    if not category: continue
                    if not taxonomy in data['withouttaxonomies']:
                        catIdensList.append(rel[0])
                else:
                    catIdensList.append(rel[0])
        catIdensList = [*set(catIdensList)]
        newIdensList = [i for i in catIdensList if i not in existingIdensList]
        for catIden in newIdensList:
            relationExists = self.db.checkRelation(
                itemID=item[FCM.ItemCol['Iden']], termID=catIden).fetchone()
            if not relationExists:
                self.db.newRelation({'item': item[FCM.ItemCol['Iden']], 'term': catIden})
            else:
                self.logger.info("Item already has relation for category: " + catIden)
        if not data.get('keepDatabaseOpen'):
            self.db.commit()
            self.db.close()

    def mergeItems(self, data):
        keepDatabaseOpen = data.get('keepDatabaseOpen')
        if not keepDatabaseOpen: self.db.open()
        if not data.get('with'): Exception("No items specified")
        item = self.getItemFromPath(data['filepath'])
        if not item: raise Exception("Item not found")
        parentSource = item[FCM.ItemCol['Source']]
        parentDesc =  item[FCM.ItemCol['Description']]
        newParentSource, newParentDesc = None, None
        existingIdensList = list()
        existingRelations = self.db.selectRelations(itemID=item[FCM.ItemCol['Iden']])
        if existingRelations:
            for rel in existingRelations: existingIdensList.append(rel[0])
        catIdensList = list()
        for mergeItemPath in data['with']:
            item2 = self.getItemFromPath(mergeItemPath)
            if not item2: continue
            if item == item2: continue
            relations = self.db.selectRelations(itemID=item2[FCM.ItemCol['Iden']])
            for rel in relations: catIdensList.append(rel[0])
            filepath2 = os.path.join(self.config['options']['default_data_dir'],
                            self.config['itemTypes'].dirFromNoun(item2[FCM.ItemCol['Type']]),
                            str(item2[FCM.ItemCol['Iden']]) + '.' + item2[FCM.ItemCol['Ext']])
            if self.db.deleteItem(item2[FCM.ItemCol['Iden']]):
                if os.path.exists(filepath2): deleteFile(self, filepath2)
            if parentSource in ("", None) and not item2[FCM.ItemCol['Source']] in ("", None):
                newParentSource = item2[FCM.ItemCol['Source']]
            if parentDesc in ("", None) and not item2[FCM.ItemCol['Description']] in ("", None):
                newParentDesc = item2[FCM.ItemCol['Description']]
        catIdensList = [*set(catIdensList)]
        newIdensList = [i for i in catIdensList if i not in existingIdensList]
        for catIden in newIdensList:
            relationExists = self.db.checkRelation(
                itemID=item[FCM.ItemCol['Iden']], termID=catIden).fetchone()
            if not relationExists:
                self.db.newRelation({'item': item[FCM.ItemCol['Iden']], 'term': catIden})
            else:
                self.logger.info("Item already has relation for category: " + catIden)
        if newParentSource: self.db.updateItemSource(item[FCM.ItemCol['Iden']], newParentSource)
        if newParentDesc: self.db.updateItemDescription(item[FCM.ItemCol['Iden']], newParentDesc)
        if not keepDatabaseOpen:
            self.db.commit()
            self.db.close()

    def synchCategories(self, data):
        keepDatabaseOpen = data.get('keepDatabaseOpen')
        if not keepDatabaseOpen: self.db.open()
        if not data.get('categories'): raise Exception('No categories inputted')
        itemIdensList = list()
        catsList = list()
        data['categories'] = [*set(data['categories'])]
        for cat in data['categories']:
            category, taxonomy = self.getCategoryFromInput(cat)
            if not category:
                if ":" in cat:
                    term = cat.split(":", 1)[1]
                    if len(term) == 0: return False
                else:
                    term = cat
                self.createTaxonomyIfNotExisting(taxonomy)
                self.db.newCategory({"name": quote(term), "taxonomy": taxonomy})
                catID = self.db.lastInsertId
                category, taxonomy = self.getCategoryFromInput(str(catID))
                if not category: continue
            catsList.append(category)
            existingRelations = self.db.selectCategoryRelations(termID=category[FCM.CatCol['Iden']])
            if existingRelations:
                for rel in existingRelations: itemIdensList.append(rel[0])
        itemIdensList = [*set(itemIdensList)]
        for cat in catsList:
            for itemIden in itemIdensList:
                relationExists = self.db.checkRelation(
                    itemID=itemIden, termID=cat[FCM.CatCol['Iden']]).fetchall()
                if len(relationExists) == 0:
                    self.db.newRelation({'item': itemIden, 'term': cat[FCM.CatCol['Iden']]})

        if not keepDatabaseOpen: self.db.commit()
        if not keepDatabaseOpen: self.db.close()

    def mergeCategories(self, data):
        keepDatabaseOpen = data.get('keepDatabaseOpen')
        if not keepDatabaseOpen: self.db.open()
        category, taxonomy = self.getCategoryFromInput(data.get("category"))
        if not category:
            if ":" in data.get("category"):
                term = data.get("category").split(":", 1)[1]
                if len(term) == 0: return False
            else:
                term = data.get("category")
            self.createTaxonomyIfNotExisting(taxonomy)
            self.db.newCategory({"name": quote(term), "taxonomy": taxonomy})
            catID = self.db.lastInsertId
            category, taxonomy = self.getCategoryFromInput(str(catID))
            if not category:
                raise Exception("Category not found")
        existingIdensList = list()
        existingRelations = self.db.selectCategoryRelations(termID=category[FCM.CatCol['Iden']])
        if existingRelations:
            for rel in existingRelations: existingIdensList.append(rel[0])
        if data.get('with'):
            itemIdensList = list()
            for catToMerge in data['with']:
                categoryMerge, taxonomyMerge = self.getCategoryFromInput(catToMerge)
                if categoryMerge == category: continue
                if not categoryMerge: continue
                relations = self.db.selectCategoryRelations(termID=categoryMerge[FCM.CatCol['Iden']])
                for rel in relations: itemIdensList.append(rel[0])
                self.db.deleteCategory(categoryMerge[FCM.CatCol['Iden']])
            itemIdensList = [*set(itemIdensList)]
            newIdensList = [i for i in itemIdensList if i not in existingIdensList]
            for itemIden in newIdensList:
                relationExists = self.db.checkRelation(
                    itemID=itemIden, termID=category[FCM.CatCol['Iden']]).fetchall()
                if len(relationExists) == 0:
                    self.db.newRelation({'item': itemIden, 'term': category[FCM.CatCol['Iden']]})
                else:
                    self.logger.info("Category already has relation for Item: " + itemIden)
        if not keepDatabaseOpen: self.db.commit()
        if not keepDatabaseOpen: self.db.close()

    def updateCategory(self, data, category=None):
        if not data.get('keepDatabaseOpen'): self.db.open()
        if not category:
            category, taxonomy = self.getCategoryFromInput(data.get("category"))
        if not category: raise Exception("Category not found")

        if data.get('additems'):
            for itemInput in data['additems']:
                self.logger.debug(itemInput)
                item = self.getItemFromPath(itemInput)
                if item:
                    relationExists = self.db.checkRelation(
                        itemID=item[FCM.ItemCol['Iden']], termID=category[FCM.CatCol['Iden']]).fetchall()
                    if len(relationExists) == 0:
                        self.db.newRelation({'item': item[FCM.ItemCol['Iden']], 'term': category[FCM.CatCol['Iden']]})
                    else:
                        self.logger.info("Category already has relation for Item: "+str(item[FCM.ItemCol['Iden']]))

        if data.get('removeitems'):
            for itemInput in data['removeitems']:
                self.logger.debug(itemInput)
                item = self.getItemFromPath(itemInput)
                if item:
                    relationExists = self.db.checkRelation(
                        itemID=item[FCM.ItemCol['Iden']], termID=category[FCM.CatCol['Iden']]).fetchall()
                    if len(relationExists) == 0:
                        self.logger.warning(
                            "Item '" + str(item[FCM.ItemCol['Iden']]) +"' has no relation to category")
                    else:
                        self.db.deleteRelation(itemid=item[FCM.ItemCol['Iden']], termid=category[FCM.CatCol['Iden']])
                        self.logger.debug("Relation deleted")

        if not data.get('keepDatabaseOpen'):
            self.db.commit()
            self.db.close()

    def cloneItem(self, _data):
        import copy
        data = copy.deepcopy(_data)
        if not data.get('keepDatabaseOpen'): self.db.open()
        item = self.getItemFromPath(data['filepath'])
        if not item:
            self.logger.error("Item not found")
            return False
        isWeblink = self.config['itemTypes'].get(item[FCM.ItemCol['Type']]).isWeblinks
        if not isWeblink:
            filepath = os.path.join(self.config['options']['default_data_dir'],
                                    self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                    str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
            if not os.path.exists(filepath): self.logger.error("File not found")
        else: filepath = unquote(item[FCM.ItemCol['Source']])
        relations = self.db.selectRelations(itemID=item[FCM.ItemCol['Iden']])
        categories = list()
        for rel in relations: categories .append(str(rel[0]))
        self.uploadItem({
            "filepath": filepath,
            "name": unquote(item[FCM.ItemCol['Name']]),
            "type": item[FCM.ItemCol['Type']],
            "ext": item[FCM.ItemCol['Ext']],
            "description": unquote(item[FCM.ItemCol['Description']]),
            "source": unquote(item[FCM.ItemCol['Source']]),
            "datetime": item[FCM.ItemCol["ModificationTime"]],
            "creationtime": item[FCM.ItemCol["CreationTime"]],
            "primarycategory": item[FCM.ItemCol["PrimaryCategory"]],
            "categories": categories,
            "keepDatabaseOpen": True
        })
        if not data.get('keepDatabaseOpen'):
            self.db.commit()
            self.db.close()

    def updateItem(self, _data, item=None):
        import copy
        data = copy.deepcopy(_data)
        keepDatabaseOpen =  data.get('keepDatabaseOpen')
        if not keepDatabaseOpen: self.db.open()
        if not item: item = self.getItemFromPath(data['filepath'])
        if not item:
            self.logger.error("Item not found")
            return False
        isWeblink = self.config['itemTypes'].get(item[FCM.ItemCol['Type']]).isWeblinks
        filepath = os.path.join(self.config['options']['default_data_dir'],
                                self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
        if not isWeblink:
            if not os.path.exists(filepath): self.logger.warning("File not found")
        fileID = item[FCM.ItemCol['Iden']]
        updateData = dict()
        if data.get('synchdatewithfile') and not isWeblink:
            self.logger.debug(os.path.getmtime(filepath))
            dt = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            self.logger.debug(dt.strftime("%Y-%m-%d %H:%M:%S"))
            data['setdatetime'] = dt.strftime("%Y-%m-%d %H:%M:%S")
        if data.get('synchmd5withfile') and not isWeblink:
            print(fileID)
            self.db.updateMD5(itemID=fileID, newMD5=getMD5FromFile(filepath))

        if data.get('setdatetime'):
            import dateutil.parser
            updateData['datetime'] = dateutil.parser.parse(data['setdatetime']).strftime("%Y-%m-%d %H:%M:%S")
        if data.get('setsource'): updateData['source'] = data['setsource']
        if data.get('setext'):
            if data['setext'].startswith("."): data['setext'] = data['setext'][1:]
            updateData['ext'] = data['setext']
            if item[FCM.ItemCol['Name']].endswith("."+item[FCM.ItemCol['Ext']]):
                t = item[FCM.ItemCol['Name']].rsplit(item[FCM.ItemCol['Ext']], 1)
                updateData['name'] = data['setext'].join(t)
            oldExtFilepath = os.path.join(self.config['options']['default_data_dir'],
                                    self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                    str(item[FCM.ItemCol['Iden']]) + '.' + item[FCM.ItemCol['Ext']])
        if data.get('setdescription'): updateData['description'] = data['setdescription']
        if data.get('setname'): updateData['name'] = data['setname']
        if data.get('setprimarycategory'):
            if data.get('addcategories'): data['addcategories'].insert(0,data['setprimarycategory'])
            else: data['addcategories'] = [data['setprimarycategory'],]
        if data.get('addcategories'):
            primaryCategoryChanged = False
            for cat in data['addcategories']:
                self.logger.debug(cat)
                catResults, taxonomy = self.getCategoryFromInput(cat)
                self.logger.debug(catResults)
                if not catResults:
                    if ":" in cat:
                        term = cat.split(":",1)[1]
                        if len(term) == 0: return False
                    else:
                        term = cat
                    self.createTaxonomyIfNotExisting(taxonomy)
                    self.db.newCategory({"name": quote(term), "taxonomy": taxonomy})
                    catID = self.db.lastInsertId
                    self.db.newRelation({'item': fileID, 'term': catID})
                else:
                    catID = catResults[FCM.CatCol['Iden']]
                    relationExists = self.db.checkRelation(itemID=fileID, termID=catID).fetchall()
                    if len(relationExists) == 0:
                        self.db.newRelation({'item': fileID, 'term': catResults[0]})
                    else:
                        self.logger.info("Item already has relation for '"+taxonomy+":"+catResults[FCM.CatCol['Name']]+"'")
                if data.get('setprimarycategory') and not primaryCategoryChanged:
                    updateData['primarycategory'] = str(catID)
                    primaryCategoryChanged = True
        if data.get('removecategories'):
            for cat in data['removecategories']:
                catResults, taxonomy = self.getCategoryFromInput(cat)
                self.logger.debug(cat)
                if catResults and len(catResults) > 0:
                    relationExists = self.db.checkRelation(itemID=fileID, termID=catResults[FCM.CatCol['Iden']]).fetchall()
                    if len(relationExists) == 0:
                        self.logger.warning("Category '"+catResults[FCM.CatCol['Name']]+"' with taxonomy '"+taxonomy+"' has no relation to item")
                    else:
                        self.db.deleteRelation(itemid=fileID, termid=catResults[FCM.CatCol['Iden']])
                        self.logger.debug("Relation deleted for '" + taxonomy + ":" + catResults[FCM.CatCol['Name']] + "'")
                else:
                    self.logger.warning("Category '" + catResults[FCM.CatCol['Name']] + "' with taxonomy '" + taxonomy + "' not found")
        updateData['md5'] = getMD5FromFile(filepath)
        if len(updateData) > 0:
            updateData['id'] = fileID
            if self.db.updateItem(updateData):
                if updateData.get('ext'):
                    newExtFilepath = os.path.join(self.config['options']['default_data_dir'],
                                          self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']]),
                                          str(item[FCM.ItemCol['Iden']]) + '.' + updateData['ext'])
                    os.rename(oldExtFilepath, newExtFilepath)
                if isWeblink:
                    item = self.getItemFromPath(str(item[FCM.ItemCol['Iden']]))
                    dataDir = self.config['options']['default_data_dir']
                    dirType = self.config['itemTypes'].dirFromNoun(item[FCM.ItemCol['Type']])
                    filePath = os.path.join(dataDir, dirType, str(item[FCM.ItemCol['Iden']]) + "."+desktopFileExt())
                    if not createDesktopFile(filePath, unquote(item[FCM.ItemCol['Name']]), unquote(item[FCM.ItemCol['Source']])):
                        self.logger.error("Unable to create desktop file")
        if not keepDatabaseOpen:
            self.db.commit()
            self.db.close()

    def getSystemSpecifics(self):
        if sys.platform.startswith('linux'):
            self.systemName = "Linux"
        elif sys.platform.startswith('win'):
            self.systemName = "Windows"
        elif sys.platform.startswith('darwin'):
            self.systemName = "Mac"
        else:
            self.systemName = sys.platform

    def confirmConnection(self):
        db = Database(self.config['db'])
        db.close()
        if not db: logger.error('Database Connection not Successful.')
        self.db = db

    def readDatabaseOptions(self):
        self.db.open()
        options = self.db.selectOptions()
        if options:
            if not self.config.get('options'):
                self.config['options'] = dict()
                self.config['options']['relative_data_dir'] = False
                self.config['options']['auto_shortcuts'] = True
                self.config['options']['auto_integration'] = True
                if self.portableMode:
                    self.config['options']['default_data_dir'] = "Files"
                    self.config['options']['relative_data_dir'] = True
                else:
                    self.config['options']['default_data_dir'] = os.path.join(os.path.dirname(
                        self.config['db']['db']),"Files")

                self.config['options']['cat_lvls'] = const.MAXCATLVLS
                self.config['options']['default_taxonomy'] = "tag"
                self.config['options']['coloured_taxonomies'] = False
                self.config['options']['purge_shortcuts_folder'] = False
                self.config['options']['progress_bar'] = True
                self.config['options']['default_shortcuts_dir'] = os.path.join(os.path.dirname(
                    self.config['db']['db']),"Shortcuts")
                self.config['options']['default_integration_dir'] = os.path.join(os.path.dirname(
                    self.config['db']['db']), "Integration")
                self.config['options']['default_results_dir'] = os.path.join(os.path.dirname(
                    self.config['db']['db']), "SearchResults")
            for option in options:
                self.config['options'][option[0]] = unquote(option[1])
            try:
                self.config['options']['cat_lvls'] = int(self.config['options']['cat_lvls'])
                self.config['options']['relative_data_dir'] = convToBool(self.config['options']['relative_data_dir'], False)
            except KeyError:
                pass

            if self.dataDirOverride:
                self.dataDirOverride = os.path.join(self.dataDirOverride, "") ## confirm path ends in '/'
                self.config['options']['default_data_dir'] = self.dataDirOverride

            if not os.path.isabs(self.config['options']['default_data_dir']):
                databaseDir = os.path.dirname(self.db.config['db'])
                relativeDataPath = os.path.join(databaseDir,  self.config['options']['default_data_dir'])
                self.config['options']['default_data_dir'] = relativeDataPath
                self.logger.debug("New Relative Data Dir:" + relativeDataPath)
            if not os.path.exists(self.config['options']['default_data_dir']):
                os.mkdir(self.config['options']['default_data_dir'])
            self.validateOptions()
            # os.chdir(os.path.dirname(self.db.config['db'])) ## set cwd to database dir
        self.db.close()

    def validateOptions(self):
        if self.config['options']["default_shortcuts_dir"] in (None, ""):
            self.config['options']["default_shortcuts_dir"] = os.path.join(os.path.dirname(
                self.config['db']['db']),"Shortcuts")
        if self.config['options']["default_integration_dir"] in (None, ""):
            self.config['options']["default_integration_dir"] = os.path.join(os.path.dirname(
                self.config['db']['db']), "Integration")
        if self.config['options']["default_results_dir"] in (None, ""):
            self.config['options']["default_results_dir"] = os.path.join(os.path.dirname(
                self.config['db']['db']), "SearchResults")
        if self.config['options'].get('auto_shortcuts') :
            self.config['options']['auto_shortcuts'] = convToBool(
                self.config['options']['auto_shortcuts'], True)
        if self.config['options'].get('auto_integration') :
            self.config['options']['auto_integration'] = convToBool(
                self.config['options']['auto_integration'], True)
        if self.config['options'].get('coloured_taxonomies') :
            self.config['options']['coloured_taxonomies'] = convToBool(
                self.config['options']['coloured_taxonomies'], False)
        if self.config['options'].get('purge_shortcuts_folder') :
            self.config['options']['purge_shortcuts_folder'] = convToBool(
                self.config['options']['purge_shortcuts_folder'], False)
        if self.config['options'].get('progress_bar'):
            self.config['options']['progress_bar'] = convToBool(
                self.config['options']['progress_bar'], True)


    def readItemTypesAndTaxonomies(self):
        self.db.open()

        if self.config.get('itemTypes'):
            self.config['itemTypes'].clear()
        else:
            self.config['itemTypes'] = ItemTypeList()
        itemTypesQuery = self.db.selectItemTypes()
        for it in itemTypesQuery:
            itemType = ItemType()
            itemType.setNounName(it[1])
            itemType.setPluralName(it[2])
            itemType.setDirName(it[3])
            itemType.setTableName(it[4])
            itemType.setEnabled(int(it[5]))
            reader = csv.reader([it[6]], skipinitialspace=True)
            for extensions in reader:
                if extensions:
                    itemType.setExtensions(extensions)
                    if itemType.hasExtension("html") and itemType.hasExtension("htm"):
                        itemType.isWebpages = True
                else:
                    itemType.isWeblinks = True
            self.config['itemTypes'].append(itemType)
        if not self.config.get('itemTypes') or len(self.config['itemTypes']) == 0:
            self.config['itemTypes'] = self.createDefaultItemTypes()

        if self.config.get('taxonomies'):
                self.config['taxonomies'].clear()
        else:
            self.config['taxonomies'] = TaxonomyList()
        taxonomiesQuery = self.db.selectAllTaxonomies()
        for tax in taxonomiesQuery:
            taxonomy = Taxonomy()
            taxonomy.setNounName(tax[1])
            taxonomy.setPluralName(tax[2])
            taxonomy.setDirName(tax[3])
            taxonomy.setTableName(tax[4])
            taxonomy.setEnabled(int(tax[5]))
            taxonomy.setHasChildren(int(tax[6]))
            taxonomy.setIsTags(int(tax[7]))
            taxonomy.setColour(tax[8])
            self.config['taxonomies'].append(taxonomy)
        if not self.config.get('taxonomies') or len(self.config['taxonomies']) == 0:
            self.config['taxonomies'] = self.createDefaultTaxonomies()
        self.db.close()

    def createDefaultItemTypes(self):
        itemTypes = ItemTypeList()
        for typeTuple in self.defaultItemTypes:
            itemType = ItemType()
            itemType.setPluralName(typeTuple[0])
            itemType.setNounName(typeTuple[1])
            itemType.setTableName(typeTuple[2])
            if len(typeTuple) == 4:
                itemType.setExtensions(typeTuple[3])
                if itemType.hasExtension("html") and itemType.hasExtension("htm"):
                    itemType.isWebpages = True
            else:
                itemType.isWeblinks = True
            itemTypes.append(itemType)
        return itemTypes

    def createDefaultTaxonomies(self):
        taxonomies = TaxonomyList()
        for taxTuple in self.defaultTaxonomies:
            taxonomy = Taxonomy()
            taxonomy.setPluralName(taxTuple[0])
            taxonomy.setNounName(taxTuple[1])
            taxonomy.setTableName(taxTuple[2])
            taxonomy.setHasChildren(taxTuple[3])
            if len(taxTuple) == 5:
                taxonomy.setIsTags(taxTuple[4])
            taxonomies.append(taxonomy)
        return taxonomies

    def writeDatabaseOptions(self):
        if self.db:
            self.writeItemTypesAndTaxonomies()
            self.db.open()
            if self.config['options']['relative_data_dir']:
                full_path = self.config['options']['default_data_dir']
                relative_path = os.path.dirname(self.db.config['db'])
                self.config['options']['default_data_dir'] = os.path.relpath(full_path, relative_path)
            for option, value in self.config['options'].items():
                    self.db.insertOption(option, quote(str(value)))
            self.db.commit()
            self.db.close()
            if self.db.error is None:
                self.logger.debug('Database options written.')

    def writeItemTypesAndTaxonomies(self):
        self.db.open()
        self.db.deleteItemTypes()
        self.db.deleteTaxonomies()
        for taxonomy in self.config['taxonomies']:
            data = dict()
            data['noun_name'] = taxonomy.nounName
            data['plural_name'] = taxonomy.pluralName
            data['dir_name'] = taxonomy.dirName
            data['table_name'] = taxonomy.tableName
            data['enabled'] = int(taxonomy.enabled)
            data['has_children'] = int(taxonomy.hasChildren)
            data['is_tags'] = int(taxonomy.isTags)
            data['colour'] = taxonomy.colour
            self.db.insertTaxonomy(data)
        for itemType in self.config['itemTypes']:
            data = dict()
            data['noun_name'] = itemType.nounName
            data['plural_name'] = itemType.pluralName
            data['dir_name'] = itemType.dirName
            data['table_name'] = itemType.tableName
            data['enabled'] = int(itemType.enabled)
            data['extensions'] = ', '.join(itemType.extensions)
            self.db.insertItemType(data)

        self.db.commit()
        if self.db.error is None:
            self.logger.debug('Item types and taxonomies written to database.')
        self.db.close()


    def setPortableMode(self, mode):self.portableMode = mode
    def setOrganizationName(self, name): self.organizationname = name
    def setApplicationName(self, name): self.applicationname = name
    def setApplicationVersion(self, name): self.applicationversion = name
    def organizationName(self): return self.organizationname
    def applicationName(self): return self.applicationname
    def applicationVersion(self): return self.applicationversion