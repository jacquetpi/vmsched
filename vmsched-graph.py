import getopt, sys, json
import numpy as np
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
from horizonplot import horizonplot
import pandas as pd

def graph_node(data : dict):
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    x_axis = [round(x/60) for x in data["epoch"]]
    empty_data = [0 for i in data["epoch"]]

    ax1prime = ax1.twinx()
    ax1.set_title('Host Memory Tiers evolution with ' + str(len(data["vm"])) + ' vm')
    mem_free = data["free_mem"]
    mem_tier0 = data["mem_tier0"]
    mem_tier1_cumulated = list()
    for i in range(len(data["mem_tier0"])):
        mem_tier1_cumulated.append(data["mem_tier0"][i] + data["mem_tier1"][i])
    mem_tier2_cumulated = list()
    for i in range(len(data["mem_tier1"])):
        mem_tier2_cumulated.append(mem_tier1_cumulated[i] + data["mem_tier2"][i])
    # Convert to numpy format
    mem_free_np = np.array([round(i/1024,1) for i in mem_free])
    mem_tier0_np = np.array([round(i/1024,1) for i in mem_tier0])
    mem_tier1_np = np.array([round(i/1024,1) for i in mem_tier1_cumulated])
    mem_tier2_np = np.array([round(i/1024,1) for i in mem_tier2_cumulated])
    ax1.fill_between(x_axis, empty_data, mem_tier0_np, color='blue', alpha=0.3, interpolate=True, label="Tier0")
    ax1.fill_between(x_axis, mem_tier0_np, mem_tier1_np,  where=(mem_tier0_np<mem_tier1_np), color='orange', alpha=0.3,  interpolate=True, label="Tier1")
    ax1.fill_between(x_axis, mem_tier1_np, mem_tier2_np, where=(mem_tier1_np<mem_tier2_np), color='green', alpha=0.3, interpolate=True, label="Tier2")
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('Memory (GB)')
    ax1.legend(loc="upper left")
    ax1prime.plot(x_axis, mem_free_np, '-', color='red', label="free mem")
    ax1prime.legend(loc="upper right")
    ax1prime.set_ylabel('Memory (GB)')

    ax2prime = ax2.twinx()
    ax2.set_title('Host CPU Tiers evolution with ' + str(len(data["vm"])) + ' vm')
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
    ax2prime.plot(x_axis, cpu_free_np, '-', color='red', label="free cpu")
    ax2.fill_between(x_axis, empty_data, cpu_tier0_np, color='blue', alpha=0.3, interpolate=True, label="Tier0")
    ax2.fill_between(x_axis, cpu_tier0_np, cpu_tier1_np, where=(cpu_tier0_np<cpu_tier1_np), color='orange', alpha=0.3, interpolate=True, label="Tier1")
    ax2.fill_between(x_axis, cpu_tier1_np, cpu_tier2_np, where=(cpu_tier1_np<cpu_tier2_np), color='green', alpha=0.3, interpolate=True, label="Tier2")
    ax2.set_xlabel('time (s)')
    ax2.set_ylabel('cores')
    ax2.legend(loc="upper left")
    ax2prime.legend(loc="upper right")
    ax2prime.set_ylabel('cores')

    # Add visual line for slices
    max_cpu=cpu_tier2_cumulated[-1]
    max_mem=mem_tier2_np[-1]
    count=0
    for time in x_axis:
        fake_x=[time,time]
        count+=1
        if count>=data["config"]["number_of_slice"]:
            count=0
            fake_y_cpu=[0,max_cpu]
            fake_y_mem=[0,max_mem]
            ax2.plot(fake_x, fake_y_cpu, color='black', linestyle='-')
            ax1.plot(fake_x, fake_y_mem, color='black', linestyle='-')
        else:
            fake_y_cpu=[0,round(max_cpu/2)]
            fake_y_mem=[0,round(max_mem/2)]
            ax2.plot(fake_x, fake_y_cpu, color='grey', linestyle='-')
            ax1.plot(fake_x, fake_y_mem, color='grey', linestyle='-')

    fig.tight_layout()

def graph_vm(data : dict):

    test = list()
    fig, axes = plt.subplots(3, 3, sharex=True)
    x_axis = [round(x/60) for x in data["epoch"]]
    empty_data = [0 for i in data["epoch"]]

    index_x = 0
    index_y = 0
    for vmname, vmdata in data["vm"].items():

        current_axe = axes[index_y][index_x]

        vmdata["mem_tier0"] = [round(i/1024,1) for i in vmdata["mem_tier0"]]
        vmdata["mem_tier1"] = [round(i/1024,1) for i in vmdata["mem_tier1"]]
        vmdata["mem_config"] = [round(i/1024,1) for i in vmdata["mem_config"]]
        vmdata["mem_avg"] = [round(i/1024,1) for i in vmdata["mem_avg"]]

        tier0_cumul_data = list()
        for i in range(len(vmdata["mem_tier0"])):
            tier0_cumul_data.append(empty_data[i] + vmdata["mem_tier0"][i])
        x = current_axe.fill_between(x_axis, np.array(empty_data), np.array(tier0_cumul_data), alpha=1, interpolate=True)
        
        tier1_cumul_data = list()
        for i in range(len(vmdata["mem_tier1"])):
            tier1_cumul_data.append(tier0_cumul_data[i] + vmdata["mem_tier1"][i])
        current_axe.fill_between(x_axis, np.array(tier0_cumul_data), np.array(tier1_cumul_data), alpha=0.5, color=x.get_facecolor(), interpolate=True)
        
        tier2_cumul_data = list()
        for i in range(len(vmdata["mem_tier1"])):
            tier2_cumul_data.append(tier1_cumul_data[i] + (vmdata["mem_config"][i] - vmdata["mem_tier1"][i] - vmdata["mem_tier0"][i]))
        x = current_axe.fill_between(x_axis, np.array(tier1_cumul_data), np.array(tier2_cumul_data), alpha=0.2, color=x.get_facecolor(), hatch='/', interpolate=True)

        current_axe.set_xlabel(vmname)
        current_axe.plot(x_axis, np.array(vmdata["mem_avg"]), '-', color='black', label="rss")
        current_axe.legend(loc="upper center")

        index_x+=1
        if index_x>2:
            index_x=0
            index_y+=1

    fig.tight_layout()

def graph_vm_save2(data : dict):

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    x_axis = [round(x/1) for x in data["epoch"]]
    empty_data = [0 for i in data["epoch"]]

    ax1prime = ax1.twinx()
    ax1.set_title('VM Memory Tiers evolution')
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('Memory (GB)')
    old_cumul_data = empty_data
    for vmname, vmdata in data["vm"].items():
        # Display area for usage:
        tier0_cumul_data = list()
        for i in range(len(vmdata["mem_tier0"])):
            tier0_cumul_data.append(old_cumul_data[i] + vmdata["mem_tier0"][i])
        x = ax1.fill_between(x_axis, np.array(old_cumul_data), np.array(tier0_cumul_data), alpha=1, interpolate=True, label=vmname)
        vmdata["color"] = x.get_facecolor()

        # mem_usage = list()
        # for i in range(len(vmdata["mem_avg"])):
        #     mem_usage.append(old_cumul_data[i] + vmdata["mem_avg"][i])
        # ax1.plot(x_axis, mem_usage, '-', color='red')

        old_cumul_data = tier0_cumul_data

    for vmname, vmdata in data["vm"].items():
        # Display area for usage:
        tier1_cumul_data = list()
        for i in range(len(vmdata["mem_tier1"])):
            tier1_cumul_data.append(old_cumul_data[i] + vmdata["mem_tier1"][i])
        ax1.fill_between(x_axis, np.array(old_cumul_data), np.array(tier1_cumul_data), alpha=0.4, color=vmdata["color"], hatch='/', interpolate=True)

        old_cumul_data = tier1_cumul_data

    for vmname, vmdata in data["vm"].items():
        # Display area for usage:
        tier2_cumul_data = list()
        for i in range(len(vmdata["mem_tier1"])):
            tier2_cumul_data.append(old_cumul_data[i] + (vmdata["mem_config"][i] - vmdata["mem_tier1"][i] - vmdata["mem_tier0"][i]))
        ax1.fill_between(x_axis, np.array(old_cumul_data), np.array(tier2_cumul_data), alpha=0.2, color=vmdata["color"], interpolate=True)

        old_cumul_data = tier2_cumul_data

    ax1.legend(loc="upper left")
    ax1prime.plot(x_axis, np.array(data["free_mem"]), '-', color='red', label="free mem")
    ax1prime.legend(loc="upper right")
    ax1prime.set_ylabel('Memory (MB)')

    # Add visual line for slices
    # max_cpu=cpu_tier2_cumulated[-1]

    # max_mem=old_cumem_rssmul_data[-1]
    # count=0
    # for time in x_axis:
    #     fake_x=[time,time]
    #     count+=1
    #     if count>=data["config"]["number_of_slice"]:
    #         count=0
    #         #fake_y_cpu=[0,max_cpu]
    #         fake_y_mem=[0,max_mem]
    #         #ax2.plot(fake_x, fake_y_cpu, color='black', linestyle='-')
    #         ax1.plot(fake_x, fake_y_mem, color='black', linestyle='-', alpha=0.3)
    #     else:
    #         #fake_y_cpu=[0,round(max_cpu/2)]
    #         fake_y_mem=[0,max_mem]
    #         #ax2.plot(fake_x, fake_y_cpu, color='grey', linestyle='-')
    #         ax1.plot(fake_x, fake_y_mem, color='grey', linestyle='-', alpha=0.2)

    fig.tight_layout()


def graph_usage(data : dict):

    fig, axes = plt.subplots(3, 3, sharex=True)
    x_axis = [round(x/60) for x in data["epoch"]]
    empty_data = [0 for i in data["epoch"]]

    index_x = 0
    index_y = 0
    for vmname, vmdata in data["vm"].items():

        current_axe = axes[index_y][index_x]

        vmdata["mem_percentile"] = [round(i/1024,1) for i in vmdata["mem_percentile"]]
        vmdata["mem_config"] = [round(i/1024,1) for i in vmdata["mem_config"]]
    
        current_axe.fill_between(x_axis, np.array(empty_data), np.array(vmdata["mem_percentile"]), alpha=1, interpolate=True)
        current_axe.fill_between(x_axis, np.array(empty_data), np.array(vmdata["mem_config"]), alpha=0.3, interpolate=True)

        current_axe.set_xlabel(vmname)
        index_x+=1
        if index_x>2:
            index_x=0
            index_y+=1

    fig.tight_layout()

def graph_horizon(data : dict):
    value_count = len(data["epoch"])
    vm_count = len(data["vm"])
    graphdata = list()
    graphlabel = list()
    metric = 'mem_percentile'
    for vmname, vmdata in data["vm"].items():
        graphdata+=vmdata[metric]
        graphlabel+=[vmname for i in range(value_count)]

    df = pd.DataFrame({'chrom': [metric]*vm_count*value_count,
                    'vmlabel': graphlabel,
                    'start': list(range(value_count)) * vm_count, 
                    'data': graphdata})
  
    fig = horizonplot(df, 'data', width=1, col='chrom', row='vmlabel', size=0.3, aspect=100)

if __name__ == '__main__':

    short_options = "hi:nvub"
    long_options = ["help", "input=", "node", "vm", "usage", "bar"]

    data_input = None
    display_graph_node = False
    display_graph_vm = False
    display_graph_usage = False
    display_graph_horizon = False

    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        print (str(err)) # Output error, and return with an error code
        sys.exit(2)
    help = "python3 vmsched-dump.py [--help] [--input={file.json}] [--node] [--vm] [--usage] [--bar]"
    for current_argument, current_value in arguments:
        if current_argument in ("-h", "--help"):
            print(help)
            sys.exit(0)
        elif current_argument in ("-i", "--input"):
            with open(current_value, 'r') as f:
                data_input = json.load(f)
        elif current_argument in ("-n", "--node"):
            display_graph_node = True
        elif current_argument in ("-v", "--vm"):
            display_graph_vm = True
        elif current_argument in ("-u", "--usage"):
            display_graph_usage = True
        elif current_argument in ("-b", "--bar"):
            display_graph_horizon = True

    sns.set_style("white")
    if data_input is None:
        print("No input specified")
        print(help)
        sys.exit(0)    

    if display_graph_node:
        graph_node(data_input)

    if display_graph_vm:
        graph_vm(data_input)

    if display_graph_usage:
        graph_usage(data_input)

    if display_graph_horizon:
        graph_horizon(data_input)

    plt.show()