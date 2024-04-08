import subprocess

def run_script(script_path):
    try:
        subprocess.run(["python", script_path], check=True)
        print(f"Das Skript '{script_path}' wurde erfolgreich ausgeführt.")
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen des Skripts '{script_path}': {e}")

# Pfade zu den beiden Python-Skripten
script1_path = "fill_database.py"
script2_path = "clean_data.py"

# Ausführen der Skripte
run_script(script1_path)
run_script(script2_path)