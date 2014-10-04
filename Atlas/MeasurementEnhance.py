#!/usr/bin/env python
#### enhances a trace object with metadata
import socket
import urllib2
import json
from ripe.atlas.sagan import TracerouteResult

class TracerouteResultAnalysis( TracerouteResult ):
   pass



def trace2txt( data ):
   res = data['result']
   msm_id = data['msm_id']
   for hop in res:
      ips = {}
      for hr in hop['result']:
         if 'from' in hr:
            if hr['from'] not in ips:
               ips[ hr['from'] ] = [ hr['rtt'] ]
            else:
               ips[ hr['from'] ].append( hr['rtt'] )
         else:
            print "%s err:%s" % ( hop['hop'] , hr )

      for ip in ips:
         host = ip
         try:
            ghba = socket.gethostbyaddr(ip)
            host = ghba[0]
         except: pass
         asn = None
         try:
            asninfo = urllib2.urlopen( "https://stat.ripe.net/data/prefix-overview/data.json?max_related=0&resource=%s" % ( ip ) )
            asnjson = json.load( asninfo )
            asn = asnjson['data']['asns'][0]['asn']
         except: pass
         print "%s [AS%s] %s (%s) %s" % ( hop['hop'], asn, host, ip , sorted(ips[ip]) )
