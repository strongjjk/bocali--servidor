# Bocali 0.6 - testes e limites

## Escopo desta entrega

Atualização da marca Pede para Bocali a partir do pacote 0.5. Nome nas telas, login, painel, comandas, manifest, títulos e instruções; ajustes de espaçamento responsivo e texto informativo do piloto. Uma demonstração HTML independente permite explorar o visual sem servidor. Não houve ativação comercial ou migração do esquema do banco.

## Resultados executados sobre esta entrega

| Grupo | Resultado | Evidência |
|---|---:|---|
| Regressão Python do banco e HTTP 0.4 | 52 passaram | tests/v06/results/python-v04.txt |
| Regressão Python do piloto protegido e backup 0.5 | 46 passaram | tests/v06/results/python-v05.txt |
| Identidade Bocali e continuidade do banco | 13 passaram | tests/v06/results/brand.txt |
| Carrinho e pedidos JavaScript | 18 passaram | tests/v06/results/domain.txt |
| Aceite e registro de impressão JavaScript | 20 passaram | tests/v06/results/order-flow.txt |
| Áreas e taxas JavaScript | 25 passaram | tests/v06/results/delivery.txt |
| Verificações de interface em Chromium controlado | 40 passaram | tests/v06/results/browser.txt |

São **111 testes Python**, **63 testes JavaScript** e **40 verificações de interface**. Também foram feitas verificações de sintaxe dos arquivos Python e JavaScript. As contagens não significam certificação para produção.

## Fluxos conferidos

Entrada no piloto, configuração de responsável, cadastro de cliente, total de R$ 25,90 no pedido fictício com adicional e entrega B, recuperação do mesmo pedido após simular perda de resposta, recebimento em sessão separada do lojista, aceite de 35 a 55 minutos, atualização para o cliente, confirmação manual de impressão simulada e reconexão sem novo pedido. Identidade Bocali conferida no título, marca visível e comanda. Conta e pedidos preservados ao reiniciar com o mesmo banco. Ausência de rolagem horizontal nas telas inicial e de mapa em 320, 390, 768 e 1440 px.

## Método e limitações da interface

Uma tentativa de navegar normalmente para o servidor local retornou `net::ERR_BLOCKED_BY_ADMINISTRATOR` neste ambiente. Não foi alterada a política do navegador.

As telas do código do projeto foram montadas com `set_content`, e chamadas HTTP da interface foram encaminhadas a um servidor WSGI local real usando sessões de teste independentes. Isso permite conferir a lógica e o visual, mas **não valida carregamento normal por URL, cookies nativos do navegador, HTTPS, redirecionamentos completos ou instalação em um celular real**. A função de impressão foi substituída por um simulador no teste. Capturas correspondem a esse ambiente controlado, não a um site publicado.

A demonstração HTML foi executada separadamente e permite adicionar itens à sacola. Ela não implementa as contas ou o servidor compartilhado. No ambiente de captura, o armazenamento local pode não estar disponível; o aplicativo mostra essa limitação.

## Não realizado

Hospedagem, Docker/Waitress em produção, teste em Windows, geocodificação real, pagamento real, impressora física, envio externo de mensagens, auditoria de segurança, teste de carga e instalação em lojas de aplicativos. Não houve verificação/registro de marca nem compra de domínio. O importador PDF continua desativado por padrão no piloto e sua dependência antiga não foi atualizada ou auditada nesta troca de marca.

## Reprodução

```sh
python -m unittest discover -s tests/v04 -p 'test_*.py' -v
python -m unittest discover -s tests/v05 -p 'test_*.py' -v
python -m unittest discover -s tests/v06 -p 'test_*.py' -v
node tests/domain.test.cjs
node tests/order-flow.test.cjs
node tests/delivery.test.cjs
python tests/v06/browser_flow.py
```

Os testes de interface exigem as dependências de desenvolvimento e Chromium, e usam somente dados descartáveis. Nenhuma base de clientes do Cantinho foi acessada ou modificada.
