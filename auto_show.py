from auto_makemkv import get_disc_info
from auto_makemkv import parser as auto_makemkv_parser
from auto_makemkv import mkv
from auto_makemkv import main as auto_makemkv
from copy import deepcopy
from makemkv import ProgressParser
from ast import literal_eval

import csv
import sys
import os

parser = deepcopy(auto_makemkv_parser)
parser.add_argument("--show_name", type=str, help="name of show", required=True)
parser.add_argument("--show_season", type=int, help="show disc season", required=True)
parser.add_argument("--show_disc", type=int, help="show disc number", required=True)
parser.add_argument(
    "--show_1ep_chapter_count",
    type=str,
    help="specify chapter count for single episodes tracks",
    default="[5,6]"
)
parser.add_argument(
    "--show_2ep_chapter_count",
    type=str,
    help="specify chapter count for multi-episode tracks",
    default="[7,8,9]"
)
parser.add_argument(
    "--show_comment_start", type=str, help="specify start of comment", default="C"
)


def main(argv=sys.argv[1:]):
    args = parser.parse_args(["-e", "tmp", *argv])

    show_name = args.show_name
    s = args.show_season
    d = args.show_disc

    extras_base = f"{show_name}/s{s:02d}_d{d:02d}"

    if not d > 1:
        ep = 1
        os.makedirs(f"{show_name}/s{s:02d}", exist_ok=True)
    else:
        with open(f"{show_name}/s{s:02d}_d{d-1:02d}.tsv", "r") as f:
            tsv_file = csv.reader(f, delimiter="\t")
            for line in tsv_file:
                ep = int(line[0][5:7])
            ep = ep + 1

    disc_info = get_disc_info(
        extras_base=extras_base, ProgressParser=ProgressParser, args=args
    )
    tracks = []
    lengths = []
    eps = []
    for i, title in enumerate(disc_info["titles"]):
        title
        # todo: move to arguments options
        if title["chapter_count"] in literal_eval(
            args.show_1ep_chapter_count
        ) and title["comment"].startswith(args.show_comment_start):
            tracks.append(i)
            lengths.append(title["length"])
            eps.append(ep)
            ep += 1
        # todo: move to arguments options
        if title["chapter_count"] in literal_eval(
            args.show_2ep_chapter_count
        ) and title["comment"].startswith(args.show_comment_start):
            tracks.append(i)
            lengths.append(title["length"])
            eps.append([ep, ep + 1])
            ep += 2

    if len(lengths) != len(set(lengths)):
        print("warning: some of the episodes have the same length!")

    extra = f"{extras_base}.tsv"
    with open(extra, "w") as f:
        for i, track in enumerate(tracks):
            if type(eps[i]) == int:
                ep_name = f"e{eps[i]:02d}"
            elif len(eps[i]) == 2:
                ep_name = f"e{eps[i][0]:02d}-{eps[i][1]:02d}"
            f.write(f"s{s:02d}/{ep_name}\t{lengths[i]}\n")

    auto_makemkv(
        [
            "-e",
            extra,
            "-o",
            show_name,
            "--no-extra_warn",
        ]
    )


if __name__ == "__main__":
    main()
