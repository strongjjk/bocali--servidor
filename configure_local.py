#!/usr/bin/env python3
"""Generate local test-only secrets on the user's own computer; never share .env."""
import argparse,os,secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description='Preparar o piloto local do Bocali')
    parser.add_argument('--show-codes',action='store_true',help='Mostrar os codigos locais no seu terminal')
    args=parser.parse_args();path=ROOT/'.env'
    if not path.exists():
        values={'PEDE_MODE':'local','PEDE_PUBLIC_ORIGIN':'http://127.0.0.1:8000',
            'PEDE_DATA_DIR':str(ROOT/'data'), 'PEDE_PILOT_CODE':secrets.token_urlsafe(24),
            'PEDE_SECRET_KEY':secrets.token_urlsafe(40),'PEDE_SETUP_TOKEN':secrets.token_urlsafe(32),
            'PEDE_DEMO_ADDRESSES':'1','PEDE_ENABLE_PDF':'1','PORT':'8000'}
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write('# Somente teste local. Nao publicar, enviar ou incluir este arquivo no ZIP.\n')
            for k,v in values.items():f.write(k+'='+v+'\n')
        show=True
        print('Configuracao local criada. Nenhuma conta, pagamento ou hospedagem foi contratado.')
    else:
        values={k:v for line in path.read_text(encoding='utf-8').splitlines() if '=' in line for k,v in [line.split('=',1)]}
        show=args.show_codes;print('Configuracao existente preservada.')
    if show:
        print('\nCODIGO PARA ENTRAR NO PILOTO:',values.get('PEDE_PILOT_CODE',''))
        print('CHAVE INICIAL DO RESPONSAVEL:',values.get('PEDE_SETUP_TOKEN',''))
        print('A segunda chave e exclusiva do responsavel. Nao mande esses valores no chat.\n')
    print('Inicie: python serve.py --local')
    print('Depois abra http://127.0.0.1:8000 neste mesmo computador.')

if __name__=='__main__':main()
