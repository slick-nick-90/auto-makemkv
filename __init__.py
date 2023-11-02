from argparse import BooleanOptionalAction

parser_args = [
    {
        "args": ["--extras", "-e"],
        "kwargs": {"help": "file path to extras tsv", "type": str, "required": True},
    },
    {
        "args": ["--minlength", "-l"],
        "kwargs": {"help": "min length of video in sec", "type": int, "default": 40},
    },
    {
        "args": ["--disc", "-d"],
        "kwargs": {"help": "disc number", "type": int, "default": 0},
    },
    {
        "args": ["--output", "-o"],
        "kwargs": {
            "help": "output directory, defaults to extras directory",
            "type": str,
            "default": "",
        },
    },
    {
        "args": ["--scan", "-s"],
        "kwargs": {
            "action": BooleanOptionalAction,
            "help": "force rescan of disc",
            "type": bool,
            "default": False,
        },
    },
    {
        "args": ["--progress_bar"],
        "kwargs": {
            "action": BooleanOptionalAction,
            "help": "show progress bar",
            "type": bool,
            "default": True,
        },
    },
    {
        "args": ["--extra_warn"],
        "kwargs": {
            "action": BooleanOptionalAction,
            "help": "show extra warning",
            "type": bool,
            "default": True,
        },
    },
]
