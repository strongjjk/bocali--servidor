# Testes Bocali 1.0 RC4

Executados antes do empacotamento:
- 12 testes Python v1.0: OK
- limpeza das lojas legadas `forno` e `acai`: OK
- produção ignora código antigo de piloto: OK
- cadastro de lojista continua criando loja própria: OK
- entrega por bairro/dinheiro/troco/cartão na maquininha: OK
- 25 testes de entrega JavaScript: OK
- 18 testes de domínio/carrinho: OK
- 20 testes de aceite/impressão: OK
- testes de payload de comanda nativa: OK
- smoke test Playwright mobile do `#/aceitador`: OK, sem erro JavaScript e sem overflow horizontal.

Limite: impressão física Epson já foi validada em versão anterior pelo usuário; este pacote não repetiu teste físico no equipamento.
