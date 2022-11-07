from model.slicemodel import SliceModel
import time
import pandas as pd
import matplotlib.pyplot as plt

class NodeModel(object):

    def __init__(self, node_name : str, model_scope : int, slice_scope, historical_occurences : int):
        if slice_scope > model_scope:
            raise ValueError("Model scope must be greater than slice scope")
        if model_scope % slice_scope !=0:
            raise ValueError("Model scope must be a slice multiple")
        self.node_name=node_name
        self.node_scope=model_scope
        self.slice_scope=slice_scope
        self.number_of_slice=int(model_scope/slice_scope)
        self.init_epoch=int(time.time())
        self.slices = list()
        for i in range(self.number_of_slice):
            self.slices.append(SliceModel(
                model_node_name= node_name, model_position=i, model_init_epoch=self.init_epoch, model_historical_occurences=historical_occurences, 
                model_number_of_slice=self.number_of_slice, leftBound=i*slice_scope, rightBound=(i+1)*slice_scope))

    def build_past_slices(self, past_slice : int):
        for slice in self.slices:
            slice.build_past_slices(past_slice)

    def get_current_iteration_and_slice_number(self):
        delta = int(time.time()) - self.init_epoch
        iteration = int(delta / self.node_scope)
        slice_number = int((delta % self.node_scope)/self.slice_scope)
        return iteration, slice_number

    def get_previous_iteration_and_slice_number(self):
        current_iteration, current_slice_number = self.get_current_iteration_and_slice_number()
        previous_slice_number = current_slice_number-1
        if previous_slice_number < 0:
            previous_slice_number = (self.number_of_slice-1)
            previous_iteration = current_iteration-1
            if previous_iteration<0:
                raise ValueError("No previous iteration at call")
        else:
            previous_iteration = current_iteration # no iteration change on last slice
        return previous_iteration, previous_slice_number

    def get_slice(self, slice_number):
        return self.slices[slice_number]

    def get_free_cpu_mem(self):
        cpu_tier_min_value, mem_tier_min_value = float('inf'), float('inf')
        for slice in self.slices:
            cpu_tier0, cpu_tier1, cpu_tier2, mem_tier0, mem_tier1, mem_tier2 = slice.get_cpu_mem_tier()
            if cpu_tier2 < cpu_tier_min_value:
                cpu_tier_min_value = cpu_tier2
            if mem_tier2 < mem_tier_min_value:
                mem_tier_min_value = mem_tier2
            if cpu_tier_min_value < 0:
                cpu_tier_min_value = 0 # Possible in an overcommited scenario
            if mem_tier_min_value < 0:
                mem_tier_min_value = 0 # Possible in an overcommited scenario
        return cpu_tier_min_value, mem_tier_min_value

    def __str__(self):
        free_cpu, free_mem = self.get_free_cpu_mem()
        txt = "NodeModel{url=" + self.node_name + "} free_cpu=" + str(free_cpu) + " free_mem=" + str(free_mem) + "\n"
        for slice in self.slices:
            txt= txt + "  |_" + str(slice) + "\n"
        return txt

    def display_model(self):
        slices=[]
        groups=[]
        tiers = {"tier0":[], "tier1":[], "tier2":[]}
        for slice in self.slices:
            slices.append(slice.get_bound_as_str())
            groups.append("cpu")
            cpu_tier0, cpu_tier1, cpu_tier2, mem_tier0, mem_tier1, mem_tier2 = slice.get_cpu_mem_tier()
            tiers["tier0"].append(cpu_tier0)
            tiers["tier1"].append(cpu_tier1)
            tiers["tier2"].append(cpu_tier2)
        for slice in self.slices:
            slices.append(slice.get_bound_as_str())
            groups.append("mem")
            cpu_tier0, cpu_tier1, cpu_tier2, mem_tier0, mem_tier1, mem_tier2 = slice.get_cpu_mem_tier()
            tiers["tier0"].append(mem_tier0)
            tiers["tier1"].append(mem_tier1)
            tiers["tier2"].append(mem_tier2)

        fig, axes = plt.subplots(1,2,figsize=(18,9))

        df = pd.DataFrame({'groups': groups, 'tier0' : tiers["tier0"], 'tier1' : tiers["tier1"], 'tier2' : tiers["tier2"]}, index=slices)
        for (k,d), ax in zip(df.groupby('groups'), axes.flat):
            axes = d.plot.bar(stacked=True, ax=ax, title=(k + " tiers"))
            axes.legend(loc=2)
        fig.canvas.manager.set_window_title("CPU/Mem tiers on node " + self.node_name)
        # def close_event():
        #     plt.close() 
        # timer = fig.canvas.new_timer(interval = 10000)
        # timer.add_callback(close_event)
        # timer.start()
        plt.show()

    def dump_state_and_slice_to_dict(self, dump_dict : dict, slice_number : int): 
        if "config" not in dump_dict:
            dump_dict["config"] = dict()
            dump_dict["config"]["node_scope"] = self.node_scope
            dump_dict["config"]["slice_scope"] = self.slice_scope
            dump_dict["config"]["number_of_slice"] = self.number_of_slice
            dump_dict["vm"]=dict()
            dump_dict["free_cpu"] = list()
            dump_dict["free_mem"] = list()
            dump_dict["cpu_tier0"] = list()
            dump_dict["cpu_tier1"] = list()
            dump_dict["cpu_tier2"] = list()
            dump_dict["mem_tier0"] = list()
            dump_dict["mem_tier1"] = list()
            dump_dict["mem_tier2"] = list()
            dump_dict["epoch"] = list()
        free_cpu, free_mem = self.get_free_cpu_mem()
        dump_dict["free_cpu"].append(free_cpu)
        dump_dict["free_mem"].append(free_mem)
        cpu_tier0, cpu_tier1, cpu_tier2, mem_tier0, mem_tier1, mem_tier2 = self.get_slice(slice_number).get_cpu_mem_tier()
        dump_dict["cpu_tier0"].append(cpu_tier0)
        dump_dict["cpu_tier1"].append(cpu_tier1)
        dump_dict["cpu_tier2"].append(cpu_tier2)
        dump_dict["mem_tier0"].append(mem_tier0)
        dump_dict["mem_tier1"].append(mem_tier1)
        dump_dict["mem_tier2"].append(mem_tier2)

        for vm, vmwrapper in self.get_slice(slice_number).get_vmwrapper().items():
            vmwrapper.get_last_slice().dump_state_to_dict(dump_dict=dump_dict["vm"], key=vm, iteration=len(dump_dict["epoch"]))
            cpu_min, cpu_max, mem_min, mem_max = vmwrapper.get_cpu_mem_tier()
            # Artificial metric as tiers are aggregated by the slice model
            vm_cpu_tier0, vm_cpu_tier1, vm_cpu_tier2, vm_mem_tier0, vm_mem_tier1, vm_mem_tier2 = self.get_slice(slice_number).compute_cpu_mem_tier(
                    slice_cpu_min=cpu_min, slice_cpu_max=cpu_max, cpu_config=vmwrapper.get_last_slice().get_cpu_config(), 
                    slice_mem_min=mem_min, slice_mem_max=mem_max, mem_config=vmwrapper.get_last_slice().get_mem_config())
            dump_dict["vm"][vm]["cpu_tier0"].append(cpu_min)
            dump_dict["vm"][vm]["cpu_tier1"].append(cpu_max)
            dump_dict["vm"][vm]["cpu_tier2"].append(cpu_tier2)
            dump_dict["vm"][vm]["mem_tier0"].append(mem_tier0)
            dump_dict["vm"][vm]["mem_tier1"].append(mem_tier1)
            dump_dict["vm"][vm]["mem_tier2"].append(mem_tier2)

        delta = int(time.time()) - self.init_epoch
        dump_dict["epoch"].append(delta)
        return dump_dict