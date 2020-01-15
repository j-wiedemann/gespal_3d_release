# gespal3d
Atelier FreeCAD de conception de palettes et emballages


### 1. Installation de FreeCAD

Se connecter à cette adresse : https://github.com/FreeCAD/FreeCAD/releases/tag/0.19_pre

Télécharger le fichier : FreeCAD_0.19.xxxxx_x64_Conda_Py3QT5-WinVS2015.7z

xxxxx peut varier au fil du temps.

Extraire l'archive avec 7zip

Naviguer dans le dossier bin et double Cliquer sur FreeCAD.exe

### 2. Préparation

Avoir un compte Github (www.github.com)

Avoir un contrat Gespal 3D

Installer Git (www.git-scm.com)

configurer git :
https://help.github.com/en/github/using-git/setting-your-username-in-git

git config --global user.email "you@example.com"
git config --global user.name "Your Name"

### 3. Personnalisation

Afficher la vue rapport :

    menu Affichage
    Panneaux
    cocher Vue Rapport

### 4. Installation de Gespal 3D

Démarrer FreeCAD:
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
