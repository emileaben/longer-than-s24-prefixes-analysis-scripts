#!/usr/bin/env python
from Atlas import MeasurementFetch
from Atlas import MeasurementPrint
from Atlas import ProbeInfo
import time
from ripe.atlas.sagan import TracerouteResult
from collections import Counter
import ipaddr
import json

measurements = {
   1767679: {'irr':True, 'size':24, 'idx':0},
   1767680: {'irr':True, 'size':25, 'idx':1},
}

interval=3600*8 # msm is every 8hrs
msm_start = int( 1412236086 / interval ) * interval

def last_responding_ips( trace ):
   rev_path = trace.ip_path[::-1]
   ips = set()
   for ip_l in rev_path:
      for ip in ip_l:
         if ip != None:
            ips.add( ip )
      if len( ips ) > 0:
         return ips
   return ips

def get_pre_dest_ips( trace ):
   '''
      returns a set of IPs for the hop before the
      intended destination
   '''
   dest_hop = None
   rev_hops = trace.hops[::-1]
   ips = set()
   for hop in rev_hops:
      if dest_hop != None:
         if dest_hop - hop.index == 1:
            for p in hop.packets:
               ips.add( p.origin )
            return ips
         else:
            return ips
      for p in hop.packets:
         if p.origin == trace.destination_address:
            dest_hop = hop.index
            break
   return ips

# for latest data
stop_t = time.time()
start_t = stop_t - interval

## ips seen as penultimate hop for responding dst
penult_ips = set()

prb_id2tr = {}

## properties per probe
for data in MeasurementFetch.fetch( 1767679, start=start_t, stop=stop_t ):
   tr = TracerouteResult( data )
   prb_id2tr[ tr.probe_id ] = data
   if tr.target_responded:
      pre_dest_ips = get_pre_dest_ips( tr )
      for ip in pre_dest_ips:
         penult_ips.add( ip )
      
count = 0
printit=[]

for data in MeasurementFetch.fetch( 1767680, start=start_t, stop=stop_t ):
   tr = TracerouteResult( data )
   if not tr.target_responded:
      last_ips = last_responding_ips( tr )
      for ip in last_ips:
         if ip in penult_ips:
            print tr.probe_id
            count += 1
            if tr.probe_id in prb_id2tr:
               printit += [ prb_id2tr[ tr.probe_id ], data ]
print "#RESULT# penultimate (len %d): %s" % ( len(penult_ips), penult_ips )
print "#RESULT# count: %d" % ( count )


for p in printit:
   try:
      MeasurementPrint.trace2txt( p , hostnames=False)
   except: pass
