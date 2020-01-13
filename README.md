# gespal3d
Atelier FreeCAD de conception de palettes et emballages

## Installation

### Préparation

Avoir un compte Github (www.github.com)

Avoir un contrat Gespal 3D

### Installation de FreeCAD en version 0.19 minimum

Installer FreeCAD version 0.19

Créer un compte sur Github

Être collaborateur (contrat)

Dans FreeCAD:
menu Outils
    Addon Manager
        Configure
        Cocher Automatically Check for Updates
        Ajouter la ligne suivante dans le rectangle blanc :
          git@github.com:j-wiedemann/gespal3d.git

        Cliquer Sur OK
    Fermer l'addon Manager
    Relancer l'addon Manager
        Chercher gespal3d dans la liste des Atelier
        Cliquer sur gespal3d
        Cliquer sur Install/Update selected
    Fermer l'addon Manager (avec la croix)
    Un message vous prévient qu'il faut redémarrer FreeCAD pour activer le nouvel atelier.
    Cliquer sur Ok pour redémarrer FreeCAD maintenant.

Dans le sélecteur d'atelier vous trouverez Gespal 3D

Sur Linux : Installer python3-git
Windows : DL

## Paramétrage
Lancer FreeCAD
Basculer sur l'atelier Gespal 3D

Menu Outils
  Éditer Paramètres
  Naviguer dans BaseApp / Preferences / Mod / Gespal3D
  Clic droit dans le rectangle blanc de droite
    Nouvel article chaîne
    Nom : sqlitedb
    Texte : chemin vers la base de données sqlite
