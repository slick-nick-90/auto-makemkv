from pathlib import Path
import csv
import json
import os
import sys
from argparse import ArgumentParser
from makemkv import MakeMKV

delims = {
	".tsv": "\t",
	".csv": ",",
}

parser = ArgumentParser()
parser.add_argument("-e", "--extras", help="file path to extras csv or tsv")
parser.add_argument("-l", "--minlength", help="min length of video in sec",default=40)
parser.add_argument("-d", "--disc", help="disc number",default=0)
parser.add_argument("-o", "--output", help="output directory, defaults to extras directory",default="")
parser.add_argument("-s", "--scan", action="store_true", help="force rescan of disc",default=False)

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

def main(argv=sys.argv[1:]):
	args = parser.parse_args(argv)

	delimiter=delims[Path(args.extras).suffix]

	if args.output:
		outDir=args.output
	else:
		outDir=os.path.dirname(os.path.abspath(args.extras))

	if not os.path.exists(outDir):
		os.makedirs(outDir)
	os.chdir(outDir)

	tinfos=[]
	with open(args.extras) as f:
		cinfos=csv.reader(f,delimiter=delimiter)
		for i in cinfos:
			if len(i) !=2:
				raise Exception(f"missing track info at:\n    {i}")
			i[1]=convert_sec(i[1])
			tinfos.append(i)

	makemkvlog="_MakeMKVOutput.log"
	if os.path.isfile(makemkvlog) and not args.scan:
		print(f"{makemkvlog} already exits")
		disc_info=parse_makemkv(makemkvlog,args.disc)
		with open("_MakeMKVOutput.json",'w') as f:
			json.dump(disc_info, f, indent=2, sort_keys=True)
	elif os.path.isfile("_MakeMKVOutput.json"):
		with open("_MakeMKVOutput.json") as f:
			disc_info=json.load(f)
	else:
		makemkv = MakeMKV(args.disc)
		disc_info = makemkv.info(minlength=args.minlengh)
		with open("_MakeMKVOutput.json",'w') as f:
			json.dump(disc_info, f, indent=2, sort_keys=True)
	print(disc_info["drives"][args.disc]["disc_name"])
	
	nosegmap=[]
	for tinfo in tinfos:
		ttitle, tlength=tinfo
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
			ts=tlength
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
				makemkv.mkv(title=track, output_dir=".")
				os.rename(os.path.join(outDir,outputfile), os.path.join(outDir,title+".mkv"))
		else:
			print("skipping {}, already exists".format(os.path.join(outDir,title+".mkv")))

	if nosegmap:
		print("the following tracks were not matched, check the length:")
		print("\n".join(nosegmap))
		print()

if __name__ == "__main__":
	main()
