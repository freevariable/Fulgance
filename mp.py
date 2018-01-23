#!/usr/bin/python

import redis
import random
import curses
r=redis.StrictRedis(host='localhost', port=6379, db=0)
r.set('foo','bar')

ACCMU=0.00
ACCSIGMA=0.027
ACC=1.36 # m/s2  au demarrage
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
X0=9900.0
T0=0.0
TLEN=X0+16876.0   # track length in m
VTHRESH=0.999
REALTIME="SIG"    # two mutually exclusive values: SIG or TVM
WAITTIME=10.0   # average wait in station (in sec)

tivs={}
stas={}
sigs={}
trss={}
trs={}
ncyc=0
t=0.0
maxLine=60.0
exitCondition=False
projectDir='default/'
schedulesDir='schedules/'
segmentsDir='segments/'

def initTIVs():
  f=open(projectDir+segmentsDir+"TIVs.txt","r")
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

def initTRSs():
  f=open(projectDir+schedulesDir+"TRs.txt","r")
  tsf=f.readlines()
  ts=[]
  f.close()
  cnt=0
  for t in tsf:
    if (t[0]!='#'):
      t=t.rstrip().split(" ")
      #"ts[cnt]=t
      ts.append(t)
      cnt=cnt+1  
  return ts

def initSTAs():
  f=open(projectDir+segmentsDir+"STAs.txt","r")
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

def initSIGs():
  f=open(projectDir+segmentsDir+"SIGs.txt","r")
  ssf=f.readlines()
  ss=[]
  f.close()
  cnt=0
  for s in ssf:
    if (s[0]!='#'):
      s=s.rstrip().split(" ")
      if (len(s)==2):
        s.append('1')
      ss.append(s)
      cnt=cnt+1  
  return ss

def initAll():
  random.seed()
  global tivs
  global stas
  global sigs
  global trss
  global trs
  tivs=initTIVs()
  stas=initSTAs()
  sigs=initSIGs()
  trss=initTRSs()
  print "trss:"
  print trss
  cnt=0
  for aa in trss:
#    if (cnt>=1):
#      break
    if ((aa[0]!="#") and (cnt==0)):
      found=False
      for asi in sigs:
         if asi[1]==aa[2]:
           aPos=1000.0*float(asi[0])
      trs=Tr(aa[0],aPos,float(aa[3]))
      #print "aa0:"+aa[0]+" aa1:"+str(aa[1])+" aa2:"+str(aa[2])
    else:
      if (aa[0]!="#"):
        found=False
        for asi in sigs:
           if asi[1]==aa[2]:
             aPos=1000.0*float(asi[0])
        aT=Tr(aa[0],aPos,float(aa[3]))
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
  inSta=False
  atSig=False
  waitSta=0.0
  BDzero=0.0

  def append(self,aTr):
    self.trs.append(aTr)
  def __iter__(self):
    yield self
    for t in self.trs:
      for i in t:
        yield i
  def __init__(self,missionName,initPos,initTime):
    print "init..."+missionName+" at pos "+str(initPos)+" and t:"+str(initTime)
    self.trs=[]
    self.x=initPos
    self.name=missionName
    self.BDtiv=0.0  #breaking distance for next TIV
    self.BDsta=0.0  #fornext station
    self.DBrt=0.0  #for next realtime event (sig or tvm)
    self.TIVcnt=findMyTIVcnt(initPos)
    print self.name+":t:"+str(t)+" My TIVcnt is: "+str(self.TIVcnt)+" based on pos:"+str(initPos)
    self.STAcnt=findMySTAcnt(initPos)
    print self.name+":t:"+str(t)+" My STAcnt is: "+str(self.STAcnt)+" based on pos:"+str(initPos)
    self.SIGcnt=findMySIGcnt(initPos)
    print self.name+":t:"+str(t)+" My SIGcnt is: "+str(self.SIGcnt)+" based on pos:"+str(initPos)
    self.nextSTA=stas[self.STAcnt]
    self.nextSIG=sigs[self.SIGcnt]
    self.nSTAx=1000.0*float(self.nextSTA[0])
    self.nSIGx=1000.0*float(self.nextSIG[0])
    self.nextTIV=tivs[self.TIVcnt]
    print self.name+":t:"+str(t)+" next TIV at PK"+self.nextTIV[0]+" with limit "+self.nextTIV[1]
    self.nTIVx=1000.0*float(self.nextTIV[0])
    self.nTIVvl=float(self.nextTIV[1])
    self.cTIVvl=0.0
    self.nTIVtype='>>'    # tiv increases speed
    self.maxVk=min(maxLine,VMX)
    self.PK=self.x
    self.aGaussRamp=aGauss()
    self.a=ACC+self.aGaussRamp
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
  def step(self):
    global t
    global exitCondition
    if (ncyc%1000==0):
      print self.name+":t:"+str(t)+":x:"+str(self.x)
    self.BDzero=-(self.v*self.v)/(2*DCC)
    if ((self.staBrake==False) and (self.x>=(self.nSTAx-self.BDzero))):
      print self.name+":t:"+str(t)+":ADVANCE STA "+str(self.vK)
      self.staBrake=True
      self.a=DCC
    if ((self.staBrake==True) and (self.vK<=0.8)):
      self.a=-0.002
    if ((self.sigBrake==False) and (self.x>=(self.nSIGx-self.BDzero))):
      print self.name+":t:"+str(t)+":ADVANCE SIG "+str(self.vK)
      self.sigBrake=True
#      a=DCC
#    if ((staBrake==True) and (vK<=0.8)):
#      a=-0.002
    if (self.x>=(self.nSIGx)):
      self.sigBrake=False
      print self.name+":t:"+str(t)+":AT SIG "+self.nextSIG[1]+" vK:"+str(self.vK)
      self.SIGcnt=self.SIGcnt+1 
      self.nextSIG=sigs[self.SIGcnt] 
      print self.name+":t:"+str(t)+"next SIG ("+self.nextSIG[1]+") at PK"+self.nextSIG[0]
      self.nSIGx=1000.0*float(self.nextSIG[0])
    if (self.x>=(self.nSTAx)):
      self.a=0.0
      self.v=0.0
      self.inSta=True
      self.waitSta=t+WAITTIME
      self.staBrake=False 
      print self.name+":t:"+str(t)+":IN STA "+self.nextSTA[1]+" vK:"+str(self.vK)
      if (self.nextSTA[1]=='W'):
        exitCondition=True
      else:
        self.STAcnt=self.STAcnt+1 
        self.nextSTA=stas[self.STAcnt] 
        print self.name+":t:"+str(t)+" next STA ("+self.nextSTA[1]+") at PK"+self.nextSTA[0]
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
      self.nextTIV=tivs[self.TIVcnt]
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
      if ((self.staBrake==False) and (self.maxVk>self.vK)):
        print self.name+":t:"+str(t)+"vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to acc" 
        self.aGaussRamp=aGauss()
        self.a=ACC+self.aGaussRamp
      if (self.maxVk<self.vK):
        print self.name+":t:"+str(t)+"vK:"+str(self.vK)+" maxVk:"+str(self.maxVk)+" =>ready to dcc"
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
      if ((self.staBrake==False) and (self.vK<self.maxVk)):
        self.a=0.0
#        print str(t)+":coasting at "+str(vK)
    else:  # a=0.0
#      if (ncyc%1000==0):
#        if (inSta==False):
#          print str(t)+" COCO vK:"+str(vK)+" maxVk:"+str(maxVk)+" aF:"+str(aFull)+" a:"+str(a)
      if ((self.vK>4.0) and (self.vK<0.965*self.maxVk)):
        print self.name+":t:"+str(t)+":boosting from vK:"+str(self.vK)+" to maxVk:"+str(self.maxVk)+" with aFull:"+str(self.aFull)
        self.a=ACC+aGauss()
#          else:
#            print str(t)+":not boosting vK:"+str(vK)+" to maxVk:"+str(maxVk)
    self.aFull=self.a-(0.1*self.v*self.v/400)
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
#    if (a==DCC):
#      print str(t)+' '+str(a)+' '+str(v)+'('+str(vK)+') '+str(x)
#    print t
#  print ncyc
#    print self.PK
  
def aGauss():
  return random.gauss(ACCMU,ACCSIGMA)

def findMySTAcnt(x):
  global stas
  xK=x/1000.0
  cnt=0
  found=False
  for ast in stas:
    if float(ast[0])>=xK:
      break
    cnt=cnt+1
  return cnt

def findMySIGcnt(x):
  global sigs
  xK=x/1000.0
  cnt=0
  found=False
  for asi in sigs:
    if float(asi[0])>=xK:
      break
    cnt=cnt+1
  return cnt

def findMyTIVcnt(x):
  global tivs
  xK=x/1000.0
  cnt=0
  found=False
  for ati in tivs:
    if float(ati[0])>=xK:
      break
    cnt=cnt+1
  return cnt

initAll()
for aT in trs:
  print "name:"+aT.name

while (exitCondition==False):
  t=ncyc/CYCLE
  for aT in trs:
    aT.step()
  if (t>3500):
    exitCondition=True
  ncyc=ncyc+1
print r.get('foo')
