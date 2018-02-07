45,47c45
< SYNCPERIOD=0.5 # how often (in s) do we sync multicores
< CYCLEPP=100    # how many ticks we calculate between two multicore syncs
< CYCLE=CYCLEPP*SYNCPERIOD # how many ticks we calculate per second 
---
> CYCLE=200 # number of time per sec calc must be made
519,521d516
< #
< # STAGE 1 : main acc updates
< #
670c665
< # STAGE 2 : other acc updates
---
> # STAGE 2
683,684c678,679
<         if not __debug__:
<           if (ncyc%CYCLE==0):
---
>         if (ncyc%CYCLE==0):
>           if not __debug__:
695,696c690,691
<             if not __debug__:
<               if (ncyc%CYCLE==0):
---
>             if (ncyc%CYCLE==0):
>               if not __debug__:
717,718c712,713
<         if not __debug__:
<           if (ncyc%CYCLE==0):
---
>         if (ncyc%CYCLE==0):
>           if not __debug__:
721c716
< # STAGE 3 : calculate aFull
---
> # STAGE 3
743,745d737
< # 
< # STAGE 4 : perform coarse grain calculations
< #
747,748d738
< # here make coarse-grain markers calculation
< # power calculation:
751a742
> #      if ((self.inSta==False) and (self.atSig==False)):
754d744
< #      if ((self.inSta==False) and (self.atSig==False)):
928c918
<   opts, args = getopt.getopt(sys.argv[1:], "h:m", ["help", "realtime", "core=","duration=", "route=", "schedule=", "services=","cores="])
---
>   opts, args = getopt.getopt(sys.argv[1:], "h:m", ["help", "realtime", "master", "core=","duration=", "route=", "schedule=", "services=","cores="])
1026,1027c1016,1017
< if (realTime==True):
<   scheduler(SYNCPERIOD,stepRT,'none')
---
> if (REALTIME==True):
>   scheduler(0.5,stepRT,'none')
