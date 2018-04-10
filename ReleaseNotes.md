## What's new in build 143
- Optimized wear and tear tick calculations
- Implemented sim save feature (sim load not implemented yet)
- Two new API verbs: v1/describe/status and /v1/save/saveName/saveTime
- Work on traffic manager

## What's new in build 142
- Implement steam engine coal & water consumption cut off in slopes
- Started implementation of wear and tear

## What's new in build 141 
- Traffic manager improvement and interfacing to the sim via the REST API

## What's new in build 140 
- Continued implementation of the simulator REST API (see README) in preparation for ALPHA 3: traffic manager  
- Fixed bugs in multithreading. Should be fine, now

## What's new in build 139
- Skeleton implementation of the traffic manager, located in directory trafficManager/ 

## What's new in build 138
- Started implementation of the simulator REST API (see README) in preparation for ALPHA 3: traffic manager

## What's new in build 137
- Bug fixing in the simulator, in preparation for ALPHA 3: traffic manager
- Created trafficManager directory

## What's new in build 136
- Bug fixing in steam engine calculations, TheCorkScrew route and the control room

## What's new in build 135
- Buffed AulderKraak Consolidation
- Completed TheCorkSscrew upward and downward segments

## What's new in build 134
- Ended implementation of tracks radius of curvature
- Bug fixing
- Modified ParisLine1 (added switches and signalling to Fontenay Workshop)

## What's new in build 132
- Steam engines copied to locoLib/
- New steam engine: AulderKraak Consolidation
- New (undocumented) route: TheCorkScrew

## What's new in build 131
- Started implementation of tracks radius of curvature

## What's new in build 130
- Added the last missing parameters to the steam engines rollingStock.txt file
- New steam engine: Decapod Est 150-001 (temporarily located in PolarComet/rollingStock.txt)

## What's new in build 129 (ALPHA TWO)
- LondonCentral now stable under medium load (schedules/medium.txt)!
- Added several parameters to the steam engines rollingStock.txt file
- Extended the PolarComet northbound segment to Newhaven

## What's new in build 125
- Another row of bug fixing in preparation for release ALPHA TWO
- Added aspect signals to LondonCentral
- Added speed signals to LondonCentral

## What's new in build 124
- Lots of bug fixing in preparation for release ALPHA TWO

## What's new in build 123
- Bugs fixing
- Imperial units support in Control Room

## What's new in build 122
- Imperial units are now supported for distances and speeds. Units are set in (routeDirectory)/routeConfig.txt
- routeConfig.txt set in PolarComet,ParisLine1, TestTrack and LondonCentral
- finished the LondonCentral route minimum viable signalling to connect the 6 segments.

## What's new in build 121
- Trains are removed from the services list when they reach a non-type 2 signal
- Non-type 2 signals with no successor signals are set to red
- Simulation ends gracefully when services list becomes empty

## What's new in build 120
- Steam engines now refill coal and water at stations
- The average waiting time at stations (in seconds) is now set in rollingStock.txt under the *waitTime* attribute
- Drivers reaction time after sig clearance has been slightly randomized
- Placed LondonCentral stations in STAs.Txt in the six segment folders
