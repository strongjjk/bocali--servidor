# Testes Bocali 1.0 RC3

Validações executadas antes do pacote:

- 8 testes oficiais v1.0: OK.
- 4 testes RC3 de entrega/pagamento: OK.
- 3 testes integrados v0.9: OK.
- 25 testes do motor de entrega legado: OK.
- 18 testes de domínio/carrinho: OK.
- 20 testes de aceite/impressão: OK.
- 2 testes de payload de impressão no servidor: OK.
- Android: 45 testes do núcleo de impressão: OK.
- Android: 10 testes de payload: OK.
- Android: 9 verificações de thread/WebView + segredo da ponte nativa: OK.

Cobertura RC3 específica:
- bairro e apelido aplicam a taxa correta sem mapa;
- taxa zero por bairro é aceita;
- bairro desconhecido é bloqueado;
- cidade divergente é bloqueada;
- dinheiro com troco é validado no total final;
- cartão na maquininha entra como pedido offline;
- comanda Android imprime troco e cartão na maquininha.

Ainda exige teste físico final do APK RC3 na Epson TM-T20X. A comunicação Android -> Epson já foi validada fisicamente em versão anterior do mesmo núcleo de impressão.
