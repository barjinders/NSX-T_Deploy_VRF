This script creates VRF gateways on existing NSX T0 gateways. The script will deploy VRF, configure them, create t1, transport zones , create vlan and overlay segments. 

Populate the below files before running the script. 

transport_zone.json: Update the display name key with the target transport zone name.

environment.json: Update this file with the NSX IP , port is default 443 but can be updated if a custom port is in use. For auth key in the username and password. The username and password gets converted into a base64 encoded stringin the code. 

create_segments_for_uplinks.json: Each VRF gateway is connected with a VLAN-backed segment for the north-south traffic. Update the name, id , transport zone name mentioned in the transport_zone.json file and the VLAN ID. 

create_vrf.json: Update the display name and ID with the target VRF names. Leave the key  "tier0_path" as blank as it will be updated in the code. Each VRF will have 2 interfaces directly connected to it. Update the names of each interface and an IP with prefix.  "t0_id" is the key that is used for creating a relationship between a VRF gateway and an interface or any other setting. Localservices define route redistribution. It can be updated as per the requirements. HA VIP is used to put a virtual IP on the uplink interface. e.g. if my Subnet is 192.168.100.0/24. Admins can use 192.168.100.2 as VIP, 192.168.100.3 as the edge left interface, 192.168.100.4 as the edge right interface. 

create_tier1s.json: Update the name for each T1 gateway that is needed to be deployed. "t0_id" is the key that is used for creating a relationship between a VRF gateway and a tier 1 gateway. Route advertisement can also be updated in this JSON for T1 gateways. 

create_l3_segments.json: This JSON file will be used to create the overlay segments. Update the "connectivity_path" key to make the segment - t1 relationship. 


