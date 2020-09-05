# coding=utf-8
# import logging
# import psutil
# import socket
# from datetime import datetime, timedelta
# import uuid
# import locale
# import time
# import string
# from flask import render_template, request, session, jsonify, Response, Blueprint, current_app, g
# from werkzeug.local import LocalProxy
# from psdash.helpers import socket_families, socket_types
# from distutils.log import info
import MySQLdb
import threading
import os
#from pip.cmdoptions import src
#print "hello"
def update():
    #print "test file update function started"

    db = MySQLdb.connect(host="localhost",    # your host, usually localhost
        user="root",         # your username
        passwd="Gift123",  # your password
        db="test")        # name of the data base
    curl = db.cursor()

    dbr = 'test'
    dbr_user = 'root'
    dbr_password = 'Gift123'

    #print "test file update function called"    
    ## Get requests from cloudlets and decision parameters
    self = '172.16.24.34'
    curl.execute("SELECT ip_address FROM resource where ip_address!='%s'"% (self))
    results = curl.fetchall()
    #print results
    
    threading.Timer(30.0, update).start()
    #print "test file thread update called" 
    ##used crop or iter next to skip itself 172.16.24.34 (Broker)
    #crop_results = iter(results)
    #next(crop_results)
    for n in results:
        #print "pppppppppppppppppppppppppppppppp",n[0]
        status = True if os.system("ping %s -c 1 > /dev/null 2>&1"% (n[0])) is 0 else False       
        if status == True:
            dbr_host = n[0]
            #print n[0]
            conn = MySQLdb.Connection(db=dbr, host=dbr_host, user=dbr_user, passwd=dbr_password)
            curr = conn.cursor()
            
            ##ziad# Get resource index and level info from cloudlets
            #print "Resource Discovery Initiated"
            exist = curr.execute("SELECT a.ip_address, b.* from resource a, decision_parameters b")
            results = curr.fetchall()
            #print exist, results
            if exist != 0:
                #print results
                cloudlet_ip = results[0][0]
                resource_index = results[0][1]
                resource_level = results[0][2]              
                #print "Decision parameters received from " + cloudlet_ip
               
                dec_param_exist = curl.execute("select * from decision_parameters where cloudlet_ip='%s'"% (cloudlet_ip))
                dec_result = curl.fetchall()
               
                #ziad# check if decision parameter table is empty
                #ziad# and for all cloudlet the record exist and updated
                #print dec_param_exist, dec_result
                if dec_param_exist != 1:
                    curl.execute("INSERT INTO decision_parameters SET cloudlet_ip='%s',resource_index=%s,resource_level='%s'"% (cloudlet_ip,resource_index,resource_level))
                    db.commit()
                    #print "Insertion Successful" + cloudlet_ip
                else:
                    curl.execute("UPDATE decision_parameters SET resource_index=%s,resource_level='%s' where cloudlet_ip='%s'"% (resource_index,resource_level,cloudlet_ip))
                    db.commit()
                    #print "Decision parameters updated " + cloudlet_ip
            else:
                print "Failed to get decision_parameters from remote"
            
            #print "Request Discovery Initiated"
            ##ziad # Get new requests from cloudlets
            curr.execute("SELECT a.ip_address, a.cloudlet_name, b.*,c.* from resource a, user_request b, status c where b.request_number=c.request_number")
            results = curr.fetchall()
            #print "11111111111111111111111111",results
            for row in results:
                cloudlet_ip = row[0]
                cloudlet_name = row[1]
                request_number = row[2]
                request_dt = row[3]
                user = row[4]
                vm_name = row[5]
                vm_ip = row[6]
                vm_cpu = row[7]
                vm_storage = row[8]
                vm_memory = row[9]
                vm_user = row[10]
                vm_pass = row[11]
                vm_file_name = row[12]
                #request_id = row[13]
                #request_number = row[14]
                request_status = row[15]
                decision_status = row[16]
                offload_status = row[17]
                migration_status = row[18]
                error_status = row[19]
                mes_to_user = row[20]  
                print request_number, request_status
                #print "Retrieval Successful"
                 
                req_record_exist = curl.execute("select request_number, ip_address from user_request")
                req_result = curl.fetchall()
                
                #ziad# check if there is any new request at any cloudlet
                if req_record_exist != 0:
                    for i in range(len(req_result)):
                        if (req_result[i][0] == request_number and req_result[i][1]== cloudlet_ip):
                            record = 1
                            break
                        else:
                            record = 0
                    #print "rrrrrrrrrrrrrrrrrrrrrrrr",record
                    if record == 0:
                        curl.execute("INSERT INTO user_request SET ip_address='%s',cloudlet_name='%s',request_number=%s,request_dt='%s',user='%s',vm_name='%s',vm_ip='%s',vm_cpu=%s,vm_storage=%s,vm_memory=%s,vm_user='%s',vm_pass='%s',vm_file_name='%s'"% (cloudlet_ip, cloudlet_name, request_number, request_dt, user, vm_name, vm_ip, vm_cpu, vm_storage, vm_memory, vm_user, vm_pass, vm_file_name))
                        db.commit()
                        curl.execute("INSERT INTO status SET ip_address='%s',request_number=%s,request_status='%s',decision_status='%s',offload_status='%s',migration_status='%s',error_status='%s',mes_to_user='%s'"% (cloudlet_ip, request_number, request_status, decision_status, offload_status, migration_status, error_status, mes_to_user))
                        db.commit()
                        print "New Request received from " + cloudlet_ip
                    else:
                        #print request_number, decision_status
                        curl.execute("update status SET request_status='%s',decision_status='%s',offload_status='%s',migration_status='%s',error_status='%s',mes_to_user='%s' where request_number=%s and ip_address='%s'"% (request_status, decision_status, offload_status, migration_status, error_status, mes_to_user, request_number, cloudlet_ip))
                        db.commit()
               
                else:   
                    print "New Request received from " + cloudlet_ip
                    curl.execute("INSERT INTO user_request SET ip_address='%s',cloudlet_name='%s',request_number=%s,request_dt='%s',user='%s',vm_name='%s',vm_ip='%s',vm_cpu=%s,vm_storage=%s,vm_memory=%s,vm_user='%s',vm_pass='%s',vm_file_name='%s'"% (cloudlet_ip, cloudlet_name, request_number, request_dt, user, vm_name, vm_ip, vm_cpu, vm_storage, vm_memory, vm_user, vm_pass, vm_file_name))
                    db.commit()
                    curl.execute("INSERT INTO status SET ip_address='%s',request_number=%s,request_status='%s',decision_status='%s',offload_status='%s',migration_status='%s',error_status='%s',mes_to_user='%s'"% (cloudlet_ip, request_number, request_status, decision_status, offload_status, migration_status, error_status, mes_to_user))
                    db.commit()     
        else:
            print "Remote request not received. Connection failed with ", n[0]
    
    curl.execute("SELECT * FROM user_request")
    results = curl.fetchall()
      
    ##ziad# print request table
#     print "Request table"
#     widths = []
#     columns = []
#     tavnit = '|'
#     separator = '+' 
#       
#     for cd in curl.description:
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
    

    ## Select request with pending decision and filter eligible cloudlets
    #curl.execute("SELECT distinct a.ip_address, a.cloudlet_name, a.request_number, a.vm_cpu, a.vm_storage, a.vm_memory, b.decision_status FROM user_request a, status b where decision_status='pending'")
    curl.execute("select a.ip_address, a.cloudlet_name, a.request_number, a.vm_cpu, a.vm_storage, a.vm_memory from user_request a, status b where a.request_number=b.request_number and b.decision_status='pending'")
    rq_result = curl.fetchall()
    #print "555555555555555555555555555555",rq_result
    curl.execute("delete from el_cloudlet")
    for row in rq_result:
        cloudlet_ip = row[0]
        cloudlet_name = row[1]
        request_number = row[2]
        vm_cpu = row[3]
        vm_storage = row[4]
        vm_memory = row[5]
        #print request_number
           
        curl.execute("select ip_address,cpu_cores,disk_free,memory_free from resource where ip_address!='%s'"% (self))
        rresult = curl.fetchall()
        #print rresult
           
        el_cloudlet = []
        ## Filter eligible cloudlets
        for i in range(len(rresult)):
            if (rresult[i][1] >= vm_cpu and rresult[i][2] >= vm_storage and rresult[i][3] >= vm_memory):
                el_cloudlet.append(rresult[i][0])
                #print "Elgible cloudlet", el_cloudlet, request_number
            else:
                el_cloudlet.append('NULL')
                #print "Elgible cloudlet", el_cloudlet, request_number
                        
        ##Stop duplicate processing on request for eligible cloudlets
        ## and insert eligible cloudlets in table el_cloudlets
        rec_exist = curl.execute("select cloudlet_ip,request_number from el_cloudlet")
        el_result = curl.fetchall()
        #print el_result
        if rec_exist != 0:
            #print el_result[1][0]
            for i in range(len(el_result)):
                #print request_number, el_result[i][0]
                if cloudlet_ip == el_result[i][0] and request_number == el_result[i][1]:
                    #print "case 1",result[i][0]
                    record = 1
                    break
                else:
                    record = 0
                    #print "case 0", result[i][0]
                      
            #print record
            if record == 0:
                for i in range(len(el_cloudlet)):
                    curl.execute("INSERT INTO el_cloudlet SET cloudlet_ip='%s',request_number=%s,el_cloudlet_ip='%s'"% (cloudlet_ip,request_number,el_cloudlet[i]))
                    db.commit()
                    #print "Insertion Successful 2"
                    #print record
        else:
            #print "Table Empty"
            for i in range(len(el_cloudlet)):
                curl.execute("INSERT INTO el_cloudlet SET cloudlet_ip='%s',request_number=%s,el_cloudlet_ip='%s'"% (cloudlet_ip,request_number,el_cloudlet[i]))
                db.commit()
                #print "Insertion Successful 1"
           
        # Finalize decision, update pending decision status in user_request
        # and push the decision along status to the respective cloudlet
        #print request_number
        #print "Request decision made, pushing results to host " + cloudlet_ip
        el_exist = curl.execute("select * from el_cloudlet where el_cloudlet_ip=(select cloudlet_ip from decision_parameters where resource_index=(select max(resource_index) from decision_parameters where resource_level != 'critical') limit 1) and request_number=%s"% (request_number))
        el_result = curl.fetchall()
        #print "hhhhhhhhhhhhhhhh",el_result
   
        if el_exist !=0:
            cloudlet_ip = el_result[0][0]
            request_number = el_result[0][1]
            final_cl_ip = el_result[0][2]
            #print cloudlet_ip
            exist = curl.execute("select * from decision")
            res = curl.fetchall()
            #print res[0][0]
            if exist !=0:
                for n in res:
                    rqn = n[0]
                    srcip = n[1]
                    #dstip = n[2]
                    if (srcip == cloudlet_ip and rqn == request_number):
                        record = 1
                        break
                    else:
                        record = 0
                            
                if record == 0:
                    curl.execute("insert into decision set request_number=%s,src_cl_ip='%s',dst_cl_ip='%s',decision_sent='no'"% (request_number, cloudlet_ip, final_cl_ip))
                    db.commit()
                    curl.execute("update status set decision_status='complete' where ip_address='%s' and request_number=%s"% (cloudlet_ip,request_number))
                    db.commit()        
               
            else:
                curl.execute("insert into decision set request_number=%s,src_cl_ip='%s',dst_cl_ip='%s',decision_sent='no'"% (request_number, cloudlet_ip, final_cl_ip))
                db.commit() 
                curl.execute("update status set decision_status='complete' where ip_address='%s' and request_number=%s"% (cloudlet_ip, request_number))
                db.commit()
        else:
            print "No eligible cloudlet exist"             
           
               
    #ziad# Send decision back to source and optimal cloudlet
    dexist = curl.execute("select * from decision where decision_sent='no'")
    ldecision = curl.fetchall()    
    if dexist !=0:
        for row in ldecision:
            request_number = row[0]
            src_cloudlet_ip = row[1]
            dst_cloudlet_ip = row[2]    
                   
            src_status = True if os.system("ping %s -c 1 > /dev/null 2>&1"% (src_cloudlet_ip)) is 0 else False       
            if src_status == True:
                conn = MySQLdb.Connection(db=dbr, host=src_cloudlet_ip, user=dbr_user, passwd=dbr_password)
                curr = conn.cursor()
               
                rdec_exist = curr.execute("select * from decision")
                rdec_result = curr.fetchall()
                #print rdec_exist
                if rdec_exist != 0:
                    for i in range(len(rdec_result)):
                        if (rdec_result[i][0] == request_number):
                            record = 1
                            break
                        else:
                            record = 0
                            #print record
                    if record == 0:
                        check = curr.execute("insert into decision set request_number=%s,src_cl_ip='%s',dst_cl_ip='%s'"% (request_number, src_cloudlet_ip, dst_cloudlet_ip))
                        conn.commit()
                        if check != 0:
#                             curl.execute("update decision set decision_sent='yes' where request_number=%s and src_cl_ip='%s'"% (request_number, src_cloudlet_ip))
#                             db.commit()
                        
                            st = curr.execute("update status set decision_status='complete' where request_number=%s"% (request_number))
                            conn.commit()
                            if st != 0:
                                print "Decision successfully pushed to remote source"
                                #print "Insertion Successful 2"
                            else:
                                print "Failed to update decision status at remote source"
                        else:
                            print "Decision was not sent to source cloudlet, connection failed with", src_cloudlet_ip                               
               
                else:   
                    check = curr.execute("insert into decision set request_number=%s,src_cl_ip='%s',dst_cl_ip='%s'"% (request_number, src_cloudlet_ip, dst_cloudlet_ip))
                    conn.commit()
                    if check != 0:
#                         curl.execute("update decision set decision_sent='yes' where request_number=%s and src_cl_ip='%s'"% (request_number, src_cloudlet_ip))
#                         db.commit()
                         
                        st = curr.execute("update status set decision_status='complete' where request_number=%s"% (request_number))
                        conn.commit()
                        if st != 0:
                            print "Decision successfully pushed to remote source"
                        else:
                            print "Failed to update decision status at remote source"
#                     curl.execute("update decision set decision_sent='yes' where request_number=%s and src_cl_ip='%s'"% (request_number, src_cloudlet_ip))
#                     db.commit()
#                     
#                     curr.execute("update status set decision_status='complete' where request_number=%s"% (request_number))
#                     conn.commit()
#                     print "Decision successfully pushed to host"
                    #print "Insertion Successful 1"
            else:
                print "Decision was not sent to source cloudlet, connection failed with", src_cloudlet_ip                               
               
            dst_status = True if os.system("ping %s -c 1 > /dev/null 2>&1"% (dst_cloudlet_ip)) is 0 else False       
            if dst_status == True:
                conn = MySQLdb.Connection(db=dbr, host=dst_cloudlet_ip, user=dbr_user, passwd=dbr_password)
                curr = conn.cursor()
                 
                rdec_exist = curr.execute("select * from decision")
                rdec_result = curr.fetchall()
                #print rdec_exist
                if rdec_exist != 0:
                    for i in range(len(rdec_result)):
                        if (rdec_result[i][0] == request_number):
                            record = 1
                            break
                        else:
                            record = 0
                            #print record
                    if record == 0:
                        check = curr.execute("insert into decision set request_number=%s,src_cl_ip='%s',dst_cl_ip='%s'"% (request_number, src_cloudlet_ip, dst_cloudlet_ip))
                        conn.commit()
                        print "Decision successfully pushed to remote destination"
#                         if check != 0:
#                             st = curr.execute("update status set decision_status='complete' where request_number=%s"% (request_number))
#                             conn.commit()  
#                             if st != 0:
#                                 print "Decision successfully pushed to remote d"
#                                 #print "Insertion Successful 2"
#                             else:
#                                 print "Failed to update decision status at remote destination"  
                        #print "Insertion Successful 2"
                else:   
                    check = curr.execute("insert into decision set request_number=%s,src_cl_ip='%s',dst_cl_ip='%s'"% (request_number, src_cloudlet_ip, dst_cloudlet_ip))
                    conn.commit()
                    print "Decision successfully pushed to remote destination"
#                     if check != 0:
#                         st = curr.execute("update status set decision_status='complete' where request_number=%s"% (request_number))
#                         conn.commit()
#                         if st != 0:
#                             print "Decision successfully pushed to remote destination"
#                             #print "Insertion Successful 2"
#                         else:
#                             print "Failed to update decision status at remote destination" 
                    #print "Insertion Successful 1"
                #print "Decision has been successfully pushed to remote. Deleting from broker"
                #curl.execute("delete from decision where request_number=%s"% (request_number))
                #db.commit()
                    
            else:
                print "Decision was not sent to destination cloudlet, connection failed with", dst_cloudlet_ip
               
#     else:
#         dummy = 0
#         #print "No decision sending is pending"
           
update()
    
    


