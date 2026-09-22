#!/usr/bin/env python3
"""Le PDF em memoria e devolve texto + rascunho estruturado para revisao."""
from __future__ import annotations
import io, json, sys
from menu_parser import parse_menu_text

MAX_FILE = 10 * 1024 * 1024
MAX_PAGES = 25
MAX_TEXT = 200_000


def extract_pdf(data: bytes) -> dict:
    from pypdf import PdfReader
    if len(data) > MAX_FILE:
        raise ValueError('O PDF excede 10 MB. Reduza o arquivo ou divida o cardapio.')
    if not data.lstrip().startswith(b'%PDF-'):
        raise ValueError('O arquivo enviado nao tem um cabecalho PDF valido.')
    reader = PdfReader(io.BytesIO(data), strict=False)
    if reader.is_encrypted:
        raise ValueError('PDF protegido por senha. Envie uma copia sem protecao.')
    if len(reader.pages) > MAX_PAGES:
        raise ValueError('Limite de 25 paginas por arquivo. Divida o cardapio.')

    pages, warnings = [], []
    total = 0
    empty_pages = []
    for number, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text(extraction_mode='layout') or ''
        except TypeError:
            try:
                text = page.extract_text() or ''
            except Exception:
                text = ''
        except Exception:
            text = ''
        if not text.strip():
            empty_pages.append(number)
        total += len(text)
        if total > MAX_TEXT:
            raise ValueError('O texto do PDF e muito grande. Divida o cardapio em arquivos menores.')
        pages.append(text)

    text = '\n'.join(pages)
    if len(text.strip()) < 8:
        raise ValueError('Esse PDF parece ser formado por imagens e nao tem texto selecionavel. Nesta versao, use um PDF com texto ou cole o conteudo do cardapio. A leitura de imagem sera adicionada em uma etapa separada.')
    if empty_pages:
        warnings.append('Pagina(s) sem texto extraivel: ' + ', '.join(map(str, empty_pages)) + '. Confira essas paginas manualmente.')

    parsed = parse_menu_text(text)
    warnings.extend(parsed['warnings'])
    return {
        'text': text,
        'pages': len(pages),
        'items': parsed['items'],
        'categories': parsed['categories'],
        'summary': parsed['summary'],
        'warnings': warnings,
        'parserVersion': '0.8',
    }


if __name__ == '__main__':
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (600 * 1024 * 1024, 600 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CPU, (18, 18))
        except (ImportError, ValueError, OSError):
            pass
        result = extract_pdf(sys.stdin.buffer.read(MAX_FILE + 1))
    except ValueError as e:
        result = {'error': str(e)}
    except ImportError:
        result = {'error': 'Instale as dependencias com pip install -r requirements.txt.'}
    except Exception:
        result = {'error': 'PDF invalido ou nao suportado. Tente outro arquivo ou cole o texto do cardapio.'}
    print(json.dumps(result, ensure_ascii=False))
