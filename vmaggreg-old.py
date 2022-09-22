import requests, os, time, sys, getopt
from collections import defaultdict
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

#STUB_LIST= [("http://localhost:9101/metrics", "tornado")]
STUB_LIST= [("http://localhost:9100/metrics", "test")]
FETCH_DELAY = 0
OUTPUT_FILE = ""

def retrieve_stub_metrics(stub_url : str, stub_prefix : str):                  
    page = requests.get(url = stub_url)                              
    lines = page.text.splitlines()    

    probe_metrics = defaultdict(dict)

    for line in lines:
        if line[0] == "#":
            continue # Remove comments
        if (not line.startswith(stub_prefix)):
            continue

        splited_line = line.split(' ')
        key = splited_line[0]
        value = float(splited_line[1])

        splited_key = key.split('_')

        if splited_key[1] == 'global':

            if splited_key[2] not in probe_metrics[splited_key[1]]:
                probe_metrics[splited_key[1]][splited_key[2]] = dict()
            probe_metrics[splited_key[1]][splited_key[2]][splited_key[3]] = value
            
        elif splited_key[1] == 'domain':

            if splited_key[2] not in probe_metrics[splited_key[1]]:
                probe_metrics[splited_key[1]][splited_key[2]] = dict()
            if splited_key[3] not in probe_metrics[splited_key[1]][splited_key[2]]:
                probe_metrics[splited_key[1]][splited_key[2]][splited_key[3]] = dict()

            probe_metrics[splited_key[1]][splited_key[2]][splited_key[3]][splited_key[4]] = value

        else:
            raise ValueError('Unknown key')

    return probe_metrics

def treat_stub_metrics(url : str, probe_metrics : dict, previous_metrics : dict = dict()):

    global FETCH_DELAY
    elapsed_time = 0
    saved_metrics = dict() # Used to compute delta between fetch
    saved_metrics['domain'] = dict()

    if 'global' not in probe_metrics:
        return previous_metrics # Currently no data
        # raise ValueError("Global metrics not found on endpoint", url)

    epoch_ms = datetime.fromtimestamp( int(probe_metrics['global']['probe']['epoch']/1000), timezone.utc)
    node_metrics = {"measurement": "node", "tags": {"url": url}, "fields": dict(), "time": epoch_ms}
    node_metrics['fields']['cpi'] = probe_metrics['global']['cpu']['cycles'] / probe_metrics['global']['cpu']['instructions']
    node_metrics['fields']['freq'] = probe_metrics['global']['cpu']['freq']
    node_metrics['fields']['cpu'] = probe_metrics['global']['cpu']['total']
    node_metrics['fields']['cpu_time'] = probe_metrics['global']['cpu']['kernel'] + probe_metrics['global']['cpu']['user']
    node_metrics['fields']['mem'] = (probe_metrics['global']['memory']['total'])/(10**3) # MB
    node_metrics['fields']['mem_usage'] = (probe_metrics['global']['memory']['total'] - probe_metrics['global']['memory']['available'])/(10**3) # MB : TODO vérifier la pertinence

    if previous_metrics:
        elapsed_time = probe_metrics['global']['probe']['epoch'] - previous_metrics['epoch']
        if elapsed_time>0:
            elapsed_cpu_time = node_metrics['fields']['cpu_time'] - previous_metrics['cpu_time']
            node_metrics['fields']['cpu_usage'] = (elapsed_cpu_time/elapsed_time)/(10**9)
            saved_metrics['cpu_usage'] = node_metrics['fields']['cpu_usage']
        else:
            if 'cpu_usage' in previous_metrics:
                node_metrics['fields']['cpu_usage'] = previous_metrics['cpu_usage']

    saved_metrics['epoch'] = probe_metrics['global']['probe']['epoch']
    saved_metrics['cpu_time'] = node_metrics['fields']['cpu_time']

    if FETCH_DELAY == 0:
        FETCH_DELAY=probe_metrics['global']['probe']['delay']

    if 'domain' in probe_metrics:
        node_metrics['fields']['vm_number'] = len(probe_metrics['domain'].keys())

        cpu_alloc_sum = mem_alloc_sum = 0
        cpu_real_sum = mem_real_sum = 0

        for domain_name, domain_metrics in probe_metrics['domain'].items():
            
            vm_metrics = {"measurement": "domain", "tags": {"url": url, "domain": domain_name}, "fields": dict(), "time": epoch_ms}
            
            vm_metrics['fields']['mem'] = domain_metrics['memory']['alloc']/(10**3) # MB
            mem_alloc_sum += vm_metrics['fields']['mem'] 
            vm_metrics['fields']['mem_usage'] = domain_metrics['memory']['rss']/(10**3) # MB TODO vérifier la pertinence
            mem_real_sum += vm_metrics['fields']['mem_usage']

            vm_metrics['fields']['cpu'] = domain_metrics['cpu']['alloc']
            cpu_alloc_sum += vm_metrics['fields']['cpu']
            vm_metrics['fields']['cpu_time'] = domain_metrics['cpu']['cputime']

            if ('domain' in previous_metrics) and (domain_name in previous_metrics['domain']) and (elapsed_time>0):

                elapsed_cpu_time = vm_metrics['fields']['cpu_time'] - previous_metrics['domain'][domain_name]['cpu_time']
                vm_metrics['fields']['cpu_usage'] = (elapsed_cpu_time/elapsed_time)/(10**9)
                cpu_real_sum += vm_metrics['fields']['cpu_usage']

            saved_metrics['domain'][domain_name] = dict()
            saved_metrics['domain'][domain_name]['cpu_time'] = vm_metrics['fields']['cpu_time']
            store_influx(vm_metrics)
            
        node_metrics['fields']['oc_cpu'] = cpu_alloc_sum / node_metrics['fields']['cpu']
        node_metrics['fields']['oc_mem'] = mem_alloc_sum / node_metrics['fields']['mem']
        node_metrics['fields']['oc_cpu_d'] = cpu_real_sum / node_metrics['fields']['cpu']
        node_metrics['fields']['oc_mem_d'] = mem_real_sum / node_metrics['fields']['mem']

    else:
        print("No domain metrics")
        node_metrics['fields']['vm_number'] = 0
        node_metrics['fields']['oc_cpu'] = 0.0
        node_metrics['fields']['oc_mem'] = 0.0
        node_metrics['fields']['oc_cpu_d'] = 0.0
        node_metrics['fields']['oc_mem_d'] = 0.0

    store_influx(node_metrics)
    return saved_metrics

def delayer_between_iteration(iteration_start : int):
        """
        We check when was launched the current iteration (and therefore, how long it took) and wait the complementary time to obtain the desired delay
        """
        duration_sec = round((time.time_ns() - iteration_start)/(10**9))
        if duration_sec < FETCH_DELAY:
            time.sleep(FETCH_DELAY - duration_sec)

def store_influx(metrics : dict()):
    myurl = os.getenv('INFLUXDB_URL')
    mytoken = os.getenv('INFLUXDB_TOKEN')
    myorg = os.getenv('INFLUXDB_ORG')
    mybucket = os.getenv('INFLUXDB_BUCKET')

    client = InfluxDBClient(url=myurl, token=mytoken, org=myorg)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    print(metrics)
    write_api.write(bucket=mybucket, org=myorg, record=metrics)

def monitor():

    begin_time_nanos = time.time_ns()
    previous_timestamp = -1
    previous_stubs_results = dict()

    while True:

        iteration_start = time.time_ns() # Keep the duration start timestamp (EPOCH)
        timestamp_key = round((iteration_start - begin_time_nanos)/(10**9)) # Key of monitoring session is the time since beginning in s

        for stub in STUB_LIST:
            stub_url, stub_prefix = stub

            if stub_url in previous_stubs_results:
                previous_stubs_results[stub_url] = treat_stub_metrics(stub_url, retrieve_stub_metrics(stub_url, stub_prefix), previous_stubs_results[stub_url])
            else:
                previous_stubs_results[stub_url] = treat_stub_metrics(stub_url, retrieve_stub_metrics(stub_url, stub_prefix))

        previous_timestamp = timestamp_key
        delayer_between_iteration(iteration_start)

if __name__ == '__main__':

    load_dotenv()
    short_options = "h:d:t:u:"
    long_options = ["help","timeout=","url="]
 
    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        print (str(err)) # Output error, and return with an error code
        sys.exit(2)
    for current_argument, current_value in arguments:
        if current_argument in ("-h", "--help"):
            print("python3 vmaggreg.py [--help] [--delay={sec}] [--url={url}]")
            sys.exit(0)
        elif current_argument in ("-u", "--url"):
            STUB_URL = current_value

    try:
        monitor()
    except KeyboardInterrupt:
        print("Program interrupted")

    
