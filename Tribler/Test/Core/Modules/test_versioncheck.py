from __future__ import absolute_import

from six import ensure_binary

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import deferLater
from twisted.web import resource, server

import Tribler.Core.Utilities.json_util as json
from Tribler.Core.Modules import versioncheck_manager
from Tribler.Core.Modules.versioncheck_manager import VersionCheckManager
from Tribler.Test.test_as_server import TestAsServer
from Tribler.Test.tools import trial_timeout


class VersionResource(resource.Resource):

    isLeaf = True

    def __init__(self, response, response_code):
        resource.Resource.__init__(self)
        self.response = response
        self.response_code = response_code

    def render_GET(self, request):
        request.setResponseCode(self.response_code)
        return self.response


class TestVersionCheck(TestAsServer):

    @inlineCallbacks
    def setUp(self):
        self.port = self.get_port()
        self.server = None
        self.should_call_new_version_callback = False
        self.new_version_called = False
        versioncheck_manager.VERSION_CHECK_URL = 'http://localhost:%s' % self.port
        yield super(TestVersionCheck, self).setUp()
        self.session.lm.version_check_manager = VersionCheckManager(self.session)

        self.session.notifier.notify = self.notifier_callback

    def notifier_callback(self, subject, changeType, obj_id, *args):
        self.new_version_called = True

    def setup_version_server(self, response, response_code=200):
        site = server.Site(VersionResource(ensure_binary(response), response_code))
        self.server = reactor.listenTCP(self.port, site)

    def assert_new_version_called(self, _res):
        self.assertTrue(self.new_version_called == self.should_call_new_version_callback)
        return maybeDeferred(self.server.stopListening)

    def check_version(self):
        return self.session.lm.version_check_manager.check_new_version().addCallback(self.assert_new_version_called)

    def test_start(self):
        """
        Test whether the periodic version lookup works as expected
        """
        self.setup_version_server(json.dumps({'name': 'v1.0'}))
        self.session.lm.version_check_manager.start()
        self.assertFalse(self.session.lm.version_check_manager.is_pending_task_active("tribler version check"))

        import Tribler.Core.Modules.versioncheck_manager as vcm
        vcm.version_id = "7.0.0"
        self.session.lm.version_check_manager.start()
        yield deferLater(reactor, 0.4, lambda: None)  # Wait a bit for the check to complete
        self.assertTrue(self.session.lm.version_check_manager.is_pending_task_active("tribler version check"))

    @trial_timeout(10)
    def test_old_version(self):
        self.setup_version_server(json.dumps({'name': 'v1.0'}))
        return self.check_version()

    @trial_timeout(10)
    def test_new_version(self):
        self.should_call_new_version_callback = True
        self.setup_version_server(json.dumps({'name': 'v1337.0'}))
        return self.check_version()

    @trial_timeout(20)
    def test_bad_request(self):
        self.setup_version_server(json.dumps({'name': 'v1.0'}), response_code=500)
        return self.check_version()

    @trial_timeout(20)
    def test_connection_error(self):
        self.setup_version_server(json.dumps({'name': 'v1.0'}))
        versioncheck_manager.VERSION_CHECK_URL = "http://this.will.not.exist"
        return self.check_version()

    @trial_timeout(20)
    def test_non_json_response(self):
        def on_error(_err):
            versioncheck_manager.check_failed = True

        self.setup_version_server('hello world - not json')

        versioncheck_manager.check_failed = False
        yield self.check_version().addErrback(on_error)

        self.assertTrue(versioncheck_manager.check_failed)
        return
