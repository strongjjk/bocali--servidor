# Bocali 1.0 RC3 - atualização operacional

Objetivo: liberar o Cantinho do Pastel para um piloto operacional com entrega simples por bairro e pagamentos presenciais.

## Entrega

O mapa deixa de ser obrigatório. O estabelecimento cadastra bairro, apelidos e taxa. Exemplo:

- Araretama | apelido: Araretema | R$ 5,00
- Centro | sem apelido | R$ 0,00

No checkout, o cliente pode informar o CEP para autopreencher rua/bairro/cidade/UF ou preencher manualmente. O servidor usa o bairro para escolher a taxa e também confere cidade e UF configuradas pela loja.

CEP incompleto não bloqueia o pedido quando rua, número, bairro, cidade e UF estão preenchidos manualmente.

## Pagamento presencial

- Dinheiro na entrega ou retirada.
- Dinheiro pode ser marcado como "Preciso de troco" e registrar "troco para R$ X".
- Cartão na entrega ou retirada usa a maquininha do estabelecimento.
- Pix e cartão online continuam opcionais e só são liberados quando o Mercado Pago estiver configurado.

## Impressão

O pedido estruturado enviado ao Android inclui a forma de pagamento, necessidade de troco e valor para troco. A comanda de balcão distingue dinheiro, cartão na maquininha e pagamentos online.

## Segurança do piloto

A taxa é sempre recalculada no servidor. O celular não escolhe o valor final da entrega. Bairros fora da tabela são bloqueados. O servidor rejeita cidade/UF diferentes das configuradas pela loja.
