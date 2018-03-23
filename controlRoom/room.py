#!/usr/bin/python

import re,sys,redis,copy,json,getopt,random
MPH=1.60934

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

randId=random.randint(10000000,100000000)
dash={}
html={}
svcs={}
projectDir="../LondonCentral/"
segmentsDir="segments/"
smallSTAsvg="BSicon_HST.svg"
trackSvg="BSicon_STR.svg"
largeSTAsvg="BSicon_BHF.svg"
#beginTrackSvg="BSicon_KBHFa.svg"
beginTrackSvg="TopEnd.svg"
#endTrackSvg="BSicon_KBHFe.svg"
endTrackSvg="BottomEnd.svg"

r=redis.StrictRedis(host='localhost', port=6379, db=0)

#dash[0]={'x':0.2,'type':'STA','cnt':0}
#dash[1]={'x':1.012,'type':'SIG','cnt':3}

def initConfig():
  f=open(projectDir+"routeConfig.txt","r")
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
        s1['nextTIV']=state['nextTIV']
        s1['advSIGcol']=state['advSIGcol']
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
  global conf
  cells=[]
  html=[]
  if conf['units']=='imperial':
    unitFactor=MPH
  else:
    unitFactor=1.0
  line="<body onload=\"populate()\">"
  html.append(line)
  firstSIG=True
  for s in sigs:
    cell={}
    rx=re.match(r'(.*)\+',s[1])
    if rx:
      for a in stas:
        if (a[1]==rx.group(1)):
          if len(s)>2:
            if ((s[2]=='1') or (s[2]=='3') or (s[2]=='5')):
              cell['PK']=float(a[0])*unitFactor
              cell['name']=a[2]
              cell['type']='STA'
              if len(a)>3:
                if a[3]=='X':
                  cell['size']='X'
              cells.append(cell)
          else:
            cell['PK']=float(a[0])*unitFactor
            cell['name']=a[2]
            cell['type']='STA'
            if len(a)>3:
              if a[3]=='X':
                cell['size']='X'
            cells.append(cell)
    else:
      cell['PK']=float(s[0])*unitFactor
      cell['type']='SIG'
      if len(s)>2:
        if (s[2]=='2'):
          if firstSIG==True:
#            firstSIG=False
            cell['type']='SIG2A'
          else:
            cell['type']='SIG2E'
      cells.append(cell)
    firstSIG=False
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
    if c['type']=='SIG2A':
      line='<div class="divTableCell"><img width="11px" src="'+beginTrackSvg+'"></div>'
      html.append(line)
      line='<div class="divTableCell"></div>'
      html.append(line)
    if c['type']=='SIG2E':
      line='<div class="divTableCell"><img width="11px" src="'+endTrackSvg+'"></div>'
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
  if zdump is not None:
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
conf={}

confraw=initConfig()
for aa in confraw:
  if (aa[0]!="#"):
    if (aa[0]=='units'):
      conf['units']=aa[1]

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
svcCnt=0
sCnt=0
for seg in segmentsList:
  stas=initSTAs(seg)
  sigs=initSIGs(seg)
  sched=initSchedule(seg)
  svcs={}
  cells={}
  svcs=getState(seg)
  sCnt=sCnt+len(svcs)
  svcCnt=svcCnt+len(svcs)
  f=open(seg+".html","w")
  for h in head:
    f.write(h)
  iframe=buildDashboard(svcs) 
  for i in iframe:
    f.write(i)
  f.close()
if (sCnt<1):
  print "ERROR. No services found in segments. Have you run sim with --realtime?"
  sys.exit(2)

elapsed=r.get("elapsedHuman")
headwaycnt=float(len(r.keys("headway:*")))
print "<html><head><title>Fulgence control room</title>"
print "<META HTTP-EQUIV=\"Pragma\" CONTENT=\"no-cache\">"
print "<style type=\"text/css\">"
print "* {"
print "  font-size:12px;"
print "  font-family: Tahoma;"
print "}"
print "a:visited, a:link {"
print "  color:#AA0000;"
print "}"
print "</style>"
print "<script>  function resizeIframe(obj) {"
print "auxH=obj.contentWindow.document.body.scrollHeight+60;"
print "    obj.style.height = auxH + 'px';"
print "  }"
print "</script></head>"
print "<body>This sim has been running for <a href=\"\" onClick=\"window.location.reload()\">"+elapsed+"</a>. (Click on the timestamp to refresh this page. It is updated every 20 to 30 seconds.)<br>"
print "<p><b>"+str(svcCnt)+"</b> services are currently operating on the line."
print "Live traffic congestion: "
if headwaycnt>0.8*float(len(stas)):
  headwaycnt=0.8*float(len(stas))
congestion=125.0*float(headwaycnt)/float(len(stas))
print "<b>"+str(congestion)+"%</b></p>"
print "<p>Click on a train service name below to show its live status</p>"
print "</p><p><b>Powered by <a href=\"https://github.com/freevariable/Fulgence\">Fulgence</a>, your precision simulator!</b></p><p>"
print "<div style=\"display: inline-block;white-space: nowrap;\">"
for seg in segmentsList:
  print "<iframe src=\""+seg+".html?q="+str(randId)+"\" scrolling=\"no\" frameborder=\"0\" onload=\"resizeIframe(this)\"></iframe>"
print "</div></p></body></html>"

#for h in html:
#  print h
