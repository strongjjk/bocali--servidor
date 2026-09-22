# Bocali 1.0 RC2 - caminho para o teste real do Cantinho do Pastel

Objetivo: chegar ao teste de quarta-feira com um pedido passando por cliente -> pagamento -> servidor -> estabelecimento -> prazo -> Epson TM-T20X.

> Este RC e para homologacao supervisionada. Nao desligue o GloriaFood nem dependa do Bocali para atendimento comercial ate concluir todo o checklist de homologacao.

## 1. Publicar o servidor em HTTPS

Use o pacote `Bocali-servidor-v10-rc2.zip` em um repositorio GitHub privado dedicado ao servidor.

No Railway:

1. Crie um projeto a partir do repositorio do servidor.
2. Adicione um volume persistente e monte em `/data`.
3. Gere um dominio publico HTTPS para o servico.
4. Nas variaveis do servico, configure:

```text
BOCALI_MODE=production
BOCALI_PUBLIC_ORIGIN=https://SEU-DOMINIO-RAILWAY
BOCALI_DATA_DIR=/data
BOCALI_SECRET_KEY=<gere localmente um segredo de 48 bytes>
BOCALI_PILOT_CODE=
BOCALI_SETUP_TOKEN=
BOCALI_DEMO_ADDRESSES=0
BOCALI_ENABLE_PDF=1
BOCALI_MP_ENVIRONMENT=test
BOCALI_MP_ACCESS_TOKEN=<credencial de teste do Mercado Pago>
BOCALI_MP_PUBLIC_KEY=<opcional neste RC>
BOCALI_MP_WEBHOOK_SECRET=<segredo do Webhook Mercado Pago>
GEOAPIFY_API_KEY=<opcional para retirada; necessario para endereco real de entrega>
```

Gere `BOCALI_SECRET_KEY` no seu computador com:

```text
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Cole o resultado apenas no Railway. Nao envie Access Token, segredo de Webhook nem `BOCALI_SECRET_KEY` por chat e nao grave esses valores no GitHub.

Depois do deploy, abra:

```text
https://SEU-DOMINIO/healthz
```

O esperado e:

```json
{"ok": true}
```

## 2. Configurar Mercado Pago primeiro em ambiente de teste

A arquitetura deste RC usa uma unica conta Mercado Pago do servidor, suficiente para o piloto do Cantinho. Ela ainda nao e a arquitetura multiestabelecimento final.

1. No painel de desenvolvedores do Mercado Pago, use as credenciais de teste da integracao do Cantinho.
2. Coloque o Access Token de teste nas variaveis do Railway.
3. Cadastre o Webhook de pagamentos apontando para:

```text
https://SEU-DOMINIO/api/webhooks/mercadopago
```

4. Coloque o segredo gerado para esse Webhook em `BOCALI_MP_WEBHOOK_SECRET`.
5. Mantenha `BOCALI_MP_ENVIRONMENT=test`.
6. Reinicie/reimplante o servico se a plataforma nao fizer isso automaticamente.

No Bocali:
- Pix e criado pelo servidor e aparece como QR Code/copia-e-cola.
- Cartao abre o Checkout Pro do Mercado Pago em Android Custom Tab, fora do WebView do Bocali.
- O pedido online somente entra na fila da loja depois da confirmacao do provedor.
- Cancelamento de pedido pago, nas etapas suportadas, solicita estorno integral antes de concluir o cancelamento.

## 3. Gerar o APK ligado ao servidor HTTPS

No repositorio usado para gerar APK:

1. Envie `Bocali-Android-v10.zip` para a raiz.
2. Envie `Bocali-gerar-apk-v10.yml` para `.github/workflows/`.
3. Va em Actions -> `Bocali - gerar APK v1.0 RC2` -> Run workflow.
4. No campo `server_url`, coloque exatamente o dominio HTTPS do Railway, sem barra final, por exemplo:

```text
https://bocali-production.up.railway.app
```

5. Quando ficar verde, baixe o artifact `Bocali-v10-rc2`.
6. Instale `Bocali-v10-rc2.apk` no celular do balcao.

Este APK e de homologacao e usa assinatura Android de debug. A assinatura definitiva/Play Store fica para depois do piloto.

## 4. Cadastrar o Cantinho como primeira loja real

No servidor de producao vazio:

1. Abra Criar conta.
2. Escolha `Tenho uma loja`.
3. Cadastre o responsavel e o nome `Cantinho do Pastel`.
4. A loja nasce pausada.
5. Importe o cardapio. Se o PDF visual confundir nome e preco, use a caixa de texto, que ja funcionou bem no teste.
6. Revise cada preco e adicional antes de publicar.
7. Configure horario, pedido minimo e retirada.
8. Para o primeiro teste, retirada e o caminho mais simples. So libere entrega depois de conferir as areas/taxas reais e a geocodificacao.
9. Abra a loja somente quando o cardapio estiver conferido.

## 5. Conectar a Epson no APK oficial

No painel do estabelecimento -> Configuracoes -> `Configurar Epson neste aparelho`:

1. Use o mesmo IP da TM-T20X que ja funcionou no teste fisico.
2. Nao altere o IP da impressora nem o roteador.
3. Consulte o estado da impressora.
4. Faca primeiro uma impressao de teste fora do fluxo comercial.

O transporte celular -> LAN -> Epson ja foi validado fisicamente. Ainda falta validar a comanda proveniente de um pedido real do servidor v1.0.

## 6. Roteiro de homologacao antes de dinheiro real

Execute nesta ordem:

1. Cliente novo -> login -> Cantinho -> retirada -> dinheiro -> pedido chega no balcao -> aceitar -> prazo -> imprimir -> finalizar.
2. Repetir com Pix de teste: confirmar que pedido nao aparece para a loja antes da aprovacao e aparece depois do Webhook.
3. Repetir com cartao de teste: Custom Tab abre, pagamento retorna ao Bocali e Webhook libera o pedido.
4. Cancelar um pagamento de teste e confirmar estorno/estado do pedido.
5. Simular internet interrompida durante impressao e confirmar que o Bocali nao reimprime automaticamente sem conferencia.
6. Reimprimir manualmente e conferir que a via fica identificada como reimpressao.
7. Conferir itens, adicionais, observacoes, total, taxa, forma de pagamento e prazo no papel.

## 7. Virar a chave para o teste real supervisionado

Somente depois dos testes acima:

1. Troque as credenciais do Mercado Pago para producao no Railway.
2. Mude `BOCALI_MP_ENVIRONMENT=production`.
3. Confirme novamente o Webhook de producao.
4. Faca uma transacao real de valor pequeno entre pessoas da equipe.
5. Confira recebimento na conta Mercado Pago, pedido no Bocali, prazo e Epson.
6. Mantenha o GloriaFood disponivel como contingencia durante o primeiro dia.

## Limitacoes conhecidas deste RC

- Leitura de PDFs muito graficos ainda pode confundir nomes/precos; use revisao ou texto colado.
- O alerta de pedido novo funciona enquanto a interface do Bocali esta ativa; notificacao push com o app totalmente fechado ainda e uma etapa posterior.
- Pagamentos estao ligados a uma unica conta Mercado Pago do servidor. Antes de oferecer pagamentos para varias lojas, implementar conexao individual/marketplace por estabelecimento.
- Recuperacao de senha por e-mail e assinatura definitiva para Play Store ainda nao fazem parte deste RC.
