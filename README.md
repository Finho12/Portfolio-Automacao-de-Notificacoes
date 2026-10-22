# Automação Web de Notificações — Selenium + Python

Projeto de portfólio que demonstra automação de um fluxo web administrativo usando Python, Selenium WebDriver e configuração por variáveis de ambiente.

> **Importante:** este repositório é uma demonstração técnica. Não contém credenciais, dados reais ou URLs de ambientes internos. Os seletores e etapas precisam ser adaptados e validados em uma aplicação de teste autorizada antes do uso.

## Objetivo

Automatizar etapas repetitivas de um fluxo de notificações:

1. Autenticação no sistema configurado.
2. Abertura da área de notificações.
3. Seleção de município e pesquisa por IDs.
4. Localização da ação de aprovação na linha correspondente.
5. Tratamento de modal de confirmação, abas e iframes.
6. Seleção do tipo de ocorrência e envio do cadastro de ordem de serviço.

## Tecnologias

- Python 3.10+
- Selenium WebDriver
- python-dotenv
- pytest (testes unitários)

## Estrutura

```text
portfolio-automacao-notificacoes/
├── aprovar_notificacao.py
├── sample_ids.txt
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── tests/
    └── test_load_ids.py
```

## Configuração

1. Instale Python 3.10 ou superior.
2. Crie e ative um ambiente virtual.
3. Instale as dependências:

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Copie `.env.example` para `.env` e informe apenas dados de um ambiente de teste autorizado.
5. Edite `sample_ids.txt` com IDs fictícios/de teste, um por linha.
6. Confira se o Chrome está instalado. O Selenium Manager tenta resolver automaticamente o ChromeDriver compatível.

## Execução segura

Por padrão, o script faz login, pesquisa os IDs e **não aprova notificações nem cadastra ordens de serviço**:

```bash
python aprovar_notificacao.py
```

Para habilitar ações que alteram dados, use somente em ambiente de teste autorizado:

```bash
python aprovar_notificacao.py --execute
```

O modo de execução exige confirmação digitando `EXECUTAR`. Revise o ambiente, os IDs e o tipo de ocorrência antes de confirmar.

## Testes

```bash
pytest -v
```

Os testes unitários verificam a leitura e a deduplicação de IDs sem acessar o sistema web.

## Pontos de qualidade demonstrados

- Configuração externa ao código e separação de segredos.
- Esperas explícitas com `WebDriverWait`.
- Funções com responsabilidades definidas.
- Tratamento de exceções comuns do Selenium.
- Logs para acompanhamento do fluxo.
- Modo seguro por padrão para evitar alterações acidentais.
- Testes unitários de funções independentes da interface.

## Limitações conhecidas

- Os seletores HTML são específicos da aplicação-alvo e podem mudar.
- A autenticação e o comportamento de abas/iframes precisam ser validados no ambiente autorizado.
- O fluxo não substitui testes de integração ou validações de negócio.
- Antes de uso real, recomenda-se adicionar evidências, relatório estruturado por ID, captura de tela em falhas e testes de regressão dos seletores.
