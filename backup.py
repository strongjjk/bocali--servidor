#!/usr/bin/env python3
"""Consistent SQLite snapshot and non-destructive restore for the private pilot.
Never served through HTTP. Backups contain sensitive data; store them privately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

REQUIRED = {'users','stores','products','members','orders','sessions','quotes','addresses','audit','favorites'}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def inspect_db(path):
    path = Path(path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=10)) as conn:
        conn.execute('PRAGMA query_only=ON')
        if conn.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('A copia falhou na verificacao de integridade.')
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('A copia contem referencias inconsistentes.')
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not REQUIRED <= names:
            raise ValueError('Este arquivo nao e um banco Bocali valido.')
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version != 4:
            raise ValueError('Versao de banco nao suportada por este restaurador.')
        return {'schemaVersion':version,
            'users':conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'stores':conn.execute('SELECT COUNT(*) FROM stores').fetchone()[0],
            'orders':conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]}


def reserve(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)


def copy_consistently(source, target):
    source, target = Path(source).resolve(strict=True), Path(target).resolve()
    if source == target:
        raise ValueError('Origem e destino devem ser diferentes.')
    inspect_db(source)
    reserve(target)
    try:
        deadline = time.monotonic() + 60
        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise TimeoutError('Backup excedeu 60 segundos. Tente com menor movimento.')
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True, timeout=10)) as src:
            with closing(sqlite3.connect(target, timeout=10)) as dst:
                src.backup(dst, pages=128, progress=progress, sleep=.02)
                dst.execute('PRAGMA journal_mode=DELETE')
        inspect_db(target)
    except Exception:
        target.unlink(missing_ok=True)
        for suffix in ('-wal','-shm','-journal'):
            Path(str(target)+suffix).unlink(missing_ok=True)
        raise
    return target


def create_backup(source, target):
    target = Path(target).resolve()
    manifest = Path(str(target)+'.json')
    if target.exists() or manifest.exists():
        raise FileExistsError('Escolha um nome novo; nenhuma copia existente sera sobrescrita.')
    target = copy_consistently(source, target)
    result = {'createdAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'sha256':sha256(target), **inspect_db(target), 'format':'pede-snapshot-v1'}
    fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    return result


def verify_backup(source):
    source = Path(source).resolve(strict=True)
    manifest = json.loads(Path(str(source)+'.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 'pede-snapshot-v1' or manifest.get('sha256') != sha256(source):
        raise ValueError('A copia nao corresponde ao manifesto. Nao restaurar.')
    return inspect_db(source)


def restore_backup(source, target):
    verify_backup(source)
    target = copy_consistently(source, target)
    try:
        with closing(sqlite3.connect(target)) as conn:
            with conn:
                # Do not reactivate old sessions, address tokens or pending quotations.
                for table in ('sessions','addresses','quotes'):
                    conn.execute('DELETE FROM '+table)
        result = inspect_db(target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {'restored':True, 'sessionsInvalidated':True, **result}


def main():
    parser = argparse.ArgumentParser(description='Copia e restauracao privada do banco Bocali')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('create');p.add_argument('--db',required=True);p.add_argument('--out',required=True)
    p = sub.add_parser('verify');p.add_argument('snapshot')
    p = sub.add_parser('restore');p.add_argument('snapshot');p.add_argument('--to',required=True)
    args = parser.parse_args()
    try:
        if args.command == 'create': result=create_backup(args.db,args.out)
        elif args.command == 'verify':result=verify_backup(args.snapshot)
        else:result=restore_backup(args.snapshot,args.to)
        print(json.dumps(result, indent=2))
    except (OSError,ValueError,sqlite3.Error,TimeoutError) as exc:
        parser.exit(1, f'Operacao interrompida: {exc}\n')

if __name__=='__main__':main()
