# Elia

A powerful terminal app for interacting with LLMs such as ChatGPT and Claude 3.

## Quickstart

Install Elia with [pipx](https://github.com/pypa/pipx), set your `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` environment variable,
and start the app:

```bash
pipx install git+https://github.com/darrenburns/elia
export OPENAI_API_KEY="xxxxxxxxxxxxxx"
elia
```

## Configuration

The location of the configuration file is noted at the bottom of
the options window (ctrl+o).

The example file below shows the available options, as well as examples of how to add new OpenAI and Anthropic models.

```toml
default_model = "gpt-3.5-turbo"
system_prompt = "You are a helpful assistant named Elia."

[openai]
api_key = "xxxxxx"
organization = "xxxxxx"

[[openai.extra_models]]
name = "gpt-5"
provider = "openai"
product = "ChatGPT"
description = "Very smart."
context_window = 100000
temperature = 0.8

[anthropic]
api_key = "xxxxxx"

[[anthropic.extra_models]]
name = "claude-4"
provider = "anthropic"
product = "Claude"
description = "Very smart."
context_window = 200000
```

You can also override the system prompt using the `ELIA_SYSTEM_PROMPT` environment variable.

```bash
export ELIA_SYSTEM_PROMPT="You are a helpful assistant who talks like a pirate."
```

## Starting a chat directly from the CLI

You can launch immediately into a chat:

```bash
elia "What is the Zen of Python?"
```

## Wiping the database

You can delete the database:

```bash
elia reset
```

## OpenAI organisation

If you're a member of multiple organizations on the OpenAI platform, you may also need to set the `OPENAI_ORGANIZATION` environment variable to your organization ID, found on the OpenAI dashboard for your organization.

```bash
export OPENAI_ORGANIZATION="org-klj8ashdkJHKJas"
```

You can also set the OpenAI organization via the config file,
as described earlier.

## Additional notes

- Elia only trims conversations to fit within the context window when you're working with an OpenAI model. It does not tokenise messages with Anthropic models.
