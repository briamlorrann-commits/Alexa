# Assistente Claude para Alexa

Uma skill personalizada da Alexa que conecta o seu Echo ao Claude. Você fala, a Alexa
transcreve, uma função AWS Lambda envia o texto para a API do Claude e a resposta volta
como fala.

```
Você ──voz──▶ Echo ──▶ Alexa (reconhecimento de fala)
                            │  ChatIntent { query: "como funciona um buraco negro" }
                            ▼
                     AWS Lambda (lambda/lambda_function.py)
                            │  "Deixa eu pensar." (resposta progressiva)
                            ▼
                     API do Claude (lambda/claude_client.py)
                            │  resposta curta, sem markdown
                            ▼
Você ◀──voz── Echo ◀── Alexa (texto para fala)
```

## Como usar

- "Alexa, abrir assistente claude" → depois: "pergunte qual a capital da Austrália"
- "Alexa, pergunte ao assistente claude por que o céu é azul"
- Continue perguntando na mesma sessão: o Claude lembra das últimas 6 trocas.
- "Parar" encerra.

As frases precisam começar com uma expressão como *pergunte*, *me diga*, *me explique*,
*o que é*, *como*, *por que*… (a lista completa está em
`skill-package/interactionModels/custom/pt-BR.json`). É uma exigência do slot
`AMAZON.SearchQuery`, que captura texto livre.

## Configuração

Você precisa de: uma chave da API da Anthropic
([console.anthropic.com](https://console.anthropic.com)), uma conta de desenvolvedor
Amazon ([developer.amazon.com/alexa](https://developer.amazon.com/alexa)) com o mesmo
e-mail do seu Echo, e uma conta AWS (opção B).

### Opção A — Skill hospedada pela Alexa (mais simples, sem conta AWS)

1. No [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask), clique
   em **Create Skill**: nome *Assistente Claude*, idioma **Portuguese (BR)**, modelo
   **Custom**, hospedagem **Alexa-hosted (Python)**.
2. Em **Build → Interaction Model → JSON Editor**, cole o conteúdo de
   `skill-package/interactionModels/custom/pt-BR.json`, salve e clique em **Build Model**.
3. Na aba **Code**, substitua `lambda_function.py` e `requirements.txt` pelos deste
   repositório e crie `claude_client.py`.
4. Defina a chave da API: o editor hospedado não tem variáveis de ambiente, então
   coloque no topo de `claude_client.py`
   `os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-...")`.
   Não faça commit desse arquivo com a chave.
5. Clique em **Deploy**, vá em **Test**, ative o modo *Development* e digite
   "abrir assistente claude".

### Opção B — AWS Lambda própria (recomendada; a chave fica em variável de ambiente)

1. Empacote a função:
   ```bash
   cd lambda
   pip install -r requirements.txt -t package/ \
       --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12
   cp *.py package/ && (cd package && zip -r ../function.zip .)
   ```
2. No console da AWS (região **us-east-1**), crie uma função Lambda Python 3.12 chamada
   `assistente-claude`, envie `function.zip` e mantenha o handler
   `lambda_function.lambda_handler`.
3. Em **Configuration**: timeout de **10 s**, memória de 256 MB e a variável de
   ambiente `ANTHROPIC_API_KEY`.
4. Adicione o gatilho **Alexa Skills Kit** com o *Skill ID* da sua skill.
5. Coloque o ARN da função em `skill-package/skill.json` (ou em **Build → Endpoint** no
   console) e faça o build do modelo de interação como no passo 2 da opção A.

Se você usa a [ASK CLI](https://developer.amazon.com/docs/smapi/quick-start-alexa-skills-kit-command-line-interface.html),
`ask deploy` publica `skill-package/` diretamente.

### Usando no seu Echo

Enquanto a skill estiver em desenvolvimento, ela já fica disponível em todos os
dispositivos Alexa ligados à sua conta de desenvolvedor. Não é preciso publicá-la.

## Ajustes (variáveis de ambiente)

| Variável | Padrão | Para que serve |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Chave da API (obrigatória) |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Modelo usado |
| `CLAUDE_EFFORT` | `low` | Profundidade de raciocínio (`low`, `medium`, `high`…). Valores mais altos ficam mais lentos |
| `CLAUDE_TIMEOUT_SECONDS` | `6.5` | Limite da chamada à API (a Alexa desiste por volta de 8 s) |
| `CLAUDE_MAX_TOKENS` | `1024` | Limite de tamanho da resposta |
| `CLAUDE_MAX_TURNS` | `6` | Quantas trocas a sessão lembra |

## Limitações

- **Tempo**: a Alexa espera no máximo ~8 segundos por resposta. Por isso a chamada usa
  esforço `low`, um timeout de 6,5 s, nenhuma nova tentativa automática e uma resposta
  progressiva ("Deixa eu pensar."). Se uma pergunta complexa estourar o tempo, a skill
  avisa. Se isso acontecer com frequência, experimente `CLAUDE_MODEL=claude-haiku-5-5`.
- **Memória só dentro da sessão**: o histórico vive nos atributos de sessão da Alexa e é
  apagado quando a skill fecha. Guarda só o texto de cada turno para caber no limite de
  tamanho desses atributos.
- **Recusas**: as requisições usam o fallback do lado do servidor (`fallbacks: "default"`).
  Se o pedido ainda assim for recusado, a skill responde com uma mensagem curta.
- **Custo**: cada pergunta é uma chamada paga na API da Anthropic.

## Testes

```bash
pip install -r lambda/requirements.txt pytest
pytest tests
```

---

## Também neste repositório

- [`lg-tv-hub/`](lg-tv-hub/README.md): **Stream Hub**, uma tela inicial para TV LG (webOS) que abre
  Netflix, Prime Video, Disney+, Paramount+, HBO Max, Crunchyroll e Apple TV com o controle.
