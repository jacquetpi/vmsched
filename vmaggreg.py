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
            raise ValueError('Unknown key', splited_key[1])

    return probe_metrics

def add_field(harvested_metrics : dict, field : str, value : float):
    if 'fields' in harvested_metrics:
        harvested_metrics['fields'][field] = value
    else:
        harvested_metrics[field] = value
    return True

def add_field_if_exists(harvested_metrics : dict, field : str, probe_value : float, reductor : int = 1):
    if probe_value is not None:
        value =  probe_value / reductor
        return add_field(harvested_metrics, field, value)
    else:
        return False

def add_sum_if_exists(harvested_metrics : dict, field : str, probe_value1 : float, probe_value2 : float, reductor : int = 1):
    if (probe_value1 is not None) and (probe_value2 is not None):
        value =  (probe_value1 + probe_value2) / reductor
        return add_field(harvested_metrics, field, value)
    else:
        return False

def add_difference_if_exists(harvested_metrics : dict, field : str, probe_value1 : float, probe_value2 : float, reductor : int = 1):
    if (probe_value1 is not None) and (probe_value2 is not None):
        value =  (probe_value1 - probe_value2) / reductor
        return add_field(harvested_metrics, field, value)
    else:
        return False

def add_ratio_if_exists(harvested_metrics : dict, field : str, probe_value1 : float, probe_value2 : float, reductor : int = 1):
    if (probe_value1 is not None) and (probe_value2 is not None):
        if probe_value2>0.0:
            value =  (probe_value1 / probe_value2) / reductor
        else:
            value = 0.0
        return add_field(harvested_metrics, field, value)
    else:
        return False

def treat_domain_metrics_delta(elapsed_time : int, vm_metrics : dict, domain_metrics : dict, vm_previous_metrics, vm_saved_metrics : dict):

    cpu_usage = 0
    if add_difference_if_exists(vm_metrics, 'elapsed_cpu_time', vm_metrics['fields'].get('cpu_time'), vm_previous_metrics.get('cpu_time')):
        if add_ratio_if_exists(vm_metrics, 'cpu_usage', vm_metrics['fields'].get('elapsed_cpu_time'), elapsed_time, (10**6)):
            cpu_usage = vm_metrics['fields']['cpu_usage']
            vm_saved_metrics['cpu_usage'] = cpu_usage 

    delta_perf = dict()

    if 'perf' in domain_metrics:

        add_ratio_if_exists(vm_metrics, 'cpi', domain_metrics['perf'].get('hwcpucycles'), domain_metrics['perf'].get('hwinstructions'))
        add_ratio_if_exists(vm_metrics, 'bmr', domain_metrics['perf'].get('hwbranchmisses'), domain_metrics['perf'].get('hwbranchinstructions'))
        add_ratio_if_exists(vm_metrics, 'cmr', domain_metrics['perf'].get('hwcachemisses'), domain_metrics['perf'].get('hwcachereferences'))

        for key in domain_metrics['perf'].keys():
            add_field_if_exists(vm_metrics, key, domain_metrics['perf'].get(key))

    return cpu_usage

def treat_domain_metrics(domain_name : str, url :str, epoch_ms : int, domain_metrics : dict, vm_previous_metrics, elapsed_time):

    vm_metrics = {"measurement": "domain", "tags": {"url": url, "domain": domain_name}, "fields": dict(), "time": datetime.fromtimestamp(epoch_ms/1000, timezone.utc)}
    
    vm_saved_metrics = dict()

    if 'memory' in domain_metrics:
        add_field_if_exists(vm_metrics, 'mem', domain_metrics['memory'].get('alloc'), (10**3)) #MB
        add_field_if_exists(vm_metrics, 'mem_rss', domain_metrics['memory'].get('rss'), (10**3))

        add_difference_if_exists(vm_metrics, 'mem_usage', domain_metrics['memory'].get('alloc'), domain_metrics['memory'].get('unused'), (10**3))

    if 'cpu' in domain_metrics:
        add_field_if_exists(vm_metrics, 'cpu', domain_metrics['cpu'].get('alloc'))
        if add_field_if_exists(vm_metrics, 'cpu_time', domain_metrics['cpu'].get('cputime')):
            vm_saved_metrics['cpu_time'] = vm_metrics['fields']['cpu_time']

    if elapsed_time>0:
        cpu_usage = treat_domain_metrics_delta(elapsed_time, vm_metrics, domain_metrics, vm_previous_metrics, vm_saved_metrics)
    else:
        cpu_usage = vm_previous_metrics.get('cpu_usage', 0)

    return vm_metrics, vm_saved_metrics, vm_metrics['fields'].get('cpu', 0), cpu_usage, vm_metrics['fields'].get('mem', vm_previous_metrics.get('mem', 0)), vm_metrics['fields'].get('mem_usage',  vm_previous_metrics.get('mem_usage', 0))

def treat_stub_metrics(url : str, probe_metrics : dict, previous_metrics : dict = dict()):

    global FETCH_DELAY
    elapsed_time = 0
    saved_metrics = dict() # Used to compute delta between fetch
    saved_metrics['domain'] = dict()

    if 'global' not in probe_metrics:
        return previous_metrics # Currently no data
        # raise ValueError("Global metrics not found on endpoint", url)

    epoch_ms = int(probe_metrics['global']['probe']['epoch'])
    node_metrics = {"measurement": "node", "tags": {"url": url}, "fields": dict(), "time": datetime.fromtimestamp(epoch_ms/1000, timezone.utc)}

    if 'perf' in probe_metrics['global']:
        # No need to compute the delta as the probe global perf counters are reset periodically
        add_ratio_if_exists(node_metrics, 'cpi', probe_metrics['global']['perf'].get('hwcpucycles'), probe_metrics['global']['perf'].get('hwinstructions'))
        add_ratio_if_exists(node_metrics, 'bmr', probe_metrics['global']['perf'].get('hwbranchmisses'), probe_metrics['global']['perf'].get('hwbranchinstructions'))
        add_ratio_if_exists(node_metrics, 'cmr', probe_metrics['global']['perf'].get('hwcachemisses'), probe_metrics['global']['perf'].get('hwcachereferences'))

        for key in probe_metrics['global']['perf'].keys():
            add_field_if_exists(node_metrics, key, probe_metrics['global']['perf'].get(key))

    if 'cpu' in probe_metrics['global']:
        add_field_if_exists(node_metrics, 'freq', probe_metrics['global']['cpu'].get('freq'))
        add_field_if_exists(node_metrics, 'minfreq', probe_metrics['global']['cpu'].get('minfreq'))
        add_field_if_exists(node_metrics, 'maxfreq', probe_metrics['global']['cpu'].get('maxfreq'))
        add_field_if_exists(node_metrics, 'cpu', probe_metrics['global']['cpu'].get('total'))

        add_sum_if_exists(node_metrics, 'cpu_time', probe_metrics['global']['cpu'].get('kernel'), probe_metrics['global']['cpu'].get('user'))
        add_field_if_exists(node_metrics, 'freq', probe_metrics['global']['cpu'].get('freq'))

    if 'memory' in probe_metrics['global']:
        add_field_if_exists(node_metrics, 'mem', probe_metrics['global']['memory'].get('total'), (10**3)) # MB
        add_difference_if_exists(node_metrics, 'mem_usage', probe_metrics['global']['memory'].get('total'), probe_metrics['global']['memory'].get('available'), (10**3)) # MB

    if 'probe' in probe_metrics['global']:
        if previous_metrics:
            does_exist = add_difference_if_exists(node_metrics, 'elapsed_time', probe_metrics['global']['probe'].get('epoch'), previous_metrics.get('epoch'))
            if does_exist and node_metrics['fields']['elapsed_time']>0:
                elapsed_time = node_metrics['fields']['elapsed_time']
                add_difference_if_exists(node_metrics, 'elapsed_cpu_time', node_metrics['fields'].get('cpu_time'), previous_metrics.get('cpu_time'))
                add_ratio_if_exists(node_metrics, 'cpu_usage', node_metrics['fields'].get('elapsed_cpu_time'), node_metrics['fields'].get('elapsed_time'), (10**6))
                add_field_if_exists(saved_metrics, 'cpu_usage', node_metrics['fields'].get('cpu_usage')) #for next round$
            else:
                add_field_if_exists(node_metrics, 'cpu_usage', previous_metrics.get('cpu_usage'))

        add_field_if_exists(saved_metrics, 'epoch', probe_metrics['global']['probe'].get('epoch'))
        if FETCH_DELAY == 0:
            FETCH_DELAY=probe_metrics['global']['probe']['delay']

    add_field_if_exists(saved_metrics, 'cpu_time', node_metrics['fields'].get('cpu_time'))

    if 'domain' in probe_metrics:
        node_metrics['fields']['vm_number'] = len(probe_metrics['domain'].keys())

        cpu_alloc_sum = mem_alloc_sum = 0
        cpu_real_sum = mem_real_sum = 0

        for domain_name, domain_metrics in probe_metrics['domain'].items():
            
            if ('domain' in previous_metrics) and (domain_name in previous_metrics['domain']) and (elapsed_time>0):
                vm_metrics, vm_saved_metrics, domain_cpu, domain_cpu_usage, domain_mem, domain_mem_usage = treat_domain_metrics(domain_name, url, epoch_ms, domain_metrics, previous_metrics['domain'][domain_name], elapsed_time)
            else:
                vm_metrics, vm_saved_metrics, domain_cpu, domain_cpu_usage, domain_mem, domain_mem_usage = treat_domain_metrics(domain_name, url, epoch_ms, domain_metrics, dict(), 0)
            cpu_alloc_sum += domain_cpu
            cpu_real_sum += domain_cpu_usage
            mem_alloc_sum += domain_mem
            mem_real_sum += domain_mem_usage

            saved_metrics['domain'][domain_name] = vm_saved_metrics

            store_influx(vm_metrics)
            
        add_ratio_if_exists(node_metrics, 'oc_cpu', cpu_alloc_sum, node_metrics['fields'].get('cpu'))
        add_ratio_if_exists(node_metrics, 'oc_mem', mem_alloc_sum, node_metrics['fields'].get('mem'))
        add_ratio_if_exists(node_metrics, 'oc_cpu_d', cpu_real_sum, node_metrics['fields'].get('cpu'))
        add_ratio_if_exists(node_metrics, 'oc_mem_d', mem_real_sum, node_metrics['fields'].get('mem'))

    else:
        print("No domain metrics")
        node_metrics['fields']['vm_number'] = 0
        add_field_if_exists(node_metrics, 'oc_cpu', 0.0)
        add_field_if_exists(node_metrics, 'oc_mem', 0.0)
        add_field_if_exists(node_metrics, 'oc_cpu_d', 0.0)
        add_field_if_exists(node_metrics, 'oc_mem_d', 0.0)

    store_influx(node_metrics)
    return saved_metrics

def delayer_between_iteration(iteration_start : int):
        """
        We check when was launched the current iteration (and therefore, how long it took) and wait the complementary time to obtain the desired delay
        """
        duration_sec = round((time.time_ns() - iteration_start)/(10**6)) # us to ms
        if duration_sec < FETCH_DELAY:
            time.sleep((FETCH_DELAY - duration_sec)/1000) # ms to s

def store_influx(metrics : dict()):
    myurl = os.getenv('INFLUXDB_URL')
    mytoken = os.getenv('INFLUXDB_TOKEN')
    myorg = os.getenv('INFLUXDB_ORG')
    mybucket = os.getenv('INFLUXDB_BUCKET')
    client = InfluxDBClient(url=myurl, token=mytoken, org=myorg)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    #print(metrics)
    write_api.write(bucket=mybucket, org=myorg, record=metrics)

def monitor():

    begin_time_nanos = time.time_ns()
    previous_timestamp = -1
    previous_stubs_results = dict()

    while True:

        iteration_start = time.time_ns() # Keep the duration start timestamp (EPOCH)

        for stub in STUB_LIST:
            stub_url, stub_prefix = stub

            if stub_url in previous_stubs_results:
                previous_stubs_results[stub_url] = treat_stub_metrics(stub_url, retrieve_stub_metrics(stub_url, stub_prefix), previous_stubs_results[stub_url])
            else:
                previous_stubs_results[stub_url] = treat_stub_metrics(stub_url, retrieve_stub_metrics(stub_url, stub_prefix))

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

    
