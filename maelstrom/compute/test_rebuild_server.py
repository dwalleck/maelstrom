"""
Copyright 2015 Rackspace

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

import base64
import unittest

from cafe.drivers.unittest.decorators import tags
from cloudcafe.common.tools.datagen import rand_name
from cloudcafe.compute.common.types import ComputeHypervisors, \
    NovaServerStatusTypes
from cloudcafe.compute.config import ComputeConfig
from cloudroast.compute.fixtures import ServerFromImageFixture
from cloudcafe.compute.servers_api.config import ServersConfig
from cloudroast.compute.fixtures import ComputeFixture


class RebuildServerTest(ComputeFixture):

    @classmethod
    def setUpClass(cls):
        super(RebuildServerTest, cls).setUpClass()

        cls.boot_method = 'image'
        cls.volume_size = 80

        cls.name = rand_name("server")
        cls.image = cls.images_client.get_image(cls.image_ref).entity
        cls.flavor = cls.flavors_client.get_flavor_details(
            cls.flavor_ref).entity
        cls.create_resp = cls.server_behaviors.create_active_server(
            cls.name, cls.image.id, cls.flavor.id)
        cls.server = cls.create_resp.entity
        cls.resources.add(cls.server.id, cls.servers_client.delete_server)

        cls.image = cls.images_client.get_image(cls.image_ref_alt).entity
        cls.rebuilt_server_response = cls.servers_client.rebuild(
            cls.server.id, cls.image_ref_alt, name=cls.name)
        cls.server = cls.server_behaviors.wait_for_server_status(
            cls.server.id, NovaServerStatusTypes.ACTIVE).entity
        cls.server.admin_pass = cls.rebuilt_server_response.entity.admin_pass

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

    def test_rebuilt_server_image_field(self):
        """Verify that a created server has image field"""
        actual_image_id = self.server.image.id if self.server.image is not None else None
        self.assertEqual(self.expected_image_id, actual_image_id)

    def test_rebuilt_server_vcpus(self):
        """Verify the number of vCPUs reported matches the expected amount"""

        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        server_actual_vcpus = remote_client.get_number_of_cpus()
        self.assertEqual(server_actual_vcpus, self.expected_vcpus)

    def test_rebuilt_server_ram(self):
        """
        The server's RAM and should be set to the amount specified
        in the flavor
        """

        remote_instance = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        lower_limit = int(self.expected_ram) - (int(self.expected_ram) * .1)
        server_ram_size = int(remote_instance.get_allocated_ram())
        self.assertTrue((int(self.expected_ram) == server_ram_size or lower_limit <= server_ram_size))

    def test_rebuilt_server_hostname(self):
        """
        Verify that the hostname of the server is the same as
        the server name
        """
        remote_client = self.server_behaviors.get_remote_instance_client(
            self.server, self.servers_config)
        hostname = remote_client.get_hostname()
        self.assertEqual(hostname, self.expected_name)

    def test_rebuilt_server_primary_disk(self):
        """
        Verify the size of the primary disk matches the expected value
        """
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