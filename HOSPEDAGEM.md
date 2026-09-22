# Hospedagem Bocali 1.0 RC2 - Railway

O pacote inclui `Dockerfile`, `railway.json`, healthcheck `/healthz` e suporte a volume persistente.

Fluxo recomendado: criar um projeto Railway a partir de um repositorio privado, anexar volume em `/data`, gerar dominio publico HTTPS, cadastrar as variaveis de ambiente indicadas em `.env.example`, implantar e conferir `/healthz`.

Nao grave segredos em arquivos versionados. Configure Access Token/segredo de Webhook do Mercado Pago e `BOCALI_SECRET_KEY` diretamente nas variaveis do servico. Comece com `BOCALI_MP_ENVIRONMENT=test`.

Depois do deploy, configure no Mercado Pago a URL de Webhook:

`https://SEU-DOMINIO/api/webhooks/mercadopago`

Use o dominio HTTPS resultante para compilar o APK oficial. O APK deve apontar para a mesma origem que `BOCALI_PUBLIC_ORIGIN`.
