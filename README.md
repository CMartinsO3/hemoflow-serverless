# Rota Vital — Guia de transporte serverless

Atividade individual 1 · Serverless — Infraestrutura de Software · ADS · CESAR School · 2026.2

**Aluno:** Caio Martins Oliveira · **Grupo:** HemoFlow · **Entrega:** 24/11

## 1. O que é

Uma função serverless (AWS Lambda, Python 3.12) que recebe por HTTP uma requisição de bolsa do Rota Vital
(`POST /guias`) e devolve a **guia de transporte**. A função serve de laboratório para o ciclo de vida do ambiente
de execução (cold start e reaproveitamento), a ausência de estado garantido e o limite de tempo.

## 2. Caminho escolhido

**Caminho A — AWS SAM CLI local** (sem conta AWS e sem cartão). O Lambda e o API Gateway rodam em containers Docker na
minha máquina. O evento gerado pelo SAM tem o mesmo formato que o Lambda recebe do API Gateway na nuvem.

- Máquina: Ubuntu 26.04.1 LTS · Docker 29.1.3 · SAM CLI 1.172.1 · Python 3.14.4 (o build usa `--use-container`, com Python 3.12 dentro do container)

## 3. Estrutura do repositório

```
template.yaml            # API POST /guias, Timeout 3 s em Globals, 128 MB, python3.12
hello_world/app.py       # handler (guia de transporte)
events/pedido.json       # evento gerado por "sam local generate-event"
tests/unit/              # testes unitários do handler (rodam sem Docker)
evidencias/              # prints dos comandos e das saídas
```

## 4. Como rodar (reproduzível)

Pré-requisitos: Docker em execução, AWS SAM CLI e Python 3.12.
Se o seu Python não for o 3.12, use `sam build --use-container` (o build roda num container com Python 3.12).

```bash
# 0. (opcional) testes unitários, sem Docker
python3 -m unittest discover -s tests/unit -v

# 1. Evento no formato do API Gateway
mkdir -p events
sam local generate-event apigateway aws-proxy --method POST --path guias \
    --body '{"requisicaoId":"R-001","hospital":"H-Recife","bolsas":["O-NEG-0142"]}' > events/pedido.json

# 2. Build e invocação direta com evento (rodar duas vezes e anotar o tempo)
sam build            # ou: sam build --use-container
time sam local invoke -e events/pedido.json
time sam local invoke -e events/pedido.json

# 3. Gatilho HTTP
sam local start-api                       # terminal 1
curl -X POST http://127.0.0.1:3000/guias -H "Content-Type: application/json" \
     -d '{"requisicaoId":"R-002","hospital":"H-Caruaru"}'        # terminal 2, 3 vezes
# parar o servidor e repetir com contêineres mantidos
sam local start-api --warm-containers LAZY

# 4. Limite de tempo (Timeout = 3 s no template; a função dorme 5 s)
curl -X POST http://127.0.0.1:3000/guias -H "Content-Type: application/json" \
     -d '{"requisicaoId":"R-003","demorar":true}'
# depois: Timeout 3 -> 10 em template.yaml, sam build, e repetir
```

### Achado: o evento do SAM vem com o `body` em base64

Com o SAM CLI 1.172.1, o `generate-event` gera `"isBase64Encoded": true` e o `body` codificado em base64.
O handler do enunciado faz `json.loads(event["body"])` direto e falha com `JSONDecodeError`.
Acrescentei no handler o tratamento de `isBase64Encoded` (3 linhas) e um teste que usa o `events/pedido.json` gerado.
O restante do código segue o enunciado. Confirmado na minha máquina (SAM 1.172.1): `grep isBase64Encoded events/pedido.json` mostrou `"isBase64Encoded": true`.

## 5. Experimentos e respostas

### 5.1 Invocação com evento (Passo 3)

| Execução | Tempo (`time`) | `invocacaoNesteAmbiente` | Observação |
|---|---|---|---|
| 1ª | 24,379 s total (`Duration` 80,03 ms) | 1 | O SAM montou a imagem local do Lambda ("Building image...") |
| 2ª | 10,987 s total (`Duration` 107,22 ms) | 1 | Imagem pronta ("Local image is up-to-date"); container novo (outro `SAM_CONTAINER_ID`) |

### 5.2 HTTP com e sem `--warm-containers` (Passo 4)

| Modo | Chamada 1 | Chamada 2 | Chamada 3 |
|---|---|---|---|
| `sam local start-api` | 1 | 1 | 1 |
| `--warm-containers LAZY` | 1 | 2 | 3 |

No modo `--warm-containers LAZY`, o `Duration` no log foi 99,80 ms na 1ª chamada (container novo) e 1,46 ms e 1,89 ms nas
duas seguintes ("Lambda function 'GuiaTransporteFunction' is already running").

### 5.3 Limite de tempo (Passo 5)

| Timeout | Resultado de `demorar: true` |
|---|---|
| 3 s | `HTTP/1.1 502 BAD GATEWAY`, `{"message":"Internal server error"}`. Log do SAM: `Function 'GuiaTransporteFunction' timed out after 3 seconds`, `Duration: 3000.00 ms`, `Invalid lambda response received: Lambda response must be valid json`. `time` do curl: 5,160 s |
| 10 s | `HTTP/1.1 201 CREATED`, guia `G-R-003`. `time` do curl: 10,818 s (a função dorme 5 s) |

### Pergunta 1 — Por que a primeira invocação demorou mais que a segunda? O que acontece na Init?

Na primeira vez, o ambiente da função ainda não existe. A plataforma precisa preparar tudo (fase Init) e depois executar o código (Invoke). Isso é o cold start. No `sam local invoke`, a 1ª execução levou 24 s e a 2ª, 11 s, mas isso foi por causa do Docker, que montou a imagem na primeira vez. O cold start apareceu no `--warm-containers`: a 1ª chamada levou 99,80 ms e as seguintes, 1,46 ms e 1,89 ms, porque o ambiente já estava pronto.

### Pergunta 2 — O que `invocacaoNesteAmbiente` mostrou com e sem `--warm-containers`? O que isso diz sobre estado em variável global?

Sem `--warm-container`, o contador deu 1, 1, 1, porque cada chamada usou um ambiente novo. Com `--warm-containers`, deu 1, 2, 3, porque o mesmo ambiente foi reaproveitado. Então uma variável global só guarda valor enquanto o ambiente continuar vivo, e a plataforma não garante isso. O que precisa ser guardado deve ir para um banco de dados.

### Pergunta 3 — O que aconteceu com `demorar = true`? Qual o tempo máximo de uma execução no Lambda e o que fazer com trabalho mais longo?

Com `demorar = true`, a função precisa de 5 s, mas o Timeout era de 3 s. O SAM interrompeu a execução (`timed out after 3 seconds`) e recebi o erro 502. Com Timeout de 10 s, funcionou e voltou 201. O tempo máximo de uma função no Lambda é de 15 minutos. Se o trabalho for mais longo, dá para dividir em etapas, usar uma fila ou usar um container.

### Pergunta 4 — Custo de 1 milhão de execuções com 128 MB e 100 ms (us-east-1)

Fórmula da aula: custo = requisições × US$ 0,20/milhão + requisições × memória (GB) × duração (s) × US$ 0,0000166667.

- Requisições: 1.000.000 × US$ 0,20 / 1.000.000 = **US$ 0,20**
- Memória: 128 MB = 128 / 1024 = 0,125 GB
- GB-s por execução: 0,125 GB × 0,1 s = 0,0125 GB-s
- GB-s em 1 milhão de execuções: 0,0125 × 1.000.000 = 12.500 GB-s
- Computação: 12.500 × US$ 0,0000166667 = **US$ 0,2083**
- **Total ≈ US$ 0,41** por milhão de execuções (≈ US$ 0,0000004 por execução)

Conferência da fórmula com o exemplo da aula (512 MB, 200 ms): 0,20 + 1.000.000 × 0,5 × 0,2 × 0,0000166667 = US$ 1,87,
igual ao slide. Sem free tier, sem API Gateway, logs e transferência de dados (como na aula).

### Pergunta 5 — Onde uma função assim faria sentido no HemoFlow, e onde não?

Faz sentido gerar a guia de transporte: é uma tarefa curta, que não depende de memória e acontece de vez em quando. Também serve para avisar quando há um alerta de temperatura. Não faz sentido para a alocação de bolsas, porque ela usa a tabela hash e a fila FEFO na memória, além do banco de dados, e o ambiente da função pode ser descartado a qualquer momento.

## 6. Evidências e vídeo

- Prints em `evidencias/` (lista de nomes em `evidencias/LEIA-ME.md`).
- Vídeo (até 3 min):

## 7. Uso de IA (PO-CESAR-021)

- **Ferramenta:** Claude (Anthropic).
- **Finalidade:** montar a estrutura do repositório, `template.yaml`, testes unitários do handler, rascunho do README e
  conferência da conta de custo.
- **Como validei:** rodei `python3 -m unittest`; rodei `sam build`,
  `sam local invoke` e `sam local start-api` na minha máquina;
