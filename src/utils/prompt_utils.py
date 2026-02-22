import os, toml


def load_prompts():
    prompts_file = os.path.join(os.path.dirname(__file__), "../config/prompts.toml")
    with open(prompts_file, "r") as f:
        data = toml.load(f)
    return data
