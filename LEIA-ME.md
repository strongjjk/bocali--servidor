# Bocali 1.0 RC2 - servidor oficial do piloto

Este pacote transforma o nucleo que foi validado localmente em um servidor preparado para hospedagem HTTPS e para o primeiro estabelecimento real do Bocali.

## Fluxos presentes

- cadastro/login de cliente;
- cadastro/login de estabelecimento, criando uma loja propria e inicialmente pausada;
- cardapio, categorias, adicionais, disponibilidade e importacao de PDF/texto;
- carrinho, retirada ou entrega, calculo de total e snapshot do pedido no servidor;
- fila do estabelecimento, aceite, prazo, preparo, retirada/entrega, cancelamento e historico;
- ponte de impressao estruturada para o app Android/Epson;
- Pix Mercado Pago gerado pelo servidor;
- cartao via Checkout Pro aberto pelo Android em Custom Tab;
- Webhook assinado para atualizar o estado do pagamento;
- estorno total automatico ao cancelar um pedido online aprovado nas etapas suportadas.

## Producao

Em `BOCALI_MODE=production`, o banco inicia sem o restaurante de demonstracao. A primeira conta criada como `Tenho uma loja` cria o primeiro estabelecimento real. Para o teste de quarta-feira, cadastre o Cantinho do Pastel por esse fluxo normal.

O servidor publicado exige `BOCALI_PUBLIC_ORIGIN` HTTPS e `BOCALI_SECRET_KEY`. Use um volume persistente em `/data` para o SQLite. O container inicia como root apenas para preparar permissoes do volume e depois derruba privilegios antes de executar o servidor.

## Pagamentos

Comece com `BOCALI_MP_ENVIRONMENT=test` e credenciais de teste do Mercado Pago. Nunca coloque Access Token, segredo do Webhook ou `BOCALI_SECRET_KEY` em GitHub publico, APK ou conversa.

Neste RC, a conta Mercado Pago configurada no servidor e unica. Isso serve para o piloto do Cantinho do Pastel. O modelo multiestabelecimento com recebimento individual por loja ainda precisa de integracao de marketplace/OAuth antes de abrir pagamentos para outras lojas.

## Cardapio por PDF

PDF com texto selecionavel funciona melhor. Cardapios muito graficos, com fotos e precos soltos, podem exigir revisao manual. O caminho de colar o texto do cardapio continua disponivel e e recomendado para o piloto se a leitura automatica ficar ambigua.

## Antes de pedidos reais

Use o roteiro `BOCALI-V10-PASSO-A-PASSO.md` do pacote completo. Nao troque o GloriaFood nem dependa do Bocali comercialmente antes de concluir pagamento em sandbox, Webhook, estorno, pedido ponta a ponta, Epson e conferencia do cardapio/taxas reais.
