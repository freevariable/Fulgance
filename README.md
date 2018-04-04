## FAQ 
**Fulgence** is a precision, highly customizable (text-based) railroad simulator. **A full demo is [available here](http://fulgence.lovethosetrains.com/controlRoom.html)**

Here is a sample of what you can get:

![alt text](https://github.com/freevariable/Fulgence/blob/master/capture.png "Paris metro demo")

The steam engine simulator in alpha version is giving promising results!! Here are the characteristic curves of a 147tons Atlantic (including tender) with two cylinders (not compounded) and a 250t payload:

![alt text](https://github.com/freevariable/Fulgence/blob/master/250t.png "Atlantic")

![alt text](https://github.com/freevariable/Fulgence/blob/master/250t.a.png "Atlantic")

### What's this?
Fulgence will let you perform various tasks:
- [x] define realistic (eg: Paris Metro Line 1) or fancy routes (eg: The Polar Comet)
- [x] define realistic or fancy schedules
- [x] define rolling stock (EMUs and steam engines!)
- [x] inquire simulation state through REST API (see below supported verbs)
- [x] run schedules in real-time or accelerated time
- [ ] scale train services according to passengers peaks (TRAFFIC MANAGER feature)
- [x] use aspect signals for train separation and route branches
- [ ] use aspect signals for trains overtaking and single track operations (TRAFFIC MANAGER feature)
- [x] use headway timers for trains separation (TRAFFIC MANAGER feature)
- [ ] use electronic signals for trains separation and route branches 
- [x] calculate power consumption (only EMUs for now, coal and water are in alpha!)
- [x] get detailed statistics for data crunching and rendering
- [x] access the control room
- [ ] get/change sim behavior thru an API (TRAFFIC MANAGER feature)

### What works as of today (build ALPHA TWO)?
Since the simulator is in ALPHA, only a subset of features are currently usable:
- you may run the sim on the *ParisLine1* and *LondonCentral* routes, with any schedule (small, medium, default, large)
- you may run the control room for the *ParisLine1* and *LondonCentral* routes
- you may run an Atlantic steam engine in the *PolarComet* route until it runs out of resources (coal or water)
- you may run a Consolidation steam engine in *TheCorkScrew* route, upward or downward segment.
- two API verbs are currently supported: v1/list/schedules and v1/describe/schedule/<scheduleID>

### Notes for route designers
#### Layout
- routes will support both on-track signals and electronic signals (only on-track for now)
- Routes are located in (Fulgence folder)/(routeName)/ 
- The global parameters such as gauge, electrification, imperial or metric units... are located in (routeName)/routeConfig.txt. Only units must be set for now.
- Routes are made of segments located in (routeName)/segments/(segmentName)/. For example: ParisLine1/segments/WestboundMain/ for the default route
- A segment is a set of contiguous blocks where each block is under control of a signal
- Blocks are not explicitely delimited or managed in Fulgence. In fact, signals define blocks.
- Blocks are unidirectional, except the ones protected by a **reversing signal** 
- Consequently, segments are unidirectional. It means that single track routes are not supported yet.
- In each segment, you need to describe the location of signals (SIGs), stations (STAs), speed limits (TIVs), radius of curvature (CRVs) and grades (GRDs). 
- All route and schedule data are kept in simple text files. Lines beginning with a hash are ignored, as one would expect.
- Schedules are kept in the (routeName)/schedules directory. You may name them whatever.txt The default shedule is default.txt
- Services are kept in (routeName)/services.txt This file is **optional**. Use it only if you have branches on your line to provide pathfinding information.
- Markers are not supported yet. In the pipe: tunnels (provide weather protection), country boundaries (with imperial/metric unit changes), points of interest (landmarks), areas of interest, platform names, substations (for line sectioning).
- Weather is not supported yet
- Steam engines replenish water and coal at stations

#### Signalling guide
The following on-track signals are implemented:
- [x]  *Type 1*: this is the usual 3-aspect signal. The possible states are: VL (green, all clear), A (yellow, prepare to stop at next signal) and C (red, impassable stop).
- [x] *Type 2*: this is a buffer signal that allows reversing to a segment which is different from the origin segment. As far as the origin segment is concerned, its only possible state is C (red, impassable) and it is preceded by a type 3 signal. As for the first signal in the reversed direction, it is controlled by a type 5 signal.
- [x] *Type 3*: this is a 2-aspect signal (A and C). It  must always **precede** a type 2, as its state depends on the switch position in the upcoming junction.
- [x] *Type 4D*: this is a diverging junction signal, used to stitch segments together. Both legs of the junction see trains **moving in the same direction**. (As opposed to the second type of diverging junction described below). Type 4D must **always be preceded** by a type 1.
- [x] *Type 4C*: this is a converging junction signal, used to stitch segments together. Both legs of the junction see trains **moving in the same direction**. It must **always be preceded** by a type 6 in both its legs.
- [x] *Type 5*: this is a diverging junction signal for trains coming from a reversing block. It must always **be preceded** by a type 2 signal. One leg of the junction is for trains **coming from** the forward direction, the other leg is for trains **going to** the reverse direction.
- [x] *Type 6*: this is a 3-aspect signal **always preceding** a type 4C signal. So there are two such type 6 signals for any given type 4C: one in each leg. Both type 6 sort of compete to control the switch position in the 4C block. 

Junction signals can manage only two legs, no less, no more. One leg is the main segment (left or right), the other one to the diverging/converging segment (left or right).Junction signals must have a unique name in both segments so that the engine may perform the segments stitching properly.

### Requirements
#### Single and multi simulation engines
- Python 2.7
- A redis server running on the localhost (apt-get install redis-server in Ubuntu). Redis is used for signal aspects real-time management.
#### Multi simulation engines
- taskset (part of utils-linux in Ubuntu).
Note: when using multi simulation engines, redis is also used for inter-process synchronisation.
#### Control room
Note: control room relies on redis for getting the real-time state of a train.

### Let's get started
To run the simulation in single simulation engine mode, simply run mp.py without arguments. What happens then is that the engine (mp.py) starts the default schedule of the default route, the Paris Metro line 1, located in ParisLine1/schedules/default.txt

By default, 50 train services are run in parallel. The sim will not stop until you hit CTRL+C

### Parameters
To run the sim in realtime, set REALTIME constant to True. Otherwise it will run as fast as possible on your CPU.

To adjust simulation precision, you may set the CYCLE variable to your wishing. I recommend to keep the default value to get the best trade off between precision and speed of execution though. 

To run the sim in debug mode, modify the first line to add the -O option to python

### Command line options
Fulgence will run fine without options, but there are several things you may wish to change:
- Set a given duration (in seconds) using *mp.py --duration=seconds*, otherwise the sim will go on forever.
- Pick a non-default route (the TestTrack route for instance) with *mp.py --route=TestTrack*
- Choose a non-default schedule: *mp.py --schedule=myschedule.txt*
- Enable real time: *mp.py --realtime*
#### Examples
- Run in real time for 1 hour: *mp.py --realtime --duration=3600*

### API
- use curl to dump the list of currently active schedules on the route: curl http://127.0.0.1:4999/v1/list/schedules
- based on the list of schedules, get live data on a specific schedule: curl http://127.0.0.1:4999/v1/describe/schedule/<scheduleName>

Exemple on *ParisLine1*, using the default schedule.txt :
curl http://127.0.0.1:4999/v1/describe/schedule/E500

### Control room
The control room is displayed as an HTML dashboard by calling *tools/room.py* **after** or **while** you run mp.py in realtime. It will not work otherwise, because it polls redis for live information and redis will be empty.

*room.py* also generates one HTML file per segment you wish to monitor. It is called *segmentName.html*

For stations to appear on the dashboard, they must be succeded by a signal named (station trigram)+(whatever) in (routeName)/segments/(routeSegment)/SIGs.txt

#### Options
- You must provide the route name using *--route*
- You must provide a segments list using *--segments*

Here are two  examples:

*tools/room.py --route=ParisLine1 --segments=WestboundMain,EastboundMain > dashboard.html* 

*tools/room.py --route=LondonCentral --segments=WestRuislip,Epping,Hainault,Wanstead,Acton,EalingBroadway > dashboard.html* 

The first example will produce three HTML files: dashboard.html, WestboundMain.html and EastboundMain.html

In the second example, seven HTML files will be produced.
