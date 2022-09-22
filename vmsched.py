from email.policy import default
import requests, os, time, sys, getopt, copy, json
from collections import defaultdict
from resultfilehandler import ResultFileHandler
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
import numpy as np
import matplotlib.pyplot as plt
import threading, subprocess, libvirt

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

SCOPE_MN = 60
TIER1_MN = 20
TIER2_MN = 40
DEBUG = False
DEBUG_TARGET = "cpu"
DEBUG_TARGET_USAGE = DEBUG_TARGET + "_usage"

TEMP_ENDPOINT_CONFIG = "/var/lib/vmsched/status.json"
#TEMP_LIBVIRT_HOST = "qemu+ssh://pijacque@spirals-tornado.lille.inria.fr/system?keyfile=id_rsa"
TEMP_LIBVIRT_HOST = "qemu:///system"

#grace_period_tracker = defaultdict(lambda: int(time.time())) #default is current epoch in s
grace_period_tracker = defaultdict(lambda: int(0))
grace_period = 600

class RssReducer(object):

    def __init__(self, domain : str, mem_retrieval_thresold : int):
        self.domain=domain
        self.mem_retrieval_thresold=mem_retrieval_thresold*1024

    def run(self):
        conn = None
        def target():
            try:
                conn = libvirt.open(TEMP_LIBVIRT_HOST)
            except libvirt.libvirtError as e:
                print(repr(e), file=sys.stderr)
                exit(1)
            dom = conn.lookupByName(self.domain)
            if(self.mem_retrieval_thresold<2048000):
                self.mem_retrieval_thresold=2048000
            if dom == None:
                print('Failed to find the domain '+ self.domain, file=sys.stderr)
                exit(1)
            print("Reduce", self.domain, "to", self.mem_retrieval_thresold, dom.setMemoryFlags(self.mem_retrieval_thresold,flags=libvirt.VIR_DOMAIN_AFFECT_LIVE))
            time.sleep(180)
            print("Increase", self.domain, "to", dom.maxMemory(), dom.setMemoryFlags(dom.maxMemory(),flags=libvirt.VIR_DOMAIN_AFFECT_LIVE))
            conn.close()

        thread = threading.Thread(target=target)
        thread.start()

def check_rss(domain : str, domain_metrics : dict, delay_metrics : list):
    ## Check if VM is in grace period
    if (grace_period_tracker[domain] + grace_period) > int(time.time()):
        print(domain, "is in grace period")
        return
    mem_usage = np.percentile(domain_metrics['mem_usage'], 90)
    mem_rss = domain_metrics['mem_rss'][-1]
    mem_retrieval = mem_rss - mem_usage
    print("debug", domain, mem_usage, mem_rss, mem_retrieval)
    if mem_retrieval > 2048: # We can retrieve at least 2GB
        print("geronimo")
        reducer = RssReducer(domain, mem_usage)
        reducer.run()
        grace_period_tracker[domain] = int(time.time()) # update grace_period_tracker

def monitor_nodes():
    myurl = os.getenv('INFLUXDB_URL')
    mytoken = os.getenv('INFLUXDB_TOKEN')
    myorg = os.getenv('INFLUXDB_ORG')
    mybucket = os.getenv('INFLUXDB_BUCKET')

    client = InfluxDBClient(url=myurl, token=mytoken, org=myorg)
    query_api = client.query_api()
    query = ' from(bucket:"' + mybucket + '")\
    |> range(start: -' + str(SCOPE_MN) + 'm)\
    |> filter(fn:(r) => r._measurement == "node")'
    # |> keep(columns: ["oc_mem"])'

    result = query_api.query(org=myorg, query=query)

    nodes = defaultdict(lambda: defaultdict(list))

    for table in result:
        for record in table.records:
            url = record.__getitem__('url')
            timestamp = (record.get_time()).timestamp()
            if timestamp not in nodes[url]["time"]: #possibly a hotspot
                nodes[url]["time"].append(timestamp)
            nodes[url][record.get_field()].append(record.get_value())

    for node in nodes.keys():
        nodes[node]["domains"] = monitor_domains(node)

    return nodes

def monitor_domains(url : str):
    myurl = os.getenv('INFLUXDB_URL')
    mytoken = os.getenv('INFLUXDB_TOKEN')
    myorg = os.getenv('INFLUXDB_ORG')
    mybucket = os.getenv('INFLUXDB_BUCKET')

    client = InfluxDBClient(url=myurl, token=mytoken, org=myorg)
    query_api = client.query_api()
    query = ' from(bucket:"' + mybucket + '")\
    |> range(start: -' + str(SCOPE_MN) + 'm)\
    |> filter(fn: (r) => r["_measurement"] == "domain")\
    |> filter(fn: (r) => r["url"] == "' + url + '")'

    result = query_api.query(org=myorg, query=query)
    domains = defaultdict(lambda: defaultdict(list))

    for table in result:
        for record in table.records:
            domain_name = record.__getitem__('domain')
            domains[domain_name][record.get_field()].append(record.get_value())

    return domains

def compute_percentile(metrics : list):
    if(metrics):
        return np.percentile(metrics,90)
    else:
        return 0

def compute_lifetime_indicator(domain_metrics : dict, delay_metrics : list):
    delay = round(delay_metrics[1] - delay_metrics[0])
    lifetime =  len(domain_metrics['cpu_time']) * delay
    if lifetime < TIER1_MN*60:
        return 0
    elif lifetime < TIER2_MN*60:
        return 1
    else:
        return 2

def compute_domain_tiers(domain_metrics : dict, delay_metrics : list):
    lifetime = compute_lifetime_indicator(domain_metrics, delay_metrics[-2:])
    if lifetime == 0:
        # Between t0 and t1 : we garantee the booked ressources to the VM
        cpu_max = np.max(domain_metrics['cpu'])
        mem_max = np.max(domain_metrics['mem'])
        return cpu_max, cpu_max, mem_max, mem_max
    elif lifetime == 1:
        # Between t1 and t2 : we garantee the percentile to the VM and keep the booked ressources in flex space
        cpu_percentile = compute_percentile(domain_metrics['cpu_usage'])
        cpu_max = np.max(domain_metrics['cpu'])
        mem_percentile = compute_percentile(domain_metrics['mem_rss'])
        mem_max = np.max(domain_metrics['mem'])
        return cpu_percentile, cpu_max, mem_percentile, mem_max
    else:
        # From t2 : we use the average and percentile value only
        cpu_avg = np.average(domain_metrics['cpu_usage'])
        cpu_percentile = compute_percentile(domain_metrics['cpu_usage'])
        mem_avg = np.average(domain_metrics['mem_rss'])
        mem_percentile = compute_percentile(domain_metrics['mem_rss'])
        return cpu_avg, cpu_percentile, mem_avg, mem_percentile

def analyze_metrics(metrics : dict):

    tiers = dict()
    for node, node_metrics in metrics.items():

        cpu_tiers = [0, 0, node_metrics['cpu'][-1]]
        mem_tiers = [0, 0, node_metrics['mem'][-1]]

        oc_cpu = node_metrics['oc_cpu'][-1] # can also use oc_cpu_d?
        alpha_oc_cpu = 1 + (oc_cpu/10)
        oc_mem = node_metrics['oc_mem'][-1]

        curr_freq = node_metrics['freq'][-1]
        min_freq = node_metrics['minfreq'][-1]
        max_freq = node_metrics['maxfreq'][-1]
        #print(curr_freq, round((curr_freq/max_freq),2), min_freq, max_freq)

        debug_list = list()
        print("debug1", node, node_metrics['domains'].keys())
        for domain_name, domain_metrics in node_metrics['domains'].items():

            # Reduce its rss if needed
            check_rss(domain_name, domain_metrics, node_metrics['time'][-2:])

            # Compute metrics
            cpu_tier0, cpu_tier1, mem_tier0, mem_tier1 = compute_domain_tiers(domain_metrics, node_metrics['time'][-2:])
            cpu_tiers[0] += cpu_tier0
            cpu_tiers[1] += cpu_tier1
            mem_tiers[0] += mem_tier0
            mem_tiers[1] += mem_tier1

            if(DEBUG):
                #print(domain_name, cpu_tier0, cpu_tier1, mem_tier0, mem_tier1)
                occurence = len(domain_metrics[DEBUG_TARGET_USAGE])
                if (not debug_list):
                    debug_list = [0] * occurence
                    plt.fill_between(node_metrics["time"][0:occurence], debug_list, domain_metrics[DEBUG_TARGET_USAGE])
                else:
                    prev_occurence = len(debug_list)
                    for i in range (0,(prev_occurence - occurence)):
                        debug_list.pop()
                    for i in range (0,(occurence - prev_occurence)):
                        domain_metrics[DEBUG_TARGET_USAGE].pop()
                    occurence = len(debug_list)
                    prev_list = debug_list.copy()
                    for i in range(0,occurence-1):
                        debug_list[i]+=domain_metrics[DEBUG_TARGET_USAGE][i]
                    plt.fill_between(node_metrics["time"][0:occurence], prev_list, debug_list)

        tiers[node] = dict()

        tiers[node]["cpu"] = dict()
        tiers[node]["cpu"]["tier0"] = min(cpu_tiers[0]*alpha_oc_cpu, cpu_tiers[2])
        if (cpu_tiers[1]*alpha_oc_cpu)<cpu_tiers[2]:
            tiers[node]["cpu"]["tier1"] = (cpu_tiers[1]*alpha_oc_cpu) - tiers[node]["cpu"]["tier0"]
            tiers[node]["cpu"]["tier2"] = cpu_tiers[2] - (cpu_tiers[1]*alpha_oc_cpu)
        else:
            tiers[node]["cpu"]["tier1"] = max(0, cpu_tiers[2] - tiers[node]["cpu"]["tier0"])
            tiers[node]["cpu"]["tier2"] = 0

        tiers[node]["mem"] = dict()
        tiers[node]["mem"]["tier0"] = min(mem_tiers[0], mem_tiers[2])
        if mem_tiers[1]<mem_tiers[2]:
            tiers[node]["mem"]["tier1"] = mem_tiers[1] - tiers[node]["mem"]["tier0"]
            tiers[node]["mem"]["tier2"] = mem_tiers[2] - mem_tiers[1]
        else:
            tiers[node]["mem"]["tier1"] = max(0, mem_tiers[2] - tiers[node]["mem"]["tier0"])
            tiers[node]["mem"]["tier2"] = 0

        if(DEBUG):
            print("On node", node, "oc", oc_cpu, "alpha", alpha_oc_cpu)
            print("On node", node, "Guaranted CPU", round(tiers[node]["cpu"]["tier0"], 2), "cores")
            print("On node", node, "Flex CPU ", round(tiers[node]["cpu"]["tier1"] ,2), "cores")
            print("On node", node, "Free CPU ", tiers[node]["cpu"]["tier2"], "cores")

            print("On node", node, "Guaranted mem", round(tiers[node]["mem"]["tier0"] ,2), "MB")
            print("On node", node, "Flex mem", round(tiers[node]["mem"]["tier1"] ,2), "MB")
            print("On node", node, "Free mem", tiers[node]["mem"]["tier2"], "MB")

            plt.plot(node_metrics["time"][0:len(node_metrics[DEBUG_TARGET_USAGE])], node_metrics[DEBUG_TARGET_USAGE], label="node", color="black", linestyle="-")
            x_axis = [node_metrics["time"][0], node_metrics["time"][-1]]
            plt.fill_between(x_axis, [0,0], [tiers[node][DEBUG_TARGET]["tier0"], tiers[node][DEBUG_TARGET]["tier0"]], alpha=0.2, label="tier0", linestyle="--", color='red')
            if tiers[node][DEBUG_TARGET]["tier1"]>0:
                real_tier1 = tiers[node][DEBUG_TARGET]["tier0"] + tiers[node][DEBUG_TARGET]["tier1"]
                plt.fill_between(x_axis, [tiers[node][DEBUG_TARGET]["tier0"], tiers[node][DEBUG_TARGET]["tier0"]], [real_tier1, real_tier1], alpha=0.2, label="tier1", linestyle="--", color='orange')
            if tiers[node][DEBUG_TARGET]["tier2"]>0:
                real_tier2 = real_tier1 + tiers[node][DEBUG_TARGET]["tier2"]
                plt.fill_between(x_axis, [real_tier1, real_tier1], [real_tier2, real_tier2], label="tier2", alpha=0.2, linestyle="--", color='green')
            plt.legend(loc="upper left")
            plt.title(DEBUG_TARGET)
            plt.show()

    return tiers

def main_loop():
    filehandler = ResultFileHandler()
    while True:
        tiers = analyze_metrics(monitor_nodes())
        filehandler.writeResult(TEMP_ENDPOINT_CONFIG, tiers)
        time.sleep(30)

if __name__ == '__main__':

    load_dotenv()
    short_options = "ho:du:"
    long_options = ["help", "output=","d","url="]

    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        print (str(err)) # Output error, and return with an error code
        sys.exit(2)
    for current_argument, current_value in arguments:
        if current_argument in ("-h", "--help"):
            print("python3 vmaggreg.py [--help] [--output=''] [--debug] [--url={url}]")
            sys.exit(0)
        elif current_argument in ("-o", "--output"):
            OUTPUT_FILE = current_value
        elif current_argument in ("-u", "--url"):
            STUB_URL = current_value
        elif current_argument in ("-d", "--debug"):
            DEBUG = True

    try:
        main_loop()
    except KeyboardInterrupt:
        print("Program interrupted")
