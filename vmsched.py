import os, time, sys, getopt, json
from resultfilehandler import ResultFileHandler
from dotenv import load_dotenv

from model.nodemodel import NodeModel

STATE_ENDPOINT = ""

SCHED_NODES = list()
SCHED_SCOPE_S = 0
SCHED_SCOPE_SLICE_S = 0
SCHED_SCOPE_INIT_FETCH_PREVIOUS = 0
SCHED_SCOPE_HISTORICAL = 3
DEBUG_DUMP_STATE = dict()

def manage_node_debug(node_model : NodeModel, slice_number : int, debug : int = 0, epoch : int = -1):
    if debug>0:
        print(node_model)
        with open("dump-" + getattr(node_model, "node_name").replace("/", "") + ".json", 'w') as f:
            node_model.dump_state_and_slice_to_dict(dump_dict=DEBUG_DUMP_STATE, slice_number=slice_number, epoch=epoch)
            f.write(json.dumps(DEBUG_DUMP_STATE))
    if debug>1:
        node_model.display_model()

def main_loop_from_dump(dump_to_load: dict, debug : int = 0):
    filehandler = ResultFileHandler()
    models = dict()
    for sched_node in SCHED_NODES:
        models[sched_node]= NodeModel(node_name=dump_to_load["config"]["node_name"], historical_occurences=dump_to_load["config"]["historical_occurences"],
        model_scope=dump_to_load["config"]["node_scope"], slice_scope=dump_to_load["config"]["slice_scope"])
    for occurence in range(len(dump_to_load["epoch"])):
        # Retrieve nodes model
        tiers = dict()
        for node_id, model in models.items():
            slice_number = model.build_slice_from_dump(dump=dump_to_load, occurence=occurence)
            tiers[node_id] = model.get_free_cpu_mem()
            manage_node_debug(node_model=model, slice_number=slice_number, debug=debug, epoch=dump_to_load["epoch"][occurence])

def main_loop_live(debug : int = 0):
    filehandler = ResultFileHandler()
    models = dict()
    # Init
    for sched_node in SCHED_NODES:
        models[sched_node]= NodeModel(node_name=sched_node, model_scope=SCHED_SCOPE_S, slice_scope=SCHED_SCOPE_SLICE_S, historical_occurences=SCHED_SCOPE_HISTORICAL)
        if SCHED_SCOPE_INIT_FETCH_PREVIOUS:
            models[sched_node].build_past_slices_from_epoch(SCHED_SCOPE_INIT_FETCH_PREVIOUS)
    # Main loop
    sleep_duration = SCHED_SCOPE_SLICE_S
    while True:
        if sleep_duration>0:
            time.sleep(sleep_duration)
        loop_begin = int(time.time())
        # Retrieve nodes model
        tiers = dict()
        for node_id, model in models.items():
            slice_number = model.build_last_slice_from_epoch()
            tiers[node_id] = model.get_free_cpu_mem()
            manage_node_debug(node_model=model, slice_number=slice_number, debug=debug)
        # Write current state
        filehandler.writeResult(STATE_ENDPOINT, tiers)
        # Wait until next slice
        sleep_duration = SCHED_SCOPE_SLICE_S - (int(time.time()) - loop_begin)
        
if __name__ == '__main__':

    short_options = "hd:u:l:"
    long_options = ["help","debug=","url=","load="]
    loaded_dump = dict()
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
        elif current_argument in ("-l", "--load"):
            with open(current_value, 'r') as f:
                loaded_dump = json.load(f)
        else:
            print("python3 vmaggreg.py [--help] [--debug={level}] [--load={dump}] [--url={url}]")
            sys.exit(0)

    load_dotenv()
    STATE_ENDPOINT = os.getenv('STATE_ENDPOINT')
    if not SCHED_NODES:
        SCHED_NODES = json.loads(os.getenv('SCHED_NODES'))
    SCHED_SCOPE_S = int(os.getenv('SCHED_SCOPE_S'))
    SCHED_SCOPE_SLICE_S = int(os.getenv('SCHED_SCOPE_SLICE_S'))
    SCHED_SCOPE_INIT_FETCH_PREVIOUS = int(os.getenv('SCHED_SCOPE_INIT_FETCH_PREVIOUS'))
    SCHED_SCOPE_HISTORICAL= int(os.getenv('SCHED_SCOPE_HISTORICAL'))

    try:
        if not loaded_dump: 
            main_loop_live(debug) # live mode
        else:
            main_loop_from_dump(loaded_dump, debug) # offline mode
    except KeyboardInterrupt:
        print("Program interrupted")
