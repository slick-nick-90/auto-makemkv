import csv
import json
import os
import sys
from argparse import ArgumentParser, BooleanOptionalAction
from makemkv import MakeMKV
from pathlib import Path

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

parser = ArgumentParser()
parser.add_argument("-e", "--extras", help="file path to extras csv or tsv")
parser.add_argument("-l", "--minlength", help="min length of video in sec", default=40)
parser.add_argument("-d", "--disc", help="disc number", default=0)
parser.add_argument("-o", "--output", help="output directory, defaults to extras directory", default="")
parser.add_argument("-s", "--scan", action="store_true", help="force rescan of disc", default=False)
parser.add_argument('--progress_bar', action=BooleanOptionalAction, help="show progress bar", default=True)

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
	os.chdir(outDir)

	tinfos=[]
	extra_warn = []
	with open(args.extras) as f:
		cinfos=csv.reader(f,delimiter=delimiter)
		for i in cinfos:
			if len(i) !=2:
				raise Exception(f"missing track info at:\n    {i}")
			if not any(i[0].endswith(s) for s in extra_end):
				extra_warn.append(i[0])
			tmp=convert_sec(i[1])
			tinfos.append([*i, tmp])

	if extra_warn:
		print("the following tracks were missing plex extra ending")
		print("\n".join(extra_warn))
		print()
	extras_base = os.path.basename(os.path.splitext(args.extras)[0])
	makemkvlog = extras_base + ".log"
	makemkvjsn = extras_base + ".json"

	if os.path.isfile(makemkvlog) and not args.scan:
		print(f"{makemkvlog} already exits")
		disc_info=parse_makemkv(makemkvlog,args.disc)
		with open(makemkvjsn,'w') as f:
			json.dump(disc_info, f, indent=2, sort_keys=True)
	elif os.path.isfile(makemkvjsn):
		with open(makemkvjsn) as f:
			disc_info=json.load(f)
	else:
		opts = {
			"minlength":args.minlength
		}
		disc_info = info(args.progress_bar, ProgressParser ,args.disc, opts)
		with open(makemkvjsn,'w') as f:
			json.dump(disc_info, f, indent=2, sort_keys=True)
	print(disc_info["disc"]["name"])

	nosegmap=[]
	for tinfo in tinfos:
		ttitle, tlength, ts=tinfo
		if ttitle == "title":
			continue
		title=ttitle.replace(":", "").replace('"', "")
		segmap=""
		for i,d in enumerate(disc_info['titles']):
			dtrack=i
			dlength = d["length"]
			dsegmap = d["source_filename"]
			doutputfile = d["file_output"]
			ds=convert_sec(dlength)
			if (ds and (ds == ts)):
				segmap=dsegmap
				track=dtrack
				outputfile=doutputfile
		if not os.path.exists(os.path.join(outDir,title+".mkv")):
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
				mkv(args.progress_bar,ProgressParser ,args.disc,opts)
				os.rename(os.path.join(outDir,outputfile), os.path.join(outDir,title+".mkv"))
		else:
			print("skipping {}, already exists".format(os.path.join(outDir,title+".mkv")))

	if nosegmap:
		print("the following tracks were not matched, check the length:")
		print("\n".join(nosegmap))
		print()

if __name__ == "__main__":
	main()
