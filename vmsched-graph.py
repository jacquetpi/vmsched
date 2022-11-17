import getopt, sys, json
from typing import DefaultDict
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from horizonplot import horizonplot
import pandas as pd
from collections import defaultdict

def graph_node(data : dict):
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    if data["config"]["slice_scope"] > 60:
        x_axis = [round(x/60) for x in data["epoch"]]
        ax1.set_xlabel('time (mn)')
    else:
        x_axis =data["epoch"]
        ax1.set_xlabel('time (s)')
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

# epoch, avg, tier0, tier1, state
def graph_node_generic(x, avg_data, percentile_data, tier0_data, tier1_data, state_data, **kwargs):
    empty_data = [0 for i in x]
    # Convert to numpy format
    plt.fill_between(x, empty_data, tier0_data, color='blue', alpha=0.3, interpolate=True, label="Tier0")
    plt.fill_between(x, tier0_data, tier1_data,  where=(tier0_data<tier1_data), color='orange', alpha=0.3,  interpolate=True, label="Tier1")
    plt.plot(x, avg_data, '-', color='black')
    plt.plot(x, percentile_data, '--', color='black')
    plt.gca().twinx().plot(x, state_data, color = 'r')

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
        vmdata["mem_percentile"] = [round(i/1024,1) for i in vmdata["mem_percentile"]['90']]
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
        graphdata+=vmdata['mem_percentile']['90']
        graphlabel+=[vmname for i in range(value_count)]

    df = pd.DataFrame({'chrom': [metric]*vm_count*value_count,
                    'vmlabel': graphlabel,
                    'start': list(range(value_count)) * vm_count, 
                    'data': graphdata})
  
    fig = horizonplot(df, 'data', width=1, col='chrom', row='vmlabel', size=0.3, aspect=100)

def graph_test(data_source : dict):

    number_of_slice=data_source["config"]["number_of_slice"]
    columns=["free_cpu","free_mem","cpu_tier0","cpu_tier1","cpu_tier2","mem_tier0","mem_tier1","mem_tier2",
            "epoch"]

    vm_based_columns=["cpu_avg","cpu_tier0","cpu_tier1","mem_avg","mem_tier0","mem_tier1","cpu_config","mem_config"]
    data={key:data_source[key]for key in columns}
    data=pd.DataFrame(data)
    data.head()
    	
    data=data.melt(id_vars="epoch",var_name="tier",value_vars=["cpu_tier0","cpu_tier1","cpu_tier2"],value_name="conso_cpu")
    sns.barplot(data=data, x="epoch", y="conso_cpu",hue="tier")

def graph_test2(data_source : dict):

    node_scope = data_source["config"]["node_scope"]
    slice_scope = data_source["config"]["slice_scope"]
    number_of_slice = data_source["config"]["number_of_slice"]

    slice_index = 0
    iteration = 0
    formatted_data = [defaultdict(lambda: list()) for x in range(number_of_slice)]
    for i in range(len(data_source["cpu_tier0"])):
        formatted_data[slice_index]["cpu_tier0"].append(data_source["cpu_tier0"][i])
        formatted_data[slice_index]["cpu_tier1"].append(data_source["cpu_tier1"][i])
        formatted_data[slice_index]["cpu_tier2"].append(data_source["cpu_tier2"][i])
        slice_index+=1
        if slice_index>=number_of_slice:
            slice_index=0
            iteration+=1

    data = pd.DataFrame.from_dict(formatted_data[0])
    #data = data.T
    # sns.barplot(data=data)
    data=data.melt(var_name="tier",value_vars=["cpu_tier0","cpu_tier1","cpu_tier2"],value_name="conso_cpu")
    sns.barplot(data=data, y="conso_cpu",hue="tier")

def graph_slice(dataframe):
    g = sns.FacetGrid(dataframe, col="vm")
    g.map(sns.barplot, "slice", "cpu_tier0")

def graph_slice2(dataframe):
    g = sns.FacetGrid(dataframe, col="slice", row="vm")
    g.map(plt.plot, "epoch", "cpu_state")

def graph_slice3(dataframe):
    g = sns.FacetGrid(dataframe, col="slice", row="vm")
    g.map(graph_node_generic, "epoch", "cpu_avg", "graph_cpu_percentile", "cpu_tier0", "cpu_tier1", "cpu_state")
    #g.map(graph_node_generic, "epoch", "mem_avg", "graph_mem_percentile", "mem_tier0", "mem_tier1", "mem_state")

def get_vm_dataframe(data_source : dict):
    number_of_slice=data_source["config"]["number_of_slice"]
    epoch = [int(x/60) for x in data_source["epoch"]]
    vm_based_columns=["cpu_avg","cpu_tier0","cpu_tier1", "cpu_state", "mem_avg","mem_tier0","mem_tier1","cpu_config","mem_config", "mem_state"]
    csv_like_data=dict()
    csv_like_data["slice"]=list()
    csv_like_data["vm"]=list()
    csv_like_data["epoch"]=list()
    csv_like_data["graph_cpu_percentile"] = list()
    csv_like_data["graph_mem_percentile"] = list()
    ordered_vm_name_list=list()
    index=0

    for vm_name, vm_stats in data_source["vm"].items():
        data={key:vm_stats[key]for key in vm_based_columns}
        ordered_vm_name="vm" + chr(65 + index)
        ordered_vm_name_list.append(ordered_vm_name)
        for key, value in data.items():
            if key not in csv_like_data:
                csv_like_data[key] = list()
            if 'mem_' in key and 'percentile' not in key and 'state' not in key:
                csv_like_data[key].extend([round(x/1024) for x in value])
            else:
                csv_like_data[key].extend(value)
        count=0
        csv_like_data["graph_cpu_percentile"].extend([x['90'] for x in vm_stats["cpu_percentile"]])
        csv_like_data["graph_mem_percentile"].extend([round(x['90']/1024) for x in vm_stats["mem_percentile"]])
        for i in range(len(data[vm_based_columns[0]])):
            csv_like_data["vm"].append(ordered_vm_name)
            slice_id = "slice" + str(count)
            csv_like_data["slice"].append(slice_id)
            count+=1
            if count >= number_of_slice:
                count=0
        index+=1
        csv_like_data["epoch"].extend(epoch)

    return pd.DataFrame(csv_like_data)

if __name__ == '__main__':

    short_options = "hi:nvub"
    long_options = ["help", "input=", "node", "vm", "usage", "bar"]

    data_input = None
    display_graph_node = False
    display_graph_vm = False
    display_graph_usage = False
    display_graph_horizon = False
    display_graph_slice = True

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
    
    if display_graph_slice:
        dataframe = get_vm_dataframe(data_input)
        graph_slice(dataframe)
        graph_slice3(dataframe)

    plt.show()