"""Standalone adaptation of MEA workbench/ollama_install.py; no MEA imports."""
import os
from pathlib import Path
import platform
import plistlib
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.request


class InstallCancelled(Exception):
    pass


def mac_version():
    return tuple(int(part) for part in platform.mac_ver()[0].split('.')[:2])


def require_supported_macos():
    if mac_version() < (14, 0):
        raise RuntimeError(
            'This Mac runs macOS '+platform.mac_ver()[0]+'. Current official Ollama requires macOS 14 or later. '
            'Upgrade macOS before updating Ollama for this model. The existing Ollama and downloaded models were not changed. '
            'You can continue using models already supported by the installed runtime. https://docs.ollama.com/macos')


def run_command(args, cancelled, timeout=900):
    with tempfile.TemporaryFile() as output:
        process=subprocess.Popen(args,stdout=output,stderr=subprocess.STDOUT,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),
                                 start_new_session=os.name!='nt')
        deadline=time.monotonic()+timeout
        while process.poll() is None:
            if cancelled() or time.monotonic()>deadline:
                if os.name!='nt':os.killpg(process.pid,signal.SIGTERM)
                else:process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                if cancelled():raise InstallCancelled()
                raise RuntimeError('Ollama installer command timed out.')
            time.sleep(.1)
        output.seek(0);message=output.read().decode('utf8',errors='replace')
        if process.returncode:
            raise RuntimeError('Ollama installation/update failed: '+message[-1800:])
        return message


def install_windows_direct(progress, cancelled):
    """Use the signed official installer when App Installer is unavailable."""
    with tempfile.TemporaryDirectory(prefix='scholarstyle-ollama-') as directory:
        installer=Path(directory)/'OllamaSetup.exe'
        progress('Downloading the official Ollama Windows installer…')
        with urllib.request.urlopen('https://ollama.com/download/OllamaSetup.exe',timeout=60) as response, installer.open('wb') as output:
            total=int(response.headers.get('Content-Length',0));received=0;last=0
            while True:
                if cancelled():raise InstallCancelled()
                chunk=response.read(1024*1024)
                if not chunk:break
                output.write(chunk);received+=len(chunk)
                if time.monotonic()-last>1:
                    progress(f'Downloading Ollama: {received/1e6:.0f} MB'+(f' / {total/1e6:.0f} MB' if total else ''))
                    last=time.monotonic()
        if cancelled():raise InstallCancelled()
        progress('Verifying the official installer signature…')
        # Literal PowerShell path quoting prevents interpolation of directory names.
        quoted="'"+str(installer).replace("'","''")+"'"
        run_command(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            '$s=Get-AuthenticodeSignature -LiteralPath '+quoted+'; '
            'if ($s.Status -ne "Valid" -or $s.SignerCertificate.Subject -notmatch "Ollama") '
            '{ throw "Ollama installer signature verification failed" }'],cancelled,60)
        if cancelled():raise InstallCancelled()
        progress('Installing Ollama. Windows may request installation permission…')
        run_command([str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-'],cancelled)


def install_runtime(progress, cancelled, upgrade=False):
    system=platform.system()
    if system=='Windows':
        winget=shutil.which('winget')
        progress('Updating Ollama…' if upgrade else 'Installing Ollama…')
        # Stop its runtime before replacing executable files. Model weights are preserved.
        if upgrade:
            subprocess.run(['taskkill','/IM','ollama.exe','/T','/F'],capture_output=True,timeout=15)
        if winget:
            try:
                run_command([winget,'upgrade' if upgrade else 'install','--id','Ollama.Ollama','--exact','--silent',
                             '--accept-package-agreements','--accept-source-agreements','--disable-interactivity'],cancelled)
            except RuntimeError:
                progress('Windows Package Manager could not complete setup; using the official installer…')
                install_windows_direct(progress,cancelled)
        else:
            install_windows_direct(progress,cancelled)
        candidate=Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Ollama/ollama.exe'
        executable=shutil.which('ollama') or (str(candidate) if candidate.is_file() else None)
        if not executable:raise RuntimeError('Ollama installation finished but its executable was not found.')
        return executable
    if system!='Darwin':
        raise RuntimeError('Automatic runtime installation is supported on macOS and Windows. Install/update Ollama using https://ollama.com/download then retry; model download is automatic on all platforms.')
    require_supported_macos()
    progress('Downloading the official Ollama installer…')
    with tempfile.TemporaryDirectory(prefix='scholarstyle-ollama-') as directory:
        directory=Path(directory);dmg=directory/'Ollama.dmg'
        with urllib.request.urlopen('https://ollama.com/download/Ollama.dmg',timeout=60) as response, dmg.open('wb') as output:
            total=int(response.headers.get('Content-Length',0));received=0;last=0
            while True:
                if cancelled():raise InstallCancelled()
                chunk=response.read(1024*1024)
                if not chunk:break
                output.write(chunk);received+=len(chunk)
                if time.monotonic()-last>1:
                    progress(f'Downloading Ollama: {received/1e6:.0f} MB'+(f' / {total/1e6:.0f} MB' if total else ''));last=time.monotonic()
        mountpoint=directory/'volume';mountpoint.mkdir()
        mounts=[str(mountpoint)]
        try:
            listing=run_command(['hdiutil','attach','-readonly','-nobrowse','-mountpoint',str(mountpoint),'-plist',str(dmg)],cancelled,120)
            mounts=[entry['mount-point'] for entry in plistlib.loads(listing.encode())['system-entities'] if 'mount-point' in entry]
            bundle=next((Path(m)/'Ollama.app' for m in mounts if (Path(m)/'Ollama.app').is_dir()),None)
            if not bundle:raise RuntimeError('The official installer did not contain Ollama.app.')
            progress('Verifying the downloaded application signature…')
            run_command(['codesign','--verify','--deep','--strict',str(bundle)],cancelled,120)
            run_command(['spctl','--assess','--type','execute',str(bundle)],cancelled,120)
            with (bundle/'Contents/Info.plist').open('rb') as info:
                minimum=plistlib.load(info).get('LSMinimumSystemVersion','14.0')
            if mac_version()<tuple(int(v) for v in minimum.split('.')[:2]):
                raise RuntimeError('Downloaded Ollama requires macOS '+minimum+'. Existing installation was not changed.')
            applications=Path.home()/'Applications';applications.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.scholarstyle-ollama-stage-',dir=applications) as stage:
                staged=Path(stage)/'Ollama.app'
                run_command(['ditto',str(bundle),str(staged)],cancelled,180)
                if cancelled():raise InstallCancelled()
                progress('Restarting local Ollama with the updated application…')
                # Close the app, then stop a CLI server only if its executable belongs to Ollama.app.
                subprocess.run(['osascript','-e','tell application id "com.electron.ollama" to quit'],capture_output=True,timeout=20)
                listeners=subprocess.run(['lsof','-t','-iTCP:11434','-sTCP:LISTEN'],capture_output=True,text=True,timeout=10)
                for value in listeners.stdout.split():
                    command=subprocess.run(['ps','-p',value,'-o','comm='],capture_output=True,text=True,timeout=10).stdout.strip()
                    if command.endswith('/Ollama.app/Contents/Resources/ollama'):
                        os.kill(int(value),signal.SIGTERM)
                    else:
                        raise RuntimeError('Port 11434 is occupied by an unrecognized process. Stop that server and retry the update.')
                target=applications/'Ollama.app';backup=None
                if target.exists():
                    backup=applications/('Ollama.previous-'+str(time.time_ns())+'.app');target.rename(backup)
                try:staged.rename(target)
                except Exception:
                    if backup:backup.rename(target)
                    raise
                progress('Ollama installed in ~/Applications. Previous user installation retained as a backup.')
                return str(target/'Contents/Resources/ollama')
        finally:
            for mount in mounts:
                subprocess.run(['hdiutil','detach',mount],capture_output=True,timeout=30)
