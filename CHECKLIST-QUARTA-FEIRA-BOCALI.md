# Checklist de quarta-feira - Cantinho do Pastel x Bocali 1.0 RC2

Marque cada item antes de abrir qualquer pedido real.

## Servidor
- [ ] Dominio HTTPS abre normalmente.
- [ ] `/healthz` responde `ok`.
- [ ] Volume `/data` esta conectado e um redeploy nao apaga conta/cardapio.
- [ ] Segredos existem somente nas variaveis da hospedagem.

## Cantinho
- [ ] Conta de estabelecimento criada.
- [ ] Nome, descricao, pedido minimo e horarios conferidos.
- [ ] Cardapio real revisado item por item.
- [ ] Adicionais e precos conferidos.
- [ ] Retirada funciona.
- [ ] Se entrega for usada, endereco, areas e taxas foram testados com enderecos reais.

## Android / Epson
- [ ] APK v1.0 RC2 instalado no celular do balcao.
- [ ] APK abre direto no servidor HTTPS correto.
- [ ] IP da Epson e o mesmo que ja foi validado fisicamente.
- [ ] Consulta de estado da TM-T20X funciona.
- [ ] Pedido de teste do servidor imprime corretamente.
- [ ] Reimpressao exige acao manual e sai identificada.

## Pedidos
- [ ] Pedido em dinheiro chega ao painel.
- [ ] Alerta sonoro funciona com o app aberto.
- [ ] Aceite exige prazo.
- [ ] Cliente ve prazo/status atualizado.
- [ ] Retirada/entrega segue as etapas corretas.

## Mercado Pago - teste
- [ ] Pix de teste e gerado com valor correto.
- [ ] Pedido Pix nao chega a loja antes da aprovacao.
- [ ] Webhook libera pedido Pix aprovado.
- [ ] Cartao abre em Custom Tab, nao dentro do WebView.
- [ ] Webhook libera pedido de cartao aprovado.
- [ ] Cancelamento/estorno de teste foi conferido.

## Primeiro teste real supervisionado
- [ ] Credenciais mudadas para producao somente apos sandbox passar.
- [ ] `BOCALI_MP_ENVIRONMENT=production` confirmado.
- [ ] Um pedido real de valor pequeno foi acompanhado do inicio ao fim.
- [ ] Recebimento apareceu na conta correta do Mercado Pago.
- [ ] Comanda da Epson bate com pedido/totais/pagamento.
- [ ] GloriaFood continua disponivel como contingencia.
