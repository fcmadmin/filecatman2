import os
import logging
import sqlite3
from urllib.parse import quote, unquote
from filecatman.core.functions import getPythonFileDir

class Database:
    con, cur, lastInsertId, error, appConfig = None, None, None, None, None
    defaultTables = (
        'items', 'terms', 'term_relationships', 'options', 'item_types', 'taxonomies'
    )
    conSuccess = False
    debug = True

    def __init__(self, config):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.appConfig = config
        if config['type'] == 'sqlite':
            self.config = {
                'db': config['db'],
                'charset': 'utf8',
                'type': 'sqlite'
            }
        else:
            raise Exception('Unknown database driver in configuration file: '+config['type'])
        if config.get('create') and config['create'] is True:
            self.createDatabase()
        else:
            self.newConnection()

    def newConnection(self):
        self.error = None
        if os.path.exists(self.config['db']):
            self.logger.debug("Using existing database: '{}'".format(self.config['db']))

        self.con = sqlite3.connect(self.config['db'])
        if self.con:
            self.cur = self.con.cursor()

        if self.cur:
            self.cur.execute("PRAGMA foreign_keys = ON;")
            self.commit()

            for table in self.defaultTables:
                self.cur.execute(
                    ''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{0}' '''.format(table))
                if not self.cur.fetchone()[0] == 1:
                    self.logger.debug("Table '{}' was missing from the database.".format(table))
                    self.createTables()
                    break

            self.close()
            self.logger.debug("Successfully opened database `{}`.".format(self.config['db']))
            self.conSuccess = True
            return True
        else:
            self.conSuccess = False
            raise Exception("Unable to open database")

    def removeConnection(self):
        # self.removeDatabase(self.config['db'])
        pass

    def createDatabase(self):
        self.error = None
        databaseName = os.path.basename(self.config['db'])
        if os.path.exists(self.config['db']):
            self.logger.debug("Using existing database: '{}'".format(self.config['db']))

        self.con = sqlite3.connect(databaseName)
        if self.con:
            self.cur = self.con.cursor()
        if self.cur:
            if self.createTables():
                self.logger.debug("Database successfully created.")
                self.conSuccess = True
                self.close()
                self.newConnection()
        else:
            self.conSuccess = False
            raise Exception("Unable to create database")

    def createTables(self):
        if self.config['type'] == 'sqlite':
            file = open(os.path.join(getPythonFileDir(),'queries','newsqlitedatabase.sql'), 'r')
            with file:
                SQL = file.read()

            self.cur.executescript(SQL)
            self.commit()

            for table in self.defaultTables:
                self.cur.execute(
                    ''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{0}' '''.format(table))
                if not self.cur.fetchone()[0] == 1:
                    raise Exception("Unable to create database tables.")

            self.logger.debug("Tables created")
            return True
        else:
            return False

    def lastError(self):
        # if not self.con.lastError().type() == 0:
        #     return self.con.lastError().databaseText()
        # elif self.error is not None:
        #     return self.error
        pass

    def printQueryError(self, e):
        if self.config['type'] == 'sqlite':
            self.logger.error("Error: "+str(e))
            self.error = str(e)

    def open(self):
        if self.con:
            try:
                self.cur = self.con.cursor()
            except sqlite3.ProgrammingError as e:
                self.con = sqlite3.connect(self.config['db'])
                self.cur = self.con.cursor()
            self.cur.execute("PRAGMA foreign_keys = ON;")
            self.commit()
        else:
            self.logger.error("Error: No connection to open.")

    def close(self):
        if self.con:
            self.con.close()
        else:
            self.logger.error("Error: No connection to close.")

    def commit(self):
        return self.con.commit()

    def rollback(self):
        return self.con.rollback()

    def versionInfo(self):
        return self.cur.execute("SELECT SQLITE_VERSION()").fetchone()

    def tables(self):
        return self.cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()

    def getLastInsertId(self):
        return self.cur.execute("SELECT last_insert_rowid()").fetchone()[0]

    def newItem(self, data):
        self.lastInsertId = None
        queryData = dict()
        colnames = dict(name="item_name", type="type_id", source="item_source",
                        datetime="item_time", description="item_description", ext="item_ext",
                        creationtime="item_creation_time")
        if data.get('name') is None or data.get('type') is None:
            self.logger.error("Error creating new item: name or typeID field is missing.")
            return
        else:
            if data.get('datetime') is None:
                if data.get('date') is None:
                    data['date'] = "0000-00-00"
                if data.get('time') is None:
                    data['time'] = "00:00:00"
                data['datetime'] = data['date']+" "+data['time']
            if data.get('creationtime') is None:
                import datetime
                data['creationtime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if data.get('description'): data['description'] = quote(data['description'])
            if data.get('source'): data['source'] = quote(data['source'])

            for colabb, value in data.items():
                if value is not None and value != "":
                    if colabb in colnames:
                        queryData[colnames[colabb]] = value

            sql = "INSERT INTO items (" + ", ".join(queryData.keys())\
                  + ") VALUES('" + "', '".join(queryData.values()) + "')"
            self.logger.debug(sql)
            self.cur.execute(sql)
            self.lastInsertId = self.getLastInsertId()
            if self.lastInsertId: self.logger.debug("Item successfully inserted.")
            else: self.logger.warning("Item already exists.")
            return True

    def newCategory(self, data, args=None):
        self.lastInsertId = None
        if args is not None:
            if args.get('replace') and args['replace'] is True:
                pass
            else:
                args['replace'] = False
        else:
            args = dict()
            args['replace'] = False
        queryData = dict()
        colnames = {"name": "term_name",
                    "taxonomy": "term_taxonomy",
                    "parent": "term_parent",
                    "description": "term_description"}

        if data.get('name') is None or data.get('taxonomy') is None:
            self.logger.error("Error creating new category: name or taxonomy field is missing.")
            return
        else:
            if data.get('description'): data['description'] = quote(data['description'])
            else: data['description'] = ""

            # if data.get('parent') in ("", None): data.pop('parent')

            for colabb, value in data.items():
                if value is not None and value != "":
                    if colabb in colnames:
                        queryData[colnames[colabb]] = value

            for key, value in queryData.items():
                self.logger.debug(key+": "+value)

            # queryTerm.setForwardOnly(True)
            if args['replace'] is True:
                if self.config['type'] == 'sqlite':
                    termSQL = "INSERT INTO terms ("+", ".join(queryData.keys())\
                              + ") VALUES('"+"', '".join(queryData.values())+"')"
                    self.logger.debug('\n'+termSQL)
                    self.cur.execute(termSQL)
                    self.lastInsertId = self.getLastInsertId()
                    if self.lastInsertId is None:
                        termSelectSQL = "SELECT term_id from terms WHERE term_slug = '{}' AND term_taxonomy = '{}'"\
                                        .format(data['slug'], data['taxonomy'])
                        self.logger.debug('\n'+termSelectSQL)
                        results = self.cur.execute(termSelectSQL)
                        if len(results.fetchall()) > 0:
                            termIden = results.fetchall()[0]
                            termUpdateSQL = "UPDATE terms SET term_name='{}', term_slug='{}', term_parent={}, term_taxonomy='{}', " \
                                            "term_description='{}' WHERE term_id = {}"\
                                            .format(data['name'], data['slug'], data['parent'], data['taxonomy'],
                                                    data['description'], termIden)
                            self.logger.debug('\n'+termUpdateSQL)
                            self.cur.execute(termUpdateSQL)
                            self.lastInsertId = str(termIden)
                            self.logger.warning("Category successfully replaced.")
            else:
                termSQL = "INSERT INTO terms ("+", ".join(queryData.keys())\
                          + ") VALUES('"+"', '".join(queryData.values())+"')"
                self.logger.debug('\n'+termSQL)
                self.cur.execute(termSQL)
                self.lastInsertId = self.getLastInsertId()
            return True

    def newRelation(self, data):
        self.lastInsertId = None
        if data.get('item') is None or data.get('term') is None:
            self.logger.error("Error creating new relation: ID field is missing.")
            return
        else:
            queryData = data
            sql = "INSERT INTO term_relationships (item_id, term_id) VALUES('{}', '{}')"\
                .format(queryData['item'], queryData['term'])
            if self.cur.execute(sql): self.incrementTermCount(queryData['term'])
            else: self.logger.warning("Relation already exists.")
            self.lastInsertId = self.getLastInsertId()
            return True

    def updateItem(self, data):
        self.lastInsertId = None
        colnames = dict(name="item_name",
                        type="type_id",
                        source="item_source",
                        datetime="item_time",
                        description="item_description",
                        ext="item_ext",
                        primarycategory="item_primary_category",
                        md5="item_md5")
        queryData = dict()
        if not data.get('id'): return False
        if data.get('description'): data['description'] = quote(data['description'])
        if data.get('source'): data['source'] = quote(data['source'])
        if data.get('name'): data['name'] = quote(data['name'])
        for colabb, value in data.items():
            if value is not None:
                if colabb in colnames:
                    queryData[colnames[colabb]] = value

        SQL = "UPDATE items Set "
        i = 0
        for key, value in queryData.items():
            line = key+"='"+value+"'"
            if i < len(queryData)-1:
                line += ", "
            i += 1
            SQL += line
        SQL += " WHERE item_id='{}'".format(data.get('id'))
        self.logger.debug('\n'+SQL)
        query = self.cur.execute(SQL)
        if query:
            self.lastInsertId = self.getLastInsertId()
            return True

    def updatePrimaryCategory(self, itemID, newPrimaryCategory):
        return self.cur.execute(
            "UPDATE items Set item_primary_category='{}' WHERE item_id='{}'".format(newPrimaryCategory, itemID))

    def updateMD5(self, itemID, newMD5):
        return self.cur.execute( "UPDATE items Set item_md5='{}' WHERE item_id='{}'".format(newMD5, itemID))

    def updateItemDate(self, itemID, newDate):
        return self.cur.execute( "UPDATE items Set item_time='{}' WHERE item_id='{}'".format(newDate, itemID))

    def updateItemSource(self, itemID, newSource):
        return self.cur.execute( "UPDATE items Set item_source='{}' WHERE item_id='{}'".format(newSource, itemID))

    def updateItemDescription(self, itemID, newDesc):
        return self.cur.execute( "UPDATE items Set item_description='{}' WHERE item_id='{}'".format(newDesc, itemID))

    def renameItem(self, itemID, newName):
        return self.cur.execute("UPDATE items Set item_name='{}' WHERE item_id='{}'".format(newName, itemID))

    def renameCategory(self, catID, newName):
        return self.cur.execute("UPDATE terms Set term_name='{}' WHERE term_id='{}'".format(newName, catID))

    def updateItemType(self, oldItemType, newItemType):
        SQL = "UPDATE items Set type_id='{}' WHERE type_id='{}'".format(newItemType, oldItemType)
        self.logger.debug('\n'+SQL)
        query = QSqlQuery(SQL, self.con)
        self.lastInsertId = query.lastInsertId()
        self.logger.debug("Item Type `{}` successfully updated to `{}`.".format(oldItemType, newItemType))

    def updateTaxonomy(self, oldTaxonomy, newTaxonomy):
        SQL = "UPDATE terms Set term_taxonomy='{}' WHERE term_taxonomy='{}'"\
              .format(newTaxonomy, oldTaxonomy)
        self.logger.debug('\n'+SQL)
        query = QSqlQuery(SQL, self.con)
        self.lastInsertId = query.lastInsertId()
        self.logger.debug("Taxonomy `{}` successfully updated to `{}`.".format(oldTaxonomy, newTaxonomy))

    def updateCategory(self, data):
        if data.get('termid') is None or data.get('name') is None:
            return

        if data.get('description'):
                data['description'] = quote(data['description'])
        else:
            data['description'] = ""

        if data.get('parent') in ("", None):
            data['parent'] = '0'

        termSQL = "UPDATE terms SET term_name='{}', term_slug='{}', term_parent={}, term_taxonomy='{}', " \
                  "term_description='{}' WHERE term_id = '{}'"\
            .format(data['name'], data['slug'], data['parent'], data['taxonomy'], data['description'], data['termid'])
        self.logger.debug('\n'+termSQL)
        queryTerm = QSqlQuery(termSQL, self.con)
        self.lastInsertId = queryTerm.lastInsertId()
        self.logger.debug("Category successfully updated.")

    def deleteItem(self, itemid):
        sql = "SELECT term_id FROM term_relationships as tr " \
              "WHERE (tr.item_id = {})".format(itemid)
        self.logger.debug("\n"+sql)
        query = self.cur.execute(sql)
        if query:
            for term in query.fetchall():
                self.decrementTermCount(term[0])
        sql = "DELETE FROM items WHERE item_id = '{}'".format(itemid)
        self.logger.debug("\n"+sql)
        self.cur.execute(sql)
        self.logger.debug("Item successfully deleted.")
        return True

    def deleteCategory(self, catIden):
        return self.cur.execute("DELETE FROM terms WHERE term_id = '{}'".format(catIden))

    def deleteRelation(self, itemid, termid):
        self.cur.execute(
            "DELETE FROM term_relationships WHERE (item_id = '{}') AND (term_id = '{}')".format(itemid, termid))
        self.decrementTermCount(termid)
        return True

    def deleteRelations(self, iden, col='item_id'):
        relations = self.cur.execute(
            "SELECT item_id, term_id FROM term_relationships WHERE {} = {}".format(col, iden)).fetchall()
        for rel in relations:
            self.cur.execute(
                "DELETE FROM term_relationships WHERE (item_id = '{}') AND (term_id = '{}')".format(rel[0], rel[1]))
            self.decrementTermCount(rel[1])
        return True

    def deleteItemTypes(self):
        self.cur.execute("DELETE FROM item_types")
        self.cur.execute("UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = 'item_types';")
        # self.logger.debug("Item Types successfully deleted.")
        return True

    def deleteTaxonomies(self):
        self.cur.execute("DELETE FROM taxonomies")
        self.cur.execute("UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = 'taxonomies';")
        # self.logger.debug("Taxonomies successfully deleted.")
        return True

    def bulkDeleteItems(self, itemIdens):
        sql = "SELECT term_id FROM term_relationships as tr " \
              "WHERE item_id IN ({})".format(", ".join(itemIdens))
        self.logger.debug('\n'+sql)
        relations = QSqlQuery(sql, self.con)
        while relations.next():
            self.decrementTermCount(relations.value(0))
        sql = "DELETE FROM items WHERE (item_id) IN ({})".format(", ".join(itemIdens))
        self.logger.debug('\n'+sql)
        QSqlQuery(sql, self.con)
        self.commit()
        self.logger.debug("Items successfully deleted.")
        return True

    def selectLastItem(self):
        return self.cur.execute("SELECT * FROM items ORDER BY item_id DESC LIMIT 1").fetchone()

    def selectItem(self, itemID, col="*"):
        return self.cur.execute("SELECT {} FROM items AS i "
                          "WHERE (item_id= '{}')".format(col, itemID)).fetchone()

    def selectTaxonomy(self, tableName):
        return self.cur.execute("SELECT * FROM taxonomies AS t "
                                "WHERE (table_name= '{}')".format(tableName))

    def selectItems(self, args=None):
        where = ["( i.item_id is not null )", ]
        startLimit = 0
        col = "*"
        limit = ""
        if args:
            if args.get('item_id'): where.append("( i.item_id = '{}' )".format(args['item_id']))
            if args.get('type_id'): where.append("( i.type_id = '{}' )".format(args['type_id']))
            if args.get('item_name'): where.append("( i.item_name = '{}' )".format(args['item_name']))
            if args.get('item_md5'): where.append("( i.item_md5 = '{}' )".format(args['item_md5']))
            if args.get('col'): col = args['col']
            if args.get('limit'):
                if args.get('start'):
                    startLimit = args['start']
                limit = "LIMIT {}, {}".format(startLimit, args['limit'])
        whereJoined = " AND ".join(where)
        sql = "SELECT {} FROM items AS i " \
              "WHERE {} " \
              "{}".format(col, whereJoined, limit)
        self.logger.debug('\n'+sql)
        return self.cur.execute(sql).fetchall()

    def selectCategory(self, catID, col="*"):
        return self.cur.execute("SELECT {} FROM terms AS t " \
              "WHERE (t.term_id = '{}')".format(col, catID)).fetchone()

    def selectCategories(self, args=None):
        where = ["( t.term_id is not null )", ]
        col = "*"
        if args:
            if args.get('term_id'):
                where.append("( t.term_id = '{}' )".format(args['term_id']))
            if args.get('term_name'):
                where.append("( t.term_name = '{}' )".format(args['term_name']))
            if args.get('term_parent'):
                where.append("( t.term_parent = '{}' )".format(args['term_parent']))
            if args.get('term_taxonomy'):
                where.append("( t.term_taxonomy = '{}' )".format(args['term_taxonomy']))
            if args.get('term_count'):
                where.append("( t.term_count = '{}' )".format(args['term_count']))
            if args.get('col'):
                col = args['col']
        whereJoined = " AND ".join(where)
        # query.setForwardOnly(True)
        sql = "SELECT {} FROM terms AS t " \
              "WHERE {}".format(col, whereJoined)
        results = self.cur.execute(sql)
        return results

    def selectCategoriesAsTree(self, args=None):
        queryArgs = dict()
        if args is None:
            args = dict()
        if args.get('taxonomy') is not None:
            queryArgs['tax'] = args['taxonomy']
        if args.get('complete') is not None:
            selectComplete = args['complete']
        else:
            selectComplete = False
        if args.get('extra') is not None:
            queryArgs['extra'] = args['extra']
        else:
            queryArgs['extra'] = None
        catLvls = self.appConfig['options']['cat_lvls']
        if selectComplete:
            sql = "SELECT root.term_id AS root_id, " \
                  "root.term_taxonomy AS root_tax, root.term_name AS root_name, " \
                  "root.term_slug AS root_slug, root.term_count AS root_count"
        else:
            sql = """SELECT root.term_id AS root_id, root.term_name AS root_name"""
        if catLvls > 0:
            sql += ","
        i = 1
        while i <= catLvls:
            curLevel = str(i)
            if selectComplete:
                sql += "\ndown{0}.term_id AS down{0}_id, " \
                       "down{0}.term_taxonomy AS down{0}_tax, down{0}.term_name as down{0}_name, " \
                       "down{0}.term_slug AS down{0}_slug, down{0}.term_count AS down{0}_count".format(curLevel)
            else:
                sql += "\ndown{0}.term_id AS down{0}_id, down{0}.term_name as down{0}_name"\
                    .format(curLevel)
            if i < catLvls:
                sql += ","
            i += 1
        sql += "\nFROM terms AS root"
        i = 1
        while i <= catLvls:
            curLevel = str(i)
            if i == 1:
                lastLevel = "root"
            else:
                lastLevel = "down"+str(i-1)
            sql += "\nLEFT JOIN terms AS down{0} ON down{0}.term_parent = {1}.term_id "\
                .format(curLevel, lastLevel)
            i += 1
        if queryArgs['extra']:
            sql += "\nWHERE (root.term_parent is NULL) AND ({})".format(queryArgs['extra'])
        else:
            sql += "\nWHERE (root.term_parent is NULL) AND (root.term_taxonomy = '{}')".format(queryArgs['tax'])
        sql += "\nORDER BY root_name"
        i = 1
        while i <= catLvls:
            curLevel = str(i)
            sql += ", down{}_name".format(curLevel)

            i += 1
        query = QSqlQuery(self.con)
        query.setForwardOnly(True)
        query.exec_(sql)
        self.logger.debug(sql)
        pool = []
        categories = []
        while query.next():
            rootIdIndex = query.record().indexOf("root_id")
            rootNameIndex = query.record().indexOf("root_name")
            if query.value(rootIdIndex) not in pool and query.value(rootNameIndex) != '':
                c = {'id': query.value(rootIdIndex),
                     'name': query.value(rootNameIndex),
                     'level': 0}
                if selectComplete:
                    c['slug'] = query.value(query.record().indexOf("root_slug"))
                    c['count'] = query.value(query.record().indexOf("root_count"))
                    c['tax'] = query.value(query.record().indexOf("root_tax"))
                categories.append(c)
            pool.append(query.value(rootIdIndex))
            i = 1
            while i <= catLvls:
                curLevel = str(i)
                downIdIndex = query.record().indexOf("down{}_id".format(curLevel))
                downNameIndex = query.record().indexOf("down{}_name".format(curLevel))
                if query.value(downIdIndex) not in pool and query.value(downNameIndex) != '':
                    c = {'id': query.value(downIdIndex),
                         'name': query.value(downNameIndex),
                         'level': i}
                    if selectComplete:
                        c['slug'] = query.value(query.record().indexOf("down{}_slug".format(curLevel)))
                        c['count'] = query.value(query.record().indexOf("down{}_count".format(curLevel)))
                        c['tax'] = query.value(query.record().indexOf("down{}_tax".format(curLevel)))
                    categories.append(c)
                pool.append(query.value(downIdIndex))
                i += 1
        return categories

    def selectRelations(self, itemID):
        return self.cur.execute("SELECT term_id FROM term_relationships AS tr "
                          "WHERE (tr.item_id= '{}')".format(itemID)).fetchall()

    def selectCategoryRelations(self, termID):
        return self.cur.execute("SELECT item_id FROM term_relationships AS tr "
                          "WHERE (tr.term_id= '{}')".format(termID)).fetchall()

    def selectRelatedTags(self, itemID, taxonomy="tag"):
        query = QSqlQuery("SELECT t.term_name from terms AS t "
                          "INNER JOIN term_relationships AS tr ON (tr.term_id = t.term_id) "
                          "WHERE (tr.item_id = {}) AND (t.term_taxonomy = '{}')".format(itemID, taxonomy),
                          self.con)
        return query

    def selectCount(self, table="items"):
        return self.cur.execute('SELECT COUNT(*) FROM {}'.format(table)).fetchone()

    def selectCountCategoriesWithTaxonomy(self, taxonomy):
        return self.cur.execute('SELECT COUNT(*) FROM terms WHERE term_taxonomy = "{}"'.format(taxonomy)).fetchone()[0]

    def selectCountRelations(self, iden, col="item_id"):
        query = self.cur.execute('SELECT COUNT(*) FROM term_relationships '
                          'WHERE {} = "{}"'.format(col, iden)).fetchone()[0]
        if query: return query
        return False

    def selectOption(self, option):
        query = QSqlQuery('SELECT option_value FROM options WHERE option_name = "{}"'.format(option),
                          self.con)
        if query.first():
            optionValue = query.value(0)
            self.logger.debug("Option {}: {}".format(option, optionValue))
            return unquote(optionValue)

    def selectOptions(self):
        return self.cur.execute(''' SELECT option_name, option_value FROM options ''')


    def selectItemTypes(self):
        return self.cur.execute('SELECT * FROM item_types')

    def selectAllTaxonomies(self):
        return self.cur.execute('SELECT * FROM taxonomies')

    def selectAllItems(self):
        return self.cur.execute('SELECT * FROM items').fetchall()

    def selectAllCategories(self):
        return self.cur.execute('SELECT * FROM terms').fetchall()

    def selectDistinctItemTypes(self):
        return QSqlQuery('SElECT DISTINCT type_id from items', self.con)

    def selectDistinctTaxonomies(self):
        return QSqlQuery('SElECT DISTINCT term_taxonomy from terms', self.con)

    def incrementTermCount(self, catid):
        self.cur.execute("UPDATE terms SET term_count = term_count + 1 "
                  "WHERE term_id = '{}'".format(catid))
        return True

    def decrementTermCount(self, catid):
        self.cur.execute("UPDATE terms SET term_count = term_count - 1 "
                  "WHERE term_id = '{}'".format(catid))
        return True

    def checkRelation(self, itemID, termID):
        query = self.cur.execute("SELECT * FROM term_relationships AS tr "
                          "WHERE (tr.item_id = '{}') AND (tr.term_id = '{}')".format(itemID, termID))
        return query

    def insertOption(self, option, value):
        SQL = str()
        if self.config['type'] == 'sqlite':
            SQL = "INSERT OR REPLACE INTO options (option_id, option_name, option_value) \n" \
                  "SELECT old.option_id, new.option_name, new.option_value \n" \
                  "FROM ( SELECT '{}' AS option_name, '{}' AS option_value ) AS new \n" \
                  "LEFT JOIN ( SELECT option_id, option_name, option_value FROM options ) AS old \n" \
                  "ON new.option_name = old.option_name;".format(option, value)
            self.cur.execute(SQL)
        # self.logger.debug('\n'+SQL)
        return True

    def insertItemType(self, data):
        if data.get('table_name') is None or data.get('plural_name') is None:
            self.logger.error("Error creating new item type: field is missing.")
            return False
        else:
            SQL = str()
            if self.config['type'] == 'sqlite':
                SQL = "INSERT INTO item_types (noun_name, plural_name, dir_name, " \
                      "table_name, enabled, extensions) \n" \
                      "VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}')" \
                    .format(data['noun_name'], data['plural_name'], data['dir_name'], data['table_name'],
                            data['enabled'], data['extensions'])
                self.cur.execute(SQL)
            # self.logger.debug('\n'+SQL)
            return True

    def insertTaxonomy(self, data):
        if data.get('table_name') is None or data.get('plural_name') is None:
            self.logger.error("Error creating new taxonomy: field is missing.")
            return False
        else:
            SQL = str()
            if self.config['type'] == 'sqlite':
                SQL = "INSERT INTO taxonomies (noun_name, plural_name, dir_name, " \
                      "table_name, enabled, has_children, is_tags, colour) \n" \
                      "VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}')" \
                    .format(data['noun_name'], data['plural_name'], data['dir_name'], data['table_name'],
                            data['enabled'], data['has_children'], data['is_tags'], data['colour'])
                self.cur.execute(SQL)
            # self.logger.debug('\n'+SQL)
            return True

    def deleteAllData(self):
        query = QSqlQuery(self.con)
        query.exec_("DELETE FROM items;")
        query.exec_("DELETE FROM terms;")
        query.exec_("DELETE FROM term_relationships;")

        query.exec_("UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = 'terms';")
        query.exec_("UPDATE SQLITE_SEQUENCE SET seq = 0 WHERE name = 'items';")
        self.logger.debug("Data successfully deleted.")
        return True

    def dropDatabase(self):
        if self.config['type'] == 'sqlite':
            os.remove(self.config['db'])
        self.logger.debug("Database successfully dropped.")
        return True

    def vacuumDatabase(self):
        self.cur.execute("VACUUM")