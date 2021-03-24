# coding: utf-8

import os
import sqlite3
from sqlite3 import Error

import FreeCAD as App
from freecad.workbench_gespal3d import g3d_component_manager
from freecad.workbench_gespal3d import print_debug
from freecad.workbench_gespal3d import DEBUG_DB
from freecad.workbench_gespal3d import PARAMPATH


__title__ = "Gespal3D Connect DB"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


def progress(status, remaining, total):
    print(f'Copied {total - remaining} of {total} pages...')

def make_backup():
    path = App.ParamGet(str(PARAMPATH))
    no_database = "true"
    og_path = path.GetString("sqlitedb", no_database)
    print("og_path : {}".format(og_path))
    head_path = os.path.split(og_path)[0]
    backup_path = os.path.join(head_path, 'Sqlite_backup.sqdb')
    try:
        # existing DB
        sqliteCon = sqlite3.connect(og_path)
        # copy into this DB
        backupCon = sqlite3.connect(backup_path)
        with backupCon:
            sqliteCon.backup(backupCon, pages=3, progress=progress)
        print("backup successful")
    except sqlite3.Error as error:
        print("Error while taking backup: ", error)
    finally:
        if backupCon:
            backupCon.close()
            sqliteCon.close()
    return

def restore_backup():
    path = App.ParamGet(str(PARAMPATH))
    no_database = "true"
    og_path = path.GetString("sqlitedb", no_database)
    head_path = os.path.split(og_path)[0]
    backup_path = os.path.join(head_path, 'Sqlite_backup.sqdb')
    try:
        # existing DB
        sqliteCon = sqlite3.connect(backup_path)
        # copy into this DB
        backupCon = sqlite3.connect(og_path)
        with backupCon:
            sqliteCon.backup(backupCon, pages=3, progress=progress)
        print("backup successful")
    except sqlite3.Error as error:
        print("Error while taking backup: ", error)
    finally:
        if backupCon:
            backupCon.close()
            sqliteCon.close()
    return

def create_new_db(sqliteCon):
    #con = sqlite3.connect('SQLite_Python.db')
    cursorObj = sqliteCon.cursor()
    # code SQL pour la table Famille_Composant
    cursorObj.execute("DROP TABLE IF EXISTS Famille_Composant;")
    sqliteCon.commit()
    cursorObj.execute('''CREATE TABLE Famille_Composant (
                         FC_COMPTEUR INTEGER PRIMARY KEY,
                         FC_NOM VARCHAR(80),
                         FC_TYPE VARCHAR(2));''')
    sqliteCon.commit()

    # code SQL pour la table composant
    cursorObj.execute("DROP TABLE IF EXISTS Composant;")
    sqliteCon.commit()
    cursorObj.execute('''CREATE TABLE Composant (
                        CO_COMPTEUR INTEGER PRIMARY KEY,
                        CO_NOM VARCHAR(200),
                        CO_FAMILLE INTEGER,
                        CO_LONGUEUR INTEGER,
                        CO_LARGEUR INTEGER,
                        CO_EPAISSEUR INTEGER,
                        CO_FORME VARCHAR(1),
                        CO_COULEUR VARCHAR(11),
                        CO_MASSE INTEGER);''')
    sqliteCon.commit()
    sqliteCon.close()

def sql_connection():
    p = App.ParamGet(str(PARAMPATH))
    no_database = "true"
    sqlite_db = p.GetString("sqlitedb", no_database)
    if sqlite_db == "true":
        print_debug(["define database path in BaseApp/Preferences/Mod/Gespal3D"])
        g3d_component_manager.G3D_ComponentsManager.Activated()
        #return
    try:
        con = sqlite3.connect(sqlite_db)
        if DEBUG_DB:
            print_debug(["DB Connection is established."])
    except Error:
        print_debug(["sql_connection got an error", Error])

    return con


def getCategories(include=[], exclude=[]):
    categories_list = []
    con = sql_connection()
    cursorObj = con.cursor()
    cursorObj.execute("SELECT * FROM Famille_Composant")
    rows = cursorObj.fetchall()
    if len(include) > 0:
        for row in rows:
            if row[2] in include:
                categories_list.append(row)
    if len(exclude) > 0:
        for row in rows:
            if not row[2] in exclude:
                categories_list.append(row)
    if DEBUG_DB:
        messages = ["getCategories :"]
        messages.append(categories_list)
        print_debug(messages)

    return categories_list


def getComposants(categorie=None):
    if categorie:
        con = sql_connection()
        cursorObj = con.cursor()
        cursorObj.execute(
            "SELECT * FROM Composant WHERE CO_FAMILLE = "
            + str(categorie)
            + " ORDER BY CO_NOM"
        )
        rows = cursorObj.fetchall()
        if DEBUG_DB:
            messages = ["getComposants :"]
            messages.append(rows)
            print_debug(messages)
        
        return rows


def getComposant(id=1):
    con = sql_connection()
    cursorObj = con.cursor()
    cursorObj.execute("SELECT * FROM Composant WHERE CO_COMPTEUR = " + str(id))
    rows = cursorObj.fetchall()
    if rows:
        component = rows[0]
    else:
        component = ['1', 'Composant', '1', '0', '100', '22', 'R', '203,193,124', '350']
    print_debug(["getComposant :", component])
    
    return component
