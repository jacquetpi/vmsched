import requests, os, time, sys, getopt, copy, json
from collections import defaultdict
from resultfilehandler import ResultFileHandler
from dotenv import load_dotenv
import numpy as np
import matplotlib.pyplot as plt

from model.nodemodel import NodeModel

STATE_ENDPOINT = ""

SCHED_NODES = list()
SCHED_SCOPE_S = 0
SCHED_SCOPE_SLICE_S = 0
SCHED_SCOPE_INIT_FETCH_PREVIOUS = 0
DEBUG_DUMP_STATE = dict()

def manage_nodes_model(node_model : NodeModel, debug : int = 0):
    previous_iteration, previous_slice_number = node_model.get_previous_iteration_and_slice_number()
    node_model.get_slice(previous_slice_number).build_slice(previous_iteration)
    if debug>0:
        print(node_model)
        with open("dump-" + getattr(node_model, "node_name").replace("/", "") + ".json", 'w') as f:
            node_model.dump_state_and_slice_to_dict(dump_dict=DEBUG_DUMP_STATE, slice_number=previous_slice_number)
            f.write(json.dumps(DEBUG_DUMP_STATE))
    if debug>1:
        node_model.display_model()
    return node_model.get_free_cpu_mem()

def main_loop(debug : int = 0):
    filehandler = ResultFileHandler()
    models = dict()
    # Init
    for sched_node in SCHED_NODES:
        models[sched_node]= NodeModel(sched_node, SCHED_SCOPE_S, SCHED_SCOPE_SLICE_S)
        if SCHED_SCOPE_INIT_FETCH_PREVIOUS:
            models[sched_node].build_past_slices(SCHED_SCOPE_INIT_FETCH_PREVIOUS)
    # Main loop
    sleep_duration = SCHED_SCOPE_SLICE_S
    while True:
        if sleep_duration>0:
            time.sleep(sleep_duration)
        loop_begin = int(time.time())
        # Retrieve nodes model
        tiers = dict()
        for node_id, model in models.items():
            tiers[node_id] = manage_nodes_model(node_model=model, debug=debug)
        # Write current state
        filehandler.writeResult(STATE_ENDPOINT, tiers)
        # Wait until next slice
        sleep_duration = SCHED_SCOPE_SLICE_S - (int(time.time()) - loop_begin)
        
if __name__ == '__main__':

    short_options = "hd:u:"
    long_options = ["help","debug=","url="]
    debug = 0

    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        print (str(err)) # Output error, and return with an error code
        sys.exit(2)
    for current_argument, current_value in arguments:
        if current_argument in ("-d", "--debug"):
            debug = int(current_value)
        elif current_argument in ("-u", "--url"):
            SCHED_NODES = json.loads(current_value)
        else:
            print("python3 vmaggreg.py [--help] [--debug={level}] [--url={url}]")
            sys.exit(0)

    load_dotenv()
    STATE_ENDPOINT = os.getenv('STATE_ENDPOINT')
    if not SCHED_NODES:
        SCHED_NODES = json.loads(os.getenv('SCHED_NODES'))
    SCHED_SCOPE_S = int(os.getenv('SCHED_SCOPE_S'))
    SCHED_SCOPE_SLICE_S = int(os.getenv('SCHED_SCOPE_SLICE_S'))
    SCHED_SCOPE_INIT_FETCH_PREVIOUS = int(os.getenv('SCHED_SCOPE_INIT_FETCH_PREVIOUS'))

    try:
        main_loop(debug)
    except KeyboardInterrupt:
        print("Program interrupted")
