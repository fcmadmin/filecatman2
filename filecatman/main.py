#!/usr/bin/env python3
import os
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

import sys
import argparse
from filecatman.core import const
from filecatman.filecatman import Filecatman
import filecatman.log as log
import filecatman.core.exceptions as Exceptions

class main():
    parser = argparse.ArgumentParser(add_help=False)
    ## Options
    parser.add_argument("-v", "--version", help="Show program's version number and exit", action="store_true")
    parser.add_argument("-d", "--database", help="Specify a filepath to load an SQLite database",
                             action="store", dest="database")
    parser.add_argument("-L", "--loglevel", help="Set the log level: none, info, warning, error, critical, debug",
                             action="store", dest="loglevel")
    parser.add_argument("-q", "--quiet", help="Sets the log level to 'none', this is the same as `-L none`",
                             dest="quiet", action="store_true", default=False)
    parser.add_argument("-h", "--help", help="Show help", action="store_true")
    parser.add_argument("-f", "--datapath", help="Select custom item data path", action="store", dest="datapath")
    parser.add_argument("--autoload", help="Auto load current database on startup", action="store_true", dest="autoload")
    parser.add_argument("--closedb", help="Close database if auto load enabled", action="store_true", dest="closedb")
    parser.add_argument("--noshortcuts", help="Disable shortcut creation", action="store_true", dest="noshortcuts")
    parser.add_argument("--nointegration", help="Disable integration", action="store_true", dest="nointegration")
    parser.add_argument("--defaulttaxonomy", help="Set default taxonomy", action="store", dest="defaulttaxonomy")
    parser.add_argument("--shortcutsdir", help="Set default shortcuts dir", action="store", dest="shortcutsdir")
    parser.add_argument("--integrationdir", help="Set default integration dir", action="store", dest="integrationdir")
    parser.add_argument("--searchresultsdir", help="Set default search results dir", action="store", dest="searchresultsdir")

    ## Command Options
    parser.add_argument("--withcategories", help=argparse.SUPPRESS, nargs="+", action="append", dest="withcategories")
    parser.add_argument("--withoutcategories", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutcategories")
    parser.add_argument("--anytax", help=argparse.SUPPRESS, nargs="+", action="append", dest="anytax")
    parser.add_argument("--catsearch", help=argparse.SUPPRESS, nargs="+", action="append", dest="catsearch")
    parser.add_argument("--taxonomies", "--tax", help=argparse.SUPPRESS, nargs="+", action="append", dest="taxonomies")
    parser.add_argument("--withouttaxonomies", "--nottax", help=argparse.SUPPRESS, nargs="+", action="append", dest="withouttaxonomies")
    parser.add_argument("--addcategories", help=argparse.SUPPRESS, nargs="+", action="append", dest="addcategories")
    parser.add_argument("--add", help=argparse.SUPPRESS, nargs="+", action="append", dest="argadd")
    parser.add_argument("--removecategories", help=argparse.SUPPRESS, nargs="+", action="append", dest="removecategories")
    parser.add_argument("--remove", help=argparse.SUPPRESS, nargs="+", action="append", dest="argremove")

    parser.add_argument("--itemtype", help=argparse.SUPPRESS, nargs="+", action="append", dest="itemtype")
    parser.add_argument("--withfileext", help=argparse.SUPPRESS, nargs="+", action="append", dest="withfileext")
    parser.add_argument("--withoutfileext", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutfileext")
    parser.add_argument("--withoutitemtype", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutitemtype")
    parser.add_argument("--printresultsdir", help=argparse.SUPPRESS, action="store_true", dest="printresultsdir")
    parser.add_argument("--synchdatewithfile", help=argparse.SUPPRESS, action="store_true", dest="synchdatewithfile")
    parser.add_argument("--synchmd5withfile", help=argparse.SUPPRESS, action="store_true", dest="synchmd5withfile")
    parser.add_argument("--withmissingfile", help=argparse.SUPPRESS, action="store_true", dest="withmissingfile")
    parser.add_argument("--sizemorethan", help=argparse.SUPPRESS, action="store", dest="sizemorethan")
    parser.add_argument("--sizelessthan", help=argparse.SUPPRESS, action="store", dest="sizelessthan")

    parser.add_argument("--withdaterange", help=argparse.SUPPRESS, nargs="+", action="append", dest="withdaterange")
    parser.add_argument("--withoutdaterange", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutdaterange")
    parser.add_argument("--withdategreaterthan", help=argparse.SUPPRESS, action="store", dest="withdategreaterthan")
    parser.add_argument("--withdatelessthan", help=argparse.SUPPRESS, action="store", dest="withdatelessthan")

    parser.add_argument("--withcdaterange", help=argparse.SUPPRESS, nargs="+", action="append", dest="withcdaterange")
    parser.add_argument("--withoutcdaterange", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutcdaterange")
    parser.add_argument("--withcdategreaterthan", help=argparse.SUPPRESS, action="store", dest="withcdategreaterthan")
    parser.add_argument("--withcdatelessthan", help=argparse.SUPPRESS, action="store", dest="withcdatelessthan")

    parser.add_argument("--withidgreaterthan", help=argparse.SUPPRESS, action="store", dest="withidgreaterthan")
    parser.add_argument("--withidlessthan", help=argparse.SUPPRESS, action="store", dest="withidlessthan")

    parser.add_argument("--withkeywords", help=argparse.SUPPRESS, nargs="+", action="append", dest="withkeywords")
    parser.add_argument("--withoutkeywords", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutkeywords")
    parser.add_argument("--categorycount", help=argparse.SUPPRESS, action="store", dest="categorycount")
    parser.add_argument("--withoutcategorycount", help=argparse.SUPPRESS, action="store", dest="withoutcategorycount")
    parser.add_argument("--countmorethan", help=argparse.SUPPRESS, action="store", dest="countmorethan")
    parser.add_argument("--countlessthan", help=argparse.SUPPRESS, action="store", dest="countlessthan")
    parser.add_argument("--withprimarycategory", help=argparse.SUPPRESS, action="store", dest="withprimarycategory")
    parser.add_argument("--withoutprimarycategory", help=argparse.SUPPRESS, action="store", dest="withoutprimarycategory")

    parser.add_argument("--source", help=argparse.SUPPRESS, action="store", dest="setsource")
    parser.add_argument("--ext", help=argparse.SUPPRESS, action="store", dest="setext")
    parser.add_argument("--description", help=argparse.SUPPRESS, action="store", dest="setdescription")
    parser.add_argument("--primarycategory", help=argparse.SUPPRESS, action="store", dest="setprimarycategory")
    parser.add_argument("--name", help=argparse.SUPPRESS, action="store", dest="setname")
    parser.add_argument("--withoutname", help=argparse.SUPPRESS, action="store", dest="withoutname")
    parser.add_argument("--withoutsource", help=argparse.SUPPRESS, action="store", dest="withoutsource")
    parser.add_argument("--withoutdescription", help=argparse.SUPPRESS, action="store", dest="withoutdescription")
    parser.add_argument("--date", help=argparse.SUPPRESS, action="store", dest="setdate")
    parser.add_argument("--md5", help=argparse.SUPPRESS, action="store", dest="md5")
    parser.add_argument("--md5file", help=argparse.SUPPRESS, action="store", dest="md5file")
    parser.add_argument("--md5changed", help=argparse.SUPPRESS, action="store_true", dest="md5changed")

    parser.add_argument("--itemcount", help=argparse.SUPPRESS, action="store", dest="itemcount")
    parser.add_argument("--withoutitemcount", help=argparse.SUPPRESS, action="store", dest="withoutitemcount")
    parser.add_argument("--additems", help=argparse.SUPPRESS, nargs="+", action="append", dest="additems")
    parser.add_argument("--removeitems", help=argparse.SUPPRESS, nargs="+", action="append", dest="removeitems")
    parser.add_argument("--withitems", help=argparse.SUPPRESS, nargs="+", action="append", dest="withitems")
    parser.add_argument("--withoutitems", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutitems")
    parser.add_argument("--withanyitems", help=argparse.SUPPRESS, nargs="+", action="append", dest="withanyitems")
    parser.add_argument("--with", help=argparse.SUPPRESS, nargs="+", action="append", dest="argwith")
    parser.add_argument("--withany", help=argparse.SUPPRESS, nargs="+", action="append", dest="argwithany")
    parser.add_argument("--from", help=argparse.SUPPRESS, nargs="+", action="append", dest="argfrom")
    parser.add_argument("--without", help=argparse.SUPPRESS, nargs="+", action="append", dest="argwithout")
    parser.add_argument("--col", help=argparse.SUPPRESS, nargs="+", action="append", dest="col")
    parser.add_argument("--hidecol", help=argparse.SUPPRESS, nargs="+", action="append", dest="hidecol")
    parser.add_argument("--nullcol", help=argparse.SUPPRESS, nargs="+", action="append", dest="nullcol")
    parser.add_argument("--withoutnullcol", help=argparse.SUPPRESS, nargs="+", action="append", dest="withoutnullcol")
    parser.add_argument("--noemoji", help=argparse.SUPPRESS, action="store_true", dest="noemoji")

    parser.add_argument("--sortby", help=argparse.SUPPRESS, action="store", dest="sortby")
    parser.add_argument("--withduplicate", help=argparse.SUPPRESS, action="store", dest="withduplicate")
    parser.add_argument("--withduplicatefile", help=argparse.SUPPRESS, action="store_true", dest="withduplicatefile")
    parser.add_argument("--asc", help=argparse.SUPPRESS, action="store_true", dest="asc")
    parser.add_argument("--desc", help=argparse.SUPPRESS, action="store_true", dest="desc")

    parser.add_argument("--itemsperpage", help=argparse.SUPPRESS, action="store", dest="itemsperpage")
    parser.add_argument("--page", help=argparse.SUPPRESS, action="store", dest="page")
    parser.add_argument("--lastpage", help=argparse.SUPPRESS, action="store_true", dest="lastpage")
    parser.add_argument("--intofirstitem", help=argparse.SUPPRESS, action="store_true", dest="intofirstitem")
    parser.add_argument("--intolastitem", help=argparse.SUPPRESS, action="store_true", dest="intolastitem")

    parser.add_argument("--fromdir", help=argparse.SUPPRESS, action="store", dest="fromdir")
    parser.add_argument("--fromfile", help=argparse.SUPPRESS, action="store", dest="fromfile")
    parser.add_argument("--listpaths", help=argparse.SUPPRESS, action="store_true", dest="listpaths")
    parser.add_argument("--listnamedpaths", help=argparse.SUPPRESS, action="store_true", dest="listnamedpaths")
    parser.add_argument("--listids", help=argparse.SUPPRESS, action="store_true", dest="listids")
    parser.add_argument("--count", help=argparse.SUPPRESS, action="store_true", dest="count")
    parser.add_argument("--nocolour", help=argparse.SUPPRESS, action="store_true", dest="nocolour")
    parser.add_argument("--size", help=argparse.SUPPRESS, action="store_true", dest="size")
    parser.add_argument("--sizenice", help=argparse.SUPPRESS, action="store_true", dest="sizenice")
    parser.add_argument("--timer", help=argparse.SUPPRESS, action="store_true", dest="timer")
    parser.add_argument("--bulk", help=argparse.SUPPRESS, action="store_true", dest="bulk")
    parser.add_argument("--last", help=argparse.SUPPRESS, action="store", dest="last")
    parser.add_argument("--first", help=argparse.SUPPRESS, action="store", dest="first")
    parser.add_argument("--export", help=argparse.SUPPRESS, action="store", dest="export")
    parser.add_argument("--random", help=argparse.SUPPRESS, action="store_true", dest="random")
    parser.add_argument("--manager", help=argparse.SUPPRESS, action="store_true", dest="manager")
    parser.add_argument("--multiple", help=argparse.SUPPRESS, nargs="+", action="append", dest="multiple")
    parser.add_argument("--launch", help=argparse.SUPPRESS, action="store_true", dest="launch")
    parser.add_argument("--inspect", help=argparse.SUPPRESS, action="store_true", dest="inspect")
    parser.add_argument("--updateifduplicate", help=argparse.SUPPRESS, action="store_true", dest="updateifduplicate")

    ## Commands
    for x in range(1, len(sys.argv)+3):
        parser.add_argument("command"+str(x), nargs="?", help=argparse.SUPPRESS)
    args = parser.parse_args()
    # Environment Variables
    DATABASE = os.getenv('FILECATMAN_DATABASE')
    ITEMDIR = os.getenv('FILECATMAN_ITEMDIR')
    def __init__(self):
        if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 10):
            log.logger.error("Python 3.10 or higher is required to run this program.")

        self.filecatmanActions = dict()
        self.filecatmanChanges = dict()
        self.helpPrinted = False
        if self.args.quiet: const.LOGGERLEVEL = "none"
        if self.args.loglevel: const.LOGGERLEVEL = self.args.loglevel.lower()
        if self.args.version: sys.exit("Filecatman: "+const.VERSION)
        if self.args.defaulttaxonomy: self.filecatmanChanges['defaulttaxonomy'] = self.args.defaulttaxonomy
        if self.args.shortcutsdir: self.filecatmanChanges['shortcutsdir'] = self.args.shortcutsdir
        if self.args.integrationdir: self.filecatmanChanges['integrationdir'] = self.args.integrationdir
        if self.args.searchresultsdir: self.filecatmanChanges['searchresultsdir'] = self.args.searchresultsdir
        match self.args.command1:
            case "dev":
                match self.args.command2:
                    case "cwd":
                        cwd = os.getcwd()
                        print(cwd)
                        exit()
                    case "filedir":
                        dir_path = os.path.dirname(os.path.realpath(__file__))
                        print(dir_path)
                        exit()
                    case "userconfigdir":
                        from filecatman.core.functions import getUserConfigDir
                        print(getUserConfigDir())
                        exit()
            case "version":
                sys.exit("Filecatman: "+const.VERSION)
            case "shortcuts":
                if self.args.help:
                    self.printHelp("shortcuts")
                    quit()
                if self.args.command2: self.filecatmanActions['shortcuts'] = self.args.command2
                else: self.filecatmanActions['shortcuts'] = None
            case "integrate":
                if self.args.help:
                    self.printHelp("integrate")
                    quit()
                if self.args.command2: self.filecatmanActions['integrate'] = self.args.command2
                else: self.filecatmanActions['integrate'] = None
            case "database":
                self.filecatmanActions['database'] = dict()
                match self.args.command2:
                    case "vacuum":
                        if self.args.help:
                            self.printHelp("database vacuum")
                            quit()
                        self.filecatmanActions['database']['vacuum'] = True
                    case "setoption":
                        if self.args.help:
                            self.printHelp("database setoption")
                            quit()
                        if self.args.command3 and  self.args.command4:
                            self.filecatmanChanges['setoption'] = {'optionname': self.args.command3, 'optionvalue': self.args.command4}
                        else:
                            self.printHelp("database setoption")
                            quit()
                    case "options":
                        const.LOGGERLEVEL = "none"
                        self.filecatmanActions['database']['listoptions'] = True
                    case "itemtypes":
                        const.LOGGERLEVEL = "none"
                        self.filecatmanActions['database']['listitemtypes'] = True
                    case "taxonomies":
                        const.LOGGERLEVEL = "none"
                        self.filecatmanActions['database']['listtaxonomies'] = True
                    case "checkfiles":
                        const.LOGGERLEVEL = "none"
                        self.filecatmanActions['database']['checkfiles'] = True
                    case "info":
                        const.LOGGERLEVEL = "none"
                        self.filecatmanActions['database']['info'] = True
                    case _:
                        const.LOGGERLEVEL = "none"
                        self.printHelp()

            case "item":
                self.filecatmanActions['item'] = dict()
                match self.args.command2:
                    case "list" | "ls" | "search":
                        self.commandItemSearch(self.args.command3, "item "+self.args.command2)
                    case "synchmd5":
                        if self.args.help:
                            self.printHelp("item synchmd5")
                            quit()
                        self.filecatmanActions['item']['synchmd5'] = True
                    case "synchdate":
                        if self.args.help:
                            self.printHelp("item synchdate")
                            quit()
                        self.filecatmanActions['item']['synchdate'] = True
                    case "lastitem":
                        if self.args.help:
                            self.printHelp("item lastitem")
                            quit()
                        const.LOGGERLEVEL = "none"
                        self.filecatmanActions['item']['lastitem'] = {}
                        if self.args.listpaths: self.filecatmanActions['item']['lastitem']['listpaths'] = True
                        elif self.args.inspect: self.filecatmanActions['item']['lastitem']['inspect'] = True
                    case "path":
                        if self.args.help:
                            self.printHelp("item path")
                            quit()
                        if self.args.command3:
                            const.LOGGERLEVEL = "none"
                            self.filecatmanActions['item']["path"] = {"filepath": self.args.command3}
                        else:
                            self.printHelp("item path")
                            quit()
                    case "download":
                        self.commandItemDownload(3, "item download")
                    case "clone":
                        self.commandItemClone(3)
                    case "inspect":
                        self.commandItemInspect(3, "item inspect")
                    case "rename":
                        if self.args.help:
                            self.printHelp("item rename")
                            quit()
                        if self.args.command3 and self.args.command4:
                            filePath = self.args.command3
                            newName = self.args.command4
                            self.filecatmanActions['item']['rename'] = {"filepath": filePath, "newname": newName}
                        else:
                            self.printHelp("item rename")
                            quit()
                    case "merge":
                        if self.args.help:
                            self.printHelp("item merge")
                            quit()
                        if self.args.command3 and self.args.argwith:
                            self.filecatmanActions['item']['merge'] = {
                                "filepath": self.args.command3,
                                "with": self.args.argwith[0]}
                        else:
                            self.printHelp("item merge")
                            quit()
                    case "mergedupes":
                        self.commandItemMergeDupes("item mergedupes")
                    case "launch":
                        if self.args.help:
                            self.printHelp("item launch")
                            quit()
                        if self.args.command3:
                            filePath = self.args.command3
                            self.filecatmanActions['item']['launch'] = {"filepath": filePath}
                        else:
                            self.printHelp("item launch")
                            quit()
                    case "delete":
                        self.commandItemDelete(3)
                    case "delrel":
                        self.commandItemDelRel(3)
                    case "copyrel":
                        if self.args.help:
                            self.printHelp("item copyrel")
                            quit()
                        if self.args.command3 and self.args.argfrom:
                            filePath = self.args.command3
                            self.filecatmanActions['item']['copyrel'] = {
                                "filepath": filePath,
                                "from": self.args.argfrom[0]
                            }
                            if self.args.taxonomies: self.filecatmanActions['item']['copyrel']['withtaxonomies'] = self.args.taxonomies[0]
                            if self.args.withouttaxonomies: self.filecatmanActions['item']['copyrel']['withouttaxonomies'] =  self.args.withouttaxonomies[0]
                        else:
                            self.printHelp("item copyrel")
                            quit()
                    case "view":
                        if self.args.help:
                            self.printHelp("item view")
                            quit()
                        const.LOGGERLEVEL = "none"
                        if self.args.command3:
                            self.filecatmanActions['item']['view'] = {"filepath": self.args.command3}
                        else:
                            self.printHelp("item view")
                            quit()
                    case "update":
                        self.commandItemUpdate(3, "item update")
                    case "upload":
                        self.commandItemUpload(3, "item upload")
                    case _:
                        const.LOGGERLEVEL = "none"
                        self.printHelp()
                        # quit()
                        pass
            case "category" | "cat":
                self.filecatmanActions['category'] = dict()
                match self.args.command2:
                    case "list" | "ls" | "search":
                        self.commandCategorySearch(self.args.command3, self.args.command1+" "+self.args.command2)
                    case "create":
                        self.commandCategoryCreate(3, self.args.command1+" "+self.args.command2)
                    case "inspect":
                        if self.args.help:
                            self.printHelp(self.args.command1+" inspect")
                            quit()
                        if self.args.command3:
                            const.LOGGERLEVEL = "none"
                            self.filecatmanActions['category']["inspect"] = {"category": self.args.command3}
                        else:
                            self.printHelp(self.args.command1+" inspect")
                            quit()
                    case "launch":
                        if self.args.help:
                            self.printHelp(self.args.command1+" launch")
                            quit()
                        if self.args.command3:
                            self.filecatmanActions['category']['launch'] = {"category": self.args.command3}
                        else:
                            self.printHelp(self.args.command1+" launch")
                            quit()
                    case "rename":
                        if self.args.help:
                            self.printHelp(self.args.command1+" rename")
                            quit()
                        if self.args.command3 and self.args.command4:
                            filePath = self.args.command3
                            newName = self.args.command4
                            self.filecatmanActions['category']['rename'] = {"category": filePath, "newname": newName}
                        else:
                            self.printHelp(self.args.command1+" rename")
                            quit()
                    case "update":
                        self.commandCategoryUpdate(3, self.args.command1+" "+self.args.command2)
                    case "delete":
                        self.commandCategoryDelete(3, self.args.command1+" "+self.args.command2)
                    case "delrel":
                        self.commandCategoryDelRel(3, self.args.command1+" "+self.args.command2)
                    case "copyrel":
                        if self.args.help:
                            self.printHelp(self.args.command1+" copyrel")
                            quit()
                        if self.args.command3 and self.args.argfrom:
                            self.filecatmanActions['category']['copyrel'] = {
                                "category": self.args.command3,
                                "from": self.args.argfrom[0]
                            }
                        else:
                            self.printHelp(self.args.command1+" copyrel")
                            quit()
                    case "view":
                        if self.args.help:
                            self.printHelp(self.args.command1+" view")
                            quit()
                        const.LOGGERLEVEL = "none"
                        if self.args.command3:
                            self.filecatmanActions['category']['view'] = {"category": self.args.command3}
                            if self.args.manager: self.filecatmanActions['category']['view']['openinmanager'] = True
                        else:
                            self.printHelp(self.args.command1+" view")
                            quit()
                    case "merge":
                        if self.args.help:
                            self.printHelp(self.args.command1+" merge")
                            quit()
                        if self.args.command3 and self.args.argwith:
                            self.filecatmanActions['category']['merge'] = {
                                "category": self.args.command3,
                                "with": self.args.argwith[0]}
                        else:
                            self.printHelp(self.args.command1+" merge")
                            quit()
                    case "synch":
                        if self.args.help:
                            self.printHelp(self.args.command1+" synch")
                            quit()
                        categoriesList = list()
                        if self.args.command3 and self.args.command4:
                            for x in range(3, len(sys.argv)):
                                argVar = eval('self.args.command{0}'.format(x))
                                if argVar: categoriesList.append(argVar)
                            self.filecatmanActions['category']['synch'] = {
                                "categories": categoriesList
                            }
                        else:
                            self.printHelp(self.args.command1+" synch")
                            quit()
                    case _:
                        const.LOGGERLEVEL = "none"
                        self.printHelp()
                        # quit()
                        pass
            case "taxonomy":
                self.filecatmanActions['taxonomy'] = dict()
                match self.args.command2:
                    case "list" | "ls" | "search":
                        self.commandTaxonomySearch(self.args.command3, "taxonomy " + self.args.command2)
                    case "merge":
                        if self.args.help:
                            self.printHelp("taxonomy merge")
                            quit()
                        if self.args.command3 and self.args.argwith:
                            self.filecatmanActions['taxonomy']['merge'] = {
                                "taxonomy": self.args.command3,
                                "with": self.args.argwith[0]}
                        else:
                            self.printHelp("taxonomy merge")
                            quit()
                    case "setcolour":
                        if self.args.help:
                            self.printHelp("taxonomy setcolour")
                            quit()
                        if self.args.command3 and self.args.command4:
                            self.filecatmanActions['taxonomy']['setcolour'] = {
                                "taxonomy": self.args.command3,
                                "colour": self.args.command4}
                        else:
                            self.printHelp("taxonomy setcolour")
                            quit()
                    case "delete":
                        if self.args.help:
                            self.printHelp("taxonomy delete")
                            quit()
                        if self.args.command3:
                            self.filecatmanActions['taxonomy']['delete'] = {
                                "taxonomy": self.args.command3}
                        else:
                            self.printHelp("taxonomy delete")
                            quit()
                    case "view":
                        const.LOGGERLEVEL = "none"
                        if self.args.command3:
                            self.filecatmanActions['taxonomy']['view'] = {"taxonomy": self.args.command3}
                        else:
                            self.printHelp("taxonomy view")
                            quit()
                    case _:
                        const.LOGGERLEVEL = "none"
                        self.printHelp()
            case "upload":
                self.commandItemUpload(2, "upload")
            case "update":
                self.commandItemUpdate(2, "update")
            case "search" | "items":
                self.commandItemSearch(self.args.command2, self.args.command1)
            case "categories" | "cats":
                self.commandCategorySearch(self.args.command2, self.args.command1)
            case "delete":
                self.commandItemDelete(2)
            case "download":
                self.commandItemDownload(2, "download")
            case "import":
                self.commandImportArchive(self.args.command2)
            case "export":
                self.commandExportArchive(self.args.command2)
            case _:
                pass
        if self.args.help:
            self.printHelp()
            quit()

        filecatmanConfig = dict()
        if self.args.noshortcuts: filecatmanConfig['noshortcuts'] = True
        if self.args.nointegration: filecatmanConfig['nointegration'] = True
        filecatmanConfig['actions'] = self.filecatmanActions
        filecatmanConfig['changes'] = self.filecatmanChanges

        filecatArgs = {
            'databasePath': self.databasePath(),
            'dataDirPath': self.dataDirPath(),
            'noImportedMode': True
        }
        if self.args.closedb: filecatArgs['closeAutoLoadDatabase'] = True
        try:
            app = Filecatman(filecatArgs)
        except Exceptions.FCM_NoDatabaseFile as e:
            if not self.args.help: self.printHelp()
            quit()

        log.initializeLogger(const.LOGGERLEVEL)
        app.executeActions(filecatmanConfig)
        if len(filecatmanConfig['actions']) == 0 and len(filecatmanConfig['changes']) == 0 :
            app.inspectDatabaseInfo(simple=True)

        if self.args.autoload: app.config['autoloadDatabase'] = True
        app.close()

    def commandCategoryDelRel(self,categoriesArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        categoriesArg = eval('self.args.command{0}'.format(str(categoriesArgNum)))
        categories = None
        if categoriesArg:
            catsList = list()
            for x in range(categoriesArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: catsList.append(argVar)
            categories = catsList
        if categories:
            self.filecatmanActions['category']['delrel'] = {"category": categories}
        else:
            self.printHelp(command)
            quit()

    def commandCategoryDelete(self,categoriesArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        categoriesArg = eval('self.args.command{0}'.format(str(categoriesArgNum)))
        categories = None
        if self.args.multiple:
            if len(self.args.multiple[0]) > 0:
                categories = self.args.multiple[0]
        elif categoriesArg:
            catsList = list()
            for x in range(categoriesArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: catsList.append(argVar)
            categories = catsList
        if categories:
            self.filecatmanActions['category']['delete'] = {"category": categories}
        else:
            self.printHelp(command)
            quit()

    def commandItemDelRel(self, filePathArgNum):
        if self.args.help:
            self.printHelp("item delrel")
            quit()
        filePathArg = eval('self.args.command{0}'.format(str(filePathArgNum)))
        filePaths = None
        if filePathArg:
            itemsList = list()
            for x in range(filePathArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: itemsList.append(argVar)
            filePaths = itemsList
        if filePaths:
            self.filecatmanActions['item']['delrel'] = {"filepath": filePaths}
        else:
            self.printHelp("item delrel")
            quit()


    def commandItemDelete(self, filePathArgNum):
        if self.args.help:
            self.printHelp('item delete')
            quit()
        filePathArg = eval('self.args.command{0}'.format(str(filePathArgNum)))
        filePaths = None
        if self.args.fromfile:
            if os.path.exists(self.args.fromfile):
                file1 = open(self.args.fromfile, 'r')
                Lines = file1.readlines()
                filePaths = list()
                for line in Lines:
                    if len(line.strip()) > 0: filePaths.append(line.strip())
        elif self.args.fromdir:
            if os.path.isdir(self.args.fromdir):
                folderPaths = list()
                for path in os.listdir(self.args.fromdir):
                    filePath = os.path.join(self.args.fromdir, path)
                    if os.path.isfile(filePath): folderPaths.append(filePath)
                filePaths = folderPaths
        elif self.args.multiple:
            if len(self.args.multiple[0]) > 0:
                filePaths = self.args.multiple[0]
        elif filePathArg:
            itemsList = list()
            for x in range(filePathArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: itemsList.append(argVar)
            filePaths = itemsList
        if filePaths:
            if not self.filecatmanActions.get('item'): self.filecatmanActions['item'] = dict()
            self.filecatmanActions['item']['delete'] = {"filepath": filePaths}
        else:
            self.printHelp('item delete')
            quit()

    def commandItemDownload(self, filePathArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        filePathArg = eval('self.args.command{0}'.format(str(filePathArgNum)))
        filePaths = None
        if self.args.fromfile:
            if os.path.exists(self.args.fromfile):
                file1 = open(self.args.fromfile, 'r')
                Lines = file1.readlines()
                filePaths = list()
                for line in Lines:
                    if len(line.strip()) > 0: filePaths.append(line.strip())
        elif self.args.multiple:
            if len(self.args.multiple[0]) > 0:
                filePaths = self.args.multiple[0]
        if filePathArg:
            filePaths = filePathArg
            if os.path.isdir(filePaths):
                folderPaths = list()
                for path in os.listdir(filePaths):
                    filePath = os.path.join(filePaths, path)
                    if os.path.isfile(filePath): folderPaths.append(filePath)
                filePaths = folderPaths
            else:
                itemsList = list()
                for x in range(filePathArgNum, len(sys.argv)):
                    argVar = eval('self.args.command{0}'.format(x))
                    if argVar: itemsList.append(argVar)
                filePaths = itemsList
        if filePaths:
            if not self.filecatmanActions.get('item'): self.filecatmanActions['item'] = dict()
            self.filecatmanActions['item']['download'] = {"filepath": filePaths}
            if self.args.argwith:  self.filecatmanActions['item']['download']['categories'] = self.args.argwith[0]
            elif self.args.withcategories: self.filecatmanActions['item']['download']['categories'] = self.args.withcategories[0]
            elif self.args.addcategories: self.filecatmanActions['item']['download']['categories'] = self.args.addcategories[0]
            elif self.args.argadd: self.filecatmanActions['item']['download']['categories'] = self.args.argadd[0]
            if self.args.setsource: self.filecatmanActions['item']['download']['source'] = self.args.setsource
            if self.args.setdescription: self.filecatmanActions['item']['download']['description'] = self.args.setdescription
            if self.args.setprimarycategory: self.filecatmanActions['item']['download']['primarycategory'] = self.args.setprimarycategory
            if self.args.setdate: self.filecatmanActions['item']['download']['datetime'] = self.args.setdate
            if self.args.setname:  self.filecatmanActions['item']['download']['name'] = self.args.setname
            if self.args.updateifduplicate:  self.filecatmanActions['item']['download']['updateifduplicate'] = True
        else:
            self.printHelp(command)
            quit()

    def commandItemUpload(self, filePathArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        filePathArg = eval('self.args.command{0}'.format(str(filePathArgNum)))
        filePaths = None
        if self.args.fromfile:
            if os.path.exists(self.args.fromfile):
                file1 = open(self.args.fromfile, 'r')
                Lines = file1.readlines()
                filePaths = list()
                for line in Lines:
                    if len(line.strip()) > 0: filePaths.append(line.strip())
        elif self.args.fromdir:
            if os.path.isdir(self.args.fromdir):
                folderPaths = list()
                for dirpath, dirs, files in os.walk(self.args.fromdir):
                    for filename in files:
                        fname = os.path.join(dirpath, filename)
                        if os.path.isfile(fname): folderPaths.append(fname)
                filePaths = folderPaths
        elif self.args.multiple:
            if len(self.args.multiple[0]) > 0:
                filePaths = self.args.multiple[0]
        elif filePathArg:
            filePaths = filePathArg
            if os.path.isdir(filePaths):
                folderPaths = list()
                for path in os.listdir(filePaths):
                    filePath = os.path.join(filePaths, path)
                    if os.path.isfile(filePath): folderPaths.append(filePath)
                filePaths = folderPaths
            else:
                itemsList = list()
                for x in range(filePathArgNum, len(sys.argv)):
                    argVar = eval('self.args.command{0}'.format(x))
                    if argVar: itemsList.append(argVar)
                filePaths = itemsList
        if filePaths:
            if not self.filecatmanActions.get('item'): self.filecatmanActions['item'] = dict()
            self.filecatmanActions['item']['upload'] = {"filepath": filePaths}
            if self.args.argwith:  self.filecatmanActions['item']['upload']['categories'] = self.args.argwith[0]
            elif self.args.withcategories: self.filecatmanActions['item']['upload']['categories'] = self.args.withcategories[0]
            elif self.args.addcategories: self.filecatmanActions['item']['upload']['categories'] = self.args.addcategories[0]
            elif self.args.argadd: self.filecatmanActions['item']['upload']['categories'] = self.args.argadd[0]
            if self.args.setsource: self.filecatmanActions['item']['upload']['source'] = self.args.setsource
            if self.args.setdescription: self.filecatmanActions['item']['upload']['description'] = self.args.setdescription
            if self.args.setprimarycategory: self.filecatmanActions['item']['upload'][ 'primarycategory'] = self.args.setprimarycategory
            if self.args.setdate: self.filecatmanActions['item']['upload']['datetime'] = self.args.setdate
            if self.args.setname:  self.filecatmanActions['item']['upload']['name'] = self.args.setname
            if self.args.bulk:  self.filecatmanActions['item']['upload']['bulk'] = True
            if self.args.updateifduplicate:  self.filecatmanActions['item']['upload']['updateifduplicate'] = True
        else:
            self.printHelp(command)
            quit()

    def commandImportArchive(self,filePathArg):
        if self.args.help:
            self.printHelp("import")
            quit()
        if filePathArg:
            self.filecatmanActions['import'] = {"filepath": filePathArg}
            if self.args.updateifduplicate:  self.filecatmanActions['import']['updateifduplicate'] = True
        else:
            self.printHelp("import")
            quit()

    def commandExportArchive(self,filePathArg):
        if self.args.help:
            self.printHelp("export")
            quit()
        if filePathArg:
            self.filecatmanActions['export'] = {"filepath": filePathArg}
        else:
            self.printHelp("export")
            quit()

    def commandItemMergeDupes(self, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        self.filecatmanActions['item']['mergedupes'] = dict()
        if self.args.intofirstitem: self.filecatmanActions['item']['mergedupes']['intofirstitem'] = True
        if self.args.intolastitem: self.filecatmanActions['item']['mergedupes']['intolastitem'] = True

    def commandItemClone(self, filePathArgNum):
        if self.args.help:
            self.printHelp("item clone")
            quit()
        filePathArg = eval('self.args.command{0}'.format(str(filePathArgNum)))
        filePaths = None
        if self.args.multiple:
            if len(self.args.multiple[0]) > 0:
                filePaths = self.args.multiple[0]
        if filePathArg:
            itemsList = list()
            for x in range(filePathArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: itemsList.append(argVar)
            filePaths = itemsList
        if filePaths:
            if not self.filecatmanActions.get('item'): self.filecatmanActions['item'] = dict()
            self.filecatmanActions['item']['clone'] = {"filepath": filePaths}
        else:
            self.printHelp("item clone")
            quit()

    def commandTaxonomySearch(self, filePathArg, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        const.LOGGERLEVEL = "none"
        self.filecatmanActions['searchtaxs'] = {}
        if filePathArg: self.filecatmanActions['searchtaxs']["searchterms"] = filePathArg
        if self.args.inspect: self.filecatmanActions['searchtaxs']['inspect'] = True

    def commandCategoryUpdate(self, categoriesArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        categoriesArg = eval('self.args.command{0}'.format(str(categoriesArgNum)))
        categories = None
        if categoriesArg:
            catsList = list()
            for x in range(categoriesArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: catsList.append(argVar)
            categories = catsList
        if categories:
            self.filecatmanActions['category']['update'] = {"category": categories}
            if self.args.additems: self.filecatmanActions['category']['update']['additems'] = self.args.additems[0]
            if self.args.removeitems: self.filecatmanActions['category']['update']['removeitems'] = self.args.removeitems[0]
        else:
            self.printHelp(command)
            quit()

    def commandCategoryCreate(self, categoriesArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        categoriesArg = eval('self.args.command{0}'.format(str(categoriesArgNum)))
        categories = None
        if categoriesArg:
            catsList = list()
            for x in range(categoriesArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: catsList.append(argVar)
            categories = catsList
        if categories:
            self.filecatmanActions['category']['create'] = {"category": categories}
        else:
            self.printHelp(command)
            quit()

    def commandCategorySearch(self, filePathArg, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        const.LOGGERLEVEL = "none"
        self.filecatmanActions['searchcats'] = {}
        if filePathArg: self.filecatmanActions['searchcats']["searchterms"] = filePathArg
        if self.args.inspect: self.filecatmanActions['searchcats']['inspect'] = True
        if self.args.taxonomies: self.filecatmanActions['searchcats']['withtaxonomies'] = self.args.taxonomies[0]
        if self.args.withouttaxonomies: self.filecatmanActions['searchcats']['withouttaxonomies'] = self.args.withouttaxonomies[0]
        if self.args.itemcount: self.filecatmanActions['searchcats']['withitemcount'] = self.args.itemcount
        if self.args.withoutitemcount: self.filecatmanActions['searchcats']['withoutitemcount'] = self.args.withoutitemcount
        if self.args.countmorethan: self.filecatmanActions['searchcats']['countmorethan'] = self.args.countmorethan
        if self.args.countlessthan: self.filecatmanActions['searchcats']['countlessthan'] = self.args.countlessthan
        if self.args.withitems: self.filecatmanActions['searchcats']['withitems'] = self.args.withitems[0]
        if self.args.withoutitems: self.filecatmanActions['searchcats']['withoutitems'] = self.args.withoutitems[0]
        if self.args.withanyitems: self.filecatmanActions['searchcats']['withanyitems'] = self.args.withanyitems[0]
        if self.args.listids: self.filecatmanActions['searchcats']['listids'] = True
        if self.args.last: self.filecatmanActions['searchcats']['last'] = self.args.last
        if self.args.first: self.filecatmanActions['searchcats']['first'] = self.args.first
        if self.args.random: self.filecatmanActions['searchcats']['randomorder'] = True
        if self.args.manager: self.filecatmanActions['searchcats']['openinmanager'] = True
        if self.args.printresultsdir: self.filecatmanActions['searchcats']['printresultsdir'] = True
        if self.args.sortby: self.filecatmanActions['searchcats']['sortby'] = self.args.sortby
        if self.args.desc: self.filecatmanActions['searchcats']['desc'] = self.args.desc
        if self.args.asc: self.filecatmanActions['searchcats']['asc'] = self.args.asc
        if self.args.withduplicate: self.filecatmanActions['searchcats']['withduplicate'] = self.args.withduplicate
        if self.args.count: self.filecatmanActions['searchcats']['count'] = True
        if self.args.nocolour: self.filecatmanActions['searchcats']['nocolour'] = True
        if self.args.col: self.filecatmanActions['searchcats']['col'] = self.args.col[0]
        if self.args.hidecol: self.filecatmanActions['searchcats']['hidecol'] = self.args.hidecol[0]

    def commandItemSearch(self, filePathArg, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        const.LOGGERLEVEL = "none"
        self.filecatmanActions['search'] = {}
        if filePathArg: self.filecatmanActions['search']["searchterms"] = filePathArg
        if self.args.withkeywords: self.filecatmanActions['search']['withkeywords'] = self.args.withkeywords[0]
        if self.args.setname: self.filecatmanActions['search']['name'] = self.args.setname
        if self.args.setsource: self.filecatmanActions['search']['source'] = self.args.setsource
        if self.args.setdescription: self.filecatmanActions['search']['description'] = self.args.setdescription
        if self.args.withoutname: self.filecatmanActions['search']['withoutname'] = self.args.withoutname
        if self.args.withoutsource: self.filecatmanActions['search']['withoutsource'] = self.args.withoutsource
        if self.args.withoutdescription: self.filecatmanActions['search']['withoutdescription'] = self.args.withoutdescription
        if self.args.withoutkeywords: self.filecatmanActions['search']['withoutkeywords'] = self.args.withoutkeywords[0]
        if self.args.argwithany:  self.filecatmanActions['search']['withanycategories'] = self.args.argwithany[0]
        if self.args.argwith:  self.filecatmanActions['search']['withcategories'] = self.args.argwith[0]
        if self.args.withitems: self.filecatmanActions['search']['withitems'] = self.args.withitems[0]
        if self.args.withoutitems:  self.filecatmanActions['search']['withoutitems'] = self.args.withoutitems[0]
        if self.args.withcategories: self.filecatmanActions['search']['withcategories'] = self.args.withcategories[0]
        if self.args.anytax: self.filecatmanActions['search']['anytax'] = self.args.anytax[0]
        if self.args.catsearch: self.filecatmanActions['search']['catsearch'] = self.args.catsearch[0]
        if self.args.argwithout: self.filecatmanActions['search']['withoutcategories'] = self.args.argwithout[0]
        elif self.args.withoutcategories: self.filecatmanActions['search']['withoutcategories'] = self.args.withoutcategories[0]
        if self.args.taxonomies: self.filecatmanActions['search']['withtaxonomies'] = self.args.taxonomies[0]
        if self.args.withouttaxonomies: self.filecatmanActions['search']['withouttaxonomies'] = self.args.withouttaxonomies[0]
        if self.args.withdaterange: self.filecatmanActions['search']['withdaterange'] = self.args.withdaterange[0]
        if self.args.withoutdaterange: self.filecatmanActions['search']['withoutdaterange'] = self.args.withoutdaterange[0]
        if self.args.withdategreaterthan: self.filecatmanActions['search']['withdategreaterthan'] = self.args.withdategreaterthan
        if self.args.withdatelessthan: self.filecatmanActions['search']['withdatelessthan'] = self.args.withdatelessthan
        if self.args.withcdaterange: self.filecatmanActions['search']['withcdaterange'] = self.args.withcdaterange[0]
        if self.args.withoutcdaterange: self.filecatmanActions['search']['withoutcdaterange'] = self.args.withoutcdaterange[0]
        if self.args.withcdategreaterthan: self.filecatmanActions['search']['withcdategreaterthan'] = self.args.withcdategreaterthan
        if self.args.withcdatelessthan: self.filecatmanActions['search']['withcdatelessthan'] = self.args.withcdatelessthan
        if self.args.withidgreaterthan: self.filecatmanActions['search']['withidgreaterthan'] = self.args.withidgreaterthan
        if self.args.withidlessthan: self.filecatmanActions['search']['withidlessthan'] = self.args.withidlessthan
        if self.args.itemtype: self.filecatmanActions['search']['withitemtype'] = self.args.itemtype[0]
        if self.args.withoutitemtype: self.filecatmanActions['search']['withoutitemtype'] = self.args.withoutitemtype[0]
        if self.args.withfileext: self.filecatmanActions['search']['withfileext'] = self.args.withfileext[0]
        if self.args.withoutfileext: self.filecatmanActions['search']['withoutfileext'] = self.args.withoutfileext[0]
        if self.args.categorycount: self.filecatmanActions['search']['withcategorycount'] = self.args.categorycount
        if self.args.withoutcategorycount: self.filecatmanActions['search']['withoutcategorycount'] = self.args.withoutcategorycount
        if self.args.countmorethan: self.filecatmanActions['search']['countmorethan'] = self.args.countmorethan
        if self.args.countlessthan: self.filecatmanActions['search']['countlessthan'] = self.args.countlessthan
        if self.args.listpaths: self.filecatmanActions['search']['listpaths'] = True
        if self.args.listnamedpaths: self.filecatmanActions['search']['listnamedpaths'] = True
        if self.args.listids: self.filecatmanActions['search']['listids'] = True
        if self.args.count: self.filecatmanActions['search']['count'] = True
        if self.args.timer: self.filecatmanActions['search']['timer'] = True
        if self.args.last: self.filecatmanActions['search']['last'] = self.args.last
        if self.args.first: self.filecatmanActions['search']['first'] = self.args.first
        if self.args.export: self.filecatmanActions['search']['export'] = self.args.export
        if self.args.withprimarycategory: self.filecatmanActions['search']['withprimarycategory'] = self.args.withprimarycategory
        if self.args.withoutprimarycategory: self.filecatmanActions['search']['withoutprimarycategory'] = self.args.withoutprimarycategory
        if self.args.random: self.filecatmanActions['search']['randomorder'] = True
        if self.args.manager: self.filecatmanActions['search']['openinmanager'] = True
        if self.args.launch: self.filecatmanActions['search']['launch'] = True
        if self.args.inspect: self.filecatmanActions['search']['inspectitems'] = True
        if self.args.printresultsdir: self.filecatmanActions['search']['printresultsdir'] = True
        if self.args.withmissingfile: self.filecatmanActions['search']['withmissingfile'] = True
        if self.args.sizemorethan: self.filecatmanActions['search']['sizemorethan'] = self.args.sizemorethan
        if self.args.sizelessthan: self.filecatmanActions['search']['sizelessthan'] = self.args.sizelessthan
        if self.args.sortby: self.filecatmanActions['search']['sortby'] = self.args.sortby
        if self.args.desc: self.filecatmanActions['search']['desc'] = self.args.desc
        if self.args.asc: self.filecatmanActions['search']['asc'] = self.args.asc
        if self.args.withduplicate: self.filecatmanActions['search']['withduplicate'] = self.args.withduplicate
        if self.args.withduplicatefile: self.filecatmanActions['search']['withduplicatefile'] = True
        if self.args.itemsperpage: self.filecatmanActions['search']['itemsperpage'] = self.args.itemsperpage
        if self.args.page: self.filecatmanActions['search']['page'] = self.args.page
        if self.args.lastpage: self.filecatmanActions['search']['lastpage'] = True
        if self.args.col: self.filecatmanActions['search']['col'] = self.args.col[0]
        if self.args.hidecol: self.filecatmanActions['search']['hidecol'] = self.args.hidecol[0]
        if self.args.nullcol: self.filecatmanActions['search']['nullcol'] = self.args.nullcol[0]
        if self.args.withoutnullcol: self.filecatmanActions['search']['withoutnullcol'] = self.args.withoutnullcol[0]
        if self.args.md5: self.filecatmanActions['search']['md5'] = self.args.md5
        if self.args.md5file: self.filecatmanActions['search']['md5file'] = self.args.md5file
        if self.args.md5changed: self.filecatmanActions['search']['md5changed'] = True
        if self.args.noemoji: self.filecatmanActions['search']['noemoji'] = True
        if self.args.size: self.filecatmanActions['search']['size'] = True
        if self.args.sizenice: self.filecatmanActions['search']['sizenice'] = True

    def commandItemInspect(self, filePathArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        const.LOGGERLEVEL = "none"
        filePathArg = eval('self.args.command{0}'.format(str(filePathArgNum)))
        filePaths = None
        if self.args.fromfile:
            if os.path.exists(self.args.fromfile):
                file1 = open(self.args.fromfile, 'r')
                Lines = file1.readlines()
                filePaths = list()
                for line in Lines:
                    if len(line.strip()) > 0: filePaths.append(line.strip())
        elif filePathArg:
            itemsList = list()
            for x in range(filePathArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: itemsList.append(argVar)
            filePaths = itemsList
        if filePaths:
            self.filecatmanActions['item']["inspect"] = dict()
            self.filecatmanActions['item']["inspect"]['filepath'] = filePaths
        else:
            self.printHelp(command)
            quit()

    def commandItemUpdate(self, filePathArgNum, command):
        if self.args.help:
            self.printHelp(command)
            quit()
        filePathArg = eval('self.args.command{0}'.format(str(filePathArgNum)))
        filePaths = None
        if self.args.fromfile:
            if os.path.exists(self.args.fromfile):
                file1 = open(self.args.fromfile, 'r')
                Lines = file1.readlines()
                filePaths = list()
                for line in Lines:
                    if len(line.strip()) > 0: filePaths.append(line.strip())
        elif self.args.fromdir:
            if os.path.isdir(self.args.fromdir):
                folderPaths = list()
                for dirpath, dirs, files in os.walk(self.args.fromdir):
                    for filename in files:
                        fname = os.path.join(dirpath, filename)
                        if os.path.isfile(fname): folderPaths.append(fname)
                filePaths = folderPaths
        elif self.args.multiple:
            if len(self.args.multiple[0]) > 0: filePaths = self.args.multiple[0]
        elif filePathArg:
            itemsList = list()
            for x in range(filePathArgNum, len(sys.argv)):
                argVar = eval('self.args.command{0}'.format(x))
                if argVar: itemsList.append(argVar)
            filePaths = itemsList

        if filePaths:
            if not self.filecatmanActions.get('item'): self.filecatmanActions['item'] = dict()
            self.filecatmanActions['item']['update'] = {"filepath": filePaths}
            if self.args.argadd: self.filecatmanActions['item']['update']['addcategories'] = self.args.argadd[0]
            elif self.args.addcategories: self.filecatmanActions['item']['update']['addcategories'] = self.args.addcategories[0]
            if self.args.argremove: self.filecatmanActions['item']['update']['removecategories'] = self.args.argremove[0]
            elif self.args.removecategories: self.filecatmanActions['item']['update']['removecategories'] = self.args.removecategories[0]
            if self.args.setext: self.filecatmanActions['item']['update']['setext'] = self.args.setext
            if self.args.setsource: self.filecatmanActions['item']['update']['setsource'] = self.args.setsource
            if self.args.setdescription: self.filecatmanActions['item']['update']['setdescription'] = self.args.setdescription
            if self.args.setprimarycategory: self.filecatmanActions['item']['update']['setprimarycategory'] = self.args.setprimarycategory
            if self.args.synchdatewithfile: self.filecatmanActions['item']['update']['synchdatewithfile'] = self.args.synchdatewithfile
            if self.args.synchmd5withfile: self.filecatmanActions['item']['update']['synchmd5withfile'] = self.args.synchmd5withfile
            if self.args.setdate: self.filecatmanActions['item']['update']['setdatetime'] = self.args.setdate
            if self.args.setname: self.filecatmanActions['item']['update']['setname'] = self.args.setname
        else:
            self.printHelp(command)
            quit()

    def printHelp(self, command=None):
        if self.helpPrinted: return False
        self.helpPrinted = True
        if not command: command = self.args.command1
        if not command:
            # self.parser.print_help()
            print(
'''Usage: filecatman [-d DATABASE] [OPTIONS] COMMAND

Options:
-v, --version            Show program's version number and exit
-d, --database DATABASE  Specify a filepath to load an SQLite database
-L, --loglevel LOGLEVEL  Set the log level: none, info, warning, error, critical, debug
-q, --quiet              Sets the log level to 'none', this is the same as `-L none`
-h, --help               Show help
-f, --datapath DATAPATH  Select custom item data path
--autoload               Auto load current database on startup
--closedb                Close database if auto load enabled
--noshortcuts            Disable shortcut creation
--nointegration          Disable integration
--defaulttaxonomy TAX    Set default taxonomy
--shortcutsdir DIR       Set default shortcuts dir
--integrationdir DIR     Set default integration dir
--searchresultsdir DIR   Set default search results dir''')
            print('''\nManagement Commands:
item        Manage items
category    Manage categories
database    Manage database
taxonomy    Manage taxonomies

Commands:
version     Show program's version number and exit
upload      Upload Files into project
download    Download URL and create item
update      Update Items
search      Search for items
delete      Delete items
items       List items
categories  List categories
shortcuts   Create shortcuts in specified directory
integrate   Move files from a specified directory into project
import      Import contents of backup archive into the project
export      Export project items, categories and settings into an archive

Run 'filecatman [options] COMMAND --help' for more information on a command.''')
        else:
            match command:
                case "database":
                    print('''\nCommands for filecatman database:
vacuum          Vacuum database
setoption       Set database option
options         View all options
itemtypes       View all itemtypes
taxonomies      View all taxonomies
checkfiles      Check files have items in database
info            View database info

Run 'filecatman [options] database COMMAND --help' for more information on a command.''')
                case "item":
                    print('''\nCommands for filecatman item:
inspect     Inspect an item
rename      Rename an item
update      Update an item
launch      Launch an item
delete      Delete an item
upload      Upload an item
view        View an items's categories
delrel      Delete an item's relations
copyrel     Copy relations from other items
download    Download URL and create item
merge       Merge item relations then delete the other items
path        Print item's filepath
clone       Clone an item and it's relations
lastitem    Print last item
search      Search for items
ls          List items
mergedupes  Merge items with duplicate MD5    
synchmd5    Synchronize MD5 of items with files   
synchdate   Synchronize date of items with files

Run 'filecatman [options] item COMMAND --help' for more information on a command.''')
                case "category" | "cat":
                    print('''\nCommands for filecatman {0}:
create      Create a category
inspect     Inspect a category
rename      Rename a category
update      Update a category
launch      Launch a category
delete      Delete a category
view        View a category's items
delrel      Delete a category's relations
copyrel     Copy relations from other categories
merge       Merge a category with other categories
search      Search for categories
ls          List categories
synch       Synchronize mulltiple category's relations

Run 'filecatman [options] {0} COMMAND --help' for more information on a command.'''.format(command))
                case "taxonomy":
                    print('''\nCommands for filecatman taxonomy:
merge      Merge a taxonomy with other taxonomies
setcolour  Set print colour of a taxonomy
ls         List taxonomies
view       View a taxonomy's categories
delete     Delete a taxonomy

Run 'filecatman [options] taxonomy COMMAND --help' for more information on a command.''')
                case "item upload" | "upload":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [path] ... [{0} options]
\nOptions for filecatman {0}:
--withcategories, --with [category id / taxonomy:name] ...          Add categories to the uploaded item
--source [source]          Set source
--description [des..]          Set description
--primarycategory [cat..]          Set primary category
--date [date]          Set date
--name [name]          Set name
--bulk          Enable bulk commit for faster speed
--fromdir [path]          Upload all files in a directory recursively
--fromfile [path]          Upload multiple file paths listed in a text file
--updateifduplicate          Update existing file on duplicate MD5
'''.format(command))
                case "item download" | "download":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [url] ... [{0} options]
\nOptions for filecatman {0}:
--withcategories, --with [category id / taxonomy:name] ...           Add categories to the downloaded item
--source [source]          Set source
--description [des..]          Set description
--primarycategory [cat..]          Set primary category
--date [date]          Set date
--name [name]          Set name
--fromfile [path]          Download multiple URLs listed in a text file
--updateifduplicate          Update existing file on duplicate MD5
'''.format(command))
                case "update" | "item update":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] ... [{0} options]
\nOptions for filecatman {0}:
--addcategories  [category id / taxonomy:name] ... Add categories to the updated item
--removecategories  [category id / taxonomy:name] ... Remove categories from the updated item
--ext [ext]    Set item extension
--source [source]    Set item source
--description [source]    Set item description
--name [name]          Set name
--date [date]          Set date
--primarycategory [source]    Set item primary category
--synchdatewithfile      Synchronise item date with file modification date
--synchmd5withfile      Synchronise item md5 with file md5
--fromdir [path]          Update all files in a directory recursively
--fromfile [path]          Update multiple items listed in a text file
'''.format(command))
                case "search" | "items" | "item search" | "item list" | "item ls":
                     print('''\nUsage for filecatman {0}:
filecatman [options] {0} [phrase] [{0} options]
 \nOptions for filecatman {0}:
--listpaths    Return list of file paths to search result items
--listnamedpaths    Return list of file paths to search result items
--listids   Return list of idens to search result items
--name     Search name column for phrase
--source     Search source column for phrase
--description     Search description column for phrase
--withoutname     Exclude name column with phrase
--withoutsource     Exclude source column with phrase
--withoutdescription     Exclude description column with phrase
--withcategories, --with [category id / taxonomy:name] ...  Include items with all these categories
--withany [category id / taxonomy:name] ...  Include items with any of these categories
--anytax [name] ...  Include items with any of these categories, searches all taxonomies
--catsearch [phrase] ...  Include items with category name similar to this phrase
--withoutcategories, --without [category id / taxonomy:name] ...  Exclude categories
--withitems [item id / filepath] ...   Results must include these items
--withoutitems [item id / filepath] ...    Results must exclude these items
--withkeywords  ...  Include keywords
--withoutkeywords ...  Exclude keywords
--taxonomies, --tax ...   Include taxonomies
--withouttaxonomies, --nottax ...    Exclude taxonomies
--withdaterange           Include date range
--withoutdaterange  Exclude date range
--withdategreaterthan     Include date greater than
--withdatelessthan  Include date less than
--withcdaterange     Include creation date range
--withoutcdaterange  Exclude creation date range
--withcdategreaterthan     Include creation date greater than
--withcdatelessthan  Include creation date less than
--withidgreaterthan     Include id greater than
--withidlessthan  Include id less than
--itemtype ...       Include item type
--withoutitemtype ...    Exclude item type
--withfileext...         Include file extension
--categorycount         Include category count
--withoutcategorycount         Exclude category count
--countmorethan     With category count more than
--countlessthan     With category count less than
--withoutfileext ...     Exclude file extension
--first [#]             First number of items to return
--last [#]             Last number of items to return
--random            Randomize results
--manager          Show results in file manager
--launch                 launch in default program
--inspect                 Return JSON of item data
--printresultsdir  Return path to search results
--withprimarycategory   Include primary category
--withoutprimarycategory   Exclude primary category
--withmissingfile   Include items with missing files
--sortby    Sort items by column name
--asc Sort ascending
--desc Sort descending
--withduplicate [column name]     Include items where column values appears multiple times
--withduplicatefile     Include items where files appear multiple times
--count         Count number of results
--itemsperpage      Paginate results with number of items per page
--page                  Page of results to return
--lastpage              Last page of results
--sizemorethan    With file size more than
--sizelessthan    With file size less than
--col [creationdate/filedate/size/source/md5]   Show column
--hidecol [iden/name/type/date/cats]   Hide column
--nullcol [name/source/description/md5]   Show results with null values in column
--withoutnullcol [name/source/description/md5]   Show results without null values in column
--noemoji   Remove emojis from name column
--timer   Time taken to fetch results
--md5   Search for files with MD5 checksum
--md5file   Get file MD5 and search database for match 
--md5changed    Search for files that have changed their MD5
--size  Print total size of results
--sizenice  Print total size of results formatted
--export  Export project data into specified directory
'''.format(command))
                case "categories" | "cats" | "category search" | "category ls" | "category list"| "cat search" | "cat ls" | "cat list":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [phrase] [{0} options]
\nOptions for filecatman {0}:
--inspect          Return JSON of category data
--taxonomies, --tax          Include taxonomies
--withouttaxonomies, --nottax          Exclude taxonomies
--itemcount          Include item count
--withoutitemcount          Exclude item count
--countmorethan     With item count more than
--countlessthan     With item count less than
--withitems [item id / filepath] ...         Include items
--withoutitems [item id / filepath] ...          Exclude items
--withanyitems [item id / filepath] ...           Include categories with any of these items
--listids          List IDs of search results
--last          Last number of categories to return 
--first          First number of categories to return
--random          Random order
--sortby          Sort categories by column name
--asc          Sort ascending
--desc          Sort descending
--withduplicate [column name]          Include where column values appears multiple times
--count         Count number of results
--col [col]   Show additional column 
--hidecol [col]   Hide column
--nocolour  Temporarily disable print colours
'''.format(command))
                case "taxonomy search" | "taxonomy ls" | "taxonomy list":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [phrase] [{0} options] '''.format(command))
                case "item merge":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [first item id / filepath] --with [other items] [{0} options]
\nCopy the category relations of the [other items] into the [first item] and then delete the [other items]. 
'''.format(command))
                case "category merge" | "cat merge":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [first category id / taxonomy:name] --with [other categories] [{0} options]
\nCopy the item relations of the [other categories] into the [first category] and then delete the [other categories].
'''.format(command))
                case "category update" | "cat update":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] ... [{0} options]
\nOptions for filecatman {0}:
--additems             Add items to the categories
--removeitems             Remove items from the categories
                '''.format(command))
                case "taxonomy merge":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [first taxonomy] --with [other taxonomies] [{0} options]
\nCopy the categories of the [other taxonomies] into the [first taxonomy] and then delete the [other taxonomies].
'''.format(command))
                case "item mergedupes":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [{0} options]
\nOptions for filecatman {0}:
--intofirstitem             Merge duplicate items into the oldest item
--intolastitem             Merge duplicate items into the newest item
'''.format(command))
                case "item delete":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] ... [{0} options]
\nOptions for filecatman {0}:
--fromfile             Delete all items listed in text file
--fromdir             Delete all items in a directory
                       '''.format(command))
                case "item copyrel":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item to copy to] --from [items to copy from] [{0} options]
\nOptions for filecatman {0}:
--taxonomies / --tax             Relations must be in these taxonomies
--withouttaxonomies / --nottax             Relations must not be in these taxonomies
'''.format(command))
                case "category copyrel" | "cat copyrel":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [first category id / taxonomy:name] --from [other categories] [{0} options]
\nCopy item relations from [other categories] into the [first category].
'''.format(command))
                case "category delrel" | "cat delrel":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] ... [{0} options]'''.format(command))
                case "category create" | "cat create":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [taxonomy:name] ... [{0} options]
\nCreate a new category or categories. Taxonomy can be ommited and the default taxonomy will be used.
'''.format(command))
                case "category delete" | "cat delete":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] ... [{0} options]'''.format(command))
                case "category synch" | "cat synch":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] [category id / taxonomy:name] ...'''.format(command))
                case "category view" | "cat view":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] [{0} options]'''.format(command))
                case "item rename":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] [new name] [{0} options]
'''.format(command))
                case "item inspect":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] ... [{0} options]'''.format(command))
                case "item launch":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] [{0} options]'''.format(command))
                case "item path":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] [{0} options]'''.format(command))
                case "category inspect" | "cat inspect":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] ... [{0} options]'''.format(command))
                case "category launch" | "cat launch":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] [{0} options]'''.format(command))
                case "item view":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] [{0} options]'''.format(command))
                case "item clone":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] ... [{0} options]'''.format(command))
                case "item delrel":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [item id / filepath] ... [{0} options]'''.format(command))
                case "item lastitem":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0}'''.format(command))
                    print('''Or:
filecatman [options] item COMMAND lastitem [COMMAND options]'''.format(command))
                case "item synchmd5" | "item synchdate":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0}'''.format(command))
                case "category rename" | "cat rename":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [category id / taxonomy:name] [new name] [{0} options]
'''.format(command))
                case "database vacuum":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0}

Execute SQLite vacuum command on database.'''.format(command))
                case "database setoption":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [database option] [new value]'''.format(command))
                case "taxonomy setcolour":
                    print('''
Usage for filecatman {0}:
filecatman [options] {0} [taxonomy] [colour code]
                '''.format(command))
                    from filecatman.core.printcolours import bcolours
                    print("Colour codes:")
                    bcolours().test2()
                case "import":
                        print('''\nUsage for filecatman {0}:
filecatman [options] {0} [JSON file] [{0} options]
\nOptions for filecatman {0}:
--updateifduplicate          Update existing items with same MD5
                    '''.format(command))
                case "export":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [directory] [{0} options]'''.format(command))
                case "shortcuts":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [directory] [{0} options]

Create category item shortcuts tree in a directory. Omit directory to use default directory.'''.format(command))
                case "integrate":
                    print('''\nUsage for filecatman {0}:
filecatman [options] {0} [directory] [{0} options]

Move files from a directory into the project and create items. Omit directory to use default directory.'''.format(command))
                case _:
                    pass

    def databasePath(self):
        if self.args.database:
            return self.args.database
        if self.DATABASE:
            return self.DATABASE
        return None

    def dataDirPath(self):
        if self.args.datapath:
            return self.args.datapath
        if self.ITEMDIR:
            return self.ITEMDIR
        return False

if __name__ == "__main__":
    main()