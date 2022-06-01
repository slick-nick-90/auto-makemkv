from pathlib import Path
import csv
import re
import os
import sys
from argparse import ArgumentParser

delims = {
	".tsv": "\t",
	".csv": ",",
}

parser = ArgumentParser()
parser.add_argument("-e", "--extras", help="file path to extras csv or tsv")
parser.add_argument("-l", "--minlength", help="min length of video in sec",default=40)
parser.add_argument("-o", "--output", help="output directory, defaults to extras directory",default="")

def convert_sec(duration):
	# https://stackoverflow.com/questions/6402812/how-to-convert-an-hmmss-time-string-to-seconds-in-python
	try:
		secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(duration.split(':'))))
	except:
		raise Exception(f"cannot convert '{duration}' to sec")
	return secs

def parse_makemkv(inputfile):
	"""	# from https://www.makemkv.com/forum2/viewtopic.php?f=1&t=7680#p42661
		ap_iaChapterCount=8,
		ap_iaDuration=9,
		ap_iaPlaylist=16,
		ap_iaSegmentsMap=26,
		ap_iaOutputFileName=27,
	"""

	fullmatch = re.compile(r'TINFO:(?P<title>\d+),9,0,"(?P<duration>[\d:]+)".+?TINFO:(?P=title),16,0,"(?P<playlist>\d+?.m..s)".+?TINFO:(?P=title),27,0,"(?P<outputfile>.+?mkv)"', re.DOTALL)

	with open(inputfile) as f:
		content = f.read().replace("\n\r", "\n")
	disc_info=fullmatch.findall(content)
	movie=re.search("CINFO:2,0,\"(.*)\"\n",content).group(1)
	if not movie:
		print("error cannot find name of disc")

	return movie,disc_info

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
	cmd=f"makemkvcon --robot --minlength={args.minlength} --messages={makemkvlog} info disc:0"
	print(cmd)
	os.system(cmd)
	movie, disc_info=parse_makemkv(makemkvlog)
	print(movie)
	
	nosegmap=[]
	for tinfo in tinfos:
		ttitle, tlength=tinfo
		if ttitle == "title":
			continue
		title=ttitle.replace(":", "").replace('"', "")
		segmap=""
		for d in disc_info:
			dtrack,dlength,dsegmap,doutputfile = d
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
				cmd=f"makemkvcon --robot --noscan --minlength={args.minlength} mkv disc:0 {track} ."
				print(cmd)
				os.system(cmd)
				os.rename(os.path.join(outDir,outputfile), os.path.join(outDir,title+".mkv"))
		else:
			print("skipping {}, already exists".format(os.path.join(outDir,title+".mkv")))

	if nosegmap:
		print("the following tracks were not matched, check the length:")
		print("\n".join(nosegmap))
		print()

if __name__ == "__main__":
	main()
