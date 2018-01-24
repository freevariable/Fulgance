#!/usr/bin/python
#Copyright 2018 freevariable (https://github.com/freevariable)

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import redis
import random
#import curses
import sys
r=redis.StrictRedis(host='localhost', port=6379, db=0)
r.set('foo','bar')

RESFACTOR=0.2
ACCSIGMA=0.27
ACC=1.35 # m/s2  au demarrage
VPOINT=29.0 # speed in km/h at which acc starts to fall
ALAW=1   # law governing acc between vpoint and vmx
         # 1 is linear
WEIGHT=143.0   #in tons
POWER=2000 #in kW
VMX=80.0   #km/h  max speed
DCC=-1.50  #m/s2 at tpoint
DLAW=1    # law governing dcc between t=0 and t=tpoint
          # 1 is linear
CYCLE=200 # number of time per sec calc must be made
             # increasing cycle beyond 200 does not improve precision by more that 1 sec for the end-to-end journey
X0=9800.0
T0=0.0
TLEN=X0+16876.0   # track length in m
VTHRESH=0.999
REALTIME="SIG"    # two mutually exclusive values: SIG or TVM
WAITTIME=10.0   # average wait in station (in sec)
SIGPOLL=1.0   # check for sig clearance (in sec)

tivs={}
stas={}
sigs={}
trss={}
trs={}
segs={}
ncyc=0
t=0.0
maxLine=60.0
exitCondition=False
projectDir='default/'
schedulesDir='schedules/'
segmentsDir='segments/'

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

def initTIVs():
  global segs
  gts={}
  for se in segs:
    f=open(projectDir+segmentsDir+se+"/TIVs.txt","r")
    tsf=f.readlines()
    ts=[]
    f.close()
    cnt=0
    for t in tsf:
      if (t[0]!='#'):
        t=t.rstrip().split(" ")
        ts.append(t)
        cnt=cnt+1  
    gts[se]=ts
  return gts

def initSchedule():
    f=open(projectDir+schedulesDir+"default.txt","r")
    tsf=f.readlines()
    ts=[]
    f.close()
    cnt=0
    for t in tsf:
      if (t[0]!='#'):
        t=t.rstrip().split(" ")
        ts.append(t)
        cnt=cnt+1  
    return ts

def initSTAs():
  global segs
  gts={}
  for se in segs:
    f=open(projectDir+segmentsDir+se+"/STAs.txt","r")
    ssf=f.readlines()
    ss=[]
    f.close()
    cnt=0
    for s in ssf:
      if (s[0]!='#'):
        s=s.rstrip().split(" ")
        ss.append(s)
        cnt=cnt+1  
    gts[se]=ss
  return gts

def initSIGs():
  global segs
  gts={}
  for se in segs:
    f=open(projectDir+segmentsDir+se+"/SIGs.txt","r")
    ssf=f.readlines()
    ss=[]
    f.close()
    cnt=0
    for s in ssf:
      redisSIG=""
      if (s[0]!='#'):
        s=s.rstrip().split(" ")
        if (len(s)<=2):
          s.append('1')
          redisSIG="green"
        else:
          if (s[2]=='1'):
            redisSIG="green"
          elif (s[2]=='2'):
            redisSIG="red"
          elif (s[2]=='3'):
            redisSIG="yellow"
        r.set("sig:"+se+":"+s[1],redisSIG)
        ss.append(s)
        cnt=cnt+1  
    gts[se]=ss
  return gts

def initAll():
  random.seed()
  global tivs
  global stas
  global sigs
  global trss
  global trs
  global segs
  segs=initSEGs()
  tivs=initTIVs()
#  print tivs
  stas=initSTAs()
#  print stas
  sigs=initSIGs()
#  print sigs
  trss=initSchedule()
  print trss
  cnt=0
  for aa in trss:
#    if (cnt>=1):
#      break
    if ((aa[0]!="#") and (cnt==0)):
      found=False
      for asi in sigs[aa[1]]:
         if asi[1]==aa[2]:
           aPos=1000.0*float(asi[0])
      trs=Tr(aa[0],aa[1],aPos,float(aa[3]))
      #print "aa0:"+aa[0]+" aa1:"+str(aa[1])+" aa2:"+str(aa[2])
    else:
      if (aa[0]!="#"):
        found=False
        for asi in sigs[aa[1]]:
           if asi[1]==aa[2]:
             aPos=1000.0*float(asi[0])
        aT=Tr(aa[0],aa[1],aPos,float(aa[3]))
        trs.append(aT)
    cnt=cnt+1 

class Tr:
  BDtiv=0.0  #breaking distance for next TIV
  BDsta=0.0  #fornext station
  DBrt=0.0  #for next realtime event (sig or tvm)
  TIVcnt=0
  STAcnt=0
  SIGcnt=0
  name=''
  nextSTA=''
  nextSIG=''
  nextTIV=''
  nSTAx=0.0
  nSIGx=0.0
  nTIVx=0.0
  nTIVvl=0.0
  cTIVvl=0.0
  nTIVtype=''
  maxVk=0.0
  initPos=0.0
  PK=0.0
  aGaussRamp=0.0
  aFull=0.0
  a=0.0
  v=0.0
  x=0.0
  nv=0.0
  cv=0.0
  vK=0.0
  tBreak=0.0
  deltaBDtiv=0.0
  deltaBDsta=0.0
  advTIV=-1.0
  staBrake=False
  sigBrake=False
  sigPoll=0.0
  sigToPoll=''
  inSta=False
  atSig=False
  waitSta=0.0
  BDzero=0.0
  segment=''

  def append(self,aTr):
    self.trs.append(aTr)
  def __iter__(self):
    yield self
    for t in self.trs:
      for i in t:
        yield i
  def __init__(self,name,initSegment,initPos,initTime):
    print "init..."+name+" at pos "+str(initPos)+" and t:"+str(initTime)
    self.trs=[]
    self.x=initPos
    self.name=name
    self.segment=initSegment
    self.BDtiv=0.0  #breaking distance for next TIV
    self.BDsta=0.0  #fornext station
    self.DBrt=0.0  #for next realtime event (sig or tvm)
    self.TIVcnt=findMyTIVcnt(initPos,initSegment)
    print self.name+":t:"+str(t)+" My TIVcnt is: "+str(self.TIVcnt)+" based on pos:"+str(initPos)
    self.STAcnt=findMySTAcnt(initPos,initSegment)
    print self.name+":t:"+str(t)+" My STAcnt is: "+str(self.STAcnt)+" based on pos:"+str(initPos)
    self.SIGcnt=findMySIGcnt(initPos,initSegment)
    print self.name+":t:"+str(t)+" My SIGcnt is: "+str(self.SIGcnt)+" based on pos:"+str(initPos)
    self.nextSTA=stas[initSegment][self.STAcnt]
    self.nextSIG=sigs[initSegment][self.SIGcnt]
    self.nSTAx=1000.0*float(self.nextSTA[0])
    self.nSIGx=1000.0*float(self.nextSIG[0])
    self.nextTIV=tivs[initSegment][self.TIVcnt]
    print self.name+":t:"+str(t)+" next TIV at PK"+self.nextTIV[0]+" with limit "+self.nextTIV[1]
    self.nTIVx=1000.0*float(self.nextTIV[0])
    self.nTIVvl=float(self.nextTIV[1])
    self.cTIVvl=0.0
    self.nTIVtype='>>'    # tiv increases speed
    self.maxVk=min(maxLine,VMX)
    self.PK=self.x
    self.aGaussRamp=aGauss()
    self.a=ACC+self.aGaussRamp
    self.aFull=0.0
    self.v=0.0
    self.vK=0.0
    self.nv=0.0
    self.cv=0.0
    self.tBreak=0.0
    self.deltaBDtiv=0.0
    self.deltaBDsta=0.0
    self.advTIV=-1.0
    self.staBrake=False
    self.sigBrake=False
    self.inSta=False
    self.atSig=False
    self.waitSta=0.0
    self.BDzero=0.0
    self.redisSIG="sig:"+self.segment+":"+sigs[self.segment][self.SIGcnt][1]
    self.advSIGcol=r.get(self.redisSIG)
#    print "redisSIG:"+self.redisSIG+" col:"+self.advSIGcol
#    self.redisSIG=''
    self.sigSpotted=False
    updateSIG(initSegment,self.SIGcnt-1,self.name,"red")

  def step(self):
    global t
    global exitCondition
#    if (ncyc%CYCLE==0):
#      print self.name+":t:"+str(t)+":x:"+str(self.x)
    self.BDzero=-(self.v*self.v)/(2*DCC)
    if ((self.staBrake==False) and (self.x>=(self.nSTAx-self.BDzero))):
      print self.name+":t:"+str(t)+":ADVANCE STA vK:"+str(self.vK)
      self.staBrake=True
      self.a=DCC#+aGauss()
    if ((self.staBrake==True) and (self.vK<=0.8)):
      self.a=-0.004
    if ((self.sigSpotted==False) and (self.x>=(self.nSIGx-self.BDzero))):
      self.redisSIG="sig:"+self.segment+":"+sigs[self.segment][self.SIGcnt][1]
      self.advSIGcol=r.get(self.redisSIG)
      print self.name+":t:"+str(t)+":ADVANCE "+self.advSIGcol+" SIG vK:"+str(self.vK)
      self.sigSpotted=True
      if (self.advSIGcol=="red"):
        self.a=DCC#+aGauss()
        self.sigBrake=True
    if ((self.sigBrake==True) and (self.vK<=0.7)):
      self.a=-0.004
    if (self.x>=(self.nSIGx)):
      if (self.sigSpotted==True):
        self.sigSpotted=False
      if (self.sigBrake==True):
        self.sigBrake=False
#        print "AT SIG stop data:"+" vK:"+str(self.vK)+" aFull:"+str(self.aFull)
        if (self.vK>1.0):
          print "FATAL at SIG"
          sys.exit()
        self.a=0.0
        self.v=0.0
        self.vK=0.0
        self.atSig=True
        self.sigPoll=t+SIGPOLL
        self.sigToPoll="sig:"+self.segment+":"+sigs[self.segment][self.SIGcnt][1]
      print self.name+":t:"+str(t)+":AT SIG "+self.nextSIG[1]+" vK:"+str(self.vK)
      updateSIG(self.segment,self.SIGcnt-1,self.name,"red")
      if (self.SIGcnt<len(sigs[self.segment])-1):
        self.SIGcnt=self.SIGcnt+1 
        self.nextSIG=sigs[self.segment][self.SIGcnt] 
        print self.name+":t:"+str(t)+"next SIG ("+self.nextSIG[1]+") at PK"+self.nextSIG[0]
        self.nSIGx=1000.0*float(self.nextSIG[0])
      else:
        print self.name+":t:"+str(t)+"no more SIG..." 
    if (self.x>=(self.nSTAx)):
#      print "AT STA stop data:"+" vK:"+str(self.vK)+" aFull:"+str(self.aFull)
      if (self.vK>1.0):
        print "FATAL at STA"
        sys.exit()
      self.a=0.0
      self.v=0.0
      self.vK=0.0
      self.inSta=True
      self.waitSta=t+WAITTIME
      self.staBrake=False 
      print self.name+":t:"+str(t)+":IN STA "+self.nextSTA[1]+" vK:"+str(self.vK)
      if ((self.nextSTA[1]=='W') or (self.nextSTA[1]=='E')):
        exitCondition=True
      else:
        self.STAcnt=self.STAcnt+1 
        self.nextSTA=stas[self.segment][self.STAcnt] 
        print self.name+":t:"+str(t)+":next STA ("+self.nextSTA[1]+") at PK"+self.nextSTA[0]
        self.nSTAx=1000.0*float(self.nextSTA[0])
    if (self.nTIVtype=='<<'):
      self.deltaBDtiv=self.BDtiv
    else:
      self.deltaBDtiv=0.0
    if ((self.advTIV>0.0) and (self.x>=self.advTIV)):
      self.advTIV=-1.0
      print self.name+":t:"+str(t)+":TIV "+str(self.TIVcnt-1)+" reached at curr speed "+str(self.vK)+", maxVk now "+str(self.maxVk)
    if (self.x>=self.nTIVx-self.deltaBDtiv):
      self.maxTIV=self.nTIVvl
      self.maxVk=min(self.maxTIV,maxLine,VMX)
      if (self.nTIVtype=='<<'):
        print self.name+":t:"+str(t)+":ADVANCE TIV "+str(self.TIVcnt)+" reached at curr speed "+str(self.vK)+", maxVk will be "+str(self.maxVk)
        self.advTIV=self.nTIVx
      else:
        print self.name+":t:"+str(t)+":TIV "+str(self.TIVcnt)+" reached at curr speed "+str(self.vK)+", maxVk now "+str(self.maxVk)
      self.TIVcnt=self.TIVcnt+1
      self.nextTIV=tivs[self.segment][self.TIVcnt]
      self.cTIVvl=self.nTIVvl
      self.nTIVx=1000.0*float(self.nextTIV[0])
      self.nTIVvl=float(self.nextTIV[1])
      if (self.nTIVvl>self.cTIVvl):
        self.nTIVtype='>>'
      else:
        self.nTIVtype='<<'  # next TIV decreases speed
        self.nv=self.nTIVvl/3.6
        self.cv=self.cTIVvl/3.6
        self.BDtiv=((self.nv*self.nv)-(self.cv*self.cv))/(2*DCC)
        self.BDtiv=1.5*self.BDtiv   # safety margin
      print self.name+":t:"+str(t)+"  next TIV at PK"+self.nextTIV[0]+" with limit "+self.nTIVtype+self.nextTIV[1]+" (currspeed:"+str(self.vK)+")"
      if (self.nTIVvl<self.cTIVvl):
        print self.name+":t:"+str(t)+"  BDtiv: "+str(self.BDtiv)
      if ((self.staBrake==False) and (self.sigBrake==False) and (self.maxVk>self.vK)):
        print self.name+":t:"+str(t)+":vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to acc" 
        self.aGaussRamp=aGauss()
        self.a=ACC+self.aGaussRamp
      if (self.maxVk<self.vK):
        print self.name+":t:"+str(t)+":vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to dcc"
        self.a=DCC
    if (self.a>0.0):
      if (self.vK>self.maxVk*VTHRESH):
        print self.name+":t:"+str(t)+":coasting at "+str(self.vK)
        self.a=0.0
      elif (self.vK<=VPOINT):
        nop='nop'
      else:
        if (self.vK<=(self.maxVk*VTHRESH)):
          if (ALAW==1):
            self.a=0.1+(ACC)*(1.0-(self.vK/self.maxVk))
#            if (ncyc%1000==0):
#              print str(t)+" ACCLAW vK:"+str(vK)+" maxVk:"+str(maxVk)+" aF:"+str(aFull)+" a:"+str(a)
          else:
            self.a=0.0
            print "ALAW unknown"
        else:
#          print str(t)+":coasting at "+str(vK)
          self.a=0.0 
    elif (self.a<0.0):
      if ((self.staBrake==False) and (self.sigBrake==False) and (self.vK<self.maxVk)):
        self.a=0.0
#        print str(t)+":coasting at "+str(vK)
    else:  # a=0.0
      if (ncyc%1000==0):
        if (self.inSta==False):
          print str(t)+" COCO vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" aF:"+str(self.aFull)+" a:"+str(self.a)
      if ((self.vK>4.0) and (self.vK<0.965*self.maxVk)):
        print self.name+":t:"+str(t)+":boosting from vK:"+str(self.vK)+" to maxVk:"+str(self.maxVk)+" with aFull:"+str(self.aFull)
        self.a=ACC+aGauss()
#          else:
#            print str(t)+":not boosting vK:"+str(vK)+" to maxVk:"+str(maxVk)
    self.aFull=self.a-(RESFACTOR*self.v*self.v/400)
#    aFull=a
    self.v=self.v+(self.aFull/CYCLE)
    self.vK=self.v*3.6
#    t=ncyc/CYCLE
    self.x=self.x+(self.v/CYCLE)
    self.PK=self.x/1000.0
    if (self.inSta==True):
      if (t>self.waitSta):
        self.inSta=False
        self.waitSta=0.0
        self.a=ACC+aGauss()
        print self.name+":t:"+str(t)+":OUT STA, a:"+str(self.a)
    if (self.atSig==True):
      if (t>self.sigPoll):
        k=r.get(self.sigToPoll)
        print self.name+":t:"+str(t)+" waiting at sig..."+self.sigToPoll+" currently:"+k
        if (k=="red"):
          self.sigPoll=t+SIGPOLL
        else:
          self.atSig=False
          self.a=ACC+aGauss()
          print self.name+":t:"+str(t)+":OUT SIG, a:"+str(self.a)
  
def aGauss():
  return random.gauss(0.0,ACCSIGMA)

def findMySTAcnt(x,seg):
  global stas
  xK=x/1000.0
  cnt=0
  found=False
  for ast in stas[seg]:
    if float(ast[0])>=xK:
      break
    cnt=cnt+1
  return cnt

def findMySIGcnt(x,seg):
  global sigs
  xK=x/1000.0
  cnt=0
  found=False
  for asi in sigs[seg]:
    if float(asi[0])>=xK:
      break
    cnt=cnt+1
  return cnt

def findMyTIVcnt(x,seg):
  global tivs
  xK=x/1000.0
  cnt=0
  found=False
  for ati in tivs[seg]:
    if float(ati[0])>=xK:
      break
    cnt=cnt+1
  return cnt

def updateSIG(seg,SIGcnt,name,state):
  global sigs
  redisSIG="sig:"+seg+":"+sigs[seg][SIGcnt][1]
  SIGtype=sigs[seg][SIGcnt][2]
  k=r.get(redisSIG)
  print "(update SIG "+redisSIG+" from value "+k+" to value "+state+")"
  if (k==state):
    print "ALREADY"
    return True
  if (state=="red"):
#    print redisSIG+" "+k 
    if (SIGcnt>=1):
      updateSIG(seg,SIGcnt-1,name,"yellow")
    if (SIGcnt>=2):
      updateSIG(seg,SIGcnt-2,name,"green")
    print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
    r.set(redisSIG,state)
  elif (state=="yellow"):
     if ((SIGtype=='1') and (k=="green")):
       print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
       r.set(redisSIG,state)
     if ((SIGtype=='1') and (k=="red")):
       print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
       r.set(redisSIG,state)
  elif (state=="green"):
     if ((SIGtype=='1') and (k=="yellow")):
       print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
       r.set(redisSIG,state)

initAll()
for aT in trs:
  print aT.name+" has been initialized"

while (exitCondition==False):
  t=ncyc/CYCLE
  for aT in trs:
    aT.step()
  if (t>3500):
    exitCondition=True
  ncyc=ncyc+1
#for k in r.scan_iter("sig:*"):
#  print k+":"+r.get(k)
