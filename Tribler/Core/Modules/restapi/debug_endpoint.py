import json

import psutil
from twisted.web import http, resource

from Tribler.Core.Utilities.instrumentation import WatchDog
from Tribler.community.tunnel.tunnel_community import TunnelCommunity


class DebugEndpoint(resource.Resource):
    """
    This endpoint is responsible for handing requests regarding debug information in Tribler.
    """

    def __init__(self, session):
        resource.Resource.__init__(self)

        child_handler_dict = {"circuits": DebugCircuitsEndpoint, "open_files": DebugOpenFilesEndpoint,
                              "open_sockets": DebugOpenSocketsEndpoint, "threads": DebugThreadsEndpoint}

        for path, child_cls in child_handler_dict.iteritems():
            self.putChild(path, child_cls(session))


class DebugCircuitsEndpoint(resource.Resource):
    """
    This class handles requests regarding the tunnel community debug information.
    """

    def __init__(self, session):
        resource.Resource.__init__(self)
        self.session = session

    def get_tunnel_community(self):
        """
        Search for the tunnel community in the dispersy communities.
        """
        for community in self.session.get_dispersy_instance().get_communities():
            if isinstance(community, TunnelCommunity):
                return community
        return None

    def render_GET(self, request):
        """
        .. http:get:: /debug/circuits

        A GET request to this endpoint returns information about the built circuits in the tunnel community.

            **Example request**:

            .. sourcecode:: none

                curl -X GET http://localhost:8085/debug/circuits

            **Example response**:

            .. sourcecode:: javascript

                {
                    "circuits": [{
                        "id": 1234,
                        "state": "EXTENDING",
                        "goal_hops": 4,
                        "bytes_up": 45,
                        "bytes_down": 49,
                        "created": 1468176257,
                        "hops": [{
                            "host": "unknown"
                        }, {
                            "host": "39.95.147.20:8965"
                        }],
                        ...
                    }, ...]
                }
        """
        tunnel_community = self.get_tunnel_community()
        if not tunnel_community:
            request.setResponseCode(http.NOT_FOUND)
            return json.dumps({"error": "tunnel community not found"})

        circuits_json = []
        for circuit_id, circuit in tunnel_community.circuits.iteritems():
            item = {'id': circuit_id, 'state': str(circuit.state), 'goal_hops': circuit.goal_hops,
                    'bytes_up': circuit.bytes_up, 'bytes_down': circuit.bytes_down, 'created': circuit.creation_time}
            hops_array = []
            for hop in circuit.hops:
                hops_array.append({'host': 'unknown' if 'UNKNOWN HOST' in hop.host else '%s:%s' % (hop.host, hop.port)})

            item['hops'] = hops_array
            circuits_json.append(item)

        return json.dumps({'circuits': circuits_json})


class DebugOpenFilesEndpoint(resource.Resource):
    """
    This class handles request for information about open files.
    """

    def __init__(self, session):
        resource.Resource.__init__(self)
        self.session = session

    def render_GET(self, request):
        """
        .. http:get:: /debug/open_files

        A GET request to this endpoint returns information about files opened by Tribler.

            **Example request**:

            .. sourcecode:: none

                curl -X GET http://localhost:8085/debug/open_files

            **Example response**:

            .. sourcecode:: javascript

                {
                    "open_files": [{
                        "path": "path/to/open/file.txt",
                        "fd": 33,
                    }, ...]
                }
        """
        my_process = psutil.Process()

        return json.dumps({
            "open_files": [{"path": open_file.path, "fd": open_file.fd} for open_file in my_process.open_files()]})


class DebugOpenSocketsEndpoint(resource.Resource):
    """
    This class handles request for information about open sockets.
    """

    def __init__(self, session):
        resource.Resource.__init__(self)
        self.session = session

    def render_GET(self, request):
        """
        .. http:get:: /debug/open_sockets

        A GET request to this endpoint returns information about open sockets.

            **Example request**:

            .. sourcecode:: none

                curl -X GET http://localhost:8085/debug/openfiles

            **Example response**:

            .. sourcecode:: javascript

                {
                    "open_sockets": [{
                        "family": 2,
                        "status": "ESTABLISHED",
                        "laddr": "0.0.0.0:0",
                        "raddr": "0.0.0.0:0",
                        "type": 30
                    }, ...]
                }
        """
        my_process = psutil.Process()
        sockets = []
        for open_socket in my_process.connections():
            sockets.append({
                "family": open_socket.family,
                "status": open_socket.status,
                "laddr": ("%s:%d" % open_socket.laddr) if open_socket.laddr else "-",
                "raddr": ("%s:%d" % open_socket.raddr) if open_socket.raddr else "-",
                "type": open_socket.type
            })

        return json.dumps({"open_sockets": sockets})


class DebugThreadsEndpoint(resource.Resource):
    """
    This class handles request for information about threads.
    """

    def __init__(self, session):
        resource.Resource.__init__(self)
        self.session = session

    def render_GET(self, request):
        """
        .. http:get:: /debug/threads

        A GET request to this endpoint returns information about running threads.

            **Example request**:

            .. sourcecode:: none

                curl -X GET http://localhost:8085/debug/threads

            **Example response**:

            .. sourcecode:: javascript

                {
                    "open_files": [{
                        "path": "path/to/open/file.txt",
                        "fd": 33,
                    }, ...]
                }
        """
        watchdog = WatchDog()
        return json.dumps({"threads": watchdog.get_threads_info()})
