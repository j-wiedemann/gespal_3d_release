## donnees du projet
PROJECT_ID = "PLAN"
PROJECT_FICHIER = "C:/PBC_Gespal_V4/32/Plans/5/PL_5.FCstd"
PROJECT_LONGUEUR = 700
PROJECT_LARGEUR = 600
PROJECT_HAUTEUR = 1400

# activer l'atelier Gespal 3D
FreeCADGui.activateWorkbench("gespal3d_workbench")

# importer la fonction
from freecad.workbench_gespal3d import enveloppe_creator

# creation d'un nouveau document
doc = App.newDocument(PROJECT_ID)

# creation de la boite englobante du projet
enveloppe_creator.makeEnveloppe(PROJECT_ID, PROJECT_LONGUEUR,PROJECT_LARGEUR,PROJECT_HAUTEUR)

# calcul du document
doc.recompute()

# afficher le repere
FreeCADGui.ActiveDocument.ActiveView.setAxisCross(True)

# vue axonometrique
FreeCADGui.activeDocument().activeView().viewAxonometric()

# tout afficher
FreeCADGui.SendMsgToActiveView("ViewFit")
# sauverger le projet
FreeCAD.getDocument(PROJECT_ID).saveAs(PROJECT_FICHIER)
