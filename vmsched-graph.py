import getopt, sys, json
import numpy as np
import matplotlib.pyplot as plt

def graph_node(data : dict):
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    x_axis = [round(x/60) for x in data["epoch"]]
    empty_data = [0 for i in data["epoch"]]

    ax1prime = ax1.twinx()
    ax1.set_title('Host Memory Tiers evolution')
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
    ax1prime.plot(x_axis, mem_free_np, '-', color='red', label="free mem")
    ax1.fill_between(x_axis, empty_data, mem_tier0_np, color='blue', alpha=0.3, interpolate=True, label="Tier0")
    ax1.fill_between(x_axis, mem_tier0_np, mem_tier1_np,  where=(mem_tier0_np<mem_tier1_np), color='orange', alpha=0.3,  interpolate=True, label="Tier1")
    ax1.fill_between(x_axis, mem_tier1_np, mem_tier2_np, where=(mem_tier1_np<mem_tier2_np), color='green', alpha=0.3, interpolate=True, label="Tier2")
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('Memory (GB)')
    ax1.legend(loc="upper left")
    ax1prime.legend(loc="upper right")
    ax1prime.set_ylabel('Memory (GB)')

    ax2prime = ax2.twinx()
    ax2.set_title('Host CPU Tiers evolution')
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
    plt.show()

def graph_vm_save(data : dict):

    test = list()
    print(len(data["vm"]))
    fig, axes = plt.subplots(3, 3, sharex=True)
    print(axes)
    x_axis = [round(x/60) for x in data["epoch"]]
    empty_data = [0 for i in data["epoch"]]

    index_x = 0
    index_y = 0
    for vmname, vmdata in data["vm"].items():

        current_axe = axes[index_y][index_x]
        current_axe_prime = current_axe.twinx()

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
        # current_axe.set_ylabel('GB')
        current_axe_prime.plot(x_axis, np.array(vmdata["mem_avg"]), '-', color='black', label="avg")
        current_axe_prime.legend(loc="upper center")
        # current_axe_prime.set_ylabel('GB')

        index_x+=1
        if index_x>2:
            index_x=0
            index_y+=1

    fig.tight_layout()
    plt.show()

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

    # max_mem=old_cumul_data[-1]
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
    plt.show()

def graph_vm(data : dict):

    test = list()
    print()
    fig, axes = plt.subplots(len(data["vm"]), sharex=True)
    print(axes)
    x_axis = [round(x/60) for x in data["epoch"]]
    empty_data = [0 for i in data["epoch"]]

    index_x = 0
    index_y = 0
    for vmname, vmdata in data["vm"].items():

        current_axe = axes[index_y][index_x]

        vmdata["mem_percentile"] = [round(i/1024,1) for i in vmdata["mem_percentile"]]
        vmdata["mem_config"] = [round(i/1024,1) for i in vmdata["mem_config"]]
    
        x = current_axe.fill_between(x_axis, np.array(empty_data), np.array(vmdata["mem_percentile"]), alpha=1, interpolate=True)
        x = current_axe.fill_between(x_axis, np.array(empty_data), np.array(vmdata["mem_config"]), alpha=0.3, interpolate=True)

        current_axe.set_xlabel(vmname)
        # current_axe.set_ylabel('GB')
        # current_axe_prime.set_ylabel('GB')

        # Add visual line for slices
        # max_mem=np.max(vmdata["mem_config"])
        # count=0
        # for time in x_axis:
        #     fake_x=[time,time]
        #     count+=1
        #     if count>=data["config"]["number_of_slice"]:
        #         count=0
        #     fake_y_mem=[0,max_mem]
        #     current_axe.plot(fake_x, fake_y_mem, color='white', linestyle='-')

        index_x+=1
        if index_x>2:
            index_x=0
            index_y+=1

    fig.tight_layout()
    plt.show()

if __name__ == '__main__':

    short_options = "hn:v:"
    long_options = ["help", "node=","vm="]

    data_vm = None
    data_node = None

    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        print (str(err)) # Output error, and return with an error code
        sys.exit(2)
    for current_argument, current_value in arguments:
        if current_argument in ("-h", "--help"):
            print("python3 vmsched-dump.py [--help] [--node={file.json}] [--vm={file.json}]")
            sys.exit(0)
        elif current_argument in ("-n", "--node"):
            with open(current_value, 'r') as f:
                data_node = json.load(f)
        elif current_argument in ("-v", "--vm"):
            with open(current_value, 'r') as f:
                data_vm = json.load(f)

    if data_vm is not None:    
        graph_vm_save(data_vm)

    if data_node is not None:    
        graph_node(data_node)
