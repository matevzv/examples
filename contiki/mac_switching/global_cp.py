#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
global_cp.py: Example Contiki global control program

Usage:
   global_cp.py [options] [-q | -v]

Options:
   --logfile name      Name of the logfile
   --config configFile Config file path
   --num_nodes numNodes Number of nodes in experiment

Example:
   ./global_cp -v --config ./config/localhost/control_program_global.yaml --num_nodes 10

Other options:
   -h, --help          show this help message and exit
   -q, --quiet         print less text
   -v, --verbose       print more text
   --version           show version and exit
"""


import datetime
import logging
import wishful_controller
import gevent
import yaml
import _thread
from contiki.mac_managers.taisc_manager import *
from local_cp import my_local_control_program

__author__ = "Peter Ruckebusch"
__copyright__ = "Copyright (c) 2016, Technische Universität Berlin"
__version__ = "0.1.0"
__email__ = "peter.ruckebusch@intec.ugent.be"


log = logging.getLogger('global_cp.main')
global_control_engine = wishful_controller.Controller()
global_taisc_manager = GlobalTAISCMACManager(global_control_engine, "CSMA")
nodes = []


@global_control_engine.new_node_callback()
def new_node(node):
    nodes.append(node)
    global_taisc_manager.add_node(node)
    print("New node appeared:")
    print(node)


@global_control_engine.node_exit_callback()
def node_exit(node, reason):
    if node in nodes:
        global_taisc_manager.remove_node(node)
        nodes.remove(node)
    print("NodeExit : NodeID : {} Reason : {}".format(node.id, reason))


@global_control_engine.set_default_callback()
def default_callback(group, node, cmd, data):
    print("{} DEFAULT CALLBACK : Group: {}, NodeName: {}, Cmd: {}, Returns: {}".format(
        datetime.datetime.now(), group, node.name, cmd, data))


def hc_message_handler(hc_connector):
    while True:
        msg = hc_connector.recv(timeout=1)
        print("{} Global CP received event {} from local CP: {}".format(datetime.datetime.now(), msg["event_name"], msg["event_value"]))
    pass


def main(args):
    log.debug(args)

    config_file_path = args['--config']
    config = None
    with open(config_file_path, 'r') as f:
        config = yaml.load(f)

    global_control_engine.load_config(config)
    global_control_engine.start()

    num_nodes = int(args['--num_nodes'])

    # Wait for nodes before starting the local CP.
    while True:
        gevent.sleep(10)
        if len(nodes) == num_nodes:
            log.info("All nodes are active we can start the local control programs")
            log.info("Connected nodes: %s", nodes)
            break
        else:
            log.info("Still waiting for %d nodes", num_nodes - len(nodes))

    hc_connector = global_control_engine.node(nodes).hc.start_local_control_program(program=my_local_control_program)
    _thread.start_new_thread(hc_message_handler, (hc_connector,))

    ret = global_taisc_manager.update_slotframe('./mac_managers/default_taisc_slotframe.csv')
    self.log.info(ret)
    parameters = {"RIME_exampleUnicastActivateApplication": 1}

    # control loop
    while True:
        log.info("Activating CSMA MAC!")
        parameters["RIME_exampleUnicastActivateApplication"] = 0
        global_control_engine.blocking(False).node(nodes).net.set_parameters(parameters, "lowpan0")
        global_taisc_manager.activate_radio_program("CSMA")
        gevent.sleep(5)
        parameters["RIME_exampleUnicastActivateApplication"] = 1
        global_control_engine.blocking(False).node(nodes).radio.iface("lowpan0").set_parameters(parameters)
        gevent.sleep(60)
        log.info("Activating TDMA MAC!")
        parameters["RIME_exampleUnicastActivateApplication"] = 0
        global_control_engine.blocking(False).node(nodes).radio.iface("lowpan0").set_parameters(parameters)
        global_taisc_manager.activate_radio_program("TDMA")
        gevent.sleep(5)
        parameters["RIME_exampleUnicastActivateApplication"] = 1
        global_control_engine.blocking(False).node(nodes).radio.iface("lowpan0").set_parameters(parameters)
        gevent.sleep(60)
        log.info("Activating TSCH MAC!")
        parameters["RIME_exampleUnicastActivateApplication"] = 0
        global_control_engine.blocking(False).node(nodes).radio.iface("lowpan0").set_parameters(parameters)
        global_taisc_manager.activate_radio_program("TSCH")
        gevent.sleep(5)
        parameters["RIME_exampleUnicastActivateApplication"] = 1
        global_control_engine.blocking(False).node(nodes).radio.iface("lowpan0").set_parameters(parameters)
        gevent.sleep(60)

if __name__ == "__main__":
    try:
        from docopt import docopt
    except:
        print("""
        Please install docopt using:
            pip install docopt==0.6.1
        For more refer to:
        https://github.com/docopt/docopt
        """)
        raise

    args = docopt(__doc__, version=__version__)

    log_level = logging.INFO  # default
    if args['--verbose']:
        log_level = logging.DEBUG
    elif args['--quiet']:
        log_level = logging.ERROR

    logfile = None
    if args['--logfile']:
        logfile = args['--logfile']

    logging.basicConfig(filename=logfile, level=log_level,
                        format='%(asctime)s - %(name)s.%(funcName)s() - %(levelname)s - %(message)s')

    try:
        main(args)
    except KeyboardInterrupt:
        log.debug("Controller exits")
    finally:
        log.debug("Exit")
        global_control_engine.stop()
