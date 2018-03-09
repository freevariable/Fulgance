#!/usr/bin/python

INITHEIGHT=30.0    # in m
FLATENESS=0.64      #chance of flat terrain
LENGTH=159.4   #in km
MAXGRADE=0.002  #in radian (or meter per meter)
MINSECTION=130.0   #in m
MAXSECTION=MINSECTION*8.3    #in m

import random
import sys

x=0.0
z=30.93
curOrderAvg=0.70
secondOrder={}
secondOrder[0]={'x':0.0,'avg':0.7,'flat':0.64,'max':0.003}
secondOrder[1]={'x':430000.0,'avg':0.03,'flat':0.36,'max':0.006}
secondOrder[2]={'x':490000.0,'avg':0.50,'flat':0.64,'max':0.004}
secondOrder[3]={'x':9999990000.0,'avg':0.50,'flat':0.64,'max':0.004}
oldGradient=0.0

def section(initTrend):
  global x
  global z
  global oldGradient
# step 1: determine trend
  trendRand=random.uniform(0.0,1.0)
  slopeRand=random.uniform(0.0,1.0)
  if (initTrend=='0'):
    trend='='
  elif (initTrend=='='):
    if trendRand<=curOrderFlat:
      trend='='
    else:
      if slopeRand<curOrderAvg:
        trend='-'
      else:
        trend='+' 
  elif (initTrend=='-'):
    if trendRand<=curOrderFlat:
      trend='='
    else:
      if slopeRand<(curOrderAvg):
        trend='-'
      else:
        trend='=' 
  elif (initTrend=='+'):
   if trendRand<=curOrderFlat:
     trend='='
   else:
     if slopeRand>(curOrderAvg):
       trend='+'
     else:
       trend='='  
  steps=[]
  if trend!='=':
    targetGrade=curOrderMax+1.0
    while targetGrade>curOrderMax:
      targetGrade=abs(random.gauss(0.0,(curOrderMax/3.6)))
# step 2: determine number of chunks  
    chunksQty=1+int(6.0*(targetGrade/curOrderMax))
# step 3: determine grade change per chunk 
    if trend=='-':
      step=-1.0*(targetGrade/chunksQty)
    else:
      step=targetGrade/chunksQty
    curGrade=0.0
#    print "target: "+str(targetGrade)
#    print "steps: "+str(chunksQty)
    for i in range (0,chunksQty):
      curGrade=curGrade+step
      steps.append(curGrade)
#    print steps
  else:
    steps.append(0.0)
# step 4: determine chunks length
#  print steps
  lens=[]
  for s in steps:
    len0=MAXSECTION+1.0
    while len0>MAXSECTION:
      len0=MINSECTION*longTail(1.4,0.5,MAXSECTION)
    gradient=int(s*10000.0)
    gradient=gradient/100.0
    cleanX=float(int(x/1.0))/1000.0
    cleanZ=float(int(z*100.0))/100.0
#    print "pK:"+str(x/1000.0)+" gradient:"+str(gradient)+"("+str(s)+")"+" "+" length:"+str(len0)+" "+str(z)
    if ((gradient!=oldGradient) or (initTrend=='0')):
#      print str(x/1000.0)+" "+str(gradient)+" "+str(z)
      print str(33.9+cleanX)+" "+str(gradient)+" "+str(cleanZ)
    z=z+s*len0
    if ((x+len0)<lenM):
      x=x+len0
    oldGradient=gradient
  return trend

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
        return float(returnval)*random.uniform(1.0,2.0)


lenM=LENGTH*1000.0
oldTrend="0"
orderCnt=1
nextOrderX=float(secondOrder[orderCnt]['x'])
curOrderAvg=float(secondOrder[orderCnt-1]['avg'])
curOrderFlat=float(secondOrder[orderCnt-1]['flat'])
curOrderMax=float(secondOrder[orderCnt-1]['max'])
while (x<(lenM-MINSECTION)):
  trend=section(oldTrend)
  oldTrend=trend
  if nextOrderX<x:
#    print "==== second order ===="
    orderCnt=orderCnt+1
    nextOrderX=float(secondOrder[orderCnt]['x'])
    curOrderAvg=float(secondOrder[orderCnt-1]['avg'])
    curOrderFlat=float(secondOrder[orderCnt-1]['flat'])
    curOrderMax=float(secondOrder[orderCnt-1]['max'])
print str(33.9+LENGTH)+" "+str(0.0)+" "+str(float(int(z*100.0))/100.0)
