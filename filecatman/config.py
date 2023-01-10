import os, json
from filecatman.core.functions import getUserConfigDir, convToBool

class Config:
    def __init__(self):
        self.__config = dict()
        self.readConfig()

    def __contains__(self, item):
        return item in self.__config

    def __getitem__(self, key):
        return self.__config[key]

    def get(self, key, default=None):
        if key in self.__config:
            return True
        elif default:
            return default
        else:
            return False

    def __setitem__(self, key, value):
        return self.setItem(key, value)

    def setItem(self, key, value):
        #logger.debug("Setting '{0}' to {1} of {2}".format(key, value, type(value)))
        self.__config[key] = value

    def writeConfig(self):
        userConfigFile = os.path.join(getUserConfigDir(),"filecatman.json")
        jsonData = dict()

        jsonData['autoloadDatabase'] = str(self.__config['autoloadDatabase'])
        if self.__config['autoloadDatabase'] and self.__config['db']:
            jsonData['db'] = str(self.__config['db']['db'])

        jsonOutput = json.dumps(jsonData, indent=4)
        with open(userConfigFile, 'w') as fp:
            fp.write(jsonOutput)
        os.chmod(userConfigFile, 0o755)

    def readConfig(self):
        userConfigFile = os.path.join(getUserConfigDir(), "filecatman.json")
        if not os.path.exists(userConfigFile): return

        with open(userConfigFile, "r") as importFile:
            try: importedData = json.load(importFile)
            except json.decoder.JSONDecodeError: return
            if importedData.get("autoloadDatabase") and importedData.get("db"):
                self.__config["autoloadDatabase"] = convToBool(importedData['autoloadDatabase'], False)
                if self.__config["autoloadDatabase"]:
                    self.__config["db"] = {
                        'db':importedData['db'],
                        'type': "sqlite"
                    }


    #
    #     if 'openWith' in self.settings.childGroups():
    #         self.__config['openWith'] = dict()
    #         self.settings.beginGroup('openWith')
    #         for ext in self.settings.childKeys():
    #             try:
    #                 value = self.settings.value(ext)
    #                 commandsList = value.split(', ')
    #                 self.__config['openWith'][ext] = dict()
    #                 for command in commandsList:
    #                     if command != "":
    #                         appPath = unquote(command)
    #                         appName = appPath.split("/")[-1]
    #                         self.__config['openWith'][ext][appName] = appPath
    #             except IndexError:
    #                 logger.warning("Configuration file contained invalid Open With settings.")
    #         self.settings.endGroup()
    #     else:
    #         self.__config['openWith'] = dict()

    #     self.settings.beginGroup("openWith")
    #     for ext, commandList in self.__config['openWith'].items():
    #         commandList = [quote(item) for item in commandList]
    #         self.settings.setValue(ext, ", ".join(commandList))
    #     self.settings.endGroup()
    #
    #     logger.debug('Configuration file written.')
