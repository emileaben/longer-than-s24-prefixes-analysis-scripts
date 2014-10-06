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
   1767681: {'irr':True, 'size':28, 'idx':2},
   1767682: {'irr':False, 'size':24, 'idx':3},
   1767683: {'irr':False, 'size':25, 'idx':4},
   1767684: {'irr':False, 'size':28, 'idx':5},
}
probes = ProbeInfo.query()

interval=3600*8 # msm is every 8hrs
msm_start = int( 1412236086 / interval ) * interval

def to_geojson( probes, probe_prop ):
   geojson = {
      "type": "FeatureCollection",
      "features": []
   }
   for p,props in probe_prop.items():
      if p in probes:
         lat = probes[ p ]['lat']
         lon = probes[ p ]['lon']
         geojson['features'].append({
            "geometry": {
                "type": "Point",
                "coordinates": [ lon,lat ]
            },
            "type": "Feature",
            "properties": props
         })
   return geojson

def last_responding_ip( trace ):
   rev_path = trace.ip_path[::-1]
   for ip_l in rev_path:
      ips = set()
      for ip in ip_l:
         if ip != None:
            ips.add( ip )
      if len( ips ) > 0:
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


# for full time series
#start_t = msm_start
#stop_stop = time.time()

# for latest data
stop_stop = time.time()
start_t = stop_stop - interval

while start_t < stop_stop:
   stop_t = start_t + interval
   ## properties per probe
   probe_prop = {}
   for msm_id in sorted( measurements ):
      pfx_size = measurements[ msm_id ]['size']
      has_irr = measurements[ msm_id ]['irr']
      # index for 'fingerprinting' behaviours
      msm_idx = measurements[ msm_id ]['idx']
      responded=0
      count=0
      # last_ips will contain the last-responding IP, if the intended dest didn't respond
      last_ips = Counter()
      asns = {}
      for data in MeasurementFetch.fetch( msm_id, start=start_t , stop=stop_t ):
         tr = TracerouteResult( data )
         ## init probe_prop 
         if not tr.probe_id in probe_prop:
            probe_prop[ tr.probe_id ] = {
               'fingerprint': [None]*len( measurements ),
            }
         prb_asn = probes[ tr.probe_id ]['asn_v4']
         if not prb_asn in asns:
            asns[ prb_asn ] = {'count':0, 'responses':0}
         asns[prb_asn]['count'] += 1
         #if tr.probe_id == 14353:
         #   print MeasurementPrint.trace2txt( data, hostnames=False )
         #print "%s %s %s" % ( tr.measurement_id, tr.probe_id, tr.target_responded )
         last_resp_ips =  last_responding_ip( tr )
         pre_dest_ips = get_pre_dest_ips( tr )
         if tr.target_responded:
            responded += 1
            asns[prb_asn]['responses'] += 1
            if len( pre_dest_ips ) > 0:
               probe_prop[ tr.probe_id ][msm_id] = {'resp': True, 'pre': list(pre_dest_ips)}
         elif last_resp_ips != None:
            for ip in last_resp_ips: 
               i = ipaddr.IPv4Address( ip )
               if not i.is_private:
                  last_ips[ ip ] += 1
                  probe_prop[ tr.probe_id ][msm_id] = {'resp': False, 'last': list(last_resp_ips)}
         count += 1
         ### fingerprints
         if tr.target_responded:
            probe_prop[ tr.probe_id ]['fingerprint'][msm_idx] = 1
         else:
            probe_prop[ tr.probe_id ]['fingerprint'][msm_idx] = -1
         #print MeasurementPrint.trace2txt( data )
      #print "SUMMARY: msm:%s respond:%.1f%% count:%d last_ips:%s" % ( msm_id , 100.0 * responded / count, count, last_ips.most_common(5) )
      print "SUMMARY (%s) (/%s irr:%s): msm:%s respond:%.1f%% count:%d" % ( start_t, pfx_size, has_irr, msm_id , 100.0 * responded / count, count )
      asn_resp_yes = 0
      asn_resp_no = 0
      asn_resp_mixed = 0
      asn_count = 0
      for asn,result in asns.items():
         asn_count += 1
         if result['count'] == result['responses']:
            asn_resp_yes += 1
         elif result['responses'] == 0:
            asn_resp_no += 1
         else:
            asn_resp_mixed += 1
      print "  ASN_RESPONDED: asn_count:%s yes:%s (%.1f%%) no:%s (%.1f%%) mixed:%s (%.1f%%)" % ( 
         asn_count,
         asn_resp_yes,
         100.0 * asn_resp_yes / asn_count,
         asn_resp_no,
         100.0 * asn_resp_no / asn_count,
         asn_resp_mixed,
         100.0 * asn_resp_mixed / asn_count )
      #geojson = to_geojson( probes, probe_prop )
   #with open('probe_dat.%s.txt' % ( start_t ), 'w') as outfile:
   #   json.dump(probe_prop, outfile)
   start_t += interval
