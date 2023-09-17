import csv
import json
import os
import sys
from configparser import ConfigParser
from argparse import ArgumentParser, BooleanOptionalAction
from makemkv import MakeMKV
from pathlib import Path
from time import sleep

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

parser = ArgumentParser()
parser.add_argument("-e", "--extras", help="file path to extras csv or tsv",type=str, required=True)
parser.add_argument("-l", "--minlength", help="min length of video in sec", type=int, default=40)
parser.add_argument("-d", "--disc", help="disc number", type=int, default=0)
parser.add_argument("-o", "--output", help="output directory, defaults to extras directory",type=str, default="")
parser.add_argument("-s", "--scan", action=BooleanOptionalAction, help="force rescan of disc", type=bool, default=False)
parser.add_argument('--progress_bar', action=BooleanOptionalAction, help="show progress bar", type=bool, default=True)
parser.add_argument('--extra_warn', action=BooleanOptionalAction, help="show extra warning", type=bool, default=True)

def convert_sec(duration):
	# https://stackoverflow.com/questions/6402812/how-to-convert-an-hmmss-time-string-to-seconds-in-python
	try:
		secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(duration.split(':'))))
	except:
		raise Exception(f"cannot convert '{duration}' to sec")
	return secs

def parse_makemkv(inputfile,disc):
	with open(inputfile) as f:
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
	makemkvlog = extras_base + ".log"
	makemkvjsn = extras_base + ".json"
	makemkvini = extras_base + ".ini"

	if os.path.isfile(makemkvlog) and not args.scan:
		print(f"{makemkvlog} already exits")
		disc_info=parse_makemkv(makemkvlog,args.disc)
		with open(makemkvjsn,'w') as f:
			json.dump(disc_info, f, indent=2, sort_keys=True)
	elif os.path.isfile(makemkvjsn):
		with open(makemkvjsn) as f:
			disc_info=json.load(f)
		if os.path.exists(makemkvini):
			config = ConfigParser()
			config.read(makemkvini)
			args.minlength = int(config["MAKEMKV"]["minlength"])
			print(f"overriding parmam to  using {makemkvini}")
			print(f"    minlength = {args.minlength}")
	else:
		opts = {
			"minlength":args.minlength
		}
		disc_info = info(args.progress_bar, ProgressParser ,args.disc, opts)
		with open(makemkvjsn,'w') as f:
			json.dump(disc_info, f, indent=2, sort_keys=True)
		if args.minlength != 40:
			config = ConfigParser()
			config.add_section("MAKEMKV")
			config.set("MAKEMKV", "minlength", str(args.minlength))
			with open(makemkvini, 'w') as f:
				config.write(f)
	
	return disc_info


def main(argv=sys.argv[1:]):
	args = parser.parse_args(argv)

	delimiter=delims[Path(args.extras).suffix]

	if args.progress_bar:
		from makemkv import ProgressParser
	else:
		ProgressParser = None

	if args.output:
		outDir=args.output
	else:
		outDir=os.path.dirname(os.path.abspath(args.extras))

	if not os.path.exists(outDir):
		os.makedirs(outDir)

	tinfos=[]
	extra_warn = []
	with open(args.extras) as f:
		cinfos=csv.reader(f,delimiter=delimiter)
		for i in cinfos:
			if not len(i) in [2, 3]:
				raise Exception(f"missing track info at:\n    {i}")
			tidx = 0
			if len(i) == 3:
				tidx = int(i[2])-1
			if args.extra_warn and not any(i[0].endswith(s) for s in extra_end):
				extra_warn.append(i[0])
			tmp=convert_sec(i[1])
			tinfos.append([i[0], i[1], tmp, tidx])

	if extra_warn:
		print("the following tracks were missing plex extra ending")
		print("\n".join(extra_warn))
		print()
		sleep(10)

	os.chdir(outDir)

	extras_base = os.path.basename(os.path.splitext(args.extras)[0])

	disc_info = get_disc_info(extras_base, ProgressParser, args)

	print(disc_info["disc"]["name"])
	disc_type = disc_types[disc_info["disc"]["type"]]

	nosegmap=[]
	for tinfo in tinfos:
		ttitle, tlength, ts, tidx=tinfo
		if ttitle == "title":
			continue
		title=ttitle.replace(":", "").replace('"', "").replace('?', "")
		segmap=""
		count = 0
		for i,d in enumerate(disc_info['titles']):
			dtrack=i
			dlength = d["length"]
			if disc_type == disc_types["BD"]:
				dsegmap = d["source_filename"]
			doutputfile = d["file_output"]
			ds=convert_sec(dlength)
			if (ds and (ds == ts)):
				if count == tidx:
					if disc_type == disc_types["BD"]:
						segmap=dsegmap
					else:
						segmap = "found"
					track=dtrack
					outputfile=doutputfile
				count += 1
		titlePlusExt = title + ".mkv"
		if not os.path.exists(titlePlusExt):
			if not segmap:
				print("{} no segmap".format(title))
				nosegmap.append(f" - {title},{tlength}")
			else:
				print(f"{title} {segmap}")
				opts = {
					"title": track, 
					"output_dir": ".",
					"minlength": args.minlength,
				}
				mkv(args.progress_bar,ProgressParser ,args.disc, opts)
				os.rename(outputfile, titlePlusExt)
		else:
			print(f"skipping {titlePlusExt}, already exists")

	if nosegmap:
		print("the following tracks were not matched, check the length:")
		print("\n".join(nosegmap))
		print()

if __name__ == "__main__":
	main()
