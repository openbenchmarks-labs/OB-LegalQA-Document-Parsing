"""Every tool setup, loaded from tools/<tool>.yaml and joined to its adapter."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from .adapters import (
    astra,
    datalab,
    extend,
    fable,
    llamaparse,
    mistral,
    pulse,
    reducto,
    specstream,
    unstructured,
)

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"

# One line per tools/<tool>.yaml. An adapter turns one PDF into markdown.
ADAPTERS: dict[str, Callable[..., tuple[str, dict]]] = {
    "astra": astra.parse,
    "datalab": datalab.parse,
    "extend": extend.parse,
    "fable": fable.parse,
    "llamaparse": llamaparse.parse,
    "mistral": mistral.parse,
    "pulse": pulse.parse,
    "reducto": reducto.parse,
    "specstream": specstream.parse,
    "unstructured": unstructured.parse,
}


@dataclass(frozen=True)
class Tool:
    """One setup of one tool.

    `settings` is every value that changes what the tool returns; the parse
    cache is keyed on it, so a parse made under other settings is never reused.
    `bypasses_vendor_cache` marks tools that keep their own result cache and
    must be told to skip it on a repeat parse. `tracked_changes_opt_in` records
    whether the setup had to ask for tracked changes, so a reader can tell a
    parser that found the strike from one that was handed it.
    """

    name: str
    vendor: str
    variant: str
    parse: Callable[..., tuple[str, dict]]
    settings: dict
    pricing: dict
    tracked_changes_opt_in: bool
    bypasses_vendor_cache: bool


def load(tools_dir: Path = TOOLS_DIR) -> dict[str, Tool]:
    tools: dict[str, Tool] = {}
    for path in sorted(tools_dir.glob("*.yaml")):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, setup in config["setups"].items():
            tools[name] = Tool(
                name=name, vendor=setup["vendor"], variant=setup["variant"],
                parse=ADAPTERS[config["tool"]], settings=setup["settings"],
                pricing=setup["pricing"],
                tracked_changes_opt_in=setup["tracked_changes_opt_in"],
                bypasses_vendor_cache=setup["bypasses_vendor_cache"])
    return tools


TOOLS = load()
