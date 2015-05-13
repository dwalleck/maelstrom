"""
Copyright 2013 Rackspace

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from cloudcafe.common.tools.datagen import rand_name
from cloudroast.compute.fixtures import ComputeFixture
import unittest


class CreateServerTest(ComputeFixture):

    @classmethod
    def setUpClass(cls):
        super(CreateServerTest, cls).setUpClass()

        cls.boot_method = 'image'
        cls.volume_size = 80
        cls.nova_driver = 'xenserver'

        cls.name = rand_name("server")
        cls.metadata = {'meta_key_1': 'meta_value_1',
                        'meta_key_2': 'meta_value_2'}
        cls.image = cls.images_client.get_image(cls.image_ref).entity
        cls.flavor = cls.flavors_client.get_flavor_details(
            cls.flavor_ref).entity
        cls.create_resp = cls.server_behaviors.create_active_server(
            cls.name, cls.image.id, cls.flavor.id, metadata=cls.metadata)
        cls.server = cls.create_resp.entity
        cls.resources.add(cls.server.id, cls.servers_client.delete_server)

        # Expected parameters
        cls.expected_vcpus = cls.flavor.vcpus
        cls.expected_ram = cls.flavor.ram
        cls.expected_name = cls.name
        cls.expected_number_of_disks = 1 + int(
            cls.flavor.extra_specs.get('number_of_data_disks', 0))
        cls.expected_primary_disk = cls.determine_primary_disk_size(
            boot_method=cls.boot_method,
            flavor=cls.flavor,
            volume_size=80)
        cls.expected_image_id = cls.determine_image_id(
            boot_method=cls.boot_method,
            image=cls.image)
        cls.expected_xenstore_disk_config_enabled = cls.determine_xenstore_disk_config_enabled(cls.server)
        cls.expected_networks = cls.determine_expected_networks(cls.flavor)
        cls.expected_accessIPv4_address = ""
        cls.expected_accessIPv6_address = ""

    @classmethod
    def determine_disk_config(cls, disk_config, image):
        return disk_config if disk_config else image.disk_config

    @classmethod
    def determine_access_ip_address(cls, access_ip_address, ip_address):
        return access_ip_address if access_ip_address else ip_address

    @classmethod
    def determine_expected_networks(cls, flavor):
        expected_networks = []
        ip_v6_networking = True if flavor.extra_specs.get('class') != 'onmetal' else False
        expected_networks.append({"name": "public", "has_ip_v4": True, "has_ip_v6": ip_v6_networking})
        expected_networks.append({"name": "private", "has_ip_v6": True, "has_ip_v6": ip_v6_networking})
        return expected_networks

    @classmethod
    def determine_primary_disk_size(cls, boot_method, flavor, volume_size=0):
        if flavor.extra_specs.get('class') == 'onmetal':
            return 28
        elif boot_method == 'volume':
            return volume_size
        else:
            return flavor.disk

    @classmethod
    def determine_image_id(cls, boot_method, image):
        if boot_method == 'volume':
            return None
        return image.id

    @classmethod
    def determine_xenstore_disk_config_enabled(cls, server):
        actual_disk_config = server.disk_config
        return actual_disk_config.lower() == 'auto'

    def test_server_addresses(self):
        pass

    def test_created_server_image_field(self):
        actual_image_id = self.server.image.id if self.server.image is not None else None
        self.assertEqual(self.expected_image_id, actual_image_id)

    def test_can_log_into_server_after_creation(self):
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        self.assertTrue(remote_client.can_authenticate())

    def test_created_server_vcpus(self):
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        server_actual_vcpus = remote_client.get_number_of_cpus()
        self.assertEqual(server_actual_vcpus, self.expected_vcpus)

    def test_created_server_ram(self):
        remote_instance = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        lower_limit = int(self.expected_ram) - (int(self.expected_ram) * .1)
        server_ram_size = int(remote_instance.get_allocated_ram())
        self.assertTrue((int(self.expected_ram) == server_ram_size or lower_limit <= server_ram_size))

    def test_created_server_hostname(self):
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        hostname = remote_client.get_hostname()
        self.assertEqual(hostname, self.expected_name)

    def test_created_server_primary_disk(self):
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        disk_size = remote_client.get_disk_size(
            self.servers_config.instance_disk_path)
        self.assertEqual(disk_size, self.expected_primary_disk)

    def test_number_of_disks(self):
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        disks = remote_client.get_all_disks()
        self.assertEqual(self.expected_number_of_disks, len(disks))

    def test_created_server_xenstore_metadata(self):
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        xen_meta = remote_client.get_xen_user_metadata()
        for key, value in self.metadata.iteritems():
            self.assertIn(key, xen_meta)
            self.assertEqual(xen_meta[key], value)

    def test_xenstore_disk_config(self):
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        auto_config_enabled = remote_client.get_xenstore_disk_config_value()
        self.assertEqual(auto_config_enabled, self.expected_xenstore_disk_config_enabled)



