# Configurando o Memora no Claude Code

## 1. Gere seu token MCP

Acesse: `{MEMORA_URL}/dashboard/settings` → seção "Claude Code (MCP)"

Clique em **"Gerar token MCP"** e copie o token gerado.

> **Importante:** O token só é exibido uma vez. Guarde-o em local seguro.

## 2. Configure o Claude Code

Adicione ao arquivo `~/.claude/mcp_servers.json`:

```json
{
  "memora": {
    "url": "{MEMORA_URL}/mcp",
    "headers": {
      "Authorization": "Bearer {SEU_TOKEN}"
    }
  }
}
```

Substitua:
- `{MEMORA_URL}` pela URL do seu Memora (ex: `http://localhost:8000`)
- `{SEU_TOKEN}` pelo token gerado no passo anterior

## 3. Verifique a conexão

No Claude Code, rode:

```
/mcp status
```

Você deve ver: `memora: connected`

## Tools disponíveis

O Memora expõe 5 tools para o Claude Code:

| Tool | Descrição |
|------|-----------|
| `search_similar_code` | Busca código similar no sistema para evitar duplicação |
| `get_business_rules` | Busca regras de negócio relevantes |
| `get_team_patterns` | Busca padrões e convenções do time |
| `get_architecture_decisions` | Busca decisões arquiteturais anteriores |
| `get_environment_context` | Lista variáveis de ambiente necessárias |

## Como usar

O Claude Code consulta o Memora automaticamente quando detecta que você está implementando algo. Você também pode pedir explicitamente:

**Exemplos:**

```
"Implemente um endpoint de desconto seguindo os padrões do nosso sistema"

"Crie uma função de validação de CPF — verifique se já temos algo similar"

"Qual é a regra de comissão antes de eu implementar esse cálculo?"
```

## Revogar token

Para revogar o token ativo, acesse as configurações do dashboard e clique em **"Revogar"**.
Após revogar, gere um novo token e atualize o `mcp_servers.json`.
