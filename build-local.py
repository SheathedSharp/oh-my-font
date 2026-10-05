#!/usr/bin/env python3
"""Create a project-local venv and generate the desktop and web formats.

Only dependencies listed in requirements.txt are installed. Nothing is installed
into the OS font directory. Does not use or rename an installed font.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parent

def main():
    if sys.version_info < (3,10):
        raise SystemExit('Python 3.10 or newer is required.')
    target=ROOT/'.venv'
    python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():
        print('Creating a local Python environment...',flush=True)
        venv.EnvBuilder(with_pip=True).create(target)
    print('Installing declared build dependencies (internet is needed on first run).',flush=True)
    subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check','-r',str(ROOT/'requirements.txt')],check=True,cwd=ROOT)
    subprocess.run([str(python),str(ROOT/'build.py'),*sys.argv[1:]],check=True,cwd=ROOT)

if __name__=='__main__':
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f'Build stopped (exit {e.returncode}). No fonts have been installed.',file=sys.stderr)
        sys.exit(e.returncode or 1)
    except OSError as e:
        print(f'Cannot prepare the build: {e}',file=sys.stderr)
        sys.exit(1)
