## FAQ 
**Fulgence** is a precision, highly customizable, text-based, REST API friendly railroad simulator made of three core components: 
- mp.py, the train engine simulator itself. Sims are complex beast, you should check out our *tutorials below*
- room.py, the control room (showing enroute trains progress). **A demo of the control room is [available here](http://fulgence.lovethosetrains.com/controlRoom.html)** 
- tr.py, the traffic manager (the brain, providing path information to the simulator)

Here is a sample of what you can get in the control room:

![alt text](https://github.com/freevariable/Fulgence/blob/master/capture.png "Paris metro demo")

### Main features
Fulgence will let you perform various tasks:
- [x] define realistic (eg: Paris Metro Line 1) or fancy routes (eg: The Polar Comet) with grades and curves
- [x] define realistic or fancy schedules on these routes
- [x] define your own rolling stock (EMUs and steam engines)
- [x] save sim, restore and resume at a later time
- [x] get live simulation JSON data through a REST API (see below supported verbs)
- [x] run schedules in real-time or accelerated time
- [ ] scale train services according to passengers peaks (TRAFFIC MANAGER feature)
- [x] place aspect signals for train separation and route branches
- [ ] place aspect signals for trains overtaking and single track operations (TRAFFIC MANAGER feature)
- [x] set headway timers for trains separation
- [ ] place electronic signals for trains separation and route branches 
- [x] calculate live power, water and coal consumption
- [x] calculate wear and tear
- [ ] identify servicing thresholds for brakes, vapor engine and moving parts. Implement breakdowns!
- [x] oversee all trains progress in the control room of your route
- [ ] update train schedules in realtime depending on time of the day/congestion (TRAFFIC MANAGER feature)

### What works as of today (build ALPHA TWO)?
Since the simulator is in ALPHA, only a subset of features are currently usable:
- you may run the sim on the *ParisLine1* and *LondonCentral* routes, with any schedule (the predefined ones or your own custom schedules)
- you may run the control room for the *ParisLine1* and *LondonCentral* routes
- you may run vanilla or custom steam engines in the *PolarComet* route until it runs out of resources (coal or water)
- you may run vanilla or custom steam engines in *TheCorkScrew* route, upward or downward segments.
- four API verbs are currently supported: v1/list/schedules, v1/describe/schedule/*scheduleName*, v1/save/*saveName*/*time* and v1/describe/status
- you may save a running sim, stop it and resume later one

The steam engine is giving promising results!! Here are the characteristic curves of a 147tons Atlantic (including tender) with two cylinders (not compounded) and a 250t payload:

![alt text](https://github.com/freevariable/Fulgence/blob/master/250t.png "Atlantic")

![alt text](https://github.com/freevariable/Fulgence/blob/master/250t.a.png "Atlantic")

### Notes for route designers
#### Layout
- routes will support both on-track signals and electronic signals (only on-track for now)
- Routes are located in (Fulgence folder)/(routeName)/ 
- The global parameters such as gauge, electrification, imperial or metric units... are located in (routeName)/routeConfig.txt. Only units must be set for now, the other parameters are optional
- Routes are made of segments located in (routeName)/segments/(segmentName)/. For example: ParisLine1/segments/WestboundMain/ for the default route
- A segment is a set of contiguous blocks where each block is under control of a signal
- Blocks are not explicitely delimited or managed in Fulgence. In fact, signals define blocks.
- Blocks are unidirectional, except the ones protected by a **reversing signal** 
- Consequently, segments are unidirectional. It means that single track routes are not supported yet.
- In each segment folder, you need to describe the location of signals (SIGs), stations (STAs), speed limits (TIVs), radius of curvature (CRVs) and grades (GRDs). 
- All route and schedule data are kept in simple text files. Lines beginning with a hash are ignored, as one would expect.
- Schedules are kept in the (routeName)/schedules directory. You may name them whatever.txt The default shedule is default.txt
- Services are kept in (routeName)/services.txt This file is **optional**. Use it only if you have branches on your line to provide pathfinding information.
- Markers are not supported yet. In the pipe: tunnels (provide weather protection), country boundaries (with imperial/metric unit changes), points of interest (landmarks), areas of interest, platform names, substations (for line sectioning).
- Weather is not supported yet
- Steam engines fully replenish water and coal at all stations on their way

#### Signal types
The following on-track signals are implemented:
- [x]  *Type 1*: this is the usual 3-aspect signal. The possible states are: VL (green, all clear), A (yellow, prepare to stop at next signal) and C (red, impassable stop).
- [x] *Type 2*: this is a buffer signal that allows reversing to a segment which is different from the origin segment. As far as the origin segment is concerned, its only possible state is C (red, impassable) and it is preceded by a type 3 signal. As for the first signal in the reversed direction, it is controlled by a type 5 signal.
- [x] *Type 3*: this is a 2-aspect signal (A and C). It  must always **precede** a type 2, as its state depends on the switch position in the upcoming junction.
- [x] *Type 4D*: this is a diverging junction signal, used to stitch segments together. Both legs of the junction see trains **moving in the same direction**. (As opposed to the second type of diverging junction described below). Type 4D must **always be preceded** by a type 1.
- [x] *Type 4C*: this is a converging junction signal, used to stitch segments together. Both legs of the junction see trains **moving in the same direction**. It must **always be preceded** by a type 6 in both its legs.
- [x] *Type 5*: this is a diverging junction signal for trains coming from a reversing block. It must always **be preceded** by a type 2 signal. One leg of the junction is for trains **coming from** the forward direction, the other leg is for trains **going to** the reverse direction.
- [x] *Type 6*: this is a 3-aspect signal **always preceding** a type 4C signal. So there are two such type 6 signals for any given type 4C: one in each leg. Both type 6 sort of compete to control the switch position in the 4C block. 

Junction signals can manage only two legs, no less, no more. One leg is the main segment (left or right), the other one to the diverging/converging segment (left or right).Junction signals must have a unique name in both segments so that the engine may perform the segments stitching properly.

#### Signals placement per segment type
- *Main branches* must start by a type 2 (succeeded by a type 5) and terminate by a type 2 (preceded by a type 3) signal. See for example: LondonCentral/segments/Epping/SIGs.txt
- *Sidings must* start with a type 4D signal and terminate with a type 4C signal (preceded by a type 6 signal)
- *Secondary branches* diverging from a main branch must start with a 4C signal and terminate with a type 2 signal (preceded by a type 3). See for exemple: LondonCentral/segments/Hainault/SIGs.txt
- *Exit to a garage* must start with a 4C signal and terminate with a type 1 signal. See for exemple: ParisLine1/segments/FontenayExit/SIGs.txt
- *Secondary branches* converging towards a main branch must start with a type 2 signal (succeeded by a type 5) and terminate with a type 4C signal (preceded by a type 6). See for exemple: LondonCentral/segments/WestActon/SIGs.txt
- *Entry from a garage* must start with a type 2 signal (succeeded by a type 5) and terminate by a type 4C (preceded by a type 6 signal)

### Installation 
sudo apt-get update

sudo apt-get install -y redis-server python curl python-redis

Then: clone Fulgence from GitHub and... voila!

## Tutorials
### Tutorial 1: run the small schedule of the LondonCentral route for 1 hour 
- mp.py --route=LondonCentral --schedule=tr.txt --duration=3600

Since mp.py is a daemon, from that point nothing will seem to happen but the sim will actually have started. To know what is going on, you have two options: either run the control room, or use the API. This is the purpose of the next tutorial.

### Tutorial 2: see real time trains progress
In this tutorial, we suppose that you have a web server up and running, with the document root located in /var/www/html

To use the control room, we must *restart the sim in realtime mode*: 
mp.py --realtime --route=LondonCentral --schedule=tr.txt --duration=3600

While the sim is running in background, we then run room.py at regular intervals, say every minute: 
controlRoom/room.py --route=LondonCentral --schedule=tr.txt --segments=Epping,WestRuislip > /var/www/html/controlRoom.html

After every room.py execution, we need to copy the generated files controlRoom/Epping.html and controlRoom/WestRuislip.html to the web server, in /var/www/html

We also need to copy all the svg files located in controlRoom/html/ to the web server:
cd controlRoom/html && cp *.svg /var/www/html/

Point your browser to http://yourwebserver/controlRoom.html and see the trains progress and the stations on the various segments of the line.

You may also want to probe the sim with an API call:
- curl http://127.0.0.1:4999/v1/describe/status
Returns usefull data about the running sim: its ID, the current time, the route name, etc

- curl http://127.0.0.1:4999/v1/list/schedules
This will bring up a JSON list of all trains currently running on the line.

### Save and restore sim
By default, the sim is saved to a file in the *saves* subdirectory every 15 minutes
You may want to schedule a specific sim save under name "myName" at (simulation) time t=55 seconds by issuing:
- curl http://127.0.0.1:4999/v1/save/myName/55

myName will be saved in the *saves* subdirectory.
To restore the sim:
- kill the running mp.py
- restart mp.py with the resume=simName option: ./mp.py --resume=myName 

You may start the sim in accelerated time and resume in realtime or the opposite: all combinations are possible. :)

### API
- get a status of a runnin sim: curl http://127.0.0.1:4999/v1/describe/status
- use curl to dump the list of currently active schedules on the route: curl http://127.0.0.1:4999/v1/list/schedules
- based on the list of schedules, get live data on a specific schedule: curl http://127.0.0.1:4999/v1/describe/schedule/scheduleName
- save the sim in file *mySaveName.pickle* after 3 minutes (180 seconds) by calling curl http://127.0.0.1:4999/v1/save/mySaveName/180

Exemple on *ParisLine1*, using the default schedule.txt :
curl http://127.0.0.1:4999/v1/describe/schedule/E500

### Control room (controlRoom/room.py)
The control room is displayed as an HTML dashboard by calling *tools/room.py* **after** or **while** you run mp.py in realtime. It will not work otherwise, because it polls redis for live information and redis will be empty.

*room.py* also generates one HTML file per segment you wish to monitor. It is called *segmentName.html*

For stations to appear on the dashboard, they must be succeded by a signal named (station trigram)+(whatever) in (routeName)/segments/(routeSegment)/SIGs.txt

#### Control room options
- You must provide the route name using *--route*
- You must provide a segments list using *--segments*  Segment names are separated by a comma
- You must provide a schedule name using *--schedule*

Here are two  examples:

*controlRoom/room.py --route=ParisLine1 --schedule=large.txt --segments=WestboundMain,EastboundMain > dashboard.html* 

*controlRoom/room.py --route=LondonCentral --schedule=default.txt --segments=WestRuislip,Epping,Hainault,Wanstead,Acton,EalingBroadway > dashboard.html* 

The first example will produce three HTML files: dashboard.html, WestboundMain.html and EastboundMain.html

In the second example, seven HTML files will be produced.

### Traffic manager (tr.py)
To be completed
