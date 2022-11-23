###########################################################
#  Author - Barjinder Singh                               #
#  mail.barjinder@gmail.com                               #
#  https://www.linkedin.com/in/barjinder-singh-48357555/  #                              
# #########################################################      


import json
import time
import requests
import warnings



##############################################################################
# Housekeeping
##############################################################################
# Prints log messages
verbose = 0

# Pretty print POST response body on Success
print_response = 1

# Just display the API call and the request body (if any)
plan = 0

##############################################################################
# Helper functions
##############################################################################

# Generic Error Response
def raiseError(r):
    print("Error: %s" % json.dumps(r.json(), indent=4, sort_keys=True))
    exit()

# pretty print json
def print_json(text):
    print(json.dumps(text, indent=4, sort_keys=True))
    return True

def banner(text, ch='=', length=78):
    spaced_text = ' %s ' % text
    banner = spaced_text.center(length, ch)
    return banner


# Generic pretty print Response
def pretty_response(r):
    if (print_response and not plan):
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except ValueError as e:
            return True
    return True

# Load json file
def load_json(file):
    with open(file) as json_file:
        data = json.load(json_file)
        return data

# Log me
def log(msg):
    if (verbose):
        print(msg)


# NSX Manager IP/FQDN URL formatter
def nsx_url(uri):
    return 'https://' + nsx_ip + ':443' + uri


# Generic GET request
def get(uri, ignore_plan=False):
    if plan and ignore_plan == False:
        print("\nGET %s\n" % uri)
        return True

    r = requests.get(nsx_url(uri), verify=False, headers=headers)
    if r.status_code != 200:
        raiseError(r)
    return r


# Generic POST request. retry_with_thumbprint flag to retry if the initial POST response has a thumbprint
def post(uri, json_body, retry_with_thumbprint=False):
    if plan:
        print("\nPOST %s" % uri)
        print("Request-Body: \n%s\n" % json.dumps(json_body, indent=4, sort_keys=True))
        return True

    r = requests.post(nsx_url(uri), verify=False, headers=headers, json=json_body)
    if ((r.status_code != 201) and (r.status_code != 200)):
        if retry_with_thumbprint == False:
            raiseError(r)
        else:
            data = r.json()
            if 'already registered with NSX' in data['error_message']:
                return r
            if 'thumbprint' in data['error_message']:
                if "ValidCmThumbPrint" in data['error_data']:
                    thumbprint = data['error_data']['ValidCmThumbPrint']
                    # Add thumbprint to json_data and retry
                    json_body['credential']['thumbprint'] = thumbprint
                elif "ValidThumbPrint" in data['error_data']:
                    thumbprint = data['error_data']['ValidThumbPrint']
                    json_body['node_deployment_info']['host_credential']['thumbprint'] = thumbprint
                else:
                    raiseError(r)

                r = requests.post(nsx_url(uri), verify=False, headers=headers, json=json_body)
                if ((r.status_code != 201)) :
                    raiseError(r)
            else:
                raiseError(r)
    return r

# Generic PUT request. Usually returns a response body
def put(uri, json_body):
    if plan:
        print("\nPUT %s" % uri)
        print("Request-Body: \n%s\n" % json.dumps(json_body, indent=4, sort_keys=True))
        return True

    r = requests.put(nsx_url(uri), verify=False, headers=headers, json=json_body)
    if r.status_code != 200:
        raiseError(r)
    return r

# Generic PATCH request. Usually does not return a response body
def patch(uri, json_body):
    if plan:
        print("\nPATCH %s" % uri)
        print("Request-Body: \n%s\n" % json.dumps(json_body, indent=4, sort_keys=True))
        return True

    r = requests.patch(nsx_url(uri), verify=False, headers=headers, json=json_body)
    if r.status_code != 200:
        raiseError(r)
    return r

# Generic DELETE request. Does not return anything
def delete(uri):
    if plan:
        print("\nDELETE %s" % uri)
        return True
    r = requests.delete(nsx_url(uri), verify=False, headers=headers)
    if r.status_code != 200:
        raiseError(r)
    return True

def update_transport_node_profile():
    print(banner("Updating transport node profile start"))

    #Get all transport zones
    r = get('/api/v1/transport-zones')

    #Get the zone info
    request_body = load_json("transport_zone.json")
    zid = {}

    for tzone in r.json()["results"]:
        for item in request_body["transport_zones"]:
            if(tzone["display_name"] == item["display_name"]):
                zid["transport_zone_id"] = tzone["id"]
                zid["transport_zone_profile_ids"] = tzone["transport_zone_profile_ids"]

    r = get('/api/v1/transport-node-profiles', ignore_plan=True)
    for item in r.json()["results"]:
        for pr in item["host_switch_spec"]["host_switches"]:
            a = pr["transport_zone_endpoints"]
            a.append(zid)
            del pr["transport_zone_endpoints"]
            pr['transport_zone_endpoints'] = a
            #Make API call to update the node
            api = "/api/v1/transport-node-profiles/"+item["id"]
            g = put(api,item)
            pretty_response(g)
    print(banner("Updating transport node profile end"))

def create_segments(paramfile):
    print(banner("Creating segments start"))
    post('/policy/api/v1/infra/sites/default/enforcement-points/default?action=reload', {})

    r = get('/api/v1/transport-zones')
    request_body = load_json(paramfile)
    for item in request_body['segments']:
        for e in r.json()["results"]:
            if(e["display_name"] == item["transport_zone_path"]):
                g = get('/policy/api/v1/infra/sites/default/enforcement-points/default/transport-zones/'+e["id"])
                item["transport_zone_path"] = g.json()["path"]
                patch('/policy/api/v1/infra/segments/' + item['display_name'], item)
                i = get('/policy/api/v1/infra/segments/' + item['display_name'])
                if(i):
                    print("Segment: "+ str(item['display_name'])+ " created.....\n")
                else:
                    print("Error creating segment(s)")
    print(banner("Creating segments end"))
    return True 

    
def delete_segments(paramfile):
    print(banner("Delete Segments"))
    # So that the VIF attachments are gone. There is a better way to do this.
    #time.sleep(60)
    request_body = load_json(paramfile)
    for item in request_body['segments']:
        delete('/policy/api/v1/infra/segments/' + item['display_name'])

    return True

def create_transport_zone():
    print (banner("Creating Transport Zones start"))
    request_body = load_json('transport_zone.json')
    e_tzs = []
    r = get('/api/v1/transport-zones')
    for i in r.json()['results']:
        e_tzs.append(i['display_name'])

    for item in request_body['transport_zones']:
        if (item['display_name'] not in e_tzs):
            r = post('/api/v1/transport-zones', item)
            pretty_response(r)

    print (banner("Creating Transport Zones end"))
    return True

def delete_transport_zone():
    print (banner("Deleting Transport Zones"))
    tz = {}
    r = get('/api/v1/transport-zones', ignore_plan=True)
    if (r.json()['result_count'] == 2):
        return True

    for item in r.json()['results']:
        tz[item['display_name']] = item['id']
    if tz:
        request_body = load_json('transport_zone.json')
        for item in request_body['transport_zones']:
            id = tz[item['display_name']]
            delete('/api/v1/transport-zones/' + id)
    return True

def delete_tier0():
    print (banner("Delete Tier0"))
    request_body = load_json('create_tier0.json')

    tier0_id = request_body['tier0s'][0]['id']
    ls_id = request_body['localeservices'][0]['id']
    base_uri = '/policy/api/v1/infra/tier-0s/' + tier0_id + '/locale-services/' + ls_id

    log('  +-- Deleting BGP neighbors')
    for bgpn in request_body['bgpneighbors']:
        uri = base_uri + '/bgp/neighbors/' + bgpn['id']
        delete(uri)

    log("  +-- Deleting Interfaces")
    for iface in request_body['interfaces']:
        uri = base_uri + '/interfaces/' + iface['id']
        delete(uri)

    log ("  +-- Deleting locale services")
    delete(base_uri)

    log("  +-- Deleting Tier0 GW")
    for item in request_body['tier0s']:
        delete('/policy/api/v1/infra/tier-0s/' + item['id'])

    return True

def create_tier0_vrf():

    print(banner("Creating T0/T0 VRF gateways start"))


    #Get Path of existing T0 gateway
    tpath = ""
    r = get('/policy/api/v1/infra/tier-0s')
    #pretty_response(r)
    for i in r.json()["results"]:
        if ("vrf_config" not in i):
            tpath = i["path"]
        else :
            print("Existing VRF Gateway: "+ str(i["display_name"]))
    if(tpath):
        print("New VRF gateway(s) will be created from: "+ tpath )
    else:
        raise ("Error! getting existing T0 path. Please check if a T0 exists and is valid!")


    #Get edge node IDs and update a JSON object with member Index
    edge_node_id = {}
    r = get('/api/v1/edge-clusters', ignore_plan=True)
    pretty_response(r)
    try:
        edge_node_id["if0"] = str(r.json()['results'][0]['members'][0]['member_index'])
        edge_node_id["if1"]= str(r.json()['results'][0]['members'][1]['member_index'])
        edge_cluster_id = r.json()['results'][0]['id']
    except:
        print("Error getting member index from the edge cluster")


    #Create T0 VRF gateways based on JSON input 
    request_body = load_json('create_vrf.json')
    for item in request_body['tier0s']:
        item["vrf_config"]["tier0_path"] = tpath

        print(banner("Creating a T0 gateway: "+ str(item['display_name'])))
        r = patch('/policy/api/v1/infra/tier-0s/' + item['display_name'], item)
        pretty_response(r)
        time.sleep(2)
        #Create T1 gateways and attach
        tier1_body = load_json('create_tier1s.json')
        for t1 in tier1_body['tier-1s']:
            if(t1["t0_id"] == item['id'] ):
                print(banner("Attaching to Tier1"))
                t1['tier0_path'] = "/infra/tier-0s/" + item['id']
                #delete the t0 key before patch
                del t1["t0_id"]
                rt = patch('/policy/api/v1/infra/tier-1s/' + t1['display_name'], t1)
                pretty_response(rt)
            # Sync enforcement point
        r =  post('/policy/api/v1/infra/sites/default/enforcement-points/default?action=reload', {})
        pretty_response(r)
        time.sleep(2)
        #Create route re-distribution for VRF Gateway
        print('  +-- Setting Route Re-distribution rules')
        for ls in request_body['localeservices']:
            ls['edge_cluster_path'] = '/infra/sites/default/enforcement-points/default/edge-clusters/' + edge_cluster_id
            uri_local = '/policy/api/v1/infra/tier-0s/' + item['id'] + '/locale-services/' + (ls['id'] + item['display_name'])
            #base_uri = uri
            r = patch(uri_local, ls)
            pretty_response(r)

        time.sleep(2)
        #Get the local service ID for this VRF gayteway
        print("Getting the local service ID for VRF gateway")
        localsvc = get('/policy/api/v1/infra/tier-0s/'+item['display_name']+'/locale-services')
        local_service_path = localsvc.json()["results"][0]["path"]
        edge_cluster_path = localsvc.json()["results"][0]["edge_cluster_path"]

        time.sleep(2)
        #Attach interfaces to the VRF Gateway
        print(banner('Creating interfaces on Tier0 VRF '+ str(item['display_name']) ))
        
        for iface in request_body['interfaces']:     
            try:
                if(iface["t0_id"] == item['id']):
                    print(banner("Adding interfaces to "+ str(item['id'])))
                    if (iface['edge_path'] == "EDGE1_PATH"  ):
                        edge_path = edge_cluster_path + '/edge-nodes/' +  edge_node_id["if0"]
                    elif (iface['edge_path'] == "EDGE2_PATH"):
                        edge_path = edge_cluster_path + '/edge-nodes/' +  edge_node_id["if1"]                
                    iface['edge_path'] = edge_path
                    uri = "/policy/api/v1"+ local_service_path + '/interfaces/' + iface['id']
                    del iface["t0_id"]
                    r = patch(uri, iface)
                    pretty_response(r)
            except Exception as e:
                print(e)
        
        #Get the interfaces from T0 Gateway
        print(banner("Getting the Interfaces for T0: "+str(item["id"])))
        uri_if= uri_local+"/interfaces"
        r = get(uri_if)
        ifpath = []
        for p in r.json()["results"]:
            ifpath.append(p["path"])
        #print("Added T0 interfaces to an array: "+ str(ifpath))

        #Update the HA VIP for each T0 Gateway
        print("Updating HA VIP Configuration for : "+ str(item["id"]))
        for vip in request_body['havip']:
            if (vip["t0_id"]) == item['id']:
                vip["ha_vip_configs"][0]["external_interface_paths"] = ifpath
                #removing custom key before the API call
                del vip["t0_id"]
                r = patch(uri_local,vip)
                pretty_response(r)
                #Adding the T0 identifier key back for the processing of next elements. 
                vip["t0_id"] = item["id"]

        #Update the static route on each T0 Gateway
        #for item in request_body['tier0s']:
        for rt in request_body['static_routes']:
            if (rt["t0_id"]) == item['id']:
                del rt["t0_id"]
                print("Adding static route : "+ str(item["id"])+ "\n"+str(rt))    
                r = patch("/policy/api/v1/infra/tier-0s/"+item["id"]+"/static-routes/static_"+item["id"],rt)
                pretty_response(r)
                rt["t0_id"] = item["id"]   
    print(banner("Creating T0/T0 VRF gateways end"))     

def update_tier1():
    print(banner("Update tier1 gateway start"))
    request_body = load_json('create_tier1s.json')

    #Update the route advertisment on each T1 router
    for item in request_body["tier-1s"]:
        url = "/policy/api/v1/infra/tier-1s/"+item["display_name"]
        print("Updating route advertisment on Tier-1: "+ str(item["display_name"]+ "\n")+ str(request_body["route_advertisment"]))
        r = patch(url,request_body["route_advertisment"])
        pretty_response(r)

        # Get Edge IDs and Edge Cluster ID
        # Assumes only 1
        #Get edge node IDs and update a JSON object with member Index
        edge_node_id = {}
        r = get('/api/v1/edge-clusters', ignore_plan=True)
        pretty_response(r)
        try:
            edge_node_id["if0"] = str(r.json()['results'][0]['members'][0]['member_index'])
            edge_node_id["if1"]= str(r.json()['results'][0]['members'][1]['member_index'])
            edge_cluster_id = r.json()['results'][0]['id']
        except:
            print("Error getting member index from the edge cluster")

        # Update Edge Cluster (as a locale-service)
        json_body = {}
        json_body['edge_cluster_path'] = '/infra/sites/default/enforcement-points/default/edge-clusters/' + edge_cluster_id

        uri = "/policy/api/v1/infra/tier-1s/" + item['display_name'] + "/locale-services/"

        r = get(uri, ignore_plan=True)
        if r.json()['result_count'] == 0:
            uri = uri + "ls-"+item["display_name"]
        else:
            ls_id = ""
            for item in r.json()['results']:
                ls_id = item['id']
                uri = uri + ls_id
        print("Updating Tier-1: "+ str(item["display_name"]) + " with edge cluster : "+ str(json_body))
        r = patch(uri, json_body)
        pretty_response(r)

        #Update the DHCP server configuration path
        r = get("/policy/api/v1/infra/dhcp-server-configs")
        json_body_dhcp = {}
        pretty_response(r)
        for item in r.json()["results"]:
            if((item["display_name"]).lower() == (request_body["dhcp_profile"]).lower()):
                print(item["path"])
                json_body_dhcp["dhcp_config_paths"]= [item["path"]]
            else:
                json_body_dhcp["dhcp_config_paths"]= []
                print("DHCP Config in create_tier1s.json could not be found. Setting the server to null")
        
        print("Updating Tier-1: "+ str(item["display_name"]) + " with DHCP Configuration : "+ str(json_body_dhcp))
        r = patch(url, json_body_dhcp)
        pretty_response(r)
    print(banner("Update tier1 gateway end"))

def update_edge_transport_zone():
    print(banner("Updating edge transport node begin."))

    #Get all transport zones
    r = get('/api/v1/transport-zones')

    #Get the zone info
    request_body = load_json("transport_zone.json")
    zid = {}

    #Get zone identifier from the TZ
    for tzone in r.json()["results"]:
        for item in request_body["transport_zones"]:
            if(tzone["display_name"] == item["display_name"]):
                zid["transport_zone_id"] = tzone["id"]
                zid["transport_zone_profile_ids"] = tzone["transport_zone_profile_ids"]

    #Get transport node information
    r = get('/api/v1/transport-nodes', ignore_plan=True)
    for item in r.json()["results"]:
        if ("edge" in item["display_name"]):
            print("Processing: "+str(item["display_name"]))
            for pr in item["host_switch_spec"]["host_switches"]:
                #********************REPLACE NVDS NAME FOR NON OCVS DEPLOYMENTS*******************
                #Replace the switch name with NVDS switch name. The name will only work with OCVS
                if( pr["host_switch_name"] == "oci-w01-vds02"):
                        b = pr["transport_zone_endpoints"]
                        #Update the key with new transport zone info
                        b.append(zid)
                        del pr["transport_zone_endpoints"]
                        pr["transport_zone_endpoints"] = b
                        #Make API call to update the node
                        api = "/api/v1/transport-nodes/"+item["id"]
                        g = put(api,item)
                        pretty_response(g)
                        break
    #print("Sleeping for 60 seconds for the transport zones to update")
    #time.sleep(60)
    print(banner("Updating edge transport node end.") )

def update_logical_switch_vlan():
    print(banner("Updating NSX logical swith to allow all VLANS start"))
    try:
        r = get("/api/v1/logical-switches/")
        vlan = ""
        for item in r.json()["results"]:
            if(item["display_name"] == "edge-ns"):
                if(item["vlan"]):
                    vlan = item["vlan"]
                    print("VLAN on Logical Switch: "+ str(item["display_name"])+ " VLAN ID: "+ str(vlan)+ " will be updated with 0-4094\n")
                    del item["vlan"]
                item["vlan_trunk_spec"] = {
                                            "vlan_ranges": [
                                                {
                                                    "end": 4094,
                                                    "start": 0
                                                }
                                            ]
                                        }

                api = ("/api/v1/logical-switches/"+item["id"])
                r = put(api,item)
                pretty_response(r)

        update_segment_vlan(vlan)
    except Exception as e:
        print("Error updating the logical switch VLAN" + str(e))
    print(banner("Updating NSX logical swith to allow all VLANS end"))

def update_segment_vlan(vlan):
    print(banner("Update segment VLAN start"))
    if(vlan):
        print("Updating the NSX-Edge-VCN-Segment with the VLAN: "+ str(vlan))
        patch("/policy/api/v1/infra/segments/NSX-Edge-VCN-Segment",{"vlan_ids":[vlan]})
        r = get("/policy/api/v1/infra/segments/NSX-Edge-VCN-Segment")
        pretty_response(r)
    else:
        print("Invalid VLAN ID")
    print(banner("Update segment VLAN end"))

def build_environment():
    update_logical_switch_vlan()
    create_transport_zone()
    update_transport_node_profile()
    update_edge_transport_zone()
    create_segments("create_segments_for_uplinks.json")
    create_tier0_vrf()
    update_tier1()
    create_segments("create_l3_segments.json")


def delete_environemnt():
    #delete_transport_zone()
    #delete_segments("create_segments_for_uplinks.json")
    delete_segments("create_l3_segments.json")



def main():
    build_environment()
    #delete_environemnt()
    

    

    

config = load_json("environment.json")
nsx_ip = config["nsx_ip"]
nsx_port = config["nsx_port"]


# Supress SSL warning
requests.packages.urllib3.disable_warnings() 

# Supress SSH/Paramiko warnings
warnings.filterwarnings("ignore") 


headers = {
  'Authorization': config["basic_auth"],
  'Content-Type': 'application/json'
}

if __name__ == "__main__":
    main()
