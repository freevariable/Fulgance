Wear&tear ticks (t,inc,curv)
Modulated by braking syst, admission sys, mechanics with various sensitivity coeff
Consummed by servicing & maintenance

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
- handle time of day
- handle weather (adhesive power in ramps/at start + Vk in strahl)
- handle gauge & electrification
- handle imperial units in rollingStock.txt 
- on steam engines, implement weight variations according to pax or freight load
- on electrified routes, implement power outages and power consumption (real time)

**UX**
- Implement real time notifications (slack?)

**API**
- Implement REST API to get info and push actions (hold a train for regulation?)

**Control Room**
- Implement info board in stations

**Signalling**
- Implement TVM (electronic signals)

**Train services**
- Implement wait at siding for a given (or any) service name to pass
- Use entry and exit portals. Spawn/destroy according to time of the day.

**Pax**
- Implement dynamic variations (depends on time of day implementation)

**POIs/ZOIs**
- Implement boundaries, tunnels, water and coal points, substations
- Implement entry and exit portals
