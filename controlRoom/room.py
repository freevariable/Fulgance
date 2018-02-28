#!/usr/bin/python

import re,sys,redis,copy,json,getopt

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
svcs={}
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

def initSchedule(seg):
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

def getState(seg):
  global sched
  lsvcs=[]
  for v in sched:
    state=r.hgetall('state:'+v)
    s=dict(state)
    s1={}
    if 'segment' in state:
      if state['segment']==seg:
        s1['name']=v
        s1['inSta']=state['inSta']
        s1['atSig']=state['atSig']
        s1['coasting']=state['coasting']
        s1['sigBrake']=state['sigBrake']
        s1['staBrake']=state['staBrake']
        s1['segment']=state['segment']
        s1['nextSTA']=state['nextSTA']
        s1['nextSIG']=state['nextSIG']
        s1['nextTIV']=int(state['nextTIV'])
        s1['x']=float(state['x'])
        s1['v']=float(state['v'])
        s1['pax']=float(state['pax'])
        s1['maxPax']=float(state['maxPax'])
        s1['maxVk']=float(state['maxVk'])
        s1['units']=state['units']
        lsvcs.append(s1)
  return lsvcs

def buildDashboard(zdump):
  global sigs
  global stas
  global svcs
  cells=[]
  html=[]
  line="<body onload=\"populate()\">"
  html.append(line)
  for s in sigs:
    cell={}
    rx=re.match(r'(.*)\+10',s[1])
    if rx:
      for a in stas:
        if (a[1]==rx.group(1)):
          if len(s)>2:
            if ((s[2]=='1') or (s[2]=='3') or (s[2]=='5')):
              cell['PK']=float(a[0])
              cell['name']=a[2]
              cell['type']='STA'
              if len(a)>3:
                if a[3]=='X':
                  cell['size']='X'
              cells.append(cell)
          else:
            cell['PK']=float(a[0])
            cell['name']=a[2]
            cell['type']='STA'
            if len(a)>3:
              if a[3]=='X':
                cell['size']='X'
            cells.append(cell)
    else:
      cell['PK']=float(s[0])
      cell['type']='SIG'
      cells.append(cell)
#    print cell
  for v in svcs:
    found=False
    oldc={}
    for c in cells:
      if float(v['x']/1000.0)<c['PK']:
        if (found==False):
#          print v['name']+'__'+str(v['PK'])+"__"+str(c['PK'])
          oldc['service']=v['name']
          found=True
      oldc=c
  for c in cells:
    if 'service' in c:
      line='<div class="divTableRow"><div class="divTableCell"><div onclick="showSrv('+"\'"+c['service']+"\'"+')">'+c['service']+'</div><div class="popUp"><span class="srvPopUp" id="'+c['service']+'"></span></div></div>'
    else:
      line='<div class="divTableRow"><div class="divTableCell"></div>'
    html.append(line)
    if c['type']=='SIG':
      line='<div class="divTableCell"><img width="11px" src="'+trackSvg+'"></div>'
      html.append(line)
      line='<div class="divTableCell"></div>'
      html.append(line)
    elif  c['type']=='STA':
      svg=smallSTAsvg
      if 'size' in c:
        if c['size']=='X':
          svg=largeSTAsvg
      line='<div class="divTableCell"><img width="11px" src="'+svg+'"></div>'
      html.append(line)
      line='<div class="divTableCell">'+c['name']+'</div>'
      html.append(line)
    line='</div>'
    html.append(line)
  line='<div id="SrvWrapper" style="display: none;">'+json.dumps(zdump)+'</div>'
  html.append(line)
  line='</div></body></html>'
  html.append(line)
  return html

try:
  opts, args = getopt.getopt(sys.argv[1:], "h:m", ["help", "route=", "segments="])
except getopt.GetoptError as err:
  print(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)

segmentsList=[]
found=False

for o, a in opts:
  if o in ("--segments"):
    segmentsList = a.split(',')
#    print segmentsList
    found=True
  elif o in ("--route"):
    projectDir = "../"+a+'/'
  else:
    assert False, "option unknown"
    sys.exit(2)

if found==False:
  print "ERROR. Segment list needed."
  sys.exit(2)

head=initHEAD()
iframes=[]
for seg in segmentsList:
  stas=initSTAs(seg)
  sigs=initSIGs(seg)
  sched=initSchedule(seg)
  svcs={}
  cells={}
  svcs=getState(seg)
  if (len(svcs)<1):
    print "ERROR. No services found in segment. Have you run sim with --realtime?"
    sys.exit(2)
  f=open(seg+".html","w")
  for h in head:
    f.write(h)
  iframe=buildDashboard(svcs) 
  for i in iframe:
    f.write(i)
  f.close()

print "<html><head><script>"
print "  function resizeIframe(obj) {"
print "    obj.style.height = obj.contentWindow.document.body.scrollHeight + 'px';"
print "  }"
print "</script></head>"
print "<body><input type=\"button\" value=\"Refresh Page\" onClick=\"window.location.reload()\">"
for seg in segmentsList:
  print "<iframe src=\""+seg+".html\" scrolling=\"no\" frameborder=\"0\" onload=\"resizeIframe(this)\"></iframe>"
print "</body></html>"

#for h in html:
#  print h
