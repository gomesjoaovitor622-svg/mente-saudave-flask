# Evidencias de teste da API

`rest-client.html` executa chamadas reais contra a API e mostra, para cada
requisicao, o metodo, a URL, o corpo enviado, o status HTTP, o tempo de resposta
e o JSON retornado.

## Como usar

1. Suba a API (`python run.py`).
2. Abra o arquivo no navegador, informando a URL da API:

```text
rest-client.html?api=http://localhost:5000
```

Se a API estiver em outra porta ou host, basta alterar o parametro `api`.

Tambem e possivel servir a pasta com um servidor estatico:

```bash
python -m http.server 5056 --directory docs/testes
```

E acessar `http://localhost:5056/rest-client.html?api=http://localhost:5000`.

> A API responde com cabecalhos CORS liberados, permitindo o consumo a partir
> desta pagina, do painel web e de aplicativos moveis.

As capturas geradas com essa pagina estao em `docs/img/testes-api.png` e sao
usadas na documentacao em PDF.
