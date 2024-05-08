## Elia

A powerful terminal user interface for interacting with large language models.

Chat with Claude 3, ChatGPT, and local models like Llama 3, Phi 3, Mistral and Gemma.

<img width="1439" alt="elia-stacked-screenshot" src="https://github.com/darrenburns/elia/assets/5740731/8fb15936-abeb-4464-b34d-f6cb001913e4">

Your conversations are stored locally in a SQLite database.

Conversations with local models are done via `ollama` and never leave your machine.

### Installation

Install Elia with [pipx](https://github.com/pypa/pipx):

```bash
pipx install elia-chat
```

Depending on the model you wish to use, you may need to set one or more environment variables (e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc).

### Quickstart

Launch Elia from the command line:

```bash
elia
```

Launch directly a new chat from the command line:

```bash
elia "What is the Zen of Python?"
```

### Running local models

1. Install [`ollama`](https://github.com/ollama/ollama).
2. Pull the model you require, e.g. `ollama pull llama3`.
3. Run the local ollama server: `ollama serve`.
4. Add the model to the config file (see below).

### Configuration

The location of the configuration file is noted at the bottom of
the options window (`ctrl+o`).

The example file below shows the available options, as well as examples of how to add new models.

```toml
# the model that is selected by default on launch
default_model = "gpt-3.5-turbo"
# the system prompt on launch
system_prompt = "You are a helpful assistant who talks like a pirate."

# example of adding local llama3 support
# only the `name` field is required here.
[[models]]
name = "ollama/llama3"

# example of a model running on a local server, e.g. LocalAI
[[models]]
name = "some-model"
api_base = "http://localhost:8080/v1/chat/completions"
api_key = "api-key-if-required"

# example of add a groq model, showing some other fields
[[models]]
name = "groq/llama2-70b-4096"
display_name = "Llama 2 70B"  # appears in UI
provider = "Groq"  # appears in UI
temperature = 1.0  # high temp = high variation in output
max_retries = 0  # number of retries on failed request

### Import from ChatGPT

Export your conversations to a JSON file using the ChatGPT UI, then import them using the `import` command.

```bash
elia import 'path/to/conversations.json'
```

### Wiping the database

```bash
elia reset
```

### Uninstalling

```bash
pipx uninstall elia-chat
```
