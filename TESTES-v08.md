# Bocali 0.8 — verificação executada

## Resultado

- 52 testes Python da base v0.4: aprovados.
- 46 testes Python da base v0.5: aprovados.
- 13 testes de identidade/compatibilidade: aprovados após atualização da versão esperada para 0.8.
- 6 testes novos do importador PDF: aprovados.
- 18 testes JavaScript de domínio/cardápio/carrinho: aprovados.
- 20 testes de aceite e impressão lógica: aprovados.
- 25 testes de zonas e taxas de entrega: aprovados.
- fluxo de interface controlado da versão anterior: todas as verificações executadas passaram, sem erros JavaScript inesperados.
- servidor local iniciado em porta de teste: `/api/health` informou `version=0.8` e `pdf=true`.
- criação de responsável + sessão + envio real do `cardapio-exemplo.pdf` à rota `/api/import-pdf`: HTTP 200 e três produtos corretos reconhecidos.

## Casos específicos do PDF

O novo parser foi testado com:

- categorias explícitas;
- categoria genérica em caixa alta;
- preços brasileiros;
- linha com dois preços, preservada como ambígua;
- PDF exemplo com texto selecionável;
- PDF vazio/sem texto, bloqueado sem inventar produtos;
- arquivo que não é PDF, rejeitado.

## Limitações dos testes

Não houve nesta etapa:

- uso de um PDF real do Cantinho do Pastel;
- OCR de imagem;
- hospedagem pública;
- pagamento real;
- impressão física na Epson;
- teste nativo em Windows do arquivo `.bat`;
- teste de carga ou auditoria externa de segurança.

Esses pontos continuam antes do uso comercial.
