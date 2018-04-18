#!/usr/bin/python

import re,sys,redis,json,getopt,random,urllib2
import time,uuid
MPH=1.60934
WAKEINTERVAL=3

alreadyPicked=[]
liveScheds=[]
maps=[]
segMaps=[]
projectDir=""
segmentsDir="segments/"
foundSch=False
conf={}
#scheduleFile=""
redisDB=0

try:
  opts, args = getopt.getopt(sys.argv[1:], "h:m", ["help", "instance="])
except getopt.GetoptError as err:
  print(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)

for o, a in opts:
  if o in ("--instance"):
    redisDB = int(a)
#  elif o in ("--schedule"):
#    foundSch=True
#    scheduleFile = a
  else:
    assert False, "option unknown"
    sys.exit(2)
#if foundSch==False:
#  print "ERROR. Schedule needed."
#  sys.exit(2)

r=redis.StrictRedis(host='localhost', port=6379, db=redisDB)
try:
  answ=r.client_list()
except redis.ConnectionError:
  print "FATAL: cannot connect to redis."
  sys.exit()

routeName=r.get("routeName")
projectDir=routeName+'/'

def getOffset(seg,name):
  global unitsFactor
  f=open(projectDir+"segments/"+seg+"/SIGs.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  for s in ssf:
    s=s.split(" ")
    if s[1]==name:
      return float(s[0])*1000.0*unitsFactor
  return None

def getSegLenAndType(seg):
  global unitsFactor
  f=open(projectDir+"segments/"+seg+"/SIGs.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  for s in ssf:
    if cnt==0:
      s=s.split(" ")
      if len(s)>2:
        firstS=s[2]
      else:
        firstS='1'
      firstN=s[1]
      if len(s)>3:
        firstB=s[3]
    cnt=cnt+1
  s=s.split(" ")
  if len(s)>2:
    lastS=s[2]
  else:
    lastS='1'
  lastN=s[1]
#  print seg+" "+str(firstS)+"->"+str(lastS)
  lnt={}
  lnt['length']=1000.0*float(s[0])*unitsFactor
  typeFound=False
  if firstS=='2':
    if lastS=='2':
      typeFound=True
      lnt['type']='Main'
      lnt['offset']=0.0
    elif lastS=='4C':
      typeFound=True
      lnt['type']='BranchConv'   
      segMain=s[3].split(":") 
      if segMain[0]=='Main':
        lnt['offset']=getOffset(segMain[1],lastN)
      else:
        print "FATAL: syntax error in signal "+lastS+":"+lastN
        sys.exit()
  elif firstS=='4D':
    if lastS=='2':
      typeFound=True
      lnt['type']='BranchDiv'
      segMain=firstB.split(":") 
      if segMain[0]=='Main':
        lnt['offset']=getOffset(segMain[1],firstN)
      else:
        print "FATAL: syntax error in signal "+firstS+":"+firstN
        sys.exit()
    elif lastS=='1':
      typeFound=True
      lnt['type']='GarageExit'
      lnt['offset']=0.0
    elif lastS=='4C':
      typeFound=True
      lnt['type']='Siding'
      lnt['offset']=0.0
  elif firstS=='1':
    if lastS=='4C':
      typeFound=True
      lnt['type']='GarageFeed'
      lnt['offset']=0.0
    elif lastS=='1':
      typeFound=True
      lnt['type']='OneOff'
      lnt['offset']=0.0
  if 'type' in lnt:
    return lnt
  print "FATAL: unknown segment type: "+seg+" firstS:"+firstS+" lastS:"+lastS
  sys.exit()
  return None

def confMAPs():
  f=open(projectDir+"maps.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  aL=[]
  for s in ssf:
    if s[0]!='#':
      s=s.rstrip().split(":")
      aS={}
      ss=s[1].split(",")
      aS[s[0]]=ss
      aL.append(aS)
  return aL

def initSEGmap(sm):
  global segMaps
  global segmentsList
  global liveScheds
  schml=[]
  schm={}
  for ll in liveScheds:
    if ll['segment']==sm:
      lli={}
      lli['x']=ll['x']
      lli['name']=ll['name']
      schml.append(lli)
  schm['points']=schml
  lnt=getSegLenAndType(sm)
  schm['length']=lnt['length']
  schm['type']=lnt['type']
  schm['offset']=lnt['offset']
#  print schm
  return schm

def initMAPs():
  global maps
  global segMaps
  global segmentsList
# stage 1: identify maps
  mapsconf=confMAPs()
#  print mapsconf
# stage 2: generate segment maps
  for se in segmentsList:
    found=False
    for sm in segMaps:
      if sm['segment']==se:
        found=True
    if found==False:
      smp={}
      smp['map']=initSEGmap(se)
      smp['segment']=se
      segMaps.append(smp)
#  print segMaps
#stage 3: generate maps
  lmaps=[]
  for m in mapsconf:
    hasMain=False
    keys=m.keys()
    if keys[0] is not None:
      cnt=0
      amap={}
      amap['map']=keys[0] 
      amap['points']=[]
      for mm in m[keys[0]]:
        for sm in segMaps:
          if sm['segment']==mm:
            if ((hasMain==False) and (sm['map']['type']=='Main')):
              hasMain=True
#              print "MAIN"
              for p in sm['map']['points']:
                amap['points'].append(p)
#                print amap['points']
#              print "/MAIN"
            elif ((hasMain==True) and (sm['map']['type']=='Main')):
              print "FATAL: map has two main branches"
              sys.exit()
            elif sm['map']['type']=='BranchDiv':
#              print "BDIV"
              for p in sm['map']['points']:          
                p1={}
                p1['x']=p['x']+sm['map']['offset']
                p1['name']=p['name']
                amap['points'].append(p1)
#              print "/BDIV"
            elif sm['map']['type']=='BranchConv':
#              print "BCONV"
              for p in sm['map']['points']:          
                p1={}
                p1['x']=p['x']+sm['map']['offset']-sm['map']['length']
                p1['name']=p['name']
                amap['points'].append(p1)
#              print "/BCONV"
#      print 'before lambda:'
#      print amap['points']
      amap['points'].sort(key=lambda l: l['x'])
#      print 'after lambda:'
#      print amap['points']
      lmaps.append(amap)
#  print "LMAPS:"
#  print lmaps
#  print "/LMAPS"
  return lmaps

def distances(m):
  global alreadyPicked
  oldp={}
  dl=[]
  for p in m['points']:
    if 'name' in oldp:
      found=False
      for a in alreadyPicked:
        if a==oldp['name']:
          found=True
      if found==False:
        d={}
        d['distance']=p['x']-oldp['x']
        d['from']=oldp['name']
        d['to']=p['name']
#      print d
        dl.append(d)
    oldp=p
  dl.sort(key=lambda l: l['distance'])
  return dl

def initSRVs(s_type):
  f=open(projectDir+"services.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  if s_type=='exit':
    s_char='-'
  elif s_type=='standard':
    s_char='+'
  else:
    return []
  a=[]
  for s in ssf:
    aS={}
    if (s[0]==s_char):
      s=s.rstrip().split(" ")
      aS['name']=s[1]
      aDivs=[]
      if s_char=='+':
        ss=s[2].split(":")
        if ss[0]!='TpH':
          print "FATAL: unknown service verb"
          sys.exit()
        ss=ss[1].split("-")
        aS['min']=int(ss[0])
        aS['max']=int(ss[1])
      elif s_char=='-':
        if s[2]!='OneOff':
          print "FATAL: unknown service verb"
          sys.exit()
      for i in range(3,len(s)):
#        print "s"+str(i)+": "+s[i]
        ss=s[i].split(":")
        aSS={}
        aSS[ss[0]]=ss[1]
        aDivs.append(aSS) 
      aS['divs']=aDivs
      cnt=cnt+1
      a.append(aS) 
  return a

def initSEGs():
  f=open(projectDir+"segments.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  for s in ssf:
    if (s[0]!='#'):
      s=s.rstrip()
      ss.append(s)
      cnt=cnt+1
  return ss

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

def initSchedules(seg,sFile):
  global segs
  f=open(projectDir+"/schedules/"+sFile,"r")
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

def getState():
  global liveScheds
  ll=[]
  rs=urllib2.urlopen('http://127.0.0.1:4999/v1/list/schedules')
  sched=json.loads(rs.read())
  for v in sched:
    state=r.hgetall('state:'+v)
    state=dict(state)
    s1={}
    if 'segment' in state:
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
      s1['service']=state['service']
      s1['advSIGcol']=state['advSIGcol']
      s1['x']=float(state['x'])
      s1['v']=float(state['v'])
      s1['pax']=float(state['pax'])
      s1['maxPax']=float(state['maxPax'])
      s1['maxVk']=float(state['maxVk'])
      s1['units']=state['units']
      ll.append(s1)
  return ll

def getSegExits(seg,sig):
  sis=initSIGs(seg)
  exits=[]
  cntEx=0
  exPos=-1
  for si in sis:
    if len(si)>4:
      if si[2]=='4D':
        br=si[4].split(":")
        if br[0]=='Branch':
          chk=getSegLenAndType(br[1])
          if 'type' in chk:
            if chk['type']=='GarageExit':
              order={}
              order['type']=si[2]
              order['name']=si[1]
              bro=si[5].split(":")
              if bro[0]=='BranchOrientation':
                order['direction']=bro[1]
              exPos=cntEx
              cnt=0    
              sigPos=-1
              for si2 in sis:
                if si2[1]==sig:
                  sigPos=cnt
                cnt=cnt+1
              if sigPos>0:
#                print "sch sig pos is:"+str(sigPos)
#                print "div sig pos is:"+str(exPos)
                if ((sigPos>exPos) or (sigPos<(exPos-2))):  #train must not be too close to div
                  exits.append(order)
    cntEx=cntEx+1
  return exits

def getReverseSeg(seg):
  chk=getSegLenAndType(seg)
  if 'type' in chk:
    if chk['type']=='Main':
      sis=initSIGs(seg)
      si=sis[-1][3].split(":")
      if si[0]=='Reverse':
        return si[1]
  return None

def getExitsForSched(sname):
  global liveScheds 
  for l in liveScheds:
    if l['name']==sname:
      break
  if l is not None:
    sseg=l['segment']
#    print sname+" is in seg: "+sseg
    exits=getSegExits(sseg,l['nextSIG'])
    if len(exits)>0:
      return exits
    else:
      altSeg=getReverseSeg(sseg)
      if altSeg is not None:
        exits=getSegExits(altSeg,l['nextSIG'])
        if len(exits)>0:
          return exits
  return None

segmentsList=initSEGs()
confraw=initConfig()
unitsFactor=1.0

for aa in confraw:
  if (aa[0]!="#"):
    if (aa[0]=='units'):
      conf['units']=aa[1]
      if conf['units']=='imperial':
        unitsFactor=MPH

downScaleQty=4
candidatesQty=downScaleQty*2
liveScheds=getState()
candidatesQty=min(candidatesQty,len(liveScheds))
candidatesQty=max(candidatesQty,8)
selected=[]
maps=initMAPs()
simID=r.get("simID")
#exits=r.lrange(simID+":exits",0,-1)
loopPick=True
cnt=0
scalingEvent={}
scalingEvent['type']='downScale'
scalingEvent['desired']=downScaleQty
scalingEvent['id']=str(uuid.uuid4())
scalingEvent['time']=r.get("elapsed")
scalingEvent['simID']=simID
while loopPick==True:
#  print "ITERATION "+str(cnt)
  for m in maps:
    dl=distances(m)
#    print dl
    if candidatesQty>0:
      alreadyPicked.append(dl[0]['from']) 
      candidatesQty=candidatesQty-1
    else:
      loopPick=False
  cnt=cnt+1

print alreadyPicked

cnt=0
for a in alreadyPicked:
  exits=getExitsForSched(a)
  if exits is not None:
    cnt=cnt+1
    candidate={}
    candidate['name']=a
#    candidate['order']=exits[0]['name']+':'+exits[0]['direction']
    candidate['sigName']=exits[0]['name']
    candidate['sigDir']=exits[0]['direction']
    if cnt<=downScaleQty:
      selected.append(candidate)
print selected
scalingEvent['set']=len(selected)
print scalingEvent

for e in selected:
  rs=urllib2.urlopen('http://127.0.0.1:4999/v1/update/schedule/'+e['name']+'/'+e['sigName']+'/'+e['sigDir']+'/'+scalingEvent['time'])
  sched=json.loads(rs.read())
  print "RES:"
  print sched

def mainLoop():
  global liveScheds
  global elapsed
  global srvs
  while True:
    elapsed=r.get("elapsed")
    if elapsed is not None:
      elapsed=int(elapsed)
      liveScheds=getState()
      print elapsed
    else:
       print "lost connection to redis...retrying..."
    time.sleep(WAKEINTERVAL)

#mainLoop()
