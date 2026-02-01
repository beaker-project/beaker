# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import unittest

from bkr.labcontroller.pxemenu import template_env


def _mock_osmajors():
    return {
        "RedHatEnterpriseLinux9": {
            "RedHatEnterpriseLinux9.2": [
                {
                    "distro_tree_id": 100,
                    "distro_osmajor": "RedHatEnterpriseLinux9",
                    "distro_osversion": "RedHatEnterpriseLinux9.2",
                    "distro_name": "RHEL-9.2.0-20230401.0",
                    "variant": "BaseOS",
                    "arch": "x86_64",
                    "kernel_options": "",
                    "available": [("lab1", "http://example.com/rhel9/")],
                    "images": [
                        ("kernel", "pxeboot/vmlinuz"),
                        ("initrd", "pxeboot/initrd.img"),
                    ],
                },
            ],
        },
        "Fedora42": {
            "Fedora42": [
                {
                    "distro_tree_id": 200,
                    "distro_osmajor": "Fedora42",
                    "distro_osversion": "Fedora42",
                    "distro_name": "Fedora-38-20230401.0",
                    "variant": "Everything",
                    "arch": "x86_64",
                    "kernel_options": "",
                    "available": [("lab1", "http://example.com/fedora42/")],
                    "images": [
                        ("kernel", "pxeboot/vmlinuz"),
                        ("initrd", "pxeboot/initrd.img"),
                    ],
                },
            ],
        },
    }


class TestPxemenuTemplates(unittest.TestCase):
    def _render(self, template_name, osmajors=None):
        if osmajors is None:
            osmajors = _mock_osmajors()
        template = template_env.get_template(template_name)
        return template.render({"osmajors": osmajors})

    def test_pxelinux_menu(self):
        output = self._render("pxelinux-menu")
        self.assertIn("RHEL-9.2.0-20230401.0", output)
        self.assertIn("Fedora-38-20230401.0", output)
        self.assertIn("/distrotrees/100/kernel", output)
        self.assertIn("/distrotrees/200/kernel", output)
        self.assertIn("menu title Beaker", output)

    def test_efi_grub_menu(self):
        output = self._render("efi-grub-menu")
        self.assertIn("RHEL-9.2.0-20230401.0", output)
        self.assertIn("Fedora-38-20230401.0", output)
        self.assertIn("/distrotrees/100/kernel", output)
        self.assertIn("root (nd)", output)

    def test_grub2_menu(self):
        output = self._render("grub2-menu")
        self.assertIn("RHEL-9.2.0-20230401.0", output)
        self.assertIn("Fedora-38-20230401.0", output)
        self.assertIn("menuentry", output)
        self.assertIn("/distrotrees/100/kernel", output)
        self.assertIn("submenu", output)

    def test_ipxe_menu(self):
        output = self._render("ipxe-menu")
        self.assertIn("#!ipxe", output)
        self.assertIn("RHEL-9.2.0-20230401.0", output)
        self.assertIn("Fedora-38-20230401.0", output)
        self.assertIn("/distrotrees/100/kernel", output)
        self.assertIn("/distrotrees/200/kernel", output)
