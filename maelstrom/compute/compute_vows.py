from pyvows import Vows, expect

from cloudcafe.compute.composites import ComputeComposite, \
    ComputeAdminComposite, ComputeIntegrationComposite


class ComputeContext(Vows.Context):

    def topic(self):
        return ComputeComposite()

@Vows.batch
class WhenACreateServerRequestIsMade(Vows.Context):

    def topic(self):
        compute = ComputeComposite()
        server = compute.servers.client.create_server(
            'testserver123', '8f569a31-ee74-409b-9dcb-fb7576e307e9', '2').entity
        return server

    def the_server_id_should_be_set(self, topic):
        expect(topic.id).Not.to_be_null()

    def the_admin_password_should_be_in_the_response(self, topic):
        expect(topic.admin_pass).Not.to_be_null()

    class AfterTheServerFinishesBuilding(Vows.Context):

        def topic(self, server):
            compute = ComputeComposite()
            created_server = compute.servers.behaviors.wait_for_server_creation(server.id)
            return created_server

        def the_server_should_have_the_correct_name(self, topic):
            expect(topic.name).to_equal("testserver123")

        class OnceTheServerIsPingable(Vows.Context):

            def topic(self, server, building_server):
                compute = ComputeComposite()
                remote_client = compute.servers.behaviors.get_remote_instance_client(
                    server, compute.servers.config)
                return server, remote_client

            def the_hostname_should_match_the_server_name(self, topic):
                server, remote_client = topic
                expect(remote_client.get_hostname()).to_equal(server.name)