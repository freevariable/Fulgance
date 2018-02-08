#!/usr/bin/python -O
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

import redis,random,math,sys
import time,getopt
r=redis.StrictRedis(host='localhost', port=6379, db=0)
r.flushall()

G=9.81  # N/kg
MULTICORE=False
CORES=1
WHEELFACTOR=G*0.025
DUMPDATA=True
TPROGRESS=False
STAPROGRESS=False
GSENSITIVITY=6.03   # sensitivity to grade
ACCSIGMA=0.027
ACC=1.35 # m/s2  au demarrage
ALAW=1   # law governing acc between vpoint and vmx
         # 1 is linear
WEIGHT=143000.0   #in kg
POWER=2000000.0 #in W
POWERWEIGHT=POWER/WEIGHT
VMX=80.0   #km/h  max speed
VMX2=(VMX*VMX)/12.96  # VMX squared, in m/s
AIRFACTOR=0.68/VMX2
VMXROOT=math.pow(VMX,0.3)
TLENGTH=90.0  #length in m
DCC=-1.10  #m/s2
EMR=-1.80   #m/s2 emergency dcc
DLAW=1    # law governing dcc between t=0 and t=tpoint
          # 1 is linear
SYNCPERIOD=0.5 # how often (in s) do we sync multicores
CYCLEPP=100    # how many ticks we calculate between two multicore syncs
CYCLE=CYCLEPP/SYNCPERIOD # how many ticks we calculate per second 
             # increasing cycle beyond 200 does not improve precision by more that 1 sec for the end-to-end journey
T0=0.0
VTHRESH=0.999
CONTROL="SIG"    # two mutually exclusive values: SIG or TVM
REALTIME=False
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
maxLine=160.0    # max speed allowed on a line, km/h
jumpseat=''
exitCondition=False
projectDir='ParisLine1/'
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
    f=open(projectDir+schedulesDir+scheduleName,"r")
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
              if not __debug__:
                print "switch:"+s[1]+" reverse set to: "+verbnoun[1]
              r.set("switch:"+s[1]+":reversePosition",verbnoun[1])
            else:
              print "FATAL: unkwnown Verb "+ verbnoun[0]+". Reverse was expected."
              sys.exit()
            verbnoun=s[4].split(":")
            if verbnoun[0]=="Forward":
              if not __debug__:
                print "switch:"+s[1]+" forward set to: "+verbnoun[1]
              r.set("switch:"+s[1]+":forwardPosition",verbnoun[1])
            else:
              print "FATAL: unkwnown Verb "+ verbnoun[0]
              sys.exit()
            verbnoun=s[5].split(":")
            if verbnoun[0]=="Default":
              if not __debug__:
                print "switch:"+s[1]+" current set to: "+verbnoun[1]
              r.set("switch:"+s[1]+":position",verbnoun[1])
            else:
              print "FATAL: unkwnown Verb "+ verbnoun[0]
              sys.exit()
            r.set("switch:"+s[1]+":isLocked",False)
        if (len(redisSIG)>2):
          r.set("sig:"+se+":"+s[1],redisSIG)
#          k=r.get("sig:"+se+":"+s[1])
#          print "sig:"+se+":"+s[1]+" "+str(k)
        ss.append(s)
        cnt=cnt+1  
    prevs=None
    if not __debug__:
      print "______"+se+"_______"
    cnt=0
    for s in ss:    # SECOND PASS
      aligned=False
      if (s[2]=='2'):
        k=r.get("switch:"+s[1]+":position")       
        if not __debug__:
          print "switch of sig "+s[1]+" is in position "+k
        if (k==se):
          if not __debug__:
            print "  switch of sig "+s[1]+" is aligned to segment"
          aligned=True
        if (cnt<len(ss)-1):
          if not __debug__:
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
 #           print "  follower color set to: "+k1
        else:
          if not __debug__:
            print "  (switch has no succ)"
        if prevs is not None:
          if not __debug__:
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
            if not __debug__:
              print "  prev color set to: "+k1
        else:
          if not __debug__:
            print "  (switch has no prev)"
#      elif (s[2]=='5'):
#        print s
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
  global jumpseat
  global r
  r.set('realtime:',REALTIME)
  if multi:
    r.set('multi:',numCores)
  segs=initSEGs()
  tivs=initTIVs()
  stas=initSTAs()
  sigs=initSIGs()
  trss=initSchedule()
#  print trss
  cnt=0
  for aa in trss:
    if ((aa[0]!="#") and (cnt==0)):
      found=False
      for asi in sigs[aa[1]]:
         if asi[1]==aa[2]:
           aPos=1000.0*float(asi[0])
      trs=Tr(aa[0],aa[1],aPos,float(aa[3]))
      jumpseat=aa[0]
      r.set("jumpseat:",jumpseat)
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
  trip=0
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
  aGaussFactor=0.0
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
  react=False
  waitSta=0.0
  waitReact=0.0
  BDzero=0.0
  segment=''
  grade=0.0 # percentage
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

  def reinit(self,initSegment,initPos,initTime):
    if not __debug__:
      print "REinit..."+self.name+" at pos "+str(initPos)+" and t:"+str(initTime)
    gFactor=G*self.gradient*GSENSITIVITY
    v2factor=0.0
    factors=gFactor+v2factor+WHEELFACTOR
    self.x=initPos
    self.trip=self.trip+1
    self.coasting=False
    self.segment=initSegment
    self.BDtiv=0.0  #breaking distance for next TIV
    self.BDsta=0.0  #fornext station
    self.DBrt=0.0  #for next realtime event (sig or tvm)
#    self.gradient=math.atan(self.grade/100.0)
    self.gradient=self.grade/100.0    #good approx even for gred 2.5%
    self.TIVcnt=findMyTIVcnt(initPos,initSegment)
    self.STAcnt=findMySTAcnt(initPos,initSegment)
    self.SIGcnt=findMySIGcnt(initPos,initSegment)
    self.nextSTA=stas[initSegment][self.STAcnt]
    self.nextSIG=sigs[initSegment][self.SIGcnt]
    self.nSTAx=1000.0*float(self.nextSTA[0])
    self.nSIGx=1000.0*float(self.nextSIG[0])
    self.nextTIV=tivs[initSegment][self.TIVcnt]
    if not __debug__:
      print self.name+":t:"+str(t)+" My TIVcnt is: "+str(self.TIVcnt)+" based on pos:"+str(initPos)
      print self.name+":t:"+str(t)+" My STAcnt is: "+str(self.STAcnt)+" based on pos:"+str(initPos)
      print self.name+":t:"+str(t)+" My SIGcnt is: "+str(self.SIGcnt)+" based on pos:"+str(initPos)
      print self.name+":t:"+str(t)+" next TIV at PK"+self.nextTIV[0]+" with limit "+self.nextTIV[1]
    self.nTIVx=1000.0*float(self.nextTIV[0])
    self.nTIVvl=float(self.nextTIV[1])
    self.cTIVvl=0.0
    self.nTIVtype='>>'    # tiv increases speed
    if (self.TIVcnt>0):
      self.maxVk=min(VMX,float(tivs[initSegment][self.TIVcnt-1][1]))
    else:
      self.maxVk=min(maxLine,VMX)
    self.PK=self.x
    self.aGaussFactor=aGauss()
    self.aFull=0.0
    self.v=0.0
    self.vK=0.0
    self.nv=0.0
    self.cv=0.0
    self.a=getAccFromFactorsAndSpeed(factors,self.v)+self.aGaussFactor
    self.tBreak=0.0
    self.deltaBDtiv=0.0
    self.deltaBDsta=0.0
    self.advTIV=-1.0
    self.staBrake=False
    self.sigBrake=False
    self.inSta=False
    self.atSig=False
    self.react=False
    self.waitSta=0.0
    self.waitReact=0.0
    self.BDzero=0.0
    self.redisSIG="sig:"+self.segment+":"+sigs[self.segment][self.SIGcnt][1]
    self.advSIGcol=r.get(self.redisSIG)
    self.sigSpotted=False
    p={}
    p['seg']=self.segment
    p['cnt']=self.SIGcnt
    p['type']=sigs[self.segment][self.SIGcnt][2]
    previousSig=findPrevSIGforOccupation(p)
    updateSIGbyTrOccupation(previousSig,self.name,"red")

  def dumpstate(self):
    r.hmset(self.name,{'t':t,'coasting':self.coasting,'x':self.x,'segment':self.segment,'gradient':self.gradient,'TIV':self.TIVcnt,'SIG':self.SIGcnt,'STA':self.STAcnt,'PK':self.PK,'aFull':self.aFull,'v':self.v,'staBrake':self.staBrake,'sigBrake':self.sigBrake,'inSta':self.inSta,'atSig':self.atSig,'sigSpotted':self.sigSpotted,'maxVk':self.maxVk,'a':self.a,'nextSTA':self.nextSTA,'nextSIG':self.nextSIG,'nextTIV':self.nextTIV,'nTIVtype':self.nTIVtype,'advSIGcol':self.advSIGcol,'redisSIG':self.redisSIG,'vK':self.vK})
#    print r.hgetall(self.name)

  def __init__(self,name,initSegment,initPos,initTime):
    global r
    if not __debug__:
      print "init..."+name+" at pos "+str(initPos)+" and t:"+str(initTime)
    gFactor=G*self.gradient*GSENSITIVITY
    v2factor=0.0
    factors=gFactor+v2factor+WHEELFACTOR
    self.trs=[]
    self.trip=0
    self.coasting=False
    self.x=initPos
    self.name=name
    self.segment=initSegment
    self.BDtiv=0.0  #breaking distance for next TIV
    self.BDsta=0.0  #fornext station
    self.DBrt=0.0  #for next realtime event (sig or tvm)
#    self.gradient=math.atan(self.grade/100.0)
    self.gradient=self.grade/100.0    #good approx even for gred 2.5%
    self.TIVcnt=findMyTIVcnt(initPos,initSegment)
    self.STAcnt=findMySTAcnt(initPos,initSegment)
    self.SIGcnt=findMySIGcnt(initPos,initSegment)
    if (self.STAcnt==0):
       print "FATAL: "+str(self.name)+" must be located at least at PK"+str(float(TLENGTH/1000))+". Currently it is located at PK"+str(initPos)
       sys.exit()
    self.nextSTA=stas[initSegment][self.STAcnt]
    self.nextSIG=sigs[initSegment][self.SIGcnt]

    self.nSTAx=1000.0*float(self.nextSTA[0])
    self.nSIGx=1000.0*float(self.nextSIG[0])
    self.nextTIV=tivs[initSegment][self.TIVcnt]
    if not __debug__:
      print self.name+":t:"+str(t)+" My TIVcnt is: "+str(self.TIVcnt)+" based on pos:"+str(initPos)
      print self.name+":t:"+str(t)+" My STAcnt is: "+str(self.STAcnt)+" based on pos:"+str(initPos)
      print self.name+":t:"+str(t)+" My SIGcnt is: "+str(self.SIGcnt)+" based on pos:"+str(initPos)
      print self.name+":t:"+str(t)+" next TIV at PK"+self.nextTIV[0]+" with limit "+self.nextTIV[1]
    self.nTIVx=1000.0*float(self.nextTIV[0])
    self.nTIVvl=float(self.nextTIV[1])
    self.cTIVvl=0.0
    self.nTIVtype='>>'    # tiv increases speed
    if (self.TIVcnt>0):
      self.maxVk=min(VMX,float(tivs[initSegment][self.TIVcnt-1][1]))
    else:
      self.maxVk=min(maxLine,VMX)
    self.PK=self.x
    self.aGaussFactor=aGauss()
    self.aFull=0.0
    self.v=0.0
    self.vK=0.0
    self.nv=0.0
    self.cv=0.0
    self.a=getAccFromFactorsAndSpeed(factors,self.v)+self.aGaussFactor
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
    facingSig={}
    facingSig['seg']=self.segment
    facingSig['cnt']=self.SIGcnt
    facingSig['type']=sigs[self.segment][self.SIGcnt][2]
    facingSig['name']=sigs[self.segment][self.SIGcnt][1]
    previousSig=findPrevSIGforOccupation(facingSig)
    print self.name+": facing Sig:"+str(facingSig)+" previous Sig:"+str(previousSig)
    self.advSIGcol="red"   # safeguard before we run step()
    self.sigSpotted=False
    sigAlreadyOccupied=r.get("sig:"+previousSig['seg']+":"+previousSig['name']+":isOccupied")
    if sigAlreadyOccupied is not None:
      print "FATAL: "+str(self.name)+" and "+str(sigAlreadyOccupied)+" share the same signal block"
      sys.exit()
    else:
      if (sigs[self.segment][self.SIGcnt][2]=='2'):
        print "FATAL: "+str(self.name)+" is facing a Type 2 signal. It should rather face the next signal (a type 5)"
        sys.exit()    
    r.set("sig:"+previousSig['seg']+":"+previousSig['name']+":isOccupied",self.name)
    updateSIGbyTrOccupation(previousSig,self.name,"red")

  def step(self):
    global t
    global exitCondition
    gFactor=G*self.gradient
    dcc=DCC-gFactor
    gFactor=gFactor*GSENSITIVITY
    vSquare=self.v*self.v
    v2factor=(AIRFACTOR*vSquare)
    factors=v2factor+gFactor+WHEELFACTOR
    mv=self.m*self.v
    if (dcc<DCC):  #since DCC is always negative...
      dcc=DCC
    self.BDzero=-(self.v*self.v)/(2*(dcc))
    if (ncyc%CYCLE==0):
      self.aGaussFactor=aGauss()
#
# STAGE 1 : main acc updates
#
    if ((self.staBrake==False) and (self.x>=(self.nSTAx-self.BDzero))):
      if not __debug__:
        print self.name+":t:"+str(t)+":ADVANCE STA x:"+str(self.nSTAx)+" vK:"+str(self.vK)
      self.staBrake=True
      self.a=dcc-gFactor#+aGauss()
    if ((self.staBrake==True) and (self.vK<=0.8)):
      self.a=-0.004
    elif (self.staBrake==True):
      self.a=dcc
    if ((self.sigSpotted==False) and (self.x>=(self.nSIGx-self.BDzero))):
      self.redisSIG="sig:"+self.segment+":"+sigs[self.segment][self.SIGcnt][1]
      self.advSIGcol=r.get(self.redisSIG)
      if not __debug__:
        print self.name+":t:"+str(t)+":ADVANCE "+self.advSIGcol+" SIG vK:"+str(self.vK)
      self.sigSpotted=True
      if (self.advSIGcol=="red"):
        self.a=dcc#+aGauss()
        self.sigBrake=True
    if ((self.sigBrake==True) and (self.vK<=0.7)):
      self.a=-0.004
    if (self.x>(self.nSIGx)):
      if (self.sigSpotted==True):
        self.sigSpotted=False
      if (self.sigBrake==True):
        self.sigBrake=False
        if (self.vK>6.0):
          print self.name+":t:"+str(t)+" **** FATAL AT SIG "+self.nextSIG[1]+" **** PK:"+str(self.PK)+" vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" aF:"+str(self.aFull)+" a:"+str(self.a)+" power: "+str(self.power)+" v2factor: "+str(v2factor)+" gFactor:"+str(gFactor)+" vSquare:"+str(vSquare)
          sys.exit()
        self.a=0.0
        self.v=0.0
        self.vK=0.0
        self.atSig=True
        self.sigPoll=t+SIGPOLL
        self.sigToPoll="sig:"+self.segment+":"+sigs[self.segment][self.SIGcnt][1]
        if not __debug__:
          print self.name+":t:"+str(t)+" waiting at sig..."+self.sigToPoll
      if not __debug__:
        print self.name+":t:"+str(t)+":AT SIG "+self.segment+":"+self.nextSIG[1]+" vK:"+str(self.vK)
      p={}
      p['seg']=self.segment
      p['cnt']=self.SIGcnt
      p['type']=sigs[self.segment][self.SIGcnt][2]
      previousSig=findPrevSIGforOccupation(p)
#      updateSIGbyTrOccupation(previousSig,self.name,"red")
      if (self.SIGcnt<len(sigs[self.segment])-1):
        self.SIGcnt=self.SIGcnt+1 
        self.nextSIG=sigs[self.segment][self.SIGcnt] 
        if not __debug__:
          print self.name+":t:"+str(t)+"next SIG ("+self.nextSIG[1]+") at PK"+self.nextSIG[0]
        self.nSIGx=1000.0*float(self.nextSIG[0])
      else:
        if (sigs[self.segment][self.SIGcnt][2]=='2'):
          if not __debug__:
            print self.name+":t:"+str(t)+"Buffer reached. Initiating reverse sequence" 
          kCur=r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":position")
          kRev=r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":reversePosition")
          kFor=r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":forwardPosition")
          if not __debug__:
            print "current switch pos: "+str(kCur)
          kOld=kCur
          if (kCur==kFor):
            kCur=kRev
          else:
            kCur=kFor
          if not __debug__:
            print "new switch pos: "+str(kCur)
          r.set("switch:"+sigs[self.segment][self.SIGcnt][1]+":position",kCur)
          r.set("switch:"+sigs[self.segment][self.SIGcnt][1]+":isLocked",True)
          prevNum=int(r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":forwardPrevSig"))
          prevSig=r.get("sig:"+kOld+":"+sigs[self.segment][prevNum][1])
          r.set("sig:"+kOld+":"+sigs[self.segment][prevNum][1],"red")
          if not __debug__:
            print "sig:"+kOld+":"+sigs[self.segment][prevNum][1]+" SET to red"
            print self.name+":delta buffer: "+str(-self.nSIGx+self.x)
          self.reinit(kCur,0.0+TLENGTH-self.nSIGx+self.x,t)
        else:
          print self.name+":t:"+str(t)+"FATAL: no more SIG..." 
          sys.exit()
      updateSIGbyTrOccupation(previousSig,self.name,"red")
    if (self.x>=(self.nSTAx)):
      if (self.vK>6.0):
        print "FATAL at STA"
        sys.exit()
      self.inSta=True
      if STAPROGRESS==True:
        print str(self.name)+','+str(self.trip)+","+str(t)+','+str(self.nextSTA[1])
      self.waitSta=t+WAITTIME
      self.staBrake=False 
      if not __debug__:
        print self.name+":t:"+str(t)+":IN STA "+self.nextSTA[1]+" vK:"+str(self.vK)+" a:"+str(self.a)
      self.a=0.0
      self.v=0.0
      self.vK=0.0
      if ((self.nextSTA[1]=='W') or (self.nextSTA[1]=='E')):
        exitCondition=True
      else:
        if (self.STAcnt<len(stas[self.segment])-1):
          self.STAcnt=self.STAcnt+1 
          self.nextSTA=stas[self.segment][self.STAcnt] 
          if not __debug__:
            print self.name+":t:"+str(t)+":next STA ("+self.nextSTA[1]+") at PK"+self.nextSTA[0]
          self.nSTAx=1000.0*float(self.nextSTA[0])
        else:
          print self.name+":t:"+str(t)+":no more STAS on segment "+self.segment
          self.nSTAx=sys.maxsize
#           exitCondition=True
    if (self.nTIVtype=='<<'):
      self.deltaBDtiv=self.BDtiv
    else:
      self.deltaBDtiv=0.0
    if ((self.advTIV>0.0) and (self.x>=self.advTIV)):
      self.advTIV=-1.0
      if not __debug__:
        print self.name+":t:"+str(t)+":TIV "+str(self.TIVcnt-1)+" reached at curr speed "+str(self.vK)+", maxVk now "+str(self.maxVk)
    if (self.x>=self.nTIVx-self.deltaBDtiv):
      self.maxTIV=self.nTIVvl
      self.maxVk=min(self.maxTIV,maxLine,VMX)
      if (self.nTIVtype=='<<'):
        if not __debug__:
          print self.name+":t:"+str(t)+":ADVANCE TIV "+str(self.TIVcnt)+" reached at curr speed "+str(self.vK)+", maxVk will be "+str(self.maxVk)
        self.advTIV=self.nTIVx
      else:
        if not __debug__:
          print self.name+":t:"+str(t)+":TIV "+str(self.TIVcnt)+" reached at curr speed "+str(self.vK)+", maxVk now "+str(self.maxVk)
      if (self.TIVcnt<len(tivs[self.segment])-1):
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
        if not __debug__:
          print self.name+":t:"+str(t)+"  next TIV at PK"+self.nextTIV[0]+" with limit "+self.nTIVtype+self.nextTIV[1]+" (currspeed:"+str(self.vK)+")"
        if (self.nTIVvl<self.cTIVvl):
          if not __debug__:
            print self.name+":t:"+str(t)+"  BDtiv: "+str(self.BDtiv)
      else:
        self.nTIVx=sys.maxsize
      if ((self.staBrake==False) and (self.sigBrake==False) and (self.maxVk>self.vK)):
        if not __debug__:
          print self.name+":t:"+str(t)+":vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to acc" 
        self.a=10.0 #any arbitrary value as long as it is positive
      if (self.maxVk<self.vK):
        if not __debug__:
          print self.name+":t:"+str(t)+":vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to dcc"
        self.a=-10.0  #any arbitrary value as long as it is neg
#
# STAGE 2 : other acc updates
#
    if (self.advSIGcol=="yellow"):
      auxMaxVk=0.65*self.maxVk
      if ((self.vK>20.0) and (auxMaxVk<self.vK)):
        if not __debug__:
          if (ncyc%CYCLE==0):
            print self.name+":t:"+str(t)+":vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to dcc to "+str(auxMaxVk)+" due to yellow"
        a=-10.0
    else:
      auxMaxVk=self.maxVk
    self.coasting=False
    if (self.a>0.0):
      if ((self.gradient<0.0025) and (self.vK>auxMaxVk*VTHRESH)):
        if not __debug__:
          if (ncyc%CYCLE==0):
            print self.name+":t:"+str(t)+":coasting at "+str(self.vK)
        self.coasting=True
        self.a=0.0
      else:
        if (self.vK<=(auxMaxVk*VTHRESH)):
          if (ALAW==1):
            self.a=getAccFromFactorsAndSpeed(factors,self.v)
            if (self.a>ACC):
              print "FATAL ACC "+str(self.a)
              sys.exit()
            if not __debug__:
              if (ncyc%CYCLE==0):
                print self.name+":t:"+str(t)+":need to go faster..."+str(self.a)
          else:
            self.a=0.0
            print "FATAL: ALAW unknown"
            sys.exit()
        else:
          self.a=0.0 
    elif (self.a<0.0):
      if ((self.staBrake==False) and (self.sigBrake==False) and (self.vK<auxMaxVk)):
        self.a=0.0
      else:
        if (auxMaxVk<self.vK):
          self.a=dcc
    else:  # a=0.0
      if ((self.vK>4.0) and (self.vK<0.910*auxMaxVk)):
        if not __debug__:
          print self.name+":t:"+str(t)+":boosting from vK:"+str(self.vK)+" to maxVk:"+str(auxMaxVk)+" with aFull:"+str(self.aFull)
        self.a=getAccFromFactorsAndSpeed(factors,self.v)+aGauss()
      elif (self.vK>4.0):
        self.coasting=True
        if not __debug__:
          if (ncyc%CYCLE==0):
            print self.name+":t:"+str(t)+":coasting at "+str(self.vK)
#
# STAGE 3 : calculate aFull
#
    if (self.a>=0.0):
      self.aFull=self.a-v2factor-gFactor-WHEELFACTOR
      if (self.aFull<0.0):
        if ((self.v+(self.aFull/CYCLE))<0.0):
          if (self.v>0.0):
            print "FATAL neg speed. aF: "+str(self.aFull)+" vK:"+str(self.vK)+" v:"+str(self.v)
            sys.exit()
          elif (self.v==0.0):   # train is stopped at sig or sta
             self.aFull=0.0
          else:
            print "FATAL neg speed. aF: "+str(self.aFull)+" vK:"+str(self.vK)+" v:"+str(self.v)
            sys.exit()
    else:
      self.aFull=self.a
      if (self.aFull>0.0):
        self.aFull=0.0 
    self.v=self.v+(self.aFull/CYCLE)
    self.vK=self.v*3.6
    self.x=self.x+(self.v/CYCLE)
    self.PK=self.x/1000.0
# 
# STAGE 4 : perform coarse grain calculations
#
    if (ncyc%CYCLE==0):
# here make coarse-grain markers calculation
# power calculation:
      self.power=WEIGHT*self.a*self.v+factors*self.v
      if (self.power<0.0):
        self.power=0.0
      if not __debug__:
        if (realTime==False):
#      if ((self.inSta==False) and (self.atSig==False)):
          print self.name+":t:"+str(t)+" State update PK:"+str(self.PK)+" vK:"+str(self.vK)+" maxVk:"+str(auxMaxVk)+" aF:"+str(self.aFull)+" a:"+str(self.a)+" power: "+str(self.power)+" v2factor: "+str(v2factor)+" gFactor:"+str(gFactor)+" vSquare:"+str(vSquare)+" inSta?"+str(self.inSta)+" STA:"+str(self.nextSTA)+" atSig?"+str(self.atSig)+" SIG:"+str(self.nextSIG)
        if TPROGRESS==True:
          print str(self.name)+','+str(self.trip)+","+str(t)+','+str(self.PK)+","+str(self.vK)+","+str(self.aFull)+","+str(self.power)
    if (self.inSta==True):
      if (t>self.waitSta):
        self.inSta=False
        self.waitSta=0.0
        self.react=True
        self.waitReact=t+longTail(9.3,71.0,7200.0)
#        self.a=getAccFromFactorsAndSpeed(factors,self.v)+aGauss()
        if not __debug__:
          print self.name+":t:"+str(t)+":OUT STA, a:"+str(self.a)+" vK:"+str(self.vK)+", reaction: "+str(self.waitReact-t)
          if ((self.waitReact-t)>10.0):
            print self.name+":t:"+str(t)+":REACTION BURST:"+str(self.waitReact-t)
    if (self.atSig==True):
      if (t>self.sigPoll):
        k=r.get(self.sigToPoll)
#        if (ncyc%CYCLE==0):
#          print self.name+":t:"+str(t)+" waiting at sig..."+self.sigToPoll+" currently:"+k
        if (sigs[self.segment][self.SIGcnt][2]=='2'):  #type 2
          k=r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":isLocked")
          kpos=r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":position")
          if not __debug__:
            print "next SIG is a type 2:"
            print sigs[self.segment][self.SIGcnt]
            print "switch is locked?"+k
            print "switch position:"+str(kpos)
          if (k=="False"):
            r.set("switch:"+sigs[self.segment][self.SIGcnt][1]+":isLocked",True)
            r.set("switch:"+sigs[self.segment][self.SIGcnt][1]+":position",self.segment)
            kpos=r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":position")
            if not __debug__:
              print "switch NEW position:"+str(kpos)
            k=r.get("switch:"+sigs[self.segment][self.SIGcnt][1]+":isLocked")
            if not __debug__:
              print "switch NEW lock:"+str(k=="True")
            r.set(self.sigToPoll,"yellow")           
            self.atSig=False
            self.react=True
            self.waitReact=t+longTail(9.3,71.0,7200.0)
            if not __debug__:
              print self.name+":t:"+str(t)+":OUT SIG, a:"+str(self.a)+", reaction:"+str(self.waitReact-t)
            if ((self.waitReact-t)>10.0):
              print self.name+":t:"+str(t)+":REACTION BURST:"+str(self.waitReact-t)
          else:
            self.sigPoll=t+SIGPOLL
#          self.a=getAccFromFactorsAndSpeed(factors,self.v)+aGauss()
    if (self.react==True):
      if (t>self.waitReact):
        self.react=False
        self.a=getAccFromFactorsAndSpeed(factors,self.v)+aGauss()
        if not __debug__:
          print self.name+":t:"+str(t)+":REACTION, a:"+str(self.a)
        self.waitReact=0.0
  
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

#def findPrevSIGforOccupation(atSigCnt,atSigType,atSigSeg):
def findPrevSIGforOccupation(atSig):
  global sigs
  prevSig={}
  if ((atSig['type']=='1') or (atSig['type']=='2') or (atSig['type']=='3')):
    if ((atSig['type']=='2') and (atSig['cnt']==0)):
      print "FATAL ERROR. Service must be reversed before invoking prevSIG"
      sys.exit()
    prevSig['seg']=atSig['seg']
    prevSig['cnt']=atSig['cnt']-1
    prevSig['type']=sigs[atSig['seg']][prevSig['cnt']][2]
    prevSig['name']=sigs[atSig['seg']][prevSig['cnt']][1]
  elif (atSig['type']=='5'):
    if (sigs[atSig['seg']][atSig['cnt']-1][2]=='2'):
      kRev=r.get("switch:"+sigs[atSig['seg']][atSig['cnt']-1][1]+":reversePosition")
      kFor=r.get("switch:"+sigs[atSig['seg']][atSig['cnt']-1][1]+":forwardPosition")
      kPrevCnt=int(r.get("switch:"+sigs[atSig['seg']][atSig['cnt']-1][1]+":forwardPrevSig"))
      if (atSig['seg']==kRev):
        kOther=kFor
      else:
        kOther=kRev
    print "type 2 "+str(kOther)
    prevSig['seg']=kOther
    prevSig['cnt']=kPrevCnt
    prevSig['type']=sigs[kOther][kPrevCnt][2]
    prevSig['name']=sigs[kOther][kPrevCnt][1]
    print prevSig
  return prevSig

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

def updateSIGbyTrOccupationIf(aSig,name,state,ifState):
  global sigs
  redisSIG="sig:"+aSig['seg']+":"+sigs[aSig['seg']][aSig['cnt']][1]
  k=r.get(redisSIG)
  if (k==ifState):
    updateSIGbyTrOccupation(aSig,name,state)

def updateSIGbyTrOccupation(aSig,name,state):
  global sigs
  redisSIG="sig:"+aSig['seg']+":"+sigs[aSig['seg']][aSig['cnt']][1]
  k=r.get(redisSIG)
  if not __debug__:
    print name+":"+str(t)+":START UPDATE SIG BY OCCU "+redisSIG+" from value "+k+" to value "+state
#  if (k==state):
#    if not __debug__:
#      print "ALREADY"
#    return True
  sigAlreadyOccupied=r.get(redisSIG+":isOccupied")
  if (aSig['type']!='0'):
    if (state=="red"):
      if sigAlreadyOccupied is not None:
        if sigAlreadyOccupied!=name:
          print name+":"+str(t)+":WARN Sig 1 is already occupied "+redisSIG+" by "+sigAlreadyOccupied
          return True
      previousSig=findPrevSIGforOccupation(aSig)
      redisSIGm1="sig:"+previousSig['seg']+":"+sigs[previousSig['seg']][previousSig['cnt']][1]
      km1=r.get(redisSIGm1+":isOccupied")
      if km1 is not None:
        if km1==name:
          r.delete(redisSIGm1+":isOccupied")
          updateSIGbyTrOccupationIf(previousSig,name,"yellow","red")
      previousPreviousSig=findPrevSIGforOccupation(previousSig)
      redisSIGm2="sig:"+previousPreviousSig['seg']+":"+sigs[previousPreviousSig['seg']][previousPreviousSig['cnt']][1]
      km2=r.get(redisSIGm2+":isOccupied")
      if km2 is None:
        if km1 is not None:
          if km1==name:
            updateSIGbyTrOccupationIf(previousPreviousSig,name,"green","yellow")
        else:
          updateSIGbyTrOccupationIf(previousPreviousSig,name,"green","yellow")
      r.set(redisSIG+":isOccupied",name)
    if (state=="yellow"):
      previousSig=findPrevSIGforOccupation(aSig)
      redisSIGm1="sig:"+previousSig['seg']+":"+sigs[previousSig['seg']][previousSig['cnt']][1]
      km1=r.get(redisSIGm1+":isOccupied")
      if km1 is None:
        updateSIGbyTrOccupationIf(previousSig,name,"green","yellow")
    if not __debug__:
      print "SIG "+aSig['name']+" was "+k+" now "+state
    r.set(redisSIG,state)
  if (aSig['type']=='5'):
    prevType2SIG="sig:"+aSig['seg']+":"+sigs[aSig['seg']][aSig['cnt']-1][1]
  k=r.get(redisSIG)
  if (k!=state):
    print "FATAL : "+name+":"+str(t)+":END UPDATE SIG BY OCCU"+redisSIG+" new value "+str(k)
    sys.exit()

def getAccFromFactorsAndSpeed(f,v):
  powerFromFactors=v*f
  availablePower=POWER-powerFromFactors
  if (availablePower<0.0):
    return 0.0
  if (v>0.0):
    acc=availablePower/(WEIGHT*v)
    return min(acc,ACC)
  else:
    return ACC

try:
  opts, args = getopt.getopt(sys.argv[1:], "h:m", ["help", "realtime", "core=","duration=", "route=", "schedule=", "services=","cores="])
except getopt.GetoptError as err:
  print(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)
duration = sys.maxsize 
multi = MULTICORE
numCores= CORES
realTime=REALTIME
core=1
scheduleName="default.txt"
serviceList=[]
for o, a in opts:
  if o == "-m":
    multi = True
  elif o in ("-h", "--help"):
    usage()
    sys.exit()
  elif o in ("--duration"):
    duration = abs(int(a))
  elif o in ("--realtime"):
    realTime=True
  elif o in ("--cores"):
    numCores = int(a)
  elif o in ("--core"):
    core = int(a)
  elif o in ("--route"):
    projectDir = a+'/'
  elif o in ("--schedule"):
    scheduleName = a
  elif o in ("--services"):
    serviceList = a.split(',')
    print serviceList
    sys.exit()
  else:
    assert False, "option unknown"
    sys.exit(2)

initAll()

def scheduler(period,f,*args):
  def g_tick():
    t1 = time.time()
    count = 0
    while True:
      count += 1
      yield max(t1 + count*period - time.time(),0)
  g = g_tick()
  while True:
    time.sleep(next(g))
    f(*args)

def stepRT(s):
  global ncyc
  global trs
  global exitCondition
  global t
  ccc=0
  while (ccc<cycles):
    t=ncyc/CYCLE
    if not __debug__:
      print "RT:"+str(t)
    for aT in trs:
      aT.step()
      if (aT.name==jumpseat):
        aT.dumpstate()
    if (t>duration):
      exitCondition=True
      sys.exit()
    ncyc=ncyc+1
    ccc=ccc+1
  time.sleep(.3)

def longTail(startpoint,incr,maxval):
    if (startpoint<1.0):
      return -2 # not fat enough!
    returnval=1
    point=startpoint
    h=random.uniform(0.0,1.0)
    while True:
      if (returnval>maxval):
        return maxval #retry with another thincounter
      if (h<(1/point)):
        point=point+incr
        returnval=returnval+1
      else:
        return float(returnval)*random.uniform(0.71,1.63)

for aT in trs:
  if not __debug__:
    print aT.name+" has been initialized"

if (DUMPDATA==True):
  if (TPROGRESS==True):
    print "service,trip,t,x,v,a,P"
  if (STAPROGRESS==True):
    print "service,trip,station"

if (realTime==True):
  cycles=CYCLEPP
  scheduler(SYNCPERIOD,stepRT,'none')
else:
  cycles=CYCLE

while (exitCondition==False):
  t=ncyc/CYCLE
  for aT in trs:
    aT.step()
  if (t>duration):
    exitCondition=True
  ncyc=ncyc+1
#for k in r.scan_iter("switch:*"):
#  print k+":"+r.get(k)
