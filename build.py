#!/usr/bin/env python3

import os
import platform
import subprocess
import shutil
from pathlib import Path

def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def print_banner():
    banner = """
╔══════════════════════════════════════════════════╗
║         IPSW Firmware Comparison Tool            ║
║              Build System v1.0.1                 ║
╚══════════════════════════════════════════════════╝
    """
    print(banner)

def build_windows():
    print("\n[*] Building Windows executable...")
    try:
        # Create dist and build directories if they don't exist
        os.makedirs('dist', exist_ok=True)
        os.makedirs('build', exist_ok=True)
        
        # Clean previous builds
        print("[+] Cleaning previous builds...")
        if os.path.exists('dist/IPSWCompare'):
            shutil.rmtree('dist/IPSWCompare')
        
        print("[+] Starting PyInstaller build...")
        command = [
            "pyinstaller",
            "--name", "IPSWCompare",
            "--windowed",
            "--icon", "app_icon.icns",
            "--add-data", "app_icon.icns;.",
            "--add-data", "forest-dark.tcl;.",
            "--add-data", "forest-dark;forest-dark",
            "--hidden-import", "PIL",
            "--hidden-import", "PIL._tkinter_finder",
            "--hidden-import", "requests",
            "ipsw_firmware_tool.py"
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("[!] PyInstaller Error Output:")
            print(result.stderr)
            raise subprocess.CalledProcessError(result.returncode, command)
            
        print("\n[✓] Windows build completed successfully!")
        print(f"[i] Executable location: {os.path.abspath('dist/IPSWCompare/IPSWCompare.exe')}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Error during Windows build: {str(e)}")
        raise
    except Exception as e:
        print(f"\n[!] Unexpected error during Windows build: {str(e)}")
        raise

def build_linux():
    print("\n[*] Building Linux AppImage...")
    try:
        # Create dist and build directories if they don't exist
        os.makedirs('dist', exist_ok=True)
        os.makedirs('build', exist_ok=True)
        
        # Clean previous builds
        print("[+] Cleaning previous builds...")
        if os.path.exists('dist/IPSWCompare'):
            shutil.rmtree('dist/IPSWCompare')
        if os.path.exists('IPSWCompare.AppDir'):
            shutil.rmtree('IPSWCompare.AppDir')
        
        print("[+] Starting PyInstaller build...")
        command = [
            "pyinstaller",
            "--name", "IPSWCompare",
            "--windowed",
            "--icon", "app_icon.icns",
            "--add-data", "app_icon.icns:.",
            "--add-data", "forest-dark.tcl:.",
            "--add-data", "forest-dark:forest-dark",
            "--hidden-import", "PIL",
            "--hidden-import", "PIL._tkinter_finder",
            "--hidden-import", "requests",
            "ipsw_firmware_tool.py"
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("[!] PyInstaller Error Output:")
            print(result.stderr)
            raise subprocess.CalledProcessError(result.returncode, command)
        
        print("[+] Creating AppDir structure...")
        os.makedirs("IPSWCompare.AppDir/usr/bin", exist_ok=True)
        os.makedirs("IPSWCompare.AppDir/usr/share/applications", exist_ok=True)
        os.makedirs("IPSWCompare.AppDir/usr/share/icons/hicolor/256x256/apps", exist_ok=True)
        
        print("[+] Creating desktop entry...")
        with open("IPSWCompare.AppDir/usr/share/applications/IPSWCompare.desktop", "w") as f:
            f.write("""[Desktop Entry]
Name=IPSW Firmware Comparison Tool
Exec=IPSWCompare
Icon=ipswcompare
Type=Application
Categories=Development;
""")
        
        print("[+] Copying application files...")
        subprocess.run(["cp", "-r", "dist/IPSWCompare/*", "IPSWCompare.AppDir/usr/bin/"], shell=True)
        subprocess.run(["cp", "app_icon.icns", "IPSWCompare.AppDir/usr/share/icons/hicolor/256x256/apps/ipswcompare.png"], shell=True)
        
        print("[+] Downloading AppImage tools...")
        subprocess.run(["wget", "-q", "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"])
        subprocess.run(["chmod", "+x", "appimagetool-x86_64.AppImage"])
        
        print("[+] Creating AppImage...")
        subprocess.run(["./appimagetool-x86_64.AppImage", "IPSWCompare.AppDir", "IPSWCompare.AppImage"])
        
        print("\n[✓] Linux build completed successfully!")
        print(f"[i] AppImage location: {os.path.abspath('IPSWCompare.AppImage')}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Error during Linux build: {str(e)}")
        raise
    except Exception as e:
        print(f"\n[!] Unexpected error during Linux build: {str(e)}")
        raise

def build_mac():
    print("\n[*] Building macOS application...")
    try:
        # Create dist and build directories if they don't exist
        os.makedirs('dist', exist_ok=True)
        os.makedirs('build', exist_ok=True)
        
        # Clean previous builds
        print("[+] Cleaning previous builds...")
        if os.path.exists('dist/IPSWCompare.app'):
            shutil.rmtree('dist/IPSWCompare.app')
        
        print("[+] Starting PyInstaller build...")
        command = [
            "pyinstaller",
            "--name", "IPSWCompare",
            "--windowed",
            "--icon", "app_icon.icns",
            "--add-data", "app_icon.icns:.",
            "--add-data", "forest-dark.tcl:.",
            "--add-data", "forest-dark:forest-dark",
            "--hidden-import", "PIL",
            "--hidden-import", "PIL._tkinter_finder",
            "--hidden-import", "requests",
            "ipsw_firmware_tool.py"
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("[!] PyInstaller Error Output:")
            print(result.stderr)
            raise subprocess.CalledProcessError(result.returncode, command)
        
        # Create DMG if hdiutil is available (macOS only)
        if shutil.which('hdiutil'):
            print("[+] Creating DMG installer...")
            dmg_name = "IPSWCompare-Installer.dmg"
            subprocess.run([
                "hdiutil",
                "create",
                "-volname", "IPSW Compare",
                "-srcfolder", "dist/IPSWCompare.app",
                "-ov",
                "-format", "UDZO",
                dmg_name
            ])
            print(f"\n[✓] DMG installer created: {os.path.abspath(dmg_name)}")
        
        print("\n[✓] macOS build completed successfully!")
        print(f"[i] Application location: {os.path.abspath('dist/IPSWCompare.app')}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Error during macOS build: {str(e)}")
        raise
    except Exception as e:
        print(f"\n[!] Unexpected error during macOS build: {str(e)}")
        raise

def check_dependencies():
    print("[*] Checking dependencies...")
    missing_deps = []
    
    try:
        import PIL
    except ImportError:
        missing_deps.append("pillow")
    
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        import tkinter
    except ImportError:
        missing_deps.append("python3-tk")
    
    if missing_deps:
        print("\n[!] Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install required packages:")
        print("pip install " + " ".join(missing_deps))
        return False
    
    print("[✓] All required Python packages found")
    return True

def verify_resources():
    print("[*] Verifying resource files...")
    required_files = [
        'app_icon.icns',
        'forest-dark.tcl',
        'forest-dark',
        'ipsw_firmware_tool.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("\n[!] Missing required files:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    
    # Verify forest-dark directory contents
    if os.path.exists('forest-dark'):
        if not os.listdir('forest-dark'):
            print("\n[!] forest-dark directory is empty!")
            return False
    
    print("[✓] All required files found")
    return True

def main():
    clear_screen()
    print_banner()
    
    if not check_dependencies() or not verify_resources():
        return
    
    while True:
        print("\nSelect target platform to build for:")
        print("1. Linux")
        print("2. Windows")
        print("3. macOS")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        try:
            if choice == "1":
                build_linux()
                break
            elif choice == "2":
                build_windows()
                break
            elif choice == "3":
                build_mac()
                break
            elif choice == "4":
                print("\n[*] Build system terminated")
                break
            else:
                print("\n[!] Invalid choice. Please enter a number between 1-4.")
        except Exception as e:
            print(f"\n[!] Build failed: {str(e)}")
            print("\nWould you like to try again? (y/n)")
            if input().lower() != 'y':
                break

if __name__ == "__main__":
    main()