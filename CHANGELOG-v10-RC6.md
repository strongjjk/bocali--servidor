# Changelog — Bocali 1.0 RC6 PRO

## Experiência do cliente
- card da loja com capa, logo, status, prazo e pedido mínimo;
- card de produto com foto real e fallback visual;
- página da loja com identidade visual e busca/categorias simplificadas;
- modal do produto com imagem maior;
- checkout reorganizado para reduzir digitação e deixar a taxa do bairro explícita;
- campos obrigatórios/opcionais mais claros;
- navegação móvel simplificada.

## Experiência do estabelecimento
- perfil da loja com logo, capa, nome, categoria, prazo, descrição e mínimo;
- checklist de prontidão da loja;
- editor de cardápio com miniaturas e upload/remoção de foto;
- navegação separada: pedidos do balcão, cardápio, importação, entregas e perfil;
- aceitador preserva fila em tempo real, prazo, som/vibração e Epson.

## Backend e segurança
- campos `logoUrl`, `coverUrl` e `imageUrl` persistidos no catálogo;
- endpoint autenticado de mídia;
- formatos limitados a JPG/PNG/WebP;
- assinatura do arquivo validada antes de gravar;
- nomes aleatórios de 128 bits;
- limites de upload;
- mídia gravada no `BOCALI_DATA_DIR`, portanto no volume Railway em produção;
- remoção e substituição limpam o arquivo anterior quando possível;
- URLs externas de imagem não são aceitas pelo catálogo.

## Android
- build 30 / `1.0.0-rc6`;
- seletor nativo aceita PDF e imagens solicitadas pela página;
- mantém ponte Epson, Custom Tabs do Mercado Pago e as proteções de origem do WebView.
