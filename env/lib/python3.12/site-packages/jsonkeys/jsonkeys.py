from __future__ import annotations
import click
from pathlib import Path
from typing import Union, Any, Iterator
from tqdm import tqdm

# Support these three main type of tree-like files
import pickle
import json
import yaml


def print_tree(
    data: Union[dict, list, Any], bfs: bool = False, indent: int = 0
) -> Iterator[str]:
    # NOTE that this could be optimized
    if type(data) == dict:
        kvs = sorted(data.items())
        if bfs:
            yield (" " * 4 * indent) + "{\n"
            yield "\n".join([(" " * 4 * (indent + 1)) + f"{k}" for k, _ in kvs]) + "\n"
            yield (" " * 4 * indent) + "}\n"
        for k, v in kvs:
            # In BFS mode in structs keep it simple by not double-printing the keys when there is not nesting for those keys
            if type(v) == dict or type(v) == list or not bfs:
                yield (" " * 4 * indent) + f"{k}\n"
                yield from print_tree(v, bfs=bfs, indent=indent + 1)
    elif type(data) == list and len(data) > 0:
        yield (" " * 4 * indent) + f"0\n"
        yield from print_tree(data[0], bfs=bfs, indent=indent + 1)


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    "output_file",
    type=click.Path(exists=False),
    required=False,
    help="Output file to write to.",
)
@click.option(
    "--bfs",
    "-b",
    is_flag=True,
    required=False,
    help="Group the keys at this node in the beginning, so that the order looks a little like a cross of BFS and DFS.",
)
def main(input_file: str, output_file: str, bfs: bool):
    """Visualize a file that is JSON-like in a simple way, by printing the keys in a tree structure. Any time there is a list,
    only print out the 0th element as a key "0". If the values recursively viewed are not dictionaries or lists print nothing.

    Always indent by 4's. Allow a BFS-like search or DFS-like search so you can group the keys for this current node.
    """
    input = Path(input_file)
    output = Path(output_file) if output_file else None
    if not input.exists():
        raise FileNotFoundError(f"Input file {input} does not exist.")
    if input.suffix == ".json":
        with open(input, "r") as f:
            data = json.load(f)
    elif input.suffix == ".pkl" or input.suffix == ".pickle":
        with open(input, "rb") as f:
            data = pickle.load(f)
    elif input.suffix == ".yaml" or input.suffix == ".yml":
        with open(input, "r") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
    else:
        raise ValueError(f"File {input} is not a JSON, YAML, or pickle file.")
    if output is not None:
        # TODO(Adriano) support some sort of tqdm
        fileSize = input.stat().st_size
        estIters = fileSize // 1000  # 1000 bytes per yield? idk...
        tr: str = ""
        for y in tqdm(print_tree(data, bfs=bfs, indent=0), count=estIters):
            tr += y
        with open(output, "w") as f:
            f.write(tr)
    else:
        for y in print_tree(data, bfs=bfs, indent=0):
            click.echo(
                y, nl=False
            )  # This includes newlines in it for interop. with files


if __name__ == "__main__":
    main()
