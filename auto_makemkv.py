from datetime import datetime
from shutil import copyfile
from pathlib import Path
import csv
import re
import os
import argparse

delims = {
	".tsv": "\t",
	".csv": ",",
}

def convert_sec(duration):
	if (re.match(r'\d+:\d+:\d+',duration)):
		pt = datetime.strptime(duration,'%H:%M:%S')
		ts = pt.second + pt.minute*60 + pt.hour*3600
	elif (re.match(r'\d+:\d+',duration)):
		pt = datetime.strptime(duration,'%M:%S')
		ts = pt.second + pt.minute*60
	else:
		print('cannot convert "{}" to seconds'.format(duration))
	return ts

def parse_makemkv(inputfile):
	""" # from https://www.makemkv.com/forum2/viewtopic.php?f=1&t=7680#p42661
		ap_iaChapterCount=8,
		ap_iaDuration=9,
		ap_iaPlaylist=16,
		ap_iaSegmentsMap=26,
		ap_iaOutputFileName=27,
	"""

	fullmatch = re.compile(r'TINFO:(?P<title>\d+),9,0,"(?P<duration>[\d:]+)".+?TINFO:(?P=title),16,0,"(?P<playlist>\d+?.m..s)".+?TINFO:(?P=title),27,0,"(?P<outputfile>.+?mkv)"', re.DOTALL)

	content = open(inputfile).read().replace("\n\r", "\n")
	disc_info=fullmatch.findall(content)
	movie=re.search("CINFO:2,0,\"(.*)\"\n",content).group(1)
	if not movie:
		print("error cannot find name of disc")

	return movie,disc_info

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--extras", help="file path to extras csv")
parser.add_argument("-m", "--minlength", help="min length of video in sec",default=40)
parser.add_argument("-o", "--output", help="min length of video in sec",default="")
args = parser.parse_args()

delimiter=delims[Path(args.extras).suffix]


if args.output:
	outDir=args.output
else:
	outDir=os.path.dirname(os.path.abspath(args.extras))

if not os.path.exists(outDir):
    os.makedirs(outDir)
os.chdir(outDir)
makemkvlog="_MakeMKVOutput.log"
cmd=f"makemkvcon --robot --minlength={args.minlength} --messages {makemkvlog} info disc:0"
os.system(cmd)
movie, disc_info=parse_makemkv(makemkvlog)
print(movie)
f=open(args.extras)

tinfos=csv.reader(f,delimiter=delimiter)
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
		ts=convert_sec(tlength)
		if (ds and (ds == ts)):
			segmap=dsegmap
			track=dtrack
			outputfile=doutputfile
	if not os.path.exists(os.path.join(outDir,title+".mkv")):
		if not segmap:
			print("{} no segmap".format(title))
			nosegmap.append(" - {},{}".format(title,tlength))
		else:
			print("{} {}".format(title,segmap))
			cmd="makemkvcon --robot --noscan --minlength={args.minlength} mkv disc:0 {track} \"{outDir}\""
			print(cmd)
			os.system(cmd)
			os.rename(os.path.join(outDir,outputfile), os.path.join(outDir,title+".mkv"))
	else:
		print("skipping {}, already exists".format(os.path.join(outDir,title+".mkv")))

if nosegmap:
	print("the following tracks were not matched, check the length:")
	print("\n".join(nosegmap))
	print()

f.close()
