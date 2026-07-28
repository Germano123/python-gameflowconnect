import sys
import os
import subprocess
import shutil

VERSION = "2.0.1-alpha"

def generate_iss_file():
    print(f"Gerando arquivo de configuracao do Inno Setup (GameFlowConnect.iss) para a versao {VERSION}...")
    iss_content = f"""; Script do Inno Setup para o GameFlowConnect
#define MyAppName "GameFlowConnect"
#define MyAppVersion "{VERSION}"
#define MyAppPublisher "GameFlow team"
#define MyAppExeName "GameFlowConnect.exe"

[Setup]
; ID unico gerado para identificar o instalador
AppId={{{{D37E8F01-7F4C-4D2A-9E8D-6FF5EBE5DE8A}}

AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DisableProgramGroupPage=yes
OutputBaseFilename=GameFlowConnect_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
; Copiar todo o conteudo gerado pelo PyInstaller na pasta dist
Source: "dist\\GameFlowConnect\\*"; DestDir: "{{app}}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
"""
    try:
        with open("GameFlowConnect.iss", "w", encoding="utf-8") as f:
            f.write(iss_content)
        print("[OK] Arquivo 'GameFlowConnect.iss' gerado com sucesso na raiz do projeto.")
    except Exception as e:
        print(f"[ERRO] Falha ao gerar arquivo GameFlowConnect.iss: {str(e)}")

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

    # Comando PyInstaller executado via modulo do python atual
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
        print("  [OK] PROCESSO DE COMPILACAO PYINSTALLER CONCLUIDO!")
        print("============================================================\n")
        print("O aplicativo portavel foi gerado na pasta:")
        print(f"-> {os.path.abspath('dist/GameFlowConnect')}\n")
        print("Voce pode testar executando o arquivo:")
        print(f"-> {os.path.abspath('dist/GameFlowConnect/GameFlowConnect.exe')}\n")

        # Copiar arquivo de configuracao .env (ou .env.example como fallback) para a pasta compilada
        env_dest = os.path.join("dist", "GameFlowConnect", ".env")
        if os.path.exists(".env"):
            shutil.copy(".env", env_dest)
            print("[OK] Arquivo de configuracao '.env' copiado para a distribuicao portatil.")
        elif os.path.exists(".env.example"):
            shutil.copy(".env.example", env_dest)
            print("[OK] '.env.example' copiado como '.env' para a distribuicao portatil (Preencha as chaves!).")

        # Gerar o arquivo .iss de configuracao do Inno Setup automaticamente
        generate_iss_file()

        # 5. Gerar versão portátil compactada (.zip)
        print("\nGerando pacote portátil compactado (.zip)...")
        try:
            zip_name = f"GameFlowConnect_v{VERSION}_Portable"
            zip_path = os.path.join("dist", zip_name)
            if os.path.exists(f"{zip_path}.zip"):
                os.remove(f"{zip_path}.zip")
            shutil.make_archive(zip_path, 'zip', root_dir="dist", base_dir="GameFlowConnect")
            print(f"[OK] Pacote portátil criado com sucesso em: {os.path.abspath(zip_path)}.zip")
        except Exception as e:
            print(f"[Aviso] Falha ao criar arquivo ZIP portátil: {str(e)}")
        
        print("\nPróximos Passos:")
        print(f"1. A versão portátil está pronta em: {os.path.abspath('dist/GameFlowConnect_v' + VERSION + '_Portable.zip')}")
        print("2. Para gerar o instalador clássico, abra o arquivo 'GameFlowConnect.iss' gerado no Inno Setup Compiler e pressione F9.")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERRO] Falha durante o processo de compilação: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_build()
