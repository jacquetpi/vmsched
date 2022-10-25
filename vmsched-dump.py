import getopt, sys, json
import numpy as np
import matplotlib.pyplot as plt

def graph(data : dict):
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    x_axis = data["epoch"]
    empty_data = [0 for i in data["epoch"]]

    ax1prime = ax1.twinx()
    ax1.set_title('CPU Tiers evolution')
    cpu_free = [0 if i < 0 else i for i in data["free_cpu"]] 
    cpu_tier0 = data["cpu_tier0"]
    cpu_tier1_cumulated = list()
    for i in range(len(data["cpu_tier0"])):
        cpu_tier1_cumulated.append(data["cpu_tier0"][i] + data["cpu_tier1"][i])
    cpu_tier2_cumulated = list()
    for i in range(len(data["cpu_tier1"])):
        cpu_tier2_cumulated.append(cpu_tier1_cumulated[i] + data["cpu_tier2"][i])
    # Convert to numpy format
    cpu_free_np = np.array(cpu_free)
    cpu_tier0_np = np.array(cpu_tier0)
    cpu_tier1_np = np.array(cpu_tier1_cumulated)
    cpu_tier2_np = np.array(cpu_tier2_cumulated)
    ax1prime.plot(x_axis, cpu_free_np, '-', color='red', label="free cpu")
    ax1.fill_between(x_axis, empty_data, cpu_tier0_np, color='blue', alpha=0.3, interpolate=True, label="Tier0")
    ax1.fill_between(x_axis, cpu_tier0_np, cpu_tier1_np, where=(cpu_tier0_np<cpu_tier1_np), color='orange', alpha=0.3, interpolate=True, label="Tier1")
    ax1.fill_between(x_axis, cpu_tier1_np, cpu_tier2_np, where=(cpu_tier1_np<cpu_tier2_np), color='green', alpha=0.3, interpolate=True, label="Tier2")
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('cores')
    ax1.legend(loc="upper left")
    ax1prime.legend(loc="upper right")
    ax1prime.set_ylabel('cores')

    ax2prime = ax2.twinx()
    ax2.set_title('Memory Tiers evolution')
    mem_free = data["free_mem"]
    mem_tier0 = data["mem_tier0"]
    mem_tier1_cumulated = list()
    for i in range(len(data["mem_tier0"])):
        mem_tier1_cumulated.append(data["mem_tier0"][i] + data["mem_tier1"][i])
    mem_tier2_cumulated = list()
    for i in range(len(data["mem_tier1"])):
        mem_tier2_cumulated.append(mem_tier1_cumulated[i] + data["mem_tier2"][i])
    # Convert to numpy format
    mem_free_np = np.array(mem_free)
    mem_tier0_np = np.array(mem_tier0)
    mem_tier1_np = np.array(mem_tier1_cumulated)
    mem_tier2_np = np.array(mem_tier2_cumulated)
    ax2prime.plot(x_axis, mem_free_np, '-', color='red', label="free mem")
    ax2.fill_between(x_axis, empty_data, mem_tier0_np, color='blue', alpha=0.3, interpolate=True, label="Tier0")
    ax2.fill_between(x_axis, mem_tier0_np, mem_tier1_np,  where=(mem_tier0_np<mem_tier1_np), color='orange', alpha=0.3,  interpolate=True, label="Tier1")
    ax2.fill_between(x_axis, mem_tier1_np, mem_tier2_np, where=(mem_tier1_np<mem_tier2_np), color='green', alpha=0.3, interpolate=True, label="Tier2")
    ax2.set_xlabel('time (s)')
    ax2.set_ylabel('Memory (MB)')
    ax2.legend(loc="upper left")
    ax2prime.legend(loc="upper right")
    ax2prime.set_ylabel('Memory (MB)')

    # Add visual line for slices
    max_cpu=cpu_tier2_cumulated[-1]
    max_mem=mem_tier2_cumulated[-1]
    count=0
    for epoch in data["epoch"]:
        fake_x=[epoch,epoch]
        count+=1
        if count>=data["config"]["number_of_slice"]:
            count=0
            fake_y_cpu=[0,max_cpu]
            fake_y_mem=[0,max_mem]
            ax1.plot(fake_x, fake_y_cpu, color='black', linestyle='-')
            ax2.plot(fake_x, fake_y_mem, color='black', linestyle='-')
        else:
            fake_y_cpu=[0,round(max_cpu/2)]
            fake_y_mem=[0,round(max_mem/2)]
            ax1.plot(fake_x, fake_y_cpu, color='grey', linestyle='-')
            ax2.plot(fake_x, fake_y_mem, color='grey', linestyle='-')

    fig.tight_layout()
    plt.show()

if __name__ == '__main__':

    short_options = "hi:"
    long_options = ["help", "input="]

    data = None
    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        print (str(err)) # Output error, and return with an error code
        sys.exit(2)
    for current_argument, current_value in arguments:
        if current_argument in ("-h", "--help"):
            print("python3 vmsched-dump.py [--help] [--input={file.json}]")
            sys.exit(0)
        elif current_argument in ("-i", "--input"):
            with open(current_value, 'r') as f:
                data = json.load(f)
            
    if data is not None:    
        graph(data)
