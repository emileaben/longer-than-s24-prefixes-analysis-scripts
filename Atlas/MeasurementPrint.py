#!/usr/bin/env python
import socket
import urllib2
import json
import sys

if hasattr(socket, 'setdefaulttimeout'):
   socket.setdefaulttimeout(5)

def memoize(f):
    """ Memoization decorator for functions taking one or more arguments. """
    class memodict(dict):
        def __init__(self, f):
            self.f = f
        def __call__(self, *args):
            return self[args]
        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret
    return memodict(f)

@memoize
def getlocforip( ip ):
   loc = None
   try:
      locinfo = urllib2.urlopen( "https://marmot.ripe.net/openipmap/ipmeta.json?ip=%s" % ( ip ) )
      locjson = json.load( locinfo )
      if len( locjson['crowdsourced'] ) > 0:
         loc = locjson['crowdsourced'][0]['canonical_georesult']
   except:
      sys.stderr.write( "eeps: problem in loading routergeoloc for ip: %s\n" % ( ip ) )
   return loc

@memoize
def getasnforip( ip ):
   asn = None
   try:
      asninfo = urllib2.urlopen( "https://stat.ripe.net/data/prefix-overview/data.json?max_related=0&resource=%s" % ( ip ) )
      asnjson = json.load( asninfo )
      asn = asnjson['data']['asns'][0]['asn']
   except: pass
   return asn

@memoize
def gethostforip( ip ):
   host = None
   try:
      ghba = socket.gethostbyaddr(ip)
      host = ghba[0]
   except: pass
   return host

def _getips( data ):
   ips = set()
   for hop in data:
      for hr in hop['result']:
         if 'from' in hr and 'rtt' in hr:
            if hr['from'] not in ips:
               ips.add( hr['from'] )
   return ips


def trace2locs( data ):
   locs = set()
   msm_id = data['msm_id']
   ips = _getips( data['result'] )
   for ip in ips:
      loc = getlocforip( ip )
      locs.add( loc )
   return locs

def trace2txt( data, **kwargs ):
   res = data['result']
   msm_id = data['msm_id']
   ## print a header
   print "## msm_id:%s prb_id:%s dst:%s" % (msm_id, data['prb_id'], data['dst_addr'])

   for hop in res:
      ips = {}
      for hr in hop['result']:
         if 'from' in hr and 'rtt' in hr:
            if hr['from'] not in ips:
               ips[ hr['from'] ] = [ hr['rtt'] ]
            else:
               ips[ hr['from'] ].append( hr['rtt'] )
         else:
            print "%s err:%s" % ( hop['hop'] , hr )

      for ip in ips:
         host = gethostforip( ip )
         asn = getasnforip( ip )
         loc = getlocforip( ip )
         #print "%s [AS%s] %s (%s) %s |%s| %s" % ( hop['hop'], asn, host, ip , sorted(ips[ip]), loc, type(loc) )
         if loc == None:
            loc = ''
         if asn == None:
            asn = ''
         else:
            asn = 'AS%s' % ( asn )
         if kwargs['hostnames'] == False or host == None:
            host = ip
         print "%s (%s) %s %s |%s|" % ( hop['hop'], asn, host , sorted(ips[ip]), loc.encode('ascii','replace') )
