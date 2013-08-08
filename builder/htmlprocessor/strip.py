# -*- coding: utf-8 -*-
import sys
import os
import urllib
import shutil
import unicodedata
from bs4 import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf-8')

from strip_function import cleanUp

def transformStringWithEncoding(str):
  return urllib.unquote(str.decode("latin-1").encode("utf-8"))

def transformString(s):
  unquoted = urllib.unquote(str(s));
  for i in u"\"',/\\@#$%^&*()!~`«»":
    unquoted = unquoted.replace(i, "_")
  return unicode(unquoted.strip("_"))
  
def formatToNFKD(s):
  return unicodedata.normalize("NFKD", transformString(s))
  
def unicodeNormalize(s):
  return (u"".join( x for x in formatToNFKD(s) if not unicodedata.category(x).startswith("M"))).lower()

def imageExist(fileName):
  global imageFiles
  global imageSet
  unquotedName = unicodeNormalize(fileName)
  if unquotedName in imageFiles:
    imageSet.add(unquotedName)
    return True

  return False


def rewriteImages(soup):
  imgTag = soup.findAll("img");

  for imgElement in imgTag:
    del imgElement["alt"]
    #todo rewrite srcset attr if we can get callback on image loading in webview
    del imgElement["srcset"]
    
    index = -1
    srcPath = imgElement["src"]
    splitedSrc = srcPath.split("/")
    if imageExist(splitedSrc[-1]):
      imgElement['src'] = "images/" + unicodeNormalize(splitedSrc[-1])
    elif imageExist(splitedSrc[-2]):
      imgElement['src'] = "images/" + unicodeNormalize(splitedSrc[-2])
    else:
      print "Image strip = " + unicodeNormalize(splitedSrc[-2])
      [s.decompose() for s in imgElement.fetchParents("div", {"class" : ["thumb tright", "thumbinner", "image"]})]

def rewriteCrossLinks(soup):
  global idMapping
  global redirectMapping
  links = soup.findAll("a")
 
  for link in links:
    destTitle = link["href"].split("/",2)[-1]
    destTitle = transformStringWithEncoding(destTitle)
    destTitle = redirectMapping.get(destTitle, destTitle);

    if destTitle in idMapping:
      link["href"] = idMapping.get(destTitle, link["href"]) + ".html"
      continue

    if "/wiki/File:" in link["href"] and "http" not in link["href"] and "www" not in link["href"]:
      imgElement = link.find("img")
      if imgElement:
        link["href"] = imgElement["src"]
        continue
  
    if "/wiki/" in link["href"]:
      if link.string:
        link.replace_with(link.string)
      else:
        link.replace_with("")

def writeHtml(content, fileName):
  global outDir
  open(os.path.join(outDir, fileName + ".html"), "w").write(content.prettify().encode('utf-8'))

##############################################################################
if len(sys.argv) < 8:
  print "Usage: " + sys.argv[0] + " <directory with html articles> <images directory> <article set info file> <redirect info file> <output directory> <threadIndex> <cpu core count>"
  exit(1)

inDir = sys.argv[1]
imagesSrcDir = sys.argv[2]
imageFiles = dict([(unicodeNormalize(file), file) for file in os.listdir(imagesSrcDir)])
idMapping = dict([(unicode(i.split("\t")[1]), unicode(i.split("\t")[0])) for i in open(sys.argv[3])])
redirectMapping = dict([(unicode(line.split("\t")[1]), unicode(line.split("\t")[3].strip())) for line in open(sys.argv[4])])
outDir = sys.argv[5]
threadIndex = int(sys.argv[6])
coreCount = int(sys.argv[7])
files = [urllib.unquote(file) for file in idMapping.values()]
thisFiles = files[threadIndex * len(files) / coreCount : (threadIndex + 1) * len(files) / coreCount]
imageSet = set()

if not os.path.exists(outDir):
	os.makedirs(outDir)

for file in thisFiles:
	soup = BeautifulSoup(open(os.path.join(inDir, file)))
	soup = cleanUp(soup)
	rewriteImages(soup)
	rewriteCrossLinks(soup)
	writeHtml(soup, file)
  
imagesDstDir = os.path.join(outDir, "images")
if not os.path.exists(imagesDstDir):
	os.makedirs(imagesDstDir)

for image in imageSet:
	shutil.copy2(os.path.join(imagesSrcDir, imageFiles[image]), os.path.join(imagesDstDir, image))