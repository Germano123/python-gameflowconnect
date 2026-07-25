import sys
import os
import subprocess
import shutil

def run_build():
    print("============================================================")
    print("  GameFlowConnect - Compilador de Executavel Windows (PyInstaller)")
    print("============================================================\n")

    # 1. Garantir que estamos no Windows
    if not sys.platform.startswith("win"):
        print("Aviso: O foco principal deste script e o empacotamento para Windows.")
        print(f"Sistema operacional atual: {sys.platform}")

    # 2. Instalar PyInstaller se necessario
    try:
        import PyInstaller
        print("[OK] PyInstaller ja esta instalado no ambiente.")
    except ImportError:
        print("PyInstaller nao encontrado. Instalando via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller instalado com sucesso!")
        except Exception as e:
            # Evitar caracteres unicode especiais no print para evitar erros de encoding no console do Windows
            print(f"Erro ao instalar PyInstaller: {str(e)}")
            sys.exit(1)

    # 3. Detectar diretorio de recursos do CustomTkinter
    try:
        import customtkinter
        ctk_path = os.path.dirname(customtkinter.__file__)
        print(f"[OK] CustomTkinter encontrado em: {ctk_path}")
    except ImportError:
        print("Erro: CustomTkinter nao encontrado no ambiente Python.")
        print("Certifique-se de ativar o ambiente virtual (venv) correspondente.")
        sys.exit(1)

    # 4. Configurar flags do PyInstaller
    sep = ";" if sys.platform.startswith("win") else ":"
    ctk_data = f"{ctk_path}{sep}customtkinter"
    
    # Limpar pastas antigas de build se existirem
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Limpando pasta residual anterior: {folder}...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Aviso ao limpar pasta: {str(e)}")

    # Comando PyInstaller executado via modulo do python atual para evitar problemas de PATH
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--name=GameFlowConnect",
        f"--add-data={ctk_data}",
        "--paths=src",
        "--clean",
        "src/main.py"
    ]

    print("\nExecutando o PyInstaller para empacotamento...")
    print(f"Comando: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\n============================================================\n")
        print("  [OK] PROCESSO DE COMPILACAO CONCLUIDO COM SUCESSO!")
        print("============================================================\n")
        print("O aplicativo compilado foi gerado na pasta:")
        print(f"-> {os.path.abspath('dist/GameFlowConnect')}\n")
        print("Você pode testar executando o arquivo:")
        print(f"-> {os.path.abspath('dist/GameFlowConnect/GameFlowConnect.exe')}\n")
        print("Dica: Copie a sua pasta 'data' (com credentials.json se houver) ")
        print("para a mesma pasta do executavel para habilitar o Google Drive localmente.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERRO] Erro durante o processo do PyInstaller: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
