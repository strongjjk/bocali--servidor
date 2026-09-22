# Atualizar de Pede 0.5 para Bocali 0.6

Esta troca de marca não exige migração do esquema do banco.

1. Pare o servidor do piloto e faça backup do banco com a ferramenta `backup.py`. Guarde também `.env`, volumes, segredos e configurações de hospedagem em local privado.
2. Extraia a versão Bocali em outra pasta. Não apague a pasta antiga nem crie um banco vazio por cima do existente.
3. Preserve os valores de `.env`. Se `PEDE_DATA_DIR` apontar para um caminho absoluto existente, mantenha-o. Caso seja necessário mover o diretório, faça a restauração para um destino novo conforme `BACKUP-E-RESTAURACAO.md` e ajuste o caminho com o servidor parado.
4. Mantenha o nome interno `pede.sqlite3`. Ele continua sendo o banco do Bocali. Cookies, cabeçalho interno, assinatura do código do piloto, formato de backup, globais JavaScript e chaves de armazenamento também foram preservados para evitar perda de compatibilidade.
5. Reinicie e confira o nome Bocali, suas contas, loja, favoritos, produtos e pedidos. Use o mesmo endereço do piloto para preservar a origem do navegador. A mudança de endereço pode exigir novo login.
6. Em caso de retorno, pare a versão nova e volte ao código anterior, apontando ao mesmo banco. A troca de marca não alterou o esquema. Não restaure um backup antigo sem considerar pedidos novos gravados depois dele.

Nenhum banco ou segredo do usuário foi modificado nesta entrega: foram usados bancos temporários nos testes.
