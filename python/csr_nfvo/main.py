# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service
from ncs.dp import Action

# ------------------------
# SERVICE CALLBACKS
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

# ------------------------
# ACTION CALLBACKS
# ------------------------
class PushDay1Service(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output, trans):
        self.log.info('action ', str(kp), " called")
        # Get root object
        root_ro = ncs.maagic.get_root(trans)
        # Get service parameters
        svc_params_cdb = ncs.maagic.get_node(trans, str(kp))
        # Make sure vnf-info object exists
        if root_ro.nfv.vnf_info.exists(svc_params_cdb._parent.name):
            nfv_info_cbd = root_ro.nfv.vnf_info[svc_params_cdb._parent.name]
            # Make sure vnf-info netplan object exists
            if root_ro.nfv.internal.netconf_deployment_plan.exists(nfv_info_cbd.vnfm + "-vnf-info-" + svc_params_cdb._parent.name):
                plan_cdb = root_ro.nfv.internal.netconf_deployment_plan[nfv_info_cbd.vnfm + "-vnf-info-" + svc_params_cdb._parent.name]
                # Make sure state ready has been reached. This means that the VNF is ready to be managed by NSO
                if plan_cdb.plan.component["cisco-nfvo-nano-services:deployment", nfv_info_cbd.vnfm + "-vnf-info-" + svc_params_cdb._parent.name].state["ready"].status == "reached":
                    with ncs.maapi.single_write_trans("admin", "python", ["ncsadmin"]) as t:
                        self.log.info("Starting sync from for ", svc_params_cdb._parent.name)
                        root = ncs.maagic.get_root(t)
                        new_interface_routing_svc = root.interfaces_routing.create(svc_params_cdb._parent.name + "-day1")
                        # Sync from
                        sync_from_result = root.devices.device[svc_params_cdb._parent.name].sync_from.request().result
                        if not sync_from_result:
                            raise ("Cannot sync from device. Result was " + sync_from_result)

                        # Create service
                        self.log.info("Creating day1 service for ", svc_params_cdb._parent.name)
                        new_interface_routing_svc.device = svc_params_cdb._parent.name
                        for interface in svc_params_cdb.interface:
                            new_interface_routing_svc.interface.create(interface.id)
                            new_interface_routing_svc.interface[interface.id].ip_address = interface.ip_address
                            new_interface_routing_svc.interface[interface.id].netmask = interface.netmask
                        new_interface_routing_svc.ospf.area = svc_params_cdb.ospf.area
                        new_interface_routing_svc.ospf.process = svc_params_cdb.ospf.process
                        
                        t.apply()
                        self.log.info("Day1 service for ", svc_params_cdb._parent.name, " created succesfully")
                else:
                    self.log.info("Did not apply day1 service for ", str(kp)," - ready state not reached ")
            
            else:
                self.log.info("Did not apply day1 service for ", str(kp)," - plan does not exists ")
        else:
            self.log.info("Did not apply day1 service for ", str(kp)," - nfv info does not exists ")
        output.result = "Completed"


class StartDeployment(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output, trans):
        
        # Create nfv-info
        self.log.info("kp: ", str(kp)) 
        with ncs.maapi.single_write_trans(uinfo.username, uinfo.context, ["ncsadmin"]) as t:
            
            csr_nfvo = ncs.maagic.get_node(t,str(kp))
            self.log.info("Creating vnf-info ", csr_nfvo.name)
            template = ncs.template.Template(csr_nfvo)
            template.apply('csr-nfvo-vnfd')
            template.apply('csr-nfvo-template')
            t.apply()

        # Create kicker
        with ncs.maapi.single_write_trans(uinfo.username, uinfo.context, ["ncsadmin"]) as t:
            # Get nfv-info information
            root = ncs.maagic.get_root(t)
            csr_nfvo = ncs.maagic.get_node(t,str(kp))
            nfv_info_cbd = root.nfv.vnf_info[csr_nfvo.name]
            self.log.info("Creating kicker ", csr_nfvo.name+"-kicker")
            new_kicker = root.kickers.data_kicker.create(csr_nfvo.name + "-kicker")
            new_kicker.monitor = "/nfv/cisco-nfvo:internal/netconf-deployment-plan[id='" + nfv_info_cbd.vnfm + "-vnf-info-" + csr_nfvo.name + "']/plan/component[type='cisco-nfvo-nano-services:deployment'][name='" + nfv_info_cbd.vnfm + "-vnf-info-" + csr_nfvo.name + "']/state[name='ncs:ready']/status"
            new_kicker.kick_node = "/csr-nfvo[name='"+nfv_info_cbd.name+"']/day1_config"
            new_kicker.action_name = "push"
            t.apply()

# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Main RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('csr-nfvo-servicepoint', ServiceCallbacks)
        self.register_action('push-day1-service-action', PushDay1Service)
        self.register_action('start-deployment-action', StartDeployment)
        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Main FINISHED')
