# Backup e restauracao do piloto

O script e uma ferramenta do responsavel tecnico, nao um recurso disponivel a todos os lojistas. As copias podem conter dados pessoais de todas as lojas. Mantenha-as privadas e protegidas. Nao as envie junto do codigo ou para este chat.

## Criar uma copia consistente

Exemplo para o ambiente local:

```sh
python backup.py create --db data/pede.sqlite3 --out backups/ensaio-001.sqlite3
python backup.py verify backups/ensaio-001.sqlite3
```

Na hospedagem, trocar a origem por `/data/pede.sqlite3` e escolher um nome novo no destino. O script cria o arquivo e um manifesto `.json` com data, contagens e hash SHA-256. Ele verifica a integridade e as referencias do banco. O nome nao pode existir anteriormente.

O hash detecta alteracoes acidentais em relacao ao manifesto. Ele nao criptografa o arquivo nem prova sua autenticidade se ambos forem modificados por um atacante. Copias e manifesto precisam de protecao adequada.

A API de backup do SQLite e usada para obter uma copia consistente enquanto a aplicacao pode estar escrevendo. Ha um limite de tempo na etapa de copia; se a operacao falhar, o arquivo incompleto e removido.

## Ensaiar a restauracao sem substituir o banco ativo

```sh
python backup.py restore backups/ensaio-001.sqlite3 --to restaurado/pede.sqlite3
```

O destino precisa ser um arquivo novo. A restauracao preserva pedidos e contas, mas apaga sessoes, enderecos temporarios e cotacoes pendentes da copia restaurada. As pessoas precisam entrar novamente. O script nao muda o banco em uso.

Para uma recuperacao operacional, parar o servico, preservar uma copia do estado anterior e preparar um novo diretorio de dados com o arquivo restaurado. Apontar `PEDE_DATA_DIR` para esse diretorio e validar tudo antes de liberar o piloto. Nao trocar arquivos enquanto o servidor estiver escrevendo nem carregar arquivos `-wal`/`-shm` de outro banco.

## O que ainda nao esta pronto

O script nao agenda backups, nao envia arquivos a armazenamento externo, nao aplica criptografia e nao testa os backups automaticamente em outro servidor. Uma copia no mesmo volume nao protege contra a perda desse volume.

Para o piloto hospedado, definir uma rotina de copia externa privada, retencao, permissao de acesso e ensaios de restauracao. Os backups nativos do provedor devem ser configurados e verificados separadamente. Nao indicar que o sistema esta protegido apenas porque o script existe.

```text
Referencia: SQLite Online Backup API
https://www.sqlite.org/backup.html
```
