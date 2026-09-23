# Testes — Bocali 1.0 RC6 PRO

Executados no ambiente de desenvolvimento:

- 15 testes Python da camada oficial/mídia/entrega: OK;
- 20 testes do fluxo de aceite, ETA e impressão: OK;
- 2 testes do adaptador de comanda nativa: OK;
- 45 testes nomeados do núcleo Android/Epson: OK;
- 10 testes de payload Android: OK;
- 9 verificações estáticas de segurança/thread do WebView: OK;
- 7 verificações do novo seletor PDF/imagens: OK;
- sintaxe Python (`backend.py`, `pilot_app.py`): OK;
- sintaxe JavaScript (`professional.js`): OK;
- teste HTTP real local: registro de lojista -> upload de logo -> leitura da imagem: OK;
- teste HTTP real local: substituição de logo -> arquivo antigo deixa de ser servido: OK.

Limitações do ambiente de QA:
- a compilação Android completa depende do GitHub Actions/Android SDK;
- a verificação visual automatizada em Chromium local foi bloqueada pela política administrativa do ambiente, então o pacote precisa de conferência visual no navegador/Android após o deploy;
- testes antigos de mapa por polígono não representam mais a arquitetura atual de entrega por bairro e não devem ser usados como critério da RC6.
