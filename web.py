# coding=utf-8
import logging
import psutil
import socket
from datetime import datetime, timedelta
import uuid
import locale
import MySQLdb
import time
import os
import string
from flask import render_template, request, session, jsonify, Response, Blueprint, current_app, g
from werkzeug.local import LocalProxy
from psdash.helpers import socket_families, socket_types
from distutils.log import info
import datetime

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
logger = logging.getLogger('psdash.web')
webapp = Blueprint('psdash', __name__, static_folder='static')

#Ziad# local DB connection
db = MySQLdb.connect(host="localhost",    # your host, usually localhost
    user="root",         # your username
    passwd="Gift123",  # your password
    db="test")        # name of the data base
cur = db.cursor()

def get_current_node():
    return current_app.psdash.get_node(g.node)
    

def get_current_service():
    return get_current_node().get_service()


current_node = LocalProxy(get_current_node)
current_service = LocalProxy(get_current_service)


def fromtimestamp(value, dateformat='%Y-%m-%d %H:%M:%S'):
    dt = datetime.fromtimestamp(int(value))
    return dt.strftime(dateformat)


@webapp.context_processor
def inject_nodes():
    return {"current_node": current_node, "nodes": current_app.psdash.get_nodes()}


@webapp.context_processor
def inject_header_data():
    sysinfo = current_service.get_sysinfo()
    uptime = timedelta(seconds=sysinfo['uptime'])
    uptime = str(uptime).split('.')[0]
    
    return {
        'os': sysinfo['os'].decode('utf-8'),
        'hostname': sysinfo['hostname'].decode('utf-8'),
        'uptime': uptime
    }

@webapp.url_defaults
def add_node(endpoint, values):
    values.setdefault('node', g.node)
        

@webapp.before_request
def add_node():
    g.node = request.args.get('node', current_app.psdash.LOCAL_NODE)


@webapp.before_request
def check_access():
    allowed_remote_addrs = current_app.config.get('PSDASH_ALLOWED_REMOTE_ADDRESSES')
    if allowed_remote_addrs:
        if request.remote_addr not in allowed_remote_addrs:
            current_app.logger.info(
                'Returning 401 for client %s as address is not in allowed addresses.',
                request.remote_addr
            )
            current_app.logger.debug('Allowed addresses: %s', allowed_remote_addrs)
            return 'Access denied', 401

    username = current_app.config.get('PSDASH_AUTH_USERNAME')
    password = current_app.config.get('PSDASH_AUTH_PASSWORD')
    if username and password:
        auth = request.authorization
        if not auth or auth.username != username or auth.password != password:
            return Response(
                'Access deined',
                401,
                {'WWW-Authenticate': 'Basic realm="psDash login required"'}
            )


@webapp.before_request
def setup_client_id():
    if 'client_id' not in session:
        client_id = uuid.uuid4()
        current_app.logger.debug('Creating id for client: %s', client_id)
        session['client_id'] = client_id


@webapp.errorhandler(psutil.AccessDenied)
def access_denied(e):
    errmsg = 'Access denied to %s (pid %d).' % (e.name, e.pid)
    return render_template('error.html', error=errmsg), 401


@webapp.errorhandler(psutil.NoSuchProcess)
def access_denied(e):
    errmsg = 'No process with pid %d was found.' % e.pid
    return render_template('error.html', error=errmsg), 404

@webapp.route('/')
def index():
    sysinfo = current_service.get_sysinfo()
    
    #ziad# Get hostname
    info = sysinfo['hostname']
    #print info
    
    netifs = current_service.get_network_interfaces().values()
    netifs.sort(key=lambda x: x.get('bytes_sent'), reverse=True)
        
    data = {
        'load_avg': sysinfo['load_avg'],
        'num_cpus': sysinfo['num_cpus'],
        'memory': current_service.get_memory(),
        'swap': current_service.get_swap_space(),
        'disks': current_service.get_disks(),
        'cpu': current_service.get_cpu(),
        'users': current_service.get_users(),
        'net_interfaces': netifs,
        'page': 'overview',
        'is_xhr': request.is_xhr
    }
    #print data['net_interfaces']
    
    #ziad# Get desired parameters
    load = data['load_avg']
    AvLoad = load[1]
    
    disk = data['disks']
    
    mem = data['memory']
    
    cores = data['num_cpus']
    
    tcpu = data['cpu']
    
    #ziad# conversion from bytes to GB
    
    tdiskgb = round(float(disk[0]["space_total"])/1000000000,1)
    fdiskgb = round(float(disk[0]["space_free"])/1000000000,1)
    
    tmemgb = round(float(mem["total"])/1000000000,1)
    fmemgb = round(float(mem["free"])/1000000000,1)
    
    #ziad# Get active network interface ip address
    ipaddress = data['net_interfaces']
   
    nam = ipaddress[0]['name']
    if nam == 'ens33':
        ip = ipaddress[0]['ip']
    else:    
        ip = ipaddress[1]['ip']
    #print ip
    
    currentDT = datetime.datetime.now()
    ltime = (currentDT.strftime("%H:%M:%S"))        
    
    msg = cur.execute("SELECT ip_address FROM resource WHERE ip_address='%s'"% (ip))
    #ipaddress = cur.fetchall()
    
    #ziad# check if resource table is empty and new cloudlet has been discovered
    if msg != 1:
        print 'New Cloudlet discovered'
        status = 'up'
        cur.execute("INSERT INTO resource SET ip_address='%s',cloudlet_name='%s',last_updated='%s',status='%s',CPU_Cores=%s,CPU_AvLoad=%s,disk_total=%s,disk_free=%s,memory_total=%s,memory_free=%s"% (ip, info, status, ltime, cores, AvLoad, tdiskgb, fdiskgb, tmemgb, fmemgb))
        db.commit()
    else:
        #print 'No new cloudlet discovered'
        cur.execute("select ip_address from resource")
        ipaddress = cur.fetchall()
        #print ipaddress
        for n in ipaddress:
            #nn = n[0]
            #print n
            status = True if os.system("ping %s -c 1 > /dev/null 2>&1"% (n[0])) is 0 else False       
            if status == True:
                status = 'up'
#                 #print status
                cur.execute("UPDATE resource SET status='%s' WHERE ip_address='%s'"% (status, n[0]))
                db.commit()    
            else:
                status = 'down'
#                 #print status
                cur.execute("UPDATE resource SET status='%s' WHERE ip_address='%s'"% (status, n[0]))
                db.commit()    
        #print status
        cur.execute("UPDATE resource SET last_updated='%s',CPU_AvLoad=%s,disk_total=%s,disk_free=%s,memory_total=%s,memory_free=%s WHERE ip_address='%s'"% (ltime, AvLoad, tdiskgb, fdiskgb, tmemgb, fmemgb, ip))
        db.commit()
        
    cur.execute("SELECT * FROM resource")
    results = cur.fetchall()
    
    #ziad# print output of resource table
#     print "Resource table"
#     widths = []
#     columns = []
#     tavnit = '|'
#     separator = '+' 
#    
#     for cd in cur.description:
#         widths.append(max(cd[2], len(cd[0])))
#         columns.append(cd[0])
#    
#     for w in widths:
#         tavnit += " %-"+"%ss |" % (w,)
#         separator += '-'*w + '--+'
#    
#     print(separator)
#     print(tavnit % tuple(columns))
#     print(separator)
#     for row in results:
#         print(tavnit % row)
#     print(separator)
       
    return render_template('index.html', **data)


@webapp.route('/processes', defaults={'sort': 'cpu_percent', 'order': 'desc', 'filter': 'user'})
@webapp.route('/processes/<string:sort>')
@webapp.route('/processes/<string:sort>/<string:order>')
@webapp.route('/processes/<string:sort>/<string:order>/<string:filter>')
def processes(sort='pid', order='asc', filter='user'):
    procs = current_service.get_process_list()
    num_procs = len(procs)

    user_procs = [p for p in procs if p['user'] != 'root']
    num_user_procs = len(user_procs)
    if filter == 'user':
        procs = user_procs

    procs.sort(
        key=lambda x: x.get(sort),
        reverse=True if order != 'asc' else False
    )

    return render_template(
        'processes.html',
        processes=procs,
        sort=sort,
        order=order,
        filter=filter,
        num_procs=num_procs,
        num_user_procs=num_user_procs,
        page='processes',
        is_xhr=request.is_xhr
    )


@webapp.route('/process/<int:pid>', defaults={'section': 'overview'})
@webapp.route('/process/<int:pid>/<string:section>')
def process(pid, section):
    valid_sections = [
        'overview',
        'threads',
        'files',
        'connections',
        'memory',
        'environment',
        'children',
        'limits'
    ]

    if section not in valid_sections:
        errmsg = 'Invalid subsection when trying to view process %d' % pid
        return render_template('error.html', error=errmsg), 404

    context = {
        'process': current_service.get_process(pid),
        'section': section,
        'page': 'processes',
        'is_xhr': request.is_xhr
    }

    if section == 'environment':
        penviron = current_service.get_process_environment(pid)

        whitelist = current_app.config.get('PSDASH_ENVIRON_WHITELIST')
        if whitelist:
            penviron = dict((k, v if k in whitelist else '*hidden by whitelist*') 
                             for k, v in penviron.iteritems())

        context['process_environ'] = penviron
    elif section == 'threads':
        context['threads'] = current_service.get_process_threads(pid)
    elif section == 'files':
        context['files'] = current_service.get_process_open_files(pid)
    elif section == 'connections':
        context['connections'] = current_service.get_process_connections(pid)
    elif section == 'memory':
        context['memory_maps'] = current_service.get_process_memory_maps(pid)
    elif section == 'children':
        context['children'] = current_service.get_process_children(pid)
    elif section == 'limits':
        context['limits'] = current_service.get_process_limits(pid)

    return render_template(
        'process/%s.html' % section,
        **context
    )


@webapp.route('/network')
def view_networks():
    netifs = current_service.get_network_interfaces().values()
    netifs.sort(key=lambda x: x.get('bytes_sent'), reverse=True)

    # {'key', 'default_value'}
    # An empty string means that no filtering will take place on that key
    form_keys = {
        'pid': '', 
        'family': socket_families[socket.AF_INET],
        'type': socket_types[socket.SOCK_STREAM],
        'state': 'LISTEN'
    }

    form_values = dict((k, request.args.get(k, default_val)) for k, default_val in form_keys.iteritems())

    for k in ('local_addr', 'remote_addr'):
        val = request.args.get(k, '')
        if ':' in val:
            host, port = val.rsplit(':', 1)
            form_values[k + '_host'] = host
            form_values[k + '_port'] = int(port)
        elif val:
            form_values[k + '_host'] = val

    conns = current_service.get_connections(form_values)
    conns.sort(key=lambda x: x['state'])

    states = [
        'ESTABLISHED', 'SYN_SENT', 'SYN_RECV',
        'FIN_WAIT1', 'FIN_WAIT2', 'TIME_WAIT',
        'CLOSE', 'CLOSE_WAIT', 'LAST_ACK',
        'LISTEN', 'CLOSING', 'NONE'
    ]

    return render_template(
        'network.html',
        page='network',
        network_interfaces=netifs,
        connections=conns,
        socket_families=socket_families,
        socket_types=socket_types,
        states=states,
        is_xhr=request.is_xhr,
        num_conns=len(conns),
        **form_values
    )


@webapp.route('/disks')
def view_disks():
    disks = current_service.get_disks(all_partitions=True)
    io_counters = current_service.get_disks_counters().items()
    io_counters.sort(key=lambda x: x[1]['read_count'], reverse=True)
    return render_template(
        'disks.html',
        page='disks',
        disks=disks,
        io_counters=io_counters,
        is_xhr=request.is_xhr
    )


@webapp.route('/logs')
def view_logs():
    available_logs = current_service.get_logs()
    available_logs.sort(cmp=lambda x1, x2: locale.strcoll(x1['path'], x2['path']))

    return render_template(
        'logs.html',
        page='logs',
        logs=available_logs,
        is_xhr=request.is_xhr
    )


@webapp.route('/log')
def view_log():
    filename = request.args['filename']
    seek_tail = request.args.get('seek_tail', '1') != '0'
    session_key = session.get('client_id')

    try:
        content = current_service.read_log(filename, session_key=session_key, seek_tail=seek_tail)
    except KeyError:
        error_msg = 'File not found. Only files passed through args are allowed.'
        if request.is_xhr:
            return error_msg
        return render_template('error.html', error=error_msg), 404

    if request.is_xhr:
        return content

    return render_template('log.html', content=content, filename=filename)


@webapp.route('/log/search')
def search_log():
    filename = request.args['filename']
    query_text = request.args['text']
    session_key = session.get('client_id')

    try:
        data = current_service.search_log(filename, query_text, session_key=session_key)
        return jsonify(data)
    except KeyError:
        return 'Could not find log file with given filename', 404


@webapp.route('/register')
def register_node():
    name = request.args['name']
    port = request.args['port']
    host = request.remote_addr
    
    current_app.psdash.register_node(name, host, port)
    return jsonify({'status': 'OK'})

#db.commit()
#db.close()

@webapp.route('/test')
def test():
    
    return render_template("test.html")
