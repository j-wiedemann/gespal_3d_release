# coding: utf-8

import sys, os
import sqlite3
from sqlite3 import Error

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui
    from freecad.workbench_gespal3d import print_debug
    from freecad.workbench_gespal3d import DEBUG_DB
    from freecad.workbench_gespal3d import PARAMPATH
    from freecad.workbench_gespal3d import ICONPATH
    from freecad.workbench_gespal3d import UIPATH
    from freecad.workbench_gespal3d import g3d_connect_db


__title__ = "Gespal 3D Components Manager"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


# Qt translation handling
def translate(context, text, disambig=None):
    return QtCore.QCoreApplication.translate(context, text, disambig)


class ComponentManager(QtGui.QDialog):
    def __init__(self, parent=None):
        super(ComponentManager, self).__init__()

        ui_file = os.path.join(UIPATH,'component_manager-gespal3d.ui')
        self.form = Gui.PySideUic.loadUi(ui_file)

        self.database_path_edit = self.form.findChild(QtGui.QLineEdit, "lineEdit")
        self.p = App.ParamGet(str(PARAMPATH))
        no_database = "true"
        self.dbPath = self.p.GetString("sqlitedb", no_database)
        
        
        self.database_path_edit.setText(self.dbPath)

        self.dbPathButton = self.form.findChild(QtGui.QPushButton, "pushButtonDBPath")
        self.dbPathButton.clicked.connect(self.chooseDatabasePath)
        
        self.componentTable =  self.form.findChild(QtGui.QTableWidget, "tableWidget")
        self.componentTable.itemChanged.connect(self.updateDB)
        self.componentTable.itemDoubleClicked.connect(self.doubleClick)
        self.componentTable.cellClicked.connect(self.cellSimpleClick)

        self.addButton = self.form.findChild(QtGui.QPushButton, "pushButtonAdd")
        self.addButton.clicked.connect(self.addComponent)

        self.delButton = self.form.findChild(QtGui.QPushButton, "pushButtonDel")
        self.delButton.clicked.connect(self.deleteComponent)

        self.cancelButton = self.form.findChild(QtGui.QPushButton, "pushButtonRej")
        self.cancelButton.clicked.connect(self.cancelAndClose)

        self.validateButton = self.form.findChild(QtGui.QPushButton, "pushButtonVal")
        self.validateButton.clicked.connect(self.acceptAndClose)
        print_debug("end setupUi")

        self.lastEditItem = {"row" : None, "column" : None, "value" : None}

        self.con = g3d_connect_db.sql_connection()
        self.cur = self.con.cursor()
        print_debug("connecting db")

        self.populate()
        print_debug("populate table")
        self.form.show()
        print_debug("show dialog")

    def closeEvent(self, event):
        print_debug(["closeEvent", event])
        self.con.close()
        #event.accept()
        

    def addComponent(self):
        """
        Add a component
        :return:
        """
        self.componentTable.setSortingEnabled(False)
        count = self.componentTable.rowCount()
        data = (count,"Désignation","0","0","1","0","R","0,0,0","0")
        sql = ''' INSERT INTO Composant(CO_COMPTEUR, CO_NOM, CO_FAMILLE, CO_LONGUEUR, CO_LARGEUR, CO_EPAISSEUR, CO_FORME, CO_COULEUR, CO_MASSE)
                      VALUES(?,?,?,?,?,?,?,?,?)'''
        self.cur.execute(sql, data)
        self.con.commit()
        self.componentTable.insertRow(count)
        self.populate()
        self.componentTable.scrollToBottom()

    def deleteComponent(self):
        """
        Delete a component row by co_compteur
        :return:
        """
        row = self.componentTable.currentRow()
        if row > -1:
            co_compteur = int(self.componentTable.item(row,0).text())
            sql = 'DELETE FROM Composant WHERE co_compteur=?'
            self.cur.execute(sql, (co_compteur,))
            self.con.commit()
            self.populate()
        else:
            print_debug("Select a component in the table first!")
            QtGui.QMessageBox.warning(None,"Pas de composant sélectionné.","Veuillez sélectionner un composant dans le tableau avant de cliquer sur Supprimer.")

    def cancelAndClose(self):
        """
        Cancel all operations previously done and close window...or not.
        FIX ME : Make a backup of the db
        :return:
        """
        self.con.close()
        self.form.close()
        print_debug("cancelAndClose done")

    def acceptAndClose(self):
        self.con.close()
        self.form.close()
        print_debug("acceptAndClose done")

    def chooseDatabasePath(self):
        """
        when user click on change button a file dialog pop up to him
        :return:
        """
        dbPath = QtGui.QFileDialog.getOpenFileName(None, "Chemin de la base de données des composants",self.dbPath, "sqlite file (*.sqdb);;All files (*)")
        if len(dbPath[0]) > 0:
            self.database_path_edit.setText(dbPath[0])
            self.dbPath = self.p.SetString("sqlitedb", dbPath[0])
            self.populate()

    def populate(self):
        self.componentTable.blockSignals(True)
        self.cur.execute("SELECT * FROM Famille_Composant")
        cat_list = self.cur.fetchall()
        self.cat_name_list = [x[1] for x in cat_list]
        self.cat_name_list.append("Ajouter...")
        self.cur.execute("SELECT * FROM Composant")
        data = self.cur.fetchall()
        count = len(data)
        self.componentTable.setRowCount(count)
        for i, item in enumerate(data):
            index_item = QtGui.QTableWidgetItem()
            index_item.setData(QtCore.Qt.EditRole, int(item[0]))
            # EDITABLE = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
            # NONEDITABLE = QtCore.Qt.ItemIsEnabled
            index_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.componentTable.setItem(i, 0, index_item)
            
            # Categorie
            cat_des = cat_list[int(item[2])-1][1]
            cat = QtGui.QTableWidgetItem(str(cat_des))
            self.componentTable.setItem(i, 1, cat)
            
            # Component name
            name = QtGui.QTableWidgetItem(str(item[1]))
            self.componentTable.setItem(i, 2, name)

            # Shape
            shape = QtGui.QTableWidgetItem(str(item[6]))
            self.componentTable.setItem(i, 3, shape)
            
            # Width
            width = QtGui.QTableWidgetItem()
            width.setData(QtCore.Qt.EditRole, int(item[4]))
            self.componentTable.setItem(i, 4, width)

            # Height
            height = QtGui.QTableWidgetItem()
            height.setData(QtCore.Qt.EditRole, int(item[5]))
            self.componentTable.setItem(i, 5, height)

            # Length
            length = QtGui.QTableWidgetItem()
            length.setData(QtCore.Qt.EditRole, int(item[3]))
            self.componentTable.setItem(i, 6, length)

            # Color
            color = [int(x) for x in item[7].split(',')]
            self.componentTable.setItem(i, 7, QtGui.QTableWidgetItem())
            if len(color) == 3:
                self.componentTable.item(i, 7).setBackground(QtGui.QColor(color[0], color[1], color[2],))
            else:
                self.componentTable.item(i, 7).setBackground(QtGui.QColor(0, 0, 0,))
            self.componentTable.item(i, 7).setFlags(QtCore.Qt.ItemIsEnabled)
            
            # Mass volumique
            massvol = QtGui.QTableWidgetItem(str(item[8]))
            self.componentTable.setItem(i, 8, massvol)
        
        self.componentTable.blockSignals(False)
        print_debug("populate done")

    def cellSimpleClick(self, row, col):
        print_debug("Cell simple clicked : row {} column {} value {}".format(row, col,self.componentTable.item(row,col).text()))
        if self.lastEditItem["row"] != None:
            if row != self.lastEditItem["row"] or col != self.lastEditItem["column"]:
                print_debug("Click outside edited cell")
                self.componentTable.removeCellWidget(self.lastEditItem["row"], self.lastEditItem["column"])
                self.componentTable.setSortingEnabled(True)
        self.lastEditItem["row"] = row
        self.lastEditItem["column"] = col
        self.lastEditItem["value"] = self.componentTable.item(row,col).text()
    
    def doubleClick(self, itm):
        row = int(itm.row())
        column = int(itm.column())
        oldvalue = itm.text()
        print_debug("Double Click : enter edit mode cell row {} column {} with value : {}".format(row, column, oldvalue))
        self.lastEditItem["row"] = row
        self.lastEditItem["column"] = column
        self.lastEditItem["value"] = oldvalue
        self.componentTable.setSortingEnabled(False)
        if column == 1: # Category
            self.componentTable.blockSignals(True)
            cat_des = oldvalue
            #cat = QtGui.QTableWidgetItem(str(""))
            comboBox = QtGui.QComboBox()
            #comboBox.setEditable(True)
            comboBox.addItems(self.cat_name_list)
            index = comboBox.findText(cat_des, QtCore.Qt.MatchFixedString)
            comboBox.setCurrentIndex(index)
            comboBox.setProperty('row', row)
            comboBox.setProperty('column', column)
            self.componentTable.blockSignals(False)
            comboBox.currentIndexChanged.connect(self.Combo_indexchanged)
            #comboBox.currentTextChanged.connect(self.categoryCB_textChanged)
            self.componentTable.setCellWidget(row, column, comboBox)
        elif column == 3: # Section Shape
            self.componentTable.blockSignals(True)
            shape_type_name = oldvalue
            shape_type = QtGui.QTableWidgetItem(str(shape_type_name))
            self.componentTable.setItem(row, column, shape_type)
            comboBox = QtGui.QComboBox()
            comboBox.setEditable(False)
            comboBox.addItems(['R','C'])
            index = comboBox.findText(shape_type_name, QtCore.Qt.MatchFixedString)
            comboBox.setCurrentIndex(index)
            comboBox.setProperty('row', row)
            comboBox.setProperty('column', column)
            self.componentTable.blockSignals(False)
            comboBox.currentIndexChanged.connect(self.Combo_indexchanged)
            #comboBox.currentTextChanged.connect(self.categoryCB_textChanged)
            self.componentTable.setCellWidget(row, column, comboBox)
        elif column == 4 or column == 5 or column == 6: # WIDTH or HEIGHT or LENGTH
            self.componentTable.blockSignals(True)
            value = oldvalue
            self.componentTable.removeCellWidget(row, column)
            spinbox = QtGui.QSpinBox()
            spinbox.setProperty('row', row)
            spinbox.setProperty('column', column)
            spinbox.setMinimum(0)
            spinbox.setMaximum(100000)
            spinbox.setValue(int(value))
            spinbox.valueChanged.connect(self.SpinBox_valuechanged)
            self.componentTable.blockSignals(False)
            self.componentTable.setCellWidget(row, column, spinbox)
        elif column == 7:
            print_debug(["checkState",itm.isSelected()])
            couleur = QtGui.QColorDialog.getColor()
            if couleur.isValid():
                red   = int(str(couleur.name()[1:3]),16)    # decode hexadecimal to int()
                green = int(str(couleur.name()[3:5]),16)    # decode hexadecimal to int()
                blue  = int(str(couleur.name()[5:7]),16)    # decode hexadecimal to int()
                self.componentTable.item(row, column).setBackground(QtGui.QColor(red, green, blue,))
        elif column == 8: # Mass Vol
            self.componentTable.blockSignals(True)
            value = oldvalue
            self.componentTable.removeCellWidget(row, column)
            spinbox = QtGui.QSpinBox()
            spinbox.setProperty('row', row)
            spinbox.setProperty('column', column)
            spinbox.setMinimum(0)
            spinbox.setMaximum(100000)
            spinbox.setValue(int(value))
            spinbox.valueChanged.connect(self.SpinBox_valuechanged)
            self.componentTable.blockSignals(False)
            self.componentTable.setCellWidget(row, column, spinbox)


    @QtCore.Slot()
    def Combo_indexchanged(self, idx):
        combo = self.sender()
        row = combo.property('row')
        column = combo.property('column')
        index = combo.currentIndex()
        print_debug('Index Changed : combo row %d column %d indexChanged to %d' % (row, column, index))
        if column == 1: # CATEGORY
            text = combo.currentText()
            if text != "Ajouter...":
                cat = QtGui.QTableWidgetItem(text)
                self.componentTable.removeCellWidget(row,column)
                self.componentTable.setItem(row, column, cat)
            else:
                (fc_nom, bool_cat) = QtGui.QInputDialog.getText(None,"Categorie", "Nom de la nouvelle catégorie :")
                if bool_cat:
                    (fc_type, bool_type) =  QtGui.QInputDialog.getItem(None,"Categorie", "Choisir BO pour des composants de type Bois Massif, choisir PX pour les composants de type Panneaux.", ["BO","PX"])
                    if bool_type:
                        self.cat_name_list.insert(-1, fc_nom)
                        data = (index+1,fc_nom,fc_type)
                        sql = ''' INSERT INTO Famille_Composant(FC_COMPTEUR, FC_NOM, FC_TYPE)
                                  VALUES(?,?,?)'''
                        self.cur.execute(sql, data)
                        self.con.commit()
                        self.componentTable.removeCellWidget(row,column)
                        cat = QtGui.QTableWidgetItem(fc_nom)
                        self.componentTable.setItem(row, column, cat)
        elif column == 3: #Shape type
            text = combo.currentText()
            self.componentTable.removeCellWidget(row,column)
            shape_type = QtGui.QTableWidgetItem(text)
            self.componentTable.setItem(row, column, shape_type)


    @QtCore.Slot()
    def categoryCB_textChanged(self, txt):
        pass
                
    @QtCore.Slot()
    def SpinBox_valuechanged(self, value):
        spinbox = self.sender()
        row = spinbox.property('row')
        column = spinbox.property('column')
        print_debug('Spinbox value changed : row %d column %d value changed to %d' % (row, column, value))
        itm = QtGui.QTableWidgetItem()
        itm.setData(QtCore.Qt.EditRole, value)
        self.componentTable.setItem(row, column, itm)
        

    def updateDB(self, itmWid):
        row = int(itmWid.row())
        column = int(itmWid.column())
        co_compteur = int(self.componentTable.item(row,0).text())
        value = str(itmWid.text())
        cell = "row " + str(itmWid.row()) + " | col " + str(itmWid.column())
        print_debug("Updating Cell : {}, with value : {}".format(cell, value))
        self.componentTable.setSortingEnabled(True)

        if column == 1:
            value = self.cat_name_list.index(value) + 1
            sql = ''' UPDATE Composant
                      SET CO_FAMILLE = ?
                      WHERE CO_COMPTEUR = ?'''

        if column == 2:
            sql = ''' UPDATE Composant
                      SET CO_NOM = ?
                      WHERE CO_COMPTEUR = ?'''

        if column == 3:
            sql = ''' UPDATE Composant
                      SET CO_FORME = ?
                      WHERE CO_COMPTEUR = ?'''

        if column == 4:
            sql = ''' UPDATE Composant
                      SET CO_LARGEUR = ?
                      WHERE CO_COMPTEUR = ?'''

        if column == 5:
            sql = ''' UPDATE Composant
                      SET CO_EPAISSEUR = ?
                      WHERE CO_COMPTEUR = ?'''

        if column == 6:
            sql = ''' UPDATE Composant
                      SET CO_LONGUEUR = ?
                      WHERE CO_COMPTEUR = ?'''

        if column == 7:
            value = ""
            comma = 0
            #print_debug(itmWid.backgroundColor().getRgb())
            for c in itmWid.backgroundColor().getRgb()[0:3]:
                value += str(c)
                if comma < 2:
                    value += ","
                    comma += 1
            sql = ''' UPDATE Composant
                      SET CO_COULEUR = ?
                      WHERE CO_COMPTEUR = ?'''

        if column == 8:
            sql = ''' UPDATE Composant
                      SET CO_MASSE = ?
                      WHERE CO_COMPTEUR = ?'''

        self.cur.execute(sql, (value, co_compteur))
        self.con.commit()



class G3D_ComponentsManager:

    "Gespal 3D - Components Manager tool"

    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONPATH, "preferences-general.svg"),
            "MenuText": QtCore.QT_TRANSLATE_NOOP("Gespal3D", "Gestionnaire de composants"),
            "Accel": "G, C",
            "ToolTip": "<html><head/><body><p><b>Gestionnaire de composants.</b> \
                    <br><br> \
                    Permet d'ajouter et supprimer des composants (barres, panneaux, dés, etc). \
                    </p></body></html>",
        }

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

    def Activated(self):
        self.form = ComponentManager()



if App.GuiUp:
    # register the FreeCAD command
    Gui.addCommand("G3D_ComponentsManager", G3D_ComponentsManager())

App.Console.PrintLog("Loading G3D Component Manager... done\n")