"""Opt-in Geoapify adapter for local tests. No API key or address is logged.
This does not authorize orders, prove an address exists, or provide an SLA.
"""
from __future__ import annotations
import json
import math
import os
import threading
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_LOCK = threading.Lock()
_LAST_CALL = 0.0

def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(value or '')) if not unicodedata.combining(c)).casefold().split())

def normalize_result(row: dict, requested: dict) -> dict | None:
    lat, lng = row.get('lat'), row.get('lon')
    if isinstance(lat, bool) or isinstance(lng, bool) or not isinstance(lat, (float, int)) or not isinstance(lng, (float, int)) or not math.isfinite(lat) or not math.isfinite(lng) or abs(lat) > 85 or abs(lng) > 180:
        return None
    rank = row.get('rank') or {}
    def confidence(key):
        try:
            return float(rank.get(key, 0))
        except (ValueError, TypeError):
            return 0.0
    state_code = str(row.get('state_code') or '').replace('BR-', '')
    exact = row.get('country_code') == 'br' and row.get('result_type') in ('building', 'amenity') and norm(row.get('housenumber')) == norm(requested['number']) and norm(row.get('city')) == norm(requested['city']) and norm(state_code) == norm(requested['state']) and bool(row.get('street')) and confidence('confidence') >= .95 and confidence('confidence_building_level') >= .9 and confidence('confidence_street_level') >= .95
    # These are conservative local policy thresholds, not provider guarantees.
    return {
        'point': {'lat': lat, 'lng': lng},
        'address': {
            'street': row.get('street') or requested['street'],
            'number': row.get('housenumber') or requested['number'],
            'neighborhood': row.get('suburb') or row.get('district') or requested['neighborhood'],
            'city': row.get('city') or requested['city'],
            'state': state_code or requested['state'],
            'postcode': row.get('postcode') or requested.get('postcode', ''),
            'complement': '',
        },
        'formatted': row.get('formatted', ''),
        'source': 'geoapify', 'precise': bool(exact),
    }

def geocode(address: dict) -> tuple[int, dict]:
    global _LAST_CALL
    if not isinstance(address, dict) or any(not isinstance(address.get(k), str) or not address[k].strip() or len(address[k]) > 120 for k in ('street', 'number', 'neighborhood', 'city', 'state')):
        return 400, {'error': 'Preencha rua, numero, bairro, cidade e UF.'}
    key = os.environ.get('GEOAPIFY_API_KEY', '').strip()
    if not key:
        return 503, {'error': 'Busca real desativada. Configure GEOAPIFY_API_KEY no servidor local.'}
    with _LOCK:
        now = time.monotonic()
        if now - _LAST_CALL < 1:
            return 429, {'error': 'Aguarde um instante antes de consultar novamente.'}
        _LAST_CALL = now
    text = ', '.join([address['street'] + ', ' + address['number'], address['neighborhood'], address['city'], address['state'], address.get('postcode', ''), 'Brasil'])
    params = urlencode({'text': text, 'format': 'json', 'filter': 'countrycode:br', 'lang': 'pt', 'limit': 4, 'apiKey': key})
    try:
        req = Request('https://api.geoapify.com/v1/geocode/search?' + params, headers={'User-Agent': 'Bocali/1.0'})
        with urlopen(req, timeout=10) as response:
            raw = response.read(1000001)
        if len(raw) > 1000000:
            raise ValueError('Response too large')
        data = json.loads(raw)
        results = [r for row in data.get('results', [])[:4] if isinstance(row, dict) and (r := normalize_result(row, address)) is not None]
        return 200, {'results': results, 'provider': 'Geoapify', 'demo': True}
    except Exception:
        # Never expose exception text: URLs may contain API keys and addresses.
        return 502, {'error': 'Provedor indisponivel. Nenhuma taxa foi liberada. Corrija ou tente novamente.'}
