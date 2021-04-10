from datetime import datetime
import csv
import re
import os
import argparse

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

	return movie,disc_info

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--extras", help="file path to extras csv")
args = parser.parse_args()

# os.system("makemkvcon --robot --minlength=90 --messages=MakeMKVOutput.txt info disc:0")

makemkvlog="MakeMKVOutput.txt"
movie, disc_info=parse_makemkv(makemkvlog)

print(movie)

tinfos=csv.reader(open(args.extras))
if not os.path.exists(movie):
    os.makedirs(movie)
for tinfo in tinfos:
	ttitle, tlength=tinfo
	if ttitle == "title":
		continue
	title=ttitle.replace(":", "")
	segmap=""
	for d in disc_info:
		dtrack,dlength,dsegmap,doutputfile = d
		ds=convert_sec(dlength)
		ts=convert_sec(tlength)
		if (ds and (ds == ts)):
			segmap=dsegmap
			track=dtrack
			outputfile=doutputfile
	if os.path.exists(os.path.join(movie,title+".mkv")):
		if not segmap:
			print("{} no segmap".format(title))
		else:
			print("{} {}".format(title,segmap))
			cmd="makemkvcon.exe --robot --minlength=90 mkv disc:0 {} {}".format(track ,movie)
			print(cmd)
			# os.system(cmd)
			# os.rename(os.path.join(movie,outputfile), os.path.join(movie,title+".mkv"))
