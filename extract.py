import pathlib

def generer_conglomerat(dossier_racine, fichier_sortie):
    racine = pathlib.Path(dossier_racine)
    extensions_cibles = {'.js', '.html', '.css', '.py'}
    
    with open(fichier_sortie, 'w', encoding='utf-8') as f_out:
        # 1. Génération de l'architecture (Tree view)
        f_out.write("### ARCHITECTURE DU PROJET ###\n\n")
        for chemin in sorted(racine.rglob('*')):
            # On ignore les dossiers cachés (comme .git ou .venv)
            if any(part.startswith('.') for part in chemin.parts):
                continue
                
            profondeur = len(chemin.relative_to(racine).parts) - 1
            indentation = '    ' * profondeur
            symbole = '|-- ' if chemin.is_file() else '[D] '
            f_out.write(f"{indentation}{symbole}{chemin.name}\n")
        
        f_out.write("\n" + "="*50 + "\n\n")

        # 2. Extraction du contenu des fichiers
        f_out.write("### CONTENU DES FICHIERS ###\n\n")
        for chemin in racine.rglob('*'):
            # Filtres : extension autorisée, pas de dossiers cachés, et on ne s'auto-lit pas
            if (chemin.suffix in extensions_cibles and 
                not any(part.startswith('.') for part in chemin.parts) and
                chemin.name != fichier_sortie):
                
                f_out.write(f"--- DÉBUT FICHIER : {chemin.relative_to(racine)} ---\n")
                f_out.write(f"--- POSITION : {chemin.absolute()} ---\n\n")
                
                try:
                    contenu = chemin.read_text(encoding='utf-8')
                    f_out.write(contenu)
                except Exception as e:
                    f_out.write(f"[ERREUR DE LECTURE : {e}]")
                
                f_out.write("\n\n--- FIN FICHIER ---\n\n")

if __name__ == "__main__":
    # Configuration
    NOM_DOSSIER = "."  # Le dossier actuel, ou mettez le chemin complet
    SORTIE = "code_complet.txt"
    
    print(f"Extraction en cours depuis {pathlib.Path(NOM_DOSSIER).absolute()}...")
    generer_conglomerat(NOM_DOSSIER, SORTIE)
    print(f"Terminé ! Tout a été copié dans : {SORTIE}")