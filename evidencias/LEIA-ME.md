# Evidências

Coloque aqui os prints (terminal inteiro, com o comando e a saída visíveis). Nomes sugeridos:

| Arquivo | O que mostra |
|---|---|
| `01-versoes.png` | `sam --version`, `docker --version`, `python3 --version` |
| `02-sam-init-ou-estrutura.png` | projeto criado / `tree` do repositório |
| `03-generate-event.png` | `sam local generate-event ...` e o `events/pedido.json` |
| `04-build.png` | `sam build` com sucesso |
| `05-invoke-1.png` e `06-invoke-2.png` | as duas invocações, com `time` |
| `07-start-api-3-chamadas.png` | três `curl` com `invocacaoNesteAmbiente` |
| `08-warm-containers.png` | três `curl` com `--warm-containers LAZY` |
| `09-timeout-3s.png` | erro de `demorar:true` com Timeout 3 |
| `10-timeout-10s.png` | `demorar:true` com Timeout 10 (sucesso) |
| `11-testes-unitarios.png` | `python3 -m unittest discover -s tests/unit -v` |
