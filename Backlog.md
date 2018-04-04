**Known issues**
- Stations/signals following a 4C must be within breaking distance of the junction otherwise they are not caught in time by trains coming from the branch. Same issue with stations/signals following a 4D on the diverging branch: they are not caught in time by trains coming from the main line and diverging.

**Documentation**
- Routes designers guide
- Scenarios designers guide
- Control room guide
- API guide
- PolarComet operating manual
- TheCorkScrew operating manual

**Realism**
- check constraints on steam engine parameters (cylinder diameter, etc)
- wear and tear: implement ticks (t,inc,curv), servicing, breakdown by category (braking sys, admission sys, mechanics)
- handle weather (adhesive power in ramps/at start + Vk in strahl)
- handle gauge & electrification
- handle imperial units in rollingStock.txt 
- on steam engines, implement weight variations according to pax or freight load
- on electrified routes, implement power outages and power consumption (real time)

**UX**
- Implement real time notifications (slack?)

**Signalling**
- Implement electronic signals

**Traffic manager**
- Support single track route operations
- Implement wait at siding for a given (or any) service name to pass
- Use entry and exit portals. Spawn/destroy according to time of the day.
- Implement dynamic variations (depends on time of day implementation)
- Implement REST API to get info and push actions (hold a train for regulation?)
- Handle time of day

**POIs/ZOIs**
- Implement boundaries, tunnels, water and coal points, substations
- Implement entry and exit portals
