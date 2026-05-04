from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


class CloudFormationLoader(yaml.SafeLoader):
    """SafeLoader that accepts CloudFormation intrinsic function tags (!Ref, !Sub, ...)."""


def _construct_cfn_tag(loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    raise yaml.constructor.ConstructorError(
        None, None, f"unsupported YAML node for CloudFormation tag: {node!r}", node.start_mark
    )


CloudFormationLoader.add_multi_constructor("!", _construct_cfn_tag)


def load_template(path: Path) -> object:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=CloudFormationLoader)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a CloudFormation template for CI sanity checks.")
    parser.add_argument(
        "path",
        nargs="?",
        default="infrastructure/templates/api-stack.yaml",
        help="Path to the template YAML (default: %(default)s)",
    )
    args = parser.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 1
    load_template(path)
    print("YAML_OK", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
