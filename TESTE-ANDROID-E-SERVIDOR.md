# Bocali 0.9 - teste do aplicativo Android com o servidor

Este modo serve apenas para um teste acompanhado na mesma rede privada. Ele usa HTTP local e nao deve receber dados reais, pagamentos ou senhas reutilizadas.

1. No computador, execute `INICIAR-ANDROID-NA-REDE.bat`.
2. O terminal mostrara um endereco parecido com `http://192.168.1.20:8000`.
3. Deixe a janela aberta e conecte o celular ao mesmo Wi-Fi/rede.
4. No APK Bocali 0.9, em **Servidor Bocali**, salve exatamente esse endereco e toque em **Abrir Bocali**.
5. Entre no piloto, crie/acesse uma conta de lojista e teste a importacao de um PDF.
6. Para pedidos, use uma segunda conta de cliente. Ao aceitar no APK, a impressao direta usa a Epson salva no aparelho.

Se o Windows Firewall perguntar, libere Python apenas para **redes privadas**. Nao abra a porta do roteador para a internet.

Para uso fora da rede interna, hospede o servidor com HTTPS em vez de usar este modo.
