Yes. The Trafiklab Realtime APIs you want are:

  - Stop Lookup to find the correct stop group (area/rikshållplats) IDs for “Gunnesbo” and “Fornborgen”.
  - Timetables to fetch departures for those area IDs, then filter by transport_mode (TRAIN for Gunnesbo C, BUS for Fornborgen). (trafiklab.se (https://www.trafiklab.se/api/our-apis/
    trafiklab-realtime-apis/stop-lookup/))

  Step 1: Get stop group IDs (area ids)
  You’ll need your Trafiklab API key. Run these and share the results:

  curl "https://realtime-api.trafiklab.se/v1/stops/name/Gunnesbo?key=YOUR_KEY"
  curl "https://realtime-api.trafiklab.se/v1/stops/name/Fornborgen?key=YOUR_KEY"

  The response includes stop_groups[].id (area id) and stop_groups[].name. The area id is what the Timetables API requires. (trafiklab.se (https://www.trafiklab.se/api/our-apis/trafiklab-
  realtime-apis/stop-lookup/))

  Step 2: Fetch realtime departures
  Once you have the area ids:

  curl "https://realtime-api.trafiklab.se/v1/departures/AREA_ID?key=YOUR_KEY"

  Optional time-specific query (local timezone, YYYY-MM-DDTHH:mm):

  curl "https://realtime-api.trafiklab.se/v1/departures/AREA_ID/2026-02-24T18:00?key=YOUR_KEY"

  The API always returns the next 60 minutes; filter client-side. (trafiklab.se (https://www.trafiklab.se/api/our-apis/trafiklab-realtime-apis/timetables/))

  Filtering

  - Gunnesbo C: keep departures where route.transport_mode == "TRAIN".
  - Fornborgen: keep departures where route.transport_mode == "BUS".

  If you paste the Stop Lookup results here, I’ll extract the correct area ids and give you exact URLs + filters for each station.

