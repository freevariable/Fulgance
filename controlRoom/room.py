#!/usr/bin/python

import re,sys,redis

ICONSTABEGIN="https://en.wikipedia.org/wiki/File:BSicon_KBHFa.svg"
ICONSTAEND="https://en.wikipedia.org/wiki/File:BSicon_KBHFe.svg"
ICONSTAMEDIUM="https://en.wikipedia.org/wiki/File:BSicon_BHF.svg"
ICONSTASMALL="https://en.wikipedia.org/wiki/File:BSicon_HST.svg"
ICONTRACK="https://en.wikipedia.org/wiki/File:BSicon_STR.svg"
ICONTRACKLEFTDIV="https://en.wikipedia.org/wiki/File:BSicon_ABZgr.svg"
ICONTRACKLEFTDIVARROW="https://en.wikipedia.org/wiki/File:BSicon_dCONTgq.svg"
ICONTRACKRIGHTDIV="https://en.wikipedia.org/wiki/File:BSicon_ABZgl.svg"
ICONTRACKRIGHTDIVARROW="https://en.wikipedia.org/wiki/File:BSicon_dCONTfq.svg"
ICONTRACKLEFTCONV="https://en.wikipedia.org/wiki/File:BSicon_KRWg%2Br.svg"
ICONTRACKRIGHTCONV="https://en.wikipedia.org/wiki/File:BSicon_KRWg%2Bl.svg"
ICONTRACKLEFTCONVBEND="https://en.wikipedia.org/wiki/File:BSicon_KRWl.svg"
ICONTRACKRIGHTCONVBEND="https://en.wikipedia.org/wiki/File:BSicon_KRWr.svg"

dash={}
html={}
projectDir="../ParisLine1/"
segmentsDir="segments/"
smallSTAsvg="BSicon_HST.svg"
trackSvg="BSicon_STR.svg"
largeSTAsvg="BSicon_BHF.svg"
beginTrackSvg="BSicon_KBHFa.svg"
endTrackSvg="BSicon_KBHFe.svg"

r=redis.StrictRedis(host='localhost', port=6379, db=0)

#dash[0]={'x':0.2,'type':'STA','cnt':0}
#dash[1]={'x':1.012,'type':'SIG','cnt':3}

def initHEAD():
  f=open("html/ctrlRoom.html.head","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  for s in ssf:
    ss.append(s)
  return ss

def initSchedules(seg):
  global segs
  f=open(projectDir+"/schedules/default.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  for s in ssf:
    if (s[0]!='#'):
      s=s.rstrip().split(" ")  
      ss.append(s[0])
      cnt=cnt+1
  return ss

def initSTAs(seg):
  global segs
  f=open(projectDir+segmentsDir+seg+"/STAs.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  for s in ssf:
    if (s[0]!='#'):
      s=s.rstrip().split(" ")
      ss.append(s)
      cnt=cnt+1
  return ss

def initSIGs(seg):
  global segs
  f=open(projectDir+segmentsDir+seg+"/SIGs.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  for s in ssf:
    if (s[0]!='#'):
      s=s.rstrip().split(" ")
      ss.append(s)
      cnt=cnt+1
  return ss

stas=initSTAs('WestboundMain')
sigs=initSIGs('WestboundMain')
svcs=initSchedules('WestboundMain')
cells={}

def getState(seg):
  global svcs
  for v in svcs:
    state=r.hgetall('state:'+v[0])
    print state

def buildDashboard():
  global sigs
  global stas
  cells=[]
  html=initHEAD()
#  print html
  for s in sigs:
    cell={}
    rx=re.match(r'(.*)\+10',s[1])
    if rx:
#      print rx.group(1)
      for a in stas:
        if (a[1]==rx.group(1)):
#          print a
          if len(s)>2:
            if ((s[2]=='1') or (s[2]=='3') or (s[2]=='5')):
              cell['pK']=float(a[0])
              cell['name']=a[2]
              cell['type']='STA'
              if len(a)>3:
                if a[3]=='X':
                  cell['size']='X'
              cells.append(cell)
          else:
            cell['pK']=float(a[0])
            cell['name']=a[2]
            cell['type']='STA'
            if len(a)>3:
              if a[3]=='X':
                cell['size']='X'
            cells.append(cell)
    else:
      cell['pK']=float(s[0])
      cell['type']='SIG'
      cells.append(cell)
#    print cell
  for c in cells:
    line='<div class="divTableRow"><div class="divTableCell"></div>'
    html.append(line)
    if c['type']=='SIG':
      line='<div class="divTableCell"><img width="10px" src="'+trackSvg+'"></div>'
      html.append(line)
      line='<div class="divTableCell"></div>'
      html.append(line)
    elif  c['type']=='STA':
      svg=smallSTAsvg
      if 'size' in c:
        if c['size']=='X':
          svg=largeSTAsvg
      line='<div class="divTableCell"><img width="10px" src="'+svg+'"></div>'
      html.append(line)
      line='<div class="divTableCell">'+c['name']+'</div>'
      html.append(line)
    line='</div>'
    html.append(line)
  line='</div></body></html>'
  html.append(line)
  return html

getState('WetboundMain')
sys.exit()
html=buildDashboard()

for h in html:
  print h
