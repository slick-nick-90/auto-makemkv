from auto_makemkv import get_disc_info
from auto_makemkv import parser as auto_makemkv_parser
from auto_makemkv import mkv
from auto_makemkv import main as auto_makemkv
from makemkv import ProgressParser
import csv
import sys
parser = auto_makemkv_parser
parser.add_argument("--show_name", type=str, help="name of show", required=True)
parser.add_argument("--show_season", type=int, help="show disc season", required=True)
parser.add_argument("--show_disc", type=int, help="show disc number", required=True)
parser.add_argument("--show_chapter_count", type=int, help="specify chapter count", default=5)
parser.add_argument("--show_comment_start", type=str, help="specify start of comment", default="C")

def main(argv=sys.argv[1:]):
    args = parser.parse_args(argv)

    show_name = args.show_name
    s = args.show_season
    d = args.show_disc

    extras_base=f"{show_name}/s{s:02d}_d{d:02d}"

    if not d>1:
        ep = 1
    else:
        with open(f"{show_name}/s{s:02d}_d{d-1:02d}.tsv",'r') as f:
            tsv_file = csv.reader(f, delimiter="\t")
            for line in tsv_file:
                ep = int(line[0][5:7])
            ep = ep + 1

    disc_info = get_disc_info(extras_base=extras_base,ProgressParser=ProgressParser,args=args)
    print(disc_info["disc"]["name"])
    tracks = []
    lengths = []
    for i, title in enumerate(disc_info["titles"]):
        title
        if title["chapter_count"] == args.show_chapter_count and title["comment"].startswith(args.show_comment_start): #todo: move to arguments options
            tracks.append(i)
            lengths.append(title["length"])

    eps = range(ep,ep+len(tracks))
    extra = f"{extras_base}.tsv"
    with open(extra,"w") as f:
        for i, track in enumerate(tracks):
            f.write(f"s{s:02d}/e{eps[i]:02d}\t{lengths[i]}\n")

    auto_makemkv([
        "-e", extra,
        "-o", show_name,
        "--no-extra_warn",
    ])


if __name__ == "__main__":
	main()
