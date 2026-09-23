# Bocali 1.0 RC6 PRO

Atualização visual e operacional voltada ao uso real do Bocali.

## O que mudou

- nova navegação separando com clareza a área do cliente e a área da loja;
- cardápio mais visual e responsivo;
- logo e foto de capa por estabelecimento;
- foto individual por produto;
- upload de imagens JPG, PNG e WebP com redução no cliente quando necessário;
- imagens armazenadas no volume persistente do servidor e servidas por URL interna aleatória;
- troca/remoção de imagens sem manter a imagem antiga associada;
- checkout simplificado: CEP opcional, rua/número/bairro obrigatórios, taxa calculada pelo bairro e complemento recolhido em opção secundária;
- navegação móvel com quatro ações principais e alvos de toque maiores;
- painel do lojista mais objetivo, com checklist de prontidão;
- aceitador continua com alerta sonoro/vibração, aceite com prazo, fila e impressão Epson;
- mantém dinheiro, troco e cartão na maquininha; Pix/cartão online ficam condicionados à conexão do Mercado Pago.

## Upload de imagens

O backend aceita somente JPG, PNG e WebP, confere assinatura básica do arquivo, impõe limite de tamanho, exige conta autorizada da loja e grava com nome aleatório. A interface Android RC6 também foi atualizada para permitir escolher imagens além de PDFs.

## Validação depois do deploy

Abra `/api/health`. A resposta deve conter:

- `version: "1.0-rc6"`
- `media: true`
- `ui: "professional"`
- `legacyFixtures: 0`

Depois faça login como lojista e teste `Minha loja` -> logo/capa e `Cardápio` -> editar produto -> foto.
