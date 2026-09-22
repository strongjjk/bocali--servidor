"""Initialize volume ownership, then drop root before starting the web process."""
import os,sys
from pathlib import Path
root=Path(os.environ.get('BOCALI_DATA_DIR',os.environ.get('PEDE_DATA_DIR','/data'))).resolve()
if not root.is_relative_to(Path('/data')):
    raise SystemExit('No container, BOCALI_DATA_DIR deve estar em /data.')
root.mkdir(parents=True,exist_ok=True)
if hasattr(os,'geteuid') and os.geteuid()==0:
    os.chown(root,10001,10001);root.chmod(0o700)
    for name in ('bocali.sqlite3','bocali.sqlite3-wal','bocali.sqlite3-shm','pede.sqlite3','pede.sqlite3-wal','pede.sqlite3-shm'):
        path=root/name
        if path.is_symlink():raise SystemExit('Arquivo de dados nao pode ser um link simbolico.')
        if path.exists():os.chown(path,10001,10001);path.chmod(0o600)
    os.setgroups([]);os.setgid(10001);os.setuid(10001)
os.umask(0o077)
os.execv(sys.executable,[sys.executable,'/app/serve.py'])
