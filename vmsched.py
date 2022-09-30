import requests, os, time, sys, getopt, copy, json
from collections import defaultdict
from resultfilehandler import ResultFileHandler
from dotenv import load_dotenv
import numpy as np
import matplotlib.pyplot as plt

from model.nodemodel import NodeModel

# Global parameters
DEBUG = False
DEBUG_TARGET = "cpu"
DEBUG_TARGET_USAGE = DEBUG_TARGET + "_usage"

STATE_ENDPOINT = ""

SCHED_SCOPE_SLICE_MN = 0
SCHED_SCOPE_MN = 0
SCHED_SCOPE_TIER1_MN = 0
SCHED_SCOPE_TIER2_MN = 0
SCHED_SCOPE_SLEEP_S = 0

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
        filehandler.writeResult(STATE_ENDPOINT, tiers)
        time.sleep(SCHED_SCOPE_SLEEP_S)

if __name__ == '__main__':

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

    load_dotenv()
    STATE_ENDPOINT = os.getenv('STATE_ENDPOINT')
    SCHED_SCOPE_SLICE_MN = int(os.getenv('SCHED_SCOPE_SLICE_MN'))
    SCHED_SCOPE_MN = int(os.getenv('SCHED_SCOPE_MN'))
    SCHED_SCOPE_TIER1_MN = int(os.getenv('SCHED_SCOPE_TIER1_MN'))
    SCHED_SCOPE_TIER2_MN = int(os.getenv('SCHED_SCOPE_TIER2_MN'))
    SCHED_SCOPE_SLEEP_S = int(os.getenv('SCHED_SCOPE_SLEEP_S'))

    try:
        main_loop()
    except KeyboardInterrupt:
        print("Program interrupted")
