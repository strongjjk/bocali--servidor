#!/usr/bin/env python3
"""Start Bocali on a private LAN for an accompanied Android pilot. Test data only."""
import os, socket, sys
from pilot_app import load_environment


def private_ip():
    candidates=[]
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(('1.1.1.1',80)); candidates.append(s.getsockname()[0]); s.close()
    except OSError:
        pass
    try:
        candidates.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    for ip in candidates:
        parts=ip.split('.')
        if len(parts)!=4: continue
        try: n=[int(x) for x in parts]
        except ValueError: continue
        if n[0]==10 or (n[0]==192 and n[1]==168) or (n[0]==172 and 16<=n[1]<=31): return ip
    raise SystemExit('Nao encontrei o IPv4 privado. Confira o Wi-Fi/Ethernet do computador.')

load_environment()
ip=private_ip(); port=int(os.environ.get('PORT','8000'))
os.environ['PEDE_MODE']='lan'
os.environ['PEDE_PUBLIC_ORIGIN']=f'http://{ip}:{port}'
print('\nBOCALI NA REDE LOCAL:',os.environ['PEDE_PUBLIC_ORIGIN'])
print('Use este endereco SOMENTE no APK de teste conectado a mesma rede.')
print('Se o Windows perguntar, permita Python apenas em redes privadas.\n')
import serve
sys.argv=['serve.py','--lan']
serve.main()
