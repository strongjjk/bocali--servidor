"""Small ViaCEP adapter used only for checkout address autofill."""
import json, re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def lookup_cep(value):
    cep=re.sub(r"\D","",str(value or ""))
    if not re.fullmatch(r"\d{8}",cep):
        return 422,{"error":"Informe um CEP com 8 digitos."}
    req=Request(f"https://viacep.com.br/ws/{cep}/json/",headers={"User-Agent":"Bocali/1.0"})
    try:
        with urlopen(req,timeout=6) as r:
            data=json.loads(r.read(200000).decode("utf-8"))
    except (URLError,HTTPError,TimeoutError,ValueError):
        return 503,{"error":"Nao foi possivel consultar o CEP agora. Preencha o endereco manualmente."}
    if data.get("erro"):
        return 404,{"error":"CEP nao encontrado."}
    return 200,{"address":{
        "street":str(data.get("logradouro") or "").strip(),
        "number":"",
        "neighborhood":str(data.get("bairro") or "").strip(),
        "city":str(data.get("localidade") or "").strip(),
        "state":str(data.get("uf") or "").strip().upper(),
        "postcode":str(data.get("cep") or "").strip(),
        "complement":""
    },"provider":"ViaCEP"}
