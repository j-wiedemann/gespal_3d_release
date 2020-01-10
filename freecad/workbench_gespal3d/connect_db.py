import FreeCAD as App
import sqlite3
from sqlite3 import Error
from freecad.workbench_gespal3d import DEBUG


def sql_connection():
    path = "User parameter:BaseApp/Preferences/Mod/Gespal3D"
    p = App.ParamGet(str(path))
    no_database = "true"
    sqlite_db = p.GetString("sqlitedb", no_database)
    if sqlite_db is "true":
        App.Console.PrintMessage("define database path in BaseApp/Preferences/Mod/Gespal3D")
        return
    try:

        con = sqlite3.connect(sqlite_db)

        if DEBUG:
            App.Console.PrintMessage("Connection is established.")

    except Error:
        App.Console.PrintMessage("sql_connection got an error")
        App.Console.PrintMessage(Error)

    return con


def getCategories(include=[], exclude=[]):
    categories_list = []
    con = sql_connection()
    cursorObj = con.cursor()
    cursorObj.execute('SELECT * FROM Famille_Composant')
    rows = cursorObj.fetchall()
    if len(include) > 0:
        for row in rows:
            if row[1] in include:
                categories_list.append(row)
    if len(exclude) > 0:
        for row in rows:
            if not row[1] in exclude:
                categories_list.append(row)
    if DEBUG:
        print("getCategories :")
        print(categories_list)
    return categories_list


def getComposants(categorie=None):
    if categorie:
        con = sql_connection()
        cursorObj = con.cursor()
        cursorObj.execute(
            'SELECT * FROM Composant WHERE CO_FAMILLE = ' + str(categorie))
        rows = cursorObj.fetchall()
        if DEBUG:
            print("getComposants :")
            print(rows)
        return rows


def getComposant(id=1):
    con = sql_connection()
    cursorObj = con.cursor()
    cursorObj.execute(
        'SELECT * FROM Composant WHERE CO_COMPTEUR = ' + str(id))
    rows = cursorObj.fetchall()
    if DEBUG:
        App.Console.PrintMessage("getComposant :")
        App.Console.PrintMessage(rows)
    return rows[0]
