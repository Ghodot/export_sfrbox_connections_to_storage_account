import requests
import json
from datetime import datetime
from xml.dom.minidom import parseString
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
import os

measure_time = datetime.now().strftime('%H:%M:%S')

request = requests.get('http://192.168.1.1/api/1.0/?method=lan.getHostsList')

xml_dom = parseString(request.text)

if xml_dom.documentElement.tagName != "rsp":
    raise Exception("Error while reading xml. First node should be rsp")
rsp_node = xml_dom.documentElement

connected_devices_output_string = ''
# Keys need to be ordered because this list is used for csv headers generation
output_keys = ['name', 'ip', 'mac', 'iface']
number_of_keys = len(output_keys)

for child_node in rsp_node.childNodes:
    # The \n in the response are interpreted as text node
    if child_node.nodeType == child_node.TEXT_NODE:
        pass
    else:
        if child_node.tagName != "host":
            raise Exception("Got a node different from host. This should not happen")
        if child_node.getAttribute("status") == 'online':

            for key in output_keys:
                connected_devices_output_string += '"' + child_node.getAttribute(key) + '",'
            
            connected_devices_output_string += measure_time + '\n'
            
connection_string = os.environ['AZURE_STORAGE_SELFDATA_CONNECTION_STRING']
blob_service_client = BlobServiceClient.from_connection_string(conn_str=connection_string)

output_file_path = datetime.now().strftime('%Y-%m-%d.csv')
blob_client = blob_service_client.get_blob_client(container='connections-logs', blob=output_file_path)


try:
    # Check for blob existance. If this doesn't fails, it means the blob exist and we can simply append to it
    blob_client.get_blob_properties()
    print(f"File {output_file_path} exists, appending")
    blob_client.append_block(connected_devices_output_string)
    
except ResourceNotFoundError:
    print(f"File {output_file_path} doesn't exist, creating it")
    blob_client.create_append_blob()
    
    # Initial content provides headers
    blob_initial_content = ','.join(output_keys) + ',measure_time' + '\n' + connected_devices_output_string
    blob_client.append_block(blob_initial_content)
    
