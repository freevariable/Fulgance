## FAQ 
### What's this?
**Fulgance** is a text-based railroad simulator that will let you perform various tasks:
- define realistic or custom (fancy) routes (without ramps and junctions for now)
- define schedules
- define rolling stock (only EMUs for now)
- distribute schedules over mutiple cores if you have many trains (only single process so single core for now)
- run schedules in real-time or accelerated time on the default route or your own routes (only accelerated-time for now)
- jump into a train to check its real-time progress (the jumpseat is not implemented yet)
- calibrate trains frequency at peak and off peak hours (not yet implemented)
- calculate power consumption (not yet implemented)
- get lots of statistics for data crunching and rendering

Notes for route designers:
- routes may use on-track signals or electronic signals (only on-track for now) for trains separation
- Fulgance will run the default route located in default/ 
- Routes are made of segments located in (routeName)/segments/(segmentName)/. For exemple: default/segments/WestboundMain/ for the default route
- In each segment, you need to describe the location of signals (SIGs), stations (STAs) and speed limits (TIVs). 
- All route and schedule data are kept in simple, self-explanatory text files. Lines beginning with a hash are ignored, as one would expect.

### Requirements
#### Single and multi core environnement
- Python 2.7
- A redis server running on the localhost (apt-get install redis-server in Ubuntu). 
#### Multi core environment
- taskset (part of utils-linux in Ubuntu)
#### Jumpseat
- Python curses (the jumpseat will not work on Windows, sorry...)

### Let's get started
- To run the engine in single-core mode, simply run mp.py without arguments
- Schedules are located in default/schedules/
- The engine (mp.py) will start the default schedule of the default route located in default/schedules/default.txt
