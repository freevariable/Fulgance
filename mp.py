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
import math
import sys
r=redis.StrictRedis(host='localhost', port=6379, db=0)
r.flushall()

#AIRFACTOR=(0.2/400.0)
WHEELFACTOR=0.00245
#WHEELFACTOR=0.0
ACCSIGMA=0.27
ACC=1.35 # m/s2  au demarrage
VPOINT=29.0 # speed in km/h at which acc starts to fall
ALAW=1   # law governing acc between vpoint and vmx
         # 1 is linear
WEIGHT=143000.0   #in kg
POWER=2000000.0 #in W
POWERWEIGHT=POWER/WEIGHT
VMX=80.0   #km/h  max speed
VMX2=(VMX*VMX)/12.96  # VMX squared, in m/s
AIRFACTOR=0.68/VMX2
VMXROOT=math.pow(VMX,0.3)
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
G=9.81  # N/kg

tivs={}
stas={}
sigs={}
trss={}
trs={}
segs={}
ncyc=0
t=0.0
maxLine=160.0
exitCondition=False
projectDir='testTrack/'
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
    for s in ssf:    # FIRST pass for type 1 and type 2 sigs
      redisSIG=""
      if (s[0]!='#'):
        s=s.rstrip().split(" ")
        if (len(s)<=2):
          s.append('1')   # this is a type 1 sig by default
          redisSIG="green"
        else:
          if (s[2]=='1'):    # type 1
            redisSIG="green"
          elif (s[2]=='2'):   #type 2
            redisSIG="red"
            if (len(s)!=6):
              print "FATAL: type 2 sig requires 3 x verb:noun"
              print s
              print len(s)
              sys.exit()
            verbnoun=s[3].split(":") 
            if verbnoun[0]=="Reverse":
              print "switch:"+s[1]+" reverse set to: "+verbnoun[1]
#              k=r.get("switch:"+s[1]+":reversePosition")
#              if (k is None):
              r.set("switch:"+s[1]+":reversePosition",verbnoun[1])
            else:
              print "FATAL: unkwnown Verb "+ verbnoun[0]+". Reverse was expected."
              sys.exit()
            verbnoun=s[4].split(":")
            if verbnoun[0]=="Forward":
              print "switch:"+s[1]+" forward set to: "+verbnoun[1]
              r.set("switch:"+s[1]+":forwardPosition",verbnoun[1])
            else:
              print "FATAL: unkwnown Verb "+ verbnoun[0]
              sys.exit()
            verbnoun=s[5].split(":")
            if verbnoun[0]=="Default":
              print "switch:"+s[1]+" default set to: "+verbnoun[1]
              r.set("switch:"+s[1]+":defaultPosition",verbnoun[1])
            else:
              print "FATAL: unkwnown Verb "+ verbnoun[0]
              sys.exit()
            r.set("switch:"+s[1]+":isLocked",False)
        if (len(redisSIG)>2):
          r.set("sig:"+se+":"+s[1],redisSIG)
        ss.append(s)
        cnt=cnt+1  
    prevs=None
    print "______"+se+"_______"
    cnt=0
    for s in ss:    # SECOND PASS
      aligned=False
      if (s[2]=='2'):
        k=r.get("switch:"+s[1]+":defaultPosition")       
        print "switch of sig "+s[1]+" is in position "+k
        if (k==se):
          print "  switch of sig "+s[1]+" is aligned to segment"
          aligned=True
        if (cnt<len(ss)-1):
          print "  switch of sig "+s[1]+" has a next sig: "+ss[cnt+1][1]+" of type: "+ss[cnt+1][2]
          if (ss[cnt+1][2]!='5'):
            print "FATAL: a sig type 2 must be followed by a type 5!"
            sys.exit()
          else:
            k1=r.get("sig:"+se+":"+ss[cnt+1][1])
            if k1 is None:
              if (aligned==True):
                r.set("sig:"+se+":"+ss[cnt+1][1],"green")
              else:
                r.set("sig:"+se+":"+ss[cnt+1][1],"red")
            k1=r.get("sig:"+se+":"+ss[cnt+1][1])       
            print "  follower color set to: "+k1
        else:
          print "  (switch has no succ)"
        if prevs is not None:
          print "  switch of sig "+s[1]+" has a prev sig: "+prevs[1]+" of type: "+prevs[2]
          r.set("switch:"+s[1]+":forwardPrevSig",cnt-1)
          if (prevs[2]!='3'):
            print "FATAL: a sig type 2 must be preceded by a type 3 or no sig!"
            sys.exit()
          else:
            k1=r.get("sig:"+se+":"+prevs[1])       
            if k1 is None:
              if (aligned==True):
                r.set("sig:"+se+":"+prevs[1],"yellow")
              else:
                r.set("sig:"+se+":"+prevs[1],"red")
            k1=r.get("sig:"+se+":"+prevs[1])       
            print "  prev color set to: "+k1
        else:
          print "  (switch has no prev)"
      elif (s[2]=='5'):
        print s
      prevs=s
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
  grade=0.0  # percentage
  gradient=0.0 # angle of inclination, in radian
  power=0.0
  m=WEIGHT

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
#    self.gradient=math.atan(self.grade/100.0)
    self.gradient=self.grade/100.0    #good approx even for gred 2.5%
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
#    self.maxVk=min(maxLine,VMX)
    self.maxVk=maxLine
    self.PK=self.x
    self.aGaussRamp=aGauss()
    self.aFull=0.0
    self.v=0.0
    self.vK=0.0
    self.nv=0.0
    self.cv=0.0
    self.a=availableAcc(self.v)+self.aGaussRamp
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
    updateSIGbyTrOccupation(initSegment,self.SIGcnt-1,self.name,"red")

  def step(self):
    global t
    global exitCondition
#    if (ncyc%CYCLE==0):
#      print self.name+":t:"+str(t)+":x:"+str(self.x)
    gFactor=G*self.gradient
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
      updateSIGbyTrOccupation(self.segment,self.SIGcnt-1,self.name,"red")
      if (self.SIGcnt<len(sigs[self.segment])-1):
        self.SIGcnt=self.SIGcnt+1 
        self.nextSIG=sigs[self.segment][self.SIGcnt] 
        print self.name+":t:"+str(t)+"next SIG ("+self.nextSIG[1]+") at PK"+self.nextSIG[0]
        self.nSIGx=1000.0*float(self.nextSIG[0])
      else:
        if (sigs[self.segment][self.SIGcnt][2]=='2'):
          print self.name+":t:"+str(t)+"Buffer reached. Initiating reverse sequence" 
        else:
          print self.name+":t:"+str(t)+"FATAL: no more SIG..." 
          sys.exit()
    if (self.x>=(self.nSTAx)):
#      print "AT STA stop data:"+" vK:"+str(self.vK)+" aFull:"+str(self.aFull)
      if (self.vK>3.0):
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
        self.a=availableAcc(self.v)+self.aGaussRamp
      if (self.maxVk<self.vK):
        print self.name+":t:"+str(t)+":vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to dcc"
        self.a=DCC
    if (self.a>0.0):
      if (self.vK>self.maxVk*VTHRESH):
        print self.name+":t:"+str(t)+":coasting at "+str(self.vK)
        self.a=0.0
      else:
        if (self.vK<=(self.maxVk*VTHRESH)):
          if (ALAW==1):
            self.a=availableAcc(self.v)#+self.aGaussRamp
            if (ncyc%CYCLE==0):
              print "need to go faster..."+str(self.a)
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
      if ((self.vK>4.0) and (self.vK<0.965*self.maxVk)):
        print self.name+":t:"+str(t)+":boosting from vK:"+str(self.vK)+" to maxVk:"+str(self.maxVk)+" with aFull:"+str(self.aFull)
        self.a=availableAcc(self.v)+aGauss()
#          else:
#            print str(t)+":not boosting vK:"+str(vK)+" to maxVk:"+str(maxVk)
    vSquare=self.v*self.v
    factors=(AIRFACTOR*vSquare)#+(WHEELFACTOR*self.v)#+G*self.gradient
    mv=self.m*self.v
    if (self.a>0.0):
      self.aFull=self.a-factors
      if (self.aFull<0.0):
        self.aFull=0.0 
    else:
#      self.aFull=self.a+factors
     self.aFull=self.a
     if (self.aFull>0.0):
       self.aFull=0.0 
    self.aFull=self.aFull-gFactor
    self.v=self.v+(self.aFull/CYCLE)
    self.vK=self.v*3.6
    self.x=self.x+(self.v/CYCLE)
    self.PK=self.x/1000.0
    if (ncyc%CYCLE==0):
      if (self.a>=0.0):
#        self.power=mv*self.a+self.v*factors+mv*G*math.sin(self.gradient)
        self.power=mv*self.a
      else:
#        self.power=self.v*factors+mv*G*math.sin(self.gradient)
        self.power=0.0
      print self.name+":t:"+str(t)+" State update PK:"+str(self.PK)+" vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" aF:"+str(self.aFull)+" a:"+str(self.a)+" power: "+str(self.power)+" factors: "+str(factors)+" gFactor:"+str(gFactor)+" vSquare:"+str(vSquare)+" AIRFACTOR: "+str(AIRFACTOR)
    if (self.inSta==True):
      if (t>self.waitSta):
        self.inSta=False
        self.waitSta=0.0
        self.a=availableAcc(self.v)+aGauss()
        print self.name+":t:"+str(t)+":OUT STA, a:"+str(self.a)
    if (self.atSig==True):
      if (t>self.sigPoll):
        k=r.get(self.sigToPoll)
        print self.name+":t:"+str(t)+" waiting at sig..."+self.sigToPoll+" currently:"+k
        if (k=="red"):
          self.sigPoll=t+SIGPOLL
        else:
          self.atSig=False
          self.a=availableAcc(self.v)+aGauss()
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

def updateSIGbyTrOccupation(seg,SIGcnt,name,state):
  global sigs
  redisSIG="sig:"+seg+":"+sigs[seg][SIGcnt][1]
  SIGtype=sigs[seg][SIGcnt][2]
  k=r.get(redisSIG)
  print "(Tr occup attempt update SIG "+redisSIG+" from value "+k+" to value "+state+")"
  if (k==state):
    print "ALREADY"
    return True
  if (SIGtype=='1'):
    if (state=="red"):
      if (SIGcnt>=1):
        updateSIGbyTrOccupation(seg,SIGcnt-1,name,"yellow")
      if (SIGcnt>=2):
        updateSIGbyTrOccupation(seg,SIGcnt-2,name,"green")
      print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
      r.set(redisSIG,state)
    elif (state=="yellow"):
       if (k=="green"):
         print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
         r.set(redisSIG,state)
       if (k=="red"):
         print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
         r.set(redisSIG,state)
    elif (state=="green"):
       if (k=="yellow"):
         print "SIG "+sigs[seg][SIGcnt][1]+" was "+k+" now "+state
         r.set(redisSIG,state)
  if (SIGtype=='5'):
    if (state=="red"):
      if (SIGcnt>=1):
        prevRedisSIG="sig:"+seg+":"+sigs[seg][SIGcnt-1][1]
        r.set("switch:"+sigs[seg][SIGcnt-1][1]+":isLocked",True)
#        print prevRedisSIG
#        print r.get("switch:"+sigs[seg][SIGcnt-1][1]+":isLocked")
        fw=r.get("switch:"+sigs[seg][SIGcnt-1][1]+":forwardPosition")
        prevNum=r.get("switch:"+sigs[seg][SIGcnt-1][1]+":forwardPrevSig")
        prevNum=int(prevNum)
        prevSig=r.get("sig:"+fw+":"+sigs[fw][prevNum][1])
        print "need to update "+sigs[fw][prevNum][1]+" the previous signal 3 on the other segment..."
        print prevSig
        sys.exit()

def availableAcc(v):
  if (v<0.1): 
    return ACC
  aux1=POWERWEIGHT/v
  if (ACC>aux1):
    return aux1
  return ACC

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
#for k in r.scan_iter("switch:*"):
#  print k+":"+r.get(k)
