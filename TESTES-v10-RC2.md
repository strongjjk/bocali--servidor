# Testes Bocali 1.0 RC2

Data da preparacao: 2026-09-21.

## Suite oficial v1.0

`python -m unittest tests.v10.test_official -v`: 8/8 testes passaram.

Cobertura: banco de producao sem loja hardcoded; cadastro de estabelecimento; pagamento online aguardando provedor; preservacao do metodo original do pedido; estorno verificado; total/idempotencia Mercado Pago; Checkout Pro com total calculado no servidor e reaproveitamento da preferencia; assinatura do Webhook.

## Dominio, entrega e impressao web

- `domain.test.cjs`: 18 testes passaram.
- `delivery.test.cjs`: 25 testes passaram.
- `order-flow.test.cjs`: 20 testes passaram.
- `native-print.test.cjs`: 2 testes passaram.
- `node --check connected.js` e `native-print.js`: passaram.

## Android

- verificacoes estaticas da ponte/thread/Custom Tab/deep link: passaram;
- nucleo Java de impressao: 43 testes nomeados passaram;
- payloads JavaScript: 10/10 passaram;
- interface simulada em navegador: 22 verificacoes passaram.

Foi adicionado teste especifico para pagamento com saldo Mercado Pago (`account_money`) nao ser impresso falsamente como cartao.

## Evidencia fisica ja obtida

Antes deste RC, o transporte Android -> rede local -> Epson TM-T20X foi testado fisicamente pelo responsavel no Cantinho do Pastel e imprimiu corretamente.

## O que ainda precisa de validacao externa

- compilar o RC2 no GitHub Actions com Android SDK real;
- instalar o RC2 no aparelho;
- deploy HTTPS com volume persistente;
- Mercado Pago em sandbox, Webhook e estorno reais do ambiente de teste;
- pedido do servidor RC2 chegando a Epson fisica;
- taxas/endereco/cardapio/horarios reais;
- depois, uma transacao pequena de producao supervisionada.

## Testes historicos antigos

A suite historica completa contem assercoes de versoes 0.4-0.9 que esperam propositalmente `paymentStatus=simulated`, versao 0.9, banco `pede.sqlite3` e manifest/piloto antigos. Essas assercoes nao sao criterios do RC2 e por isso nao sao usadas como gate do build v1.0. Os testes de regras de dominio/entrega/ordens continuam sendo executados separadamente e passaram.
