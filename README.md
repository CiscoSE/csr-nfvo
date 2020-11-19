# Cloud Services Router NFVO

This NSO package creates a new cloud service router virtual network function using the cisco NFVO bundle. In addition to that, it uses kickers to detect when the VNF is ready and apply a day1 service that configures the interfaces and OSPF

## Install

1. Clone this repo under the packages directory
2. cd to src and execute make clean all
3. Perform a packages reload in NSO
4. Make sure to review templates/csr-nfvo-template.xml and replace values that match your environment. 

## Requisites
1. NSO 5.1 or greater 
2. python3
3. cisco-ios NED
4. [interfaces-routing service package](https://github.com/CiscoSE/interfaces-routing)
5. esc NED
6. Cisco NFVO bundle

## Config example

```bash
admin@ncs# show running-config csr-nfvo 
csr-nfvo lwr04-csr-01
 mgmt_gateway 192.168.1.254
 mgmt_ip      192.168.1.1
 mgmt_netmask 255.255.255.0
 mgmt_mac     00:50:56:ff:d6:38
 host         192.168.0.1
 datastore    "datastore123"
 day1_config interface 2
  ip_address 1.1.1.1
  netmask    255.255.255.0
 !
 day1_config interface 3
  ip_address 1.1.2.1
  netmask    255.255.255.0
 !
 day1_config ospf process 1
 day1_config ospf area 0
!
admin@ncs# 
```


## Contacts

* Santiago Flores Kanter (sfloresk@cisco.com)