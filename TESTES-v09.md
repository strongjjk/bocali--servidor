# Bocali 0.9 — verificacoes executadas

## Servidor e regras

- 52 testes da base 0.4 passaram.
- 46 testes da base 0.5 passaram.
- 13 testes de identidade/persistencia passaram com a versao atualizada para 0.9.
- 6 testes do importador 0.8 passaram.
- 3 testes novos de integracao 0.9 passaram.
- testes JavaScript de dominio, fluxo de pedido e entrega passaram.
- 2 testes do payload de impressao nativa passaram.

Os novos testes verificam: modo LAN apenas com IPv4 privado, rejeicao de IPv4 publico e repeticao segura da confirmacao de uma tentativa de impressao depois de perda de resposta.

## Android

- 40 testes nomeados do nucleo de impressao passaram.
- 10 testes do payload Android passaram.
- `ui.js` e `bridge.js` passaram na verificacao sintatica do Node.

A compilacao Android 0.9 ainda depende do GitHub Actions/Android SDK. O ambiente desta entrega nao executou o APK 0.9 em um aparelho fisico.

## Validacao fisica anterior

O modulo Android 0.2 foi instalado pelo usuario e a impressao direta celular -> rede local -> Epson TM-T20X foi confirmada fisicamente no Cantinho do Pastel. Isso valida o caminho de rede/impressora usado como base, mas nao substitui o teste do APK 0.9 integrado ao servidor.

## Fluxo de navegador

O fluxo legado de navegador foi reexecutado parcialmente e passou por cadastro, pedido, aceite, prazo, comanda, confirmacao de impressao simulada, reconexao e responsividade antes de atingir o limite de tempo do ambiente na etapa final de capturas. Nenhuma falha funcional havia aparecido ate esse ponto.

## Limites

Nao foram executados nesta entrega: pagamento real, notificacao push, OCR de imagem, geocodificacao externa real, carga de producao, publicacao em loja de aplicativos ou teste do APK 0.9 na Epson.
