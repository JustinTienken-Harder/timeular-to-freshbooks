## Project Description Invoice for Wave APp

This is a new project that will utilize the current components that exist in Timeular to create monthly invoices for WaveApp. This projects converts CSV's into WaveApp invoices that my mom can further edit as needed. 



- Notes
- Client (labeled Activity)
- Time
- Billable Rate (but that's a lie)
- Tags are related to billable rate


WaveApp Side:
Clients (with unique identifiers)
Services (with Unique identifiers and actual going rate)
Notes

### The actual goal:

We wish to upload a CSV of timesheets containing Time, Tag (of the service. Each service has billable hourly rates), and Activity. The invoices are for each client (notated by Activity in the time sheet). Activities that don't have a client (on the WaveApp side), should be consolidated in a browser application by the user (ideally, a dropdown menu or search bar with suggested clients). Furthermore, in each invoice (a Client), the time entries should be combined with equivalent tags. These tags should also have an associated Service for WaveApp.


