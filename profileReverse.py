#!/usr/bin/python

import sys

sourceProfile=[]
reversedProfile=[]

def loadProfile():
  f=open("GRDs.txt","r")
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

def reverse():
  global sourceProfile
  global reversedProfile
  sourceProfile=loadProfile()
  lastRow=sourceProfile[-1]
  lenkm=float(lastRow.split(" ")[0])
  cntLines=0
  for p in sourceProfile:
    prev=[]
    prev=[0.0,0.0,0.0]
    if cntLines>0:
      oldRow=curRow
    curRow=p.split(" ")
    if cntLines>0:
      prev[0]=lenkm-float(curRow[0])
      if oldRow[1]=='0.0':
        prev[1]=0.0
      else:
        prev[1]=-1.0*float(oldRow[1])
      prev[2]=float(curRow[2])
    else:
      prev[0]=lenkm-float(curRow[0])
      prev[1]=0.0
      prev[2]=float(curRow[2])
    #print str(lenkm-curX)+" "+str(curGRD)+" "+str(curZ)
    reversedProfile.append(prev)
    cntLines=cntLines+1
  for p in reversed(reversedProfile):
    print str(p[0])+" "+str(p[1])+" "+str(p[2])

reverse()
