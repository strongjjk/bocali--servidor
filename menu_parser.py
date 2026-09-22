#!/usr/bin/env python3
"""Parser conservador de cardapios do Bocali.

O objetivo e organizar um rascunho, nunca publicar automaticamente.
Ele privilegia evitar precos inventados a tentar adivinhar estruturas ambiguas.
"""
from __future__ import annotations
import re
import secrets
import unicodedata
from typing import Iterable

PRICE_RE = re.compile(r"(?<!\d)(?:R\$\s*(?:\d{1,4}(?:\.\d{3})*(?:[,.]\d{1,2})?)|\d{1,4}(?:\.\d{3})*[,.]\d{2})(?!\d)", re.I)
KNOWN_CATEGORY_WORDS = (
    'pasteis','pastéis','classicos','clássicos','especiais','bebidas','doces','salgados','pizzas',
    'porcoes','porções','acai','açaí','combos','lanches','sobremesas','sucos','caldos','massas','pratos',
    'porcoes','porções','adicionais','extras','promocoes','promoções','executivos','hamburgueres','hambúrgueres',
    'hot dog','cachorro quente','porcoes','porções','cervejas','refrigerantes','drinks','cafes','cafés'
)


def norm(value: str) -> str:
    value = unicodedata.normalize('NFD', str(value or ''))
    return ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn').strip().lower()


def money_to_cents(token: str):
    s = re.sub(r'(?i)R\$\s*', '', str(token or '')).strip().replace(' ', '')
    if not s:
        return None
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})*,\d{2}', s):
        s = s.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d+[,\.]\d{1,2}', s):
        s = s.replace(',', '.')
    elif re.fullmatch(r'\d+', s):
        # Inteiro sem centavos so e aceito se a linha tinha R$.
        if 'R$' not in str(token).upper():
            return None
    else:
        return None
    try:
        value = round(float(s) * 100)
    except ValueError:
        return None
    return value if 0 < value <= 10_000_000 else None


def clean_line(line: str) -> str:
    line = line.replace('\u00a0', ' ').replace('\t', ' ')
    line = re.sub(r'[ ]{2,}', ' ', line)
    return line.strip(' \u2022\u00b7|')


def looks_like_category(line: str) -> bool:
    raw = clean_line(line).rstrip(':')
    if not 2 <= len(raw) <= 48:
        return False
    if PRICE_RE.search(raw):
        return False
    n = norm(raw)
    if any(n == norm(x) or n.startswith(norm(x) + ' ') for x in KNOWN_CATEGORY_WORDS):
        return True
    letters = [c for c in raw if c.isalpha()]
    if len(letters) < 2:
        return False
    # Titulos em caixa alta aparecem com frequencia em cardapios exportados em PDF.
    upper_ratio = sum(c.isupper() for c in letters) / len(letters)
    if upper_ratio >= 0.82 and len(raw.split()) <= 6:
        return True
    return False


def _trim_name(value: str) -> str:
    value = re.sub(r'[.\s\-–—:|]+$', '', value).strip()
    value = re.sub(r'^[\u2022\-–—\s]+', '', value)
    return value[:100].strip()


def parse_menu_text(text: str, max_items: int = 250) -> dict:
    lines = [clean_line(x) for x in str(text or '').splitlines()]
    items = []
    warnings = []
    category = 'Importados'
    categories = []
    ignored_price_lines = 0
    category_seen = False

    for line_number, line in enumerate(lines, 1):
        if not line:
            continue
        if looks_like_category(line):
            category = line.rstrip(':')[:50]
            category_seen = True
            if category not in categories:
                categories.append(category)
            continue

        matches = list(PRICE_RE.finditer(line))
        if not matches:
            continue

        prices = []
        for match in matches:
            cents = money_to_cents(match.group(0))
            if cents is not None:
                prices.append((match, cents))
        if not prices:
            continue

        name = _trim_name(line[:prices[0][0].start()])
        if len(name) < 2:
            ignored_price_lines += 1
            warnings.append(f'Linha {line_number}: havia preco, mas faltou um nome claro antes dele.')
            continue

        item = {
            'id': 'imp_' + secrets.token_hex(8),
            'name': name,
            'description': '',
            'category': category,
            'price': None,
            'source': line[:300],
            'reviewed': False,
            'selected': True,
            'ambiguous': len(prices) > 1,
            'line': line_number,
            'confidence': 'high' if len(prices) == 1 and category_seen else 'medium',
            'priceOptions': [p for _, p in prices[:8]],
        }

        if len(prices) == 1:
            item['price'] = prices[0][1]
            trailing = clean_line(line[prices[0][0].end():])
            # Texto curto apos o preco pode ser uma unidade/observacao de tabela; nao inventamos descricao.
            if trailing:
                item['confidence'] = 'medium'
                warnings.append(f'Linha {line_number}: confira o texto depois do preco em "{name}".')
        else:
            item['confidence'] = 'low'
            warnings.append(f'Linha {line_number}: mais de um preco em "{name}". Escolha o tamanho/valor correto antes de publicar.')

        items.append(item)
        if len(items) >= max_items:
            warnings.append(f'O limite deste lote e {max_items} produtos. Divida o cardapio em mais de uma importacao.')
            break

    if ignored_price_lines:
        warnings.insert(0, f'{ignored_price_lines} linha(s) com preco nao viraram produto porque o nome nao estava claro.')
    if not items:
        warnings.append('Nenhum produto com nome e preco foi reconhecido. Confira se o PDF tem texto selecionavel.')
    else:
        high = sum(i['confidence'] == 'high' for i in items)
        ambiguous = sum(bool(i['ambiguous']) for i in items)
        warnings.append(f'Rascunho criado com {len(items)} item(ns): {high} com leitura clara e {ambiguous} com mais de um preco.')
        warnings.append('Nada e publicado automaticamente. Confira nomes, categorias, tamanhos e precos antes de salvar o cardapio.')

    return {
        'items': items,
        'categories': categories,
        'warnings': warnings,
        'summary': {
            'items': len(items),
            'highConfidence': sum(i['confidence'] == 'high' for i in items),
            'mediumConfidence': sum(i['confidence'] == 'medium' for i in items),
            'lowConfidence': sum(i['confidence'] == 'low' for i in items),
            'ambiguous': sum(bool(i['ambiguous']) for i in items),
        },
    }
