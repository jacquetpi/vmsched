from model.slicevmwrapper import SliceVmWrapper
from model.slicehostwrapper import SliceHostWrapper
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from collections import defaultdict
import os

class SliceModel(object):

    def __init__(self, model_node_name : str, model_position : int, model_init_epoch : int, model_number_of_slice : int, leftBound : int, rightBound : int):
        #Data related to model
        self.model_node_name=model_node_name
        self.model_position=model_position
        self.model_init_epoch=model_init_epoch
        self.model_number_of_slice=model_number_of_slice
        #Data related to slice
        self.leftBound=leftBound
        self.rightBound=rightBound
        self.size=rightBound-leftBound
        # Data itself:
        self.slicevmdata=dict()
        self.slicenodedata=SliceHostWrapper(self.model_node_name)

    def build_past_slices(self, past_iteration : int = 1):
        for i in range((-past_iteration),0):
            self.build_slice(iteration=i)

    def build_slice(self, iteration : int):
        begin_epoch = self.model_init_epoch + ((iteration)*(self.model_number_of_slice*self.size)) + (self.model_position*self.size)
        end_epoch = begin_epoch + self.size
        self.add_data_slice(begin_epoch, end_epoch)

    def add_data_slice(self, begin_epoch : int, end_epoch : int):
        node_stats = self.retrieve_node_data(begin_epoch, end_epoch)
        self.slicenodedata.add_data(node_stats)
        domain_data = self.retrieve_domain_data(begin_epoch, end_epoch)
        #print("debug", begin_epoch, end_epoch, len(node_stats.keys()), len(domain_data.keys()))
        for domain_name, domain_stats in domain_data.items():
            if domain_name not in self.slicevmdata:
                self.slicevmdata[domain_name]=SliceVmWrapper(domain_name)
            self.slicevmdata[domain_name].add_data(domain_stats)

    def get_vm_cpu_mem_min_max(self):
        slice_cpu_min, slice_cpu_max = 0, 0
        slice_mem_min, slice_mem_max = 0, 0
        for vm, vmwrapper in self.slicevmdata.items():
            wp_cpu_min, wp_cpu_max, wp_mem_max, wp_mem_min = vmwrapper.get_cpu_mem_tier()
            slice_cpu_min += wp_cpu_min
            slice_cpu_max += wp_cpu_max
            slice_mem_min += wp_mem_min
            slice_mem_max += wp_mem_max
        return slice_cpu_min, slice_cpu_max, slice_mem_min, slice_mem_max

    def get_cpu_mem_tier(self):
        cpu_config, mem_config = self.get_host_config()
        if cpu_config<0 or mem_config<0:
            #print("Not enough data to compute cpu/mem tier on this slice: [" + str(self.leftBound) + ";" + str(self.rightBound) + "[")
            return 0, 0, 0, 0, 0, 0
        slice_cpu_min, slice_cpu_max, slice_mem_min, slice_mem_max = self.get_vm_cpu_mem_min_max()
        # print("debug", slice_cpu_min, slice_cpu_max, cpu_config, slice_mem_min, slice_mem_max, mem_config)
        # Compute CPU tier
        cpu_tier0 = round(slice_cpu_min,1)
        cpu_tier1 = round(slice_cpu_max - cpu_tier0,1)
        if cpu_tier1 <= 0:
            cpu_tier1 = 0
        if cpu_tier1>cpu_config:
            cpu_tier1 = cpu_config-cpu_tier0
            cpu_tier2 = 0
        else:
            cpu_tier2 = round(cpu_config - cpu_tier1 - cpu_tier0,1)
        # Compute memory tier
        mem_tier0 = int(slice_mem_min)
        mem_tier1 = int(slice_mem_max - mem_tier0)
        if mem_tier1 < 0:
            mem_tier1 = 0
        if mem_tier1>mem_config:
            mem_tier1 = mem_config-mem_tier0
            mem_tier2 = 0
        else:
            mem_tier2 = int(mem_config - mem_tier1 - mem_tier0)
        #print("debug", cpu_tier0, cpu_tier1, cpu_tier2, mem_tier0, mem_tier1, mem_tier2)
        return cpu_tier0, cpu_tier1, cpu_tier2, mem_tier0, mem_tier1, mem_tier2
        

    def retrieve_domain_data(self, begin_epoch : int, end_epoch : int):
        myurl = os.getenv('INFLUXDB_URL')
        mytoken = os.getenv('INFLUXDB_TOKEN')
        myorg = os.getenv('INFLUXDB_ORG')
        mybucket = os.getenv('INFLUXDB_BUCKET')

        client = InfluxDBClient(url=myurl, token=mytoken, org=myorg)
        query_api = client.query_api()
        query = ' from(bucket:"' + mybucket + '")\
        |> range(start: ' + str(begin_epoch) + ', stop: ' + str(end_epoch) + ')\
        |> filter(fn: (r) => r["_measurement"] == "domain")\
        |> filter(fn: (r) => r["url"] == "' + self.model_node_name + '")'

        result = query_api.query(org=myorg, query=query)
        domains_data = defaultdict(lambda: defaultdict(list))

        for table in result:
            for record in table.records:
                domain_name = record.__getitem__('domain')
                timestamp = (record.get_time()).timestamp()
                domains_data[domain_name][record.get_field()].append(record.get_value())
                domains_data[domain_name]["time"].append(timestamp)
        return domains_data

    def retrieve_node_data(self, begin_epoch : int, end_epoch : int):
        myurl = os.getenv('INFLUXDB_URL')
        mytoken = os.getenv('INFLUXDB_TOKEN')
        myorg = os.getenv('INFLUXDB_ORG')
        mybucket = os.getenv('INFLUXDB_BUCKET')

        client = InfluxDBClient(url=myurl, token=mytoken, org=myorg)
        query_api = client.query_api()
        query = ' from(bucket:"' + mybucket + '")\
        |> range(start: ' + str(begin_epoch) + ', stop: ' + str(end_epoch) + ')\
        |> filter(fn:(r) => r._measurement == "node")\
        |> filter(fn: (r) => r["url"] == "' + self.model_node_name + '")'

        result = query_api.query(org=myorg, query=query)

        node_data = defaultdict(list)

        for table in result:
            for record in table.records:
                timestamp = (record.get_time()).timestamp()
                if timestamp not in node_data["time"]:
                    node_data["time"].append(timestamp)
                node_data[record.get_field()].append(record.get_value())
        return node_data

    def get_host_config(self):
        return self.slicenodedata.get_host_config()

    def get_bound_as_str(self):
        return str(self.leftBound) + ";" + str(self.rightBound) + "["

    def __str__(self):
        slice_cpu_min, slice_cpu_max, slice_mem_min, slice_mem_max = self.get_vm_cpu_mem_min_max()
        slice_cpu_config, slice_mem_config = self.get_host_config()
        txt = "SliceModel[" + str(self.leftBound) + ";" + str(self.rightBound) + "[:" + \
            " cumul cpu min/max " + str(round(slice_cpu_min,1)) + "/" + str(round(slice_cpu_max,1)) +\
            " cumul mem min/max " + str(round(slice_mem_min,1)) + "/" + str(round(slice_mem_max,1)) +\
            "\n    >{" + str(self.slicenodedata) + "}"
        for vm, slicevm in self.slicevmdata.items():
            txt += "\n    >{" + str(slicevm) + "}"
        return txt