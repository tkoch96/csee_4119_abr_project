import sys
sys.path.append("../")
from csee_4119_abr_project.netsim.netsim import Netsim
args = type("", (), {})()
args.topology = 'topos/topo1'
args.command='start'
args.q = False
args.v = False
args.log = None
ns = Netsim(args)
ns.start_network()
