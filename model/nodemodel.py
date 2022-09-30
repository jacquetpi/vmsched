from audioop import reverse
from dotenv import load_dotenv
from slicemodel import SliceModel
import time
from dotenv import load_dotenv # for development purpose only
import pandas as pd
import matplotlib.pyplot as plt

class NodeModel(object):

    def __init__(self, node_name : str, model_scope : int, slice_scope):
        if slice_scope > model_scope !=0:
            raise ValueError("Model scope must greater than slice scope")
        if model_scope % slice_scope !=0:
            raise ValueError("Model scope must a slice multiple")
        self.node_name=node_name
        self.node_scope=model_scope
        self.slice_scope=slice_scope
        self.number_of_slice=int(model_scope/slice_scope)
        self.init_epoch=int(time.time())
        self.slices = list()
        for i in range(self.number_of_slice):
            self.slices.append(SliceModel(
                model_node_name= node_name, model_position=i, model_init_epoch=self.init_epoch, 
                model_number_of_slice=self.number_of_slice, leftBound=i*slice_scope, rightBound=(i+1)*slice_scope))

    def build_past_slices(self):
        print(self.init_epoch)
        for slice in self.slices:
            slice.build_past_slices(3)

    def get_current_iteration_and_slide_number(self):
        delta = int(time.time()) - self.init_epoch
        iteration = int(delta / self.node_scope)
        slide_number = int((delta % self.node_scope)/self.slice_scope)
        return iteration, slide_number

    def get_previous_iteration_and_slide_number(self):
        current_iteration, current_slide_number = self.get_current_iteration_and_slide_number()
        previous_slide_number = current_slide_number-1
        if previous_slide_number < 0:
            previous_slide_number = (self.number_of_slice-1)
            previous_iteration = current_iteration-1
            if previous_iteration<0:
                raise ValueError("No previous iteration at call")
        else:
            previous_iteration = current_iteration # no iteration change on last slide
        return previous_iteration, previous_slide_number

    def get_slide(self, slice_number):
        return self.slices[slice_number]

    def __str__(self):
        txt = self.node_name + " model:\n"
        for slice in self.slices:
            txt= txt + str(slice) + "\n"
        return txt

    def display_model(self):
        slices=[]
        cpu_data = {"tier0":[], "tier1":[], "tier2":[]}
        mem_data = {"tier0":[], "tier1":[], "tier2":[]}
        for slice in self.slices:
            slices.append(slice.get_bound_as_str())
            slice_cpu_min, slice_cpu_max, slice_mem_min, slice_mem_max = slice.get_vm_cpu_mem_tier()
            print(slice_cpu_min, slice_cpu_max, slice_mem_min, slice_mem_max)
            cpu_config, mem_config = slice.get_host_config()
            cpu_data["tier0"].append(slice_cpu_min)
            cpu_data["tier1"].append(slice_cpu_max-slice_cpu_min)
            cpu_data["tier2"].append(cpu_config-slice_cpu_max)
            mem_data["tier0"].append(slice_mem_min)
            mem_data["tier1"].append(slice_mem_max-slice_mem_min)
            mem_data["tier2"].append(mem_config-slice_mem_max)

        df=pd.DataFrame(cpu_data,index=slices)
        df.plot(kind="bar",stacked=True, title="CPU tier", figsize=(10,8))

        df2=pd.DataFrame(mem_data,index=slices)
        df2.plot(kind="bar",stacked=True, title="Mem tier", figsize=(10,8))

        plt.legend(loc="lower left",bbox_to_anchor=(0.8,1.0))
        plt.show()

## For development purpose only
if __name__ == '__main__':
    debug_scope = 24
    debug_slice = 6
    load_dotenv()
    model = NodeModel("http://localhost:9100/metrics", debug_scope,debug_slice)
    model.build_past_slices()
    time.sleep(debug_slice)
    while True:
        previous_iteration, previous_slide_number = model.get_previous_iteration_and_slide_number()
        model.get_slide(previous_slide_number).build_slice(previous_iteration)
        print(str(model) + "\n")
        #model.display_model()
        time.sleep(debug_slice)