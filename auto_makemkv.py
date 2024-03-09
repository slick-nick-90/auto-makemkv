import csv
import json
import os
import sys
from dataclasses import dataclass
from configparser import ConfigParser
from argparse import ArgumentParser
from makemkv import MakeMKV
from pathlib import Path
from time import sleep
import __init__

delims = {
    ".tsv": "\t",
    ".csv": ",",
}

extra_end = [
    "-behindthescenes",
    "-deleted",
    "-featurette",
    "-interview",
    "-scene",
    "-short",
    "-trailer",
    "-other",
]

disc_types = {
    "DVD": 0,
    "BD": 1,
}


@dataclass
class Track_Info():
    title: str
    length: str
    s: int
    idx: int
    defined_idx: bool


parser = ArgumentParser()
for parser_arg in __init__.parser_args:
    parser.add_argument(*parser_arg["args"], **parser_arg["kwargs"])

def clean_name(name):
    # remove special characters
    name.replace("Â", "")
    return name

def convert_sec(duration):
    # https://stackoverflow.com/questions/6402812/how-to-convert-an-hmmss-time-string-to-seconds-in-python
    try:
        secs = sum(
            int(x) * 60**i for i, x in enumerate(reversed(duration.split(":")))
        )
    except:
        raise Exception(f"cannot convert '{duration}' to sec")
    return secs


def parse_makemkv(input_file, disc):
    with open(input_file) as f:
        content = f.read().replace("\n\r", "\n")
    makemkv = MakeMKV(disc)
    disc_info = makemkv._parse_makemkv_log(content.split("\n"))
    return disc_info


def info(progress_bar, ProgressParser, disc, opts):
    if progress_bar:
        with ProgressParser() as progress:
            makemkv = MakeMKV(disc, progress_handler=progress.parse_progress)
            disc_info = makemkv.info(**opts)
    else:
        makemkv = MakeMKV(disc)
        disc_info = makemkv.info(**opts)
    return disc_info


def mkv(progress_bar, ProgressParser, disc, opts):
    if progress_bar:
        with ProgressParser() as progress:
            makemkv = MakeMKV(disc, progress_handler=progress.parse_progress)
            makemkv.mkv(**opts)
    else:
        makemkv = MakeMKV(disc)
        makemkv.mkv(**opts)


def get_disc_info(extras_base, ProgressParser, args):
    makemkv_log = extras_base + ".log"
    makemkv_jsn = extras_base + ".json"
    makemkv_ini = extras_base + ".ini"

    if os.path.isfile(makemkv_log) and not args.scan:
        print(f"{makemkv_log} already exits")
        disc_info = parse_makemkv(makemkv_log, args.disc)
        with open(makemkv_jsn, "w") as f:
            json.dump(disc_info, f, indent=2, sort_keys=True)
    elif os.path.isfile(makemkv_jsn):
        with open(makemkv_jsn) as f:
            disc_info = json.load(f)
        if os.path.exists(makemkv_ini):
            config = ConfigParser()
            config.read(makemkv_ini)
            args.minlength = int(config["MAKEMKV"]["minlength"])
            print(f"overriding param to  using {makemkv_ini}")
            print(f"    minlength = {args.minlength}")
    else:
        opts = {"minlength": args.minlength}
        disc_info = info(args.progress_bar, ProgressParser, args.disc, opts)
        with open(makemkv_jsn, "w") as f:
            json.dump(disc_info, f, indent=2, sort_keys=True)
        if args.minlength != 40:
            config = ConfigParser()
            config.add_section("MAKEMKV")
            config.set("MAKEMKV", "minlength", str(args.minlength))
            with open(makemkv_ini, "w") as f:
                config.write(f)

    return disc_info


def main(argv=sys.argv[1:]):
    args = parser.parse_args(argv)

    delimiter = delims[Path(args.extras).suffix]

    if args.progress_bar:
        from makemkv.progress import ProgressParser
    else:
        ProgressParser = None

    if args.output:
        outDir = args.output
    else:
        outDir = os.path.dirname(os.path.abspath(args.extras))

    if not os.path.exists(outDir):
        os.makedirs(outDir)

    t_infos = []
    extra_warn = []
    length_warn = []
    with open(args.extras) as f:
        c_infos = csv.reader(f, delimiter=delimiter)
        for i in c_infos:
            defined_idx = False
            if not len(i) in [2, 3]:
                raise Exception(f"missing track info at:\n    {i}")
            t_idx = 0
            if len(i) == 3:
                t_idx = int(i[2]) - 1
                defined_idx = True
            if args.extra_warn and not any(i[0].endswith(s) for s in extra_end):
                extra_warn.append(i[0])
            tmp = convert_sec(i[1])
            t_infos.append(Track_Info(i[0], i[1], tmp, t_idx, defined_idx))

    if extra_warn:
        print("the following tracks were missing plex extra ending")
        print("\n".join(extra_warn))
        print()
        for i in range(10, 0, -1):
            print(f"continuing in {i} seconds")
            sleep(1)

    os.chdir(outDir)

    extras_base = os.path.basename(os.path.splitext(args.extras)[0])

    disc_info = get_disc_info(extras_base, ProgressParser, args)

    print(disc_info["disc"]["name"])
    disc_type = disc_types[disc_info["disc"]["type"]]

    no_segmap = []
    for t_info in t_infos:
        if t_info.title == "title":
            continue
        title = t_info.title.replace(":", "").replace('"', "").replace("?", "")
        titlePlusExt = title + ".mkv"
        segmap = ""
        match_track = []
        match_output_file = []
        match_segmap = []
        for d_track, d in enumerate(disc_info["titles"]):
            ds = convert_sec(d["length"])
            if ds and (ds == t_info.s):
                if disc_type == disc_types["BD"]:
                    match_segmap.append(d["source_filename"])
                else:
                    match_segmap.append("found")
                match_track.append(d_track)
                match_output_file.append(d["file_output"])
        if t_info.defined_idx and len(match_track) > 1:
            print(f"warning: more than one track has length of {t_info.length} found on disk")
            length_warn.append(f" - {title},{t_info.length}")
        if not os.path.exists(titlePlusExt):
            if t_info.idx >= len(match_track):
                print("{} no segmap".format(title))
                no_segmap.append(f" - {title},{t_info.length}")
            else:
                track = match_track[t_info.idx]
                output_file = match_output_file[t_info.idx]
                segmap = match_segmap[t_info.idx]
                print(f"{title} {segmap}")
                opts = {
                    "title": track,
                    "output_dir": ".",
                    "minlength": args.minlength,
                }
                mkv(args.progress_bar, ProgressParser, args.disc, opts)
                os.rename(clean_name(output_file), titlePlusExt)
        else:
            print(f"skipping {titlePlusExt}, already exists")

    if no_segmap:
        print("the following tracks were not matched, check the length:")
        print("\n".join(no_segmap))
        print()
    if length_warn:
        print("the following tracks had multiple length matches:")
        print("\n".join(length_warn))
        print()


if __name__ == "__main__":
    main()
