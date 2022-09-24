
#!/usr/bin/python3.10

import sys

import argparse
import hashlib
try:
    from csee_4119_abr_project.common.util import check_output, check_both
except ModuleNotFoundError:
    sys.path.append("..")
    from common.util import check_output, check_both
TC='sudo /sbin/tc'
DEFAULT_CLASS=9999
ROOT_Q_HANDLE=9999
import logging
logging.basicConfig(stream=sys.stderr,level=logging.DEBUG)
global_log = logging.getLogger("TestLog")

class TC_Wrapper:
    def __init__(self, args):
        self.args = args

    # Return a consistent traffic class for the given pair of IP addresses
    def class_for_ip_pair(self,ip_pair):
        # hash the IP pair to a traffic class number ("sort" them first so we 
        # always hash them in the same order). Valid class numbers are 1 - 9999,
        # but we don't allow 9999 since it's the default class
        if self.args.ip_pair[0] < self.args.ip_pair[1]:
            ip_pair_str = self.args.ip_pair[0] + self.args.ip_pair[1]
        else:
            ip_pair_str = self.args.ip_pair[1] + self.args.ip_pair[0]
        return (int(hashlib.sha1(ip_pair_str).hexdigest(), 16) % 9998) + 1


    # Start traffic shaping on the specified interface by attaching a hierarchical
    # token bucket to the interface (the "root" queue for that interface). We can
    # then add individual classes to the "root" token bucket as needed.
    def start(self):
        check_output('%s qdisc add dev %s root handle %i: htb default %i'\
            % (TC, self.args.interface, ROOT_Q_HANDLE, DEFAULT_CLASS))

        # make a default class for normal traffic
        check_output('%s class replace dev %s parent %i: classid %i:%i htb rate 1000mbit ceil 1000mbit'\
            % (TC, self.args.interface, ROOT_Q_HANDLE, ROOT_Q_HANDLE, DEFAULT_CLASS))



    # Stop traffic shaping on the specified interface by removing the root queueing
    # discipline on that interface (the token bucket we added in start())
    def stop(self):
        cmd = "{} qdisc del dev {} root".format(TC, self.args.interface)
        out = check_both(cmd, shouldPrint=False, check=False)
        if out[1] != 0 and 'RTNETLINK answers: No such file or directory' not in out[0][0]:
            raise Exception("Error stopping traffic shaping")


    # Update the traffic class associated with the pair of IP addresses specified
    # as command line arguments
    def update(self):
        # Figure out which traffic class we're updating
        if self.args.traffic_class:
            traffic_class = self.args.traffic_class
        elif self.args.ip_pair:
            traffic_class = self.class_for_ip_pair(self.args.ip_pair)
        else:
            traffic_class = DEFAULT_CLASS

        # Update the queues for the traffic class with the new BW/latency
        cmd = '{} class replace dev {} parent {}: classid {}:{} htb rate {} ceil {}'.format(
            TC, self.args.interface, ROOT_Q_HANDLE, ROOT_Q_HANDLE, traffic_class,
            self.args.bandwidth, self.args.bandwidth)
        global_log.info(cmd)
        check_output(cmd)
        cmd = '{} qdisc replace dev {} parent {}:{} handle {}: netem delay {}'.format(
            TC, self.args.interface, ROOT_Q_HANDLE, traffic_class, traffic_class,
            self.args.latency)
        check_output(cmd)
        global_log.info(cmd)

        # Update the rules mapping IP address pairs to the traffic class
        if self.args.ip_pair:
            U32='%s filter replace dev %s protocol ip parent %i: prio 1 u32'\
                % (TC, self.args.interface, ROOT_Q_HANDLE)
            cmd = '%s match ip dst %s match ip src %s flowid %i:%i'%(
                U32, self.args.ip_pair[0], self.args.ip_pair[1], ROOT_Q_HANDLE, traffic_class)
            global_log.info(cmd)
            check_output(cmd)
            cmd = '%s match ip dst %s match ip src %s flowid %i:%i'%(
                U32, self.args.ip_pair[1], self.args.ip_pair[0], ROOT_Q_HANDLE, traffic_class)
            global_log.info(cmd)
            check_output(cmd)


    def show(self):
        ret_s = ""
        print('=============== Queue Disciplines ===============')
        ret_s += check_output('{} -s qdisc show dev {}'.format(
            TC, self.args.interface))[0]
        print('\n================ Traffic Classes ================')
        ret_s += check_output('{} -s class show dev {}'.format(
            TC, self.args.interface))[0]
        print('\n==================== Filters ====================')
        ret_s += check_output('{} -s filter show dev {}'.format(
            TC, self.args.interface))[0]
        return ret_s

def main(args):
    tcw = TC_Wrapper(args)
    if args.command == 'start':
        tcw.start()
    elif args.command == 'stop':
        tcw.stop()
    elif args.command == 'update':
        tcw.update()
    elif args.command == 'show':
        tcw.show()


if __name__ == "__main__":
    # set up command line args
    parser = argparse.ArgumentParser(description='Adjust traffic shaping settings')
    parser.add_argument('command', choices=['start','stop','show','update'], help='command: start or stop traffic shaping; show current filters; or update a filter')
    parser.add_argument('ip_pair', nargs='*', default=None, help='The pair of IP addresses between which the specified BW and latency should apply. If not provided, the class specified with -c is updated. If neither is provided, the default class is updated.')
    parser.add_argument('-i', '--interface', default='lo', help='the interface to adjust')
    parser.add_argument('-b', '--bandwidth', default='1000mbit', help='download bandwidth (e.g., 100mbit)')
    parser.add_argument('-l', '--latency', default='0ms', help='outbound latency (e.g., 20ms)')
    parser.add_argument('-c', '--traffic_class', type=int, default=0, help='traffic class number to update. If none provided, the hash of the IP pair is used. If no IP pair is provided, the default class is updated.')
    args = parser.parse_args()

    main(args)
