# Bocali 0.9

- Integra o painel conectado ao aplicativo Android que ja imprimiu fisicamente na Epson TM-T20X.
- O APK passa a abrir a interface completa do Bocali a partir de um servidor configurado.
- Upload de PDF no WebView Android habilitado por seletor de documentos.
- Ao aceitar um pedido, a comanda pode ser enviada pela ponte Android sem a janela de impressao do navegador.
- O servidor e o aparelho usam IDs de tentativa para reduzir reenvios duplicados.
- Confirmacao de papel tornou-se idempotente quando repetida com o mesmo resultado.
- Novo modo LAN privado para teste acompanhado entre computador e celular na mesma rede.
- Pagamentos continuam simulados e as comandas integradas permanecem marcadas como TESTE ate a etapa comercial.
