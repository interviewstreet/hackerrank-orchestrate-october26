"""Advisory language-model layer: plain-language explanations and human-review flags.

The deterministic engine decides every status and step. This layer only *comments* on a finished result, and anything it
says that is not backed by the engine's own output is discarded. It never touches output.csv.
"""
