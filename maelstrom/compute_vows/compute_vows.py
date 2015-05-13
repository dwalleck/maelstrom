from pyvows import Vows, expect

from cafe.drivers.base import FixtureReporter
from cloudcafe.compute.composites import ComputeComposite


class ComputeContext(Vows.Context, object):

    _class_cleanup_tasks = []
    _reporter = None
    fixture_log = None

    def setup(self):
        self._reporter = FixtureReporter(self)
        self.fixture_log = self._reporter.logger.log
        self._reporter.start()
        self.compute = ComputeComposite()

    def teardown(self):
        self._reporter.stop()


@Vows.batch
class WhenACreateServerRequestIsMade(ComputeContext):

    def setup(self):
        ComputeContext.setup(self)
        self.name = 'testserver123'
        self.image_id = self.compute.images.config.primary_image
        self.flavor_id = self.compute.flavors.config.primary_flavor

    def topic(self):
        server = self.compute.servers.client.create_server(
            self.name, self.image_id, self.flavor_id).entity
        return server

    def the_server_id_should_be_set(self, topic):
        expect(topic.id).Not.to_be_null()

    class AfterTheServerFinishesBuilding(ComputeContext):

        def topic(self, server):
            created_server = self.compute.servers.behaviors.wait_for_server_creation(server.id)
            return created_server

        def the_server_should_have_the_correct_name(self, topic):
            expect(topic.name).to_equal("testserver123")

        class WhenILogIntoTheCreatedServer(ComputeContext):

            @staticmethod
            def determine_primary_disk_size(boot_method, flavor, volume_size=0):
                if flavor.extra_specs.get('class') == 'onmetal':
                    return 28
                elif boot_method == 'volume':
                    return volume_size
                else:
                    return flavor.disk

            @staticmethod
            def determine_image_id(boot_method, image):
                if boot_method == 'volume':
                    return None
                return image.id

            def setup(self):
                ComputeContext.setup(self)

                self.boot_method = 'image'
                self.volume_size = 80

                self.image = self.compute.images.client.get_image(
                    self.compute.images.config.primary_image).entity
                self.flavor = self.compute.flavors.client.get_flavor_details(
                    self.compute.flavors.config.primary_flavor).entity

                # Expected parameters
                self.expected_vcpus = self.flavor.vcpus
                self.expected_ram = self.flavor.ram
                self.expected_name = 'testserver123'
                self.expected_number_of_disks = 1 + int(
                    self.flavor.extra_specs.get('number_of_data_disks', 0))
                self.expected_primary_disk = self.determine_primary_disk_size(
                    boot_method=self.boot_method,
                    flavor=self.flavor,
                    volume_size=80)

            def topic(self, server, building_server):
                server.admin_pass = building_server.admin_pass
                remote_client = self.compute.servers.behaviors.get_remote_instance_client(
                    server, self.compute.servers.config)
                return server, remote_client

            def the_hostname_should_match_the_server_name(self, topic):
                server, remote_client = topic
                expect(remote_client.get_hostname()).to_equal(server.name)

            def it_should_have_the_correct_number_of_cpus(self, topic):
                server, remote_client = topic
                server_actual_vcpus = remote_client.get_number_of_cpus()
                expect(server_actual_vcpus).to_equal(self.expected_vcpus)

            def it_should_have_the_correct_amount_of_ram(self, topic):
                server, remote_client = topic

            def it_should_have_the_correct_number_of_disks(self, topic):
                server, remote_client = topic
                disks = remote_client.get_all_disks()
                expect(disks).to_length(self.expected_number_of_disks)

            def the_primary_disk_should_be_the_expected_size(self, topic):
                server, remote_client = topic
                disk_size = remote_client.get_disk_size(
                    self.compute.servers.config.instance_disk_path)
                expect(disk_size).to_equal(self.expected_primary_disk)

