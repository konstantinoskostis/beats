from functionbeat import BaseTest

import json
import os
import unittest


class Test(BaseTest):

    @unittest.skip("temporarily disabled")
    def test_base(self):
        """
        Basic test with exiting Functionbeat normally
        """
        self.render_config_template(
            path=os.path.abspath(self.working_dir) + "/log/*",
            local=True,
        )

        functionbeat_proc = self.start_beat()
        self.wait_until(lambda: self.log_contains("functionbeat is running"))
        exit_code = functionbeat_proc.kill_and_wait()
        assert exit_code == 0

    def test_export_function_template(self):
        """
        Test if the template can be exported
        """

        function_name = "testcloudwatchlogs"
        bucket_name = "my-bucket-name"
        fnb_name = "fnb" + function_name
        role = "arn:aws:iam::123456789012:role/MyFunction"
        security_group_ids = ["sg-ABCDEFGHIJKL"]
        subnet_ids = ["subnet-ABCDEFGHIJKL"]
        log_group = "/aws/lambda/functionbeat-cloudwatch"

        self._generate_dummy_binary_for_template_checksum()

        self.render_config_template(
            path=os.path.abspath(self.working_dir) + "/log/*",
            cloudwatch={
                "name": function_name,
                "bucket": bucket_name,
                "role": role,
                "virtual_private_cloud": {
                    "security_group_ids": security_group_ids,
                    "subnet_ids": subnet_ids,
                },
                "log_group": log_group,
            },
        )
        functionbeat_proc = self.start_beat(
            logging_args=["-d", "*"],
            extra_args=["export", "function", function_name]
        )

        self.wait_until(lambda: self.log_contains("PASS"))
        exit_code = functionbeat_proc.kill_and_wait()
        assert exit_code == 0

        function_template = self._get_generated_function_template()
        function_properties = function_template["Resources"][fnb_name]["Properties"]

        assert function_properties["FunctionName"] == function_name
        assert function_properties["Code"]["S3Bucket"] == bucket_name
        assert function_properties["Role"] == role
        assert function_properties["VpcConfig"]["SecurityGroupIds"] == security_group_ids
        assert function_properties["VpcConfig"]["SubnetIds"] == subnet_ids

    def test_export_function_template_with_invalid_configuration(self):
        """
        Test if invalid configuration is exportable
        """
        function_name = "INVALID_$_FUNCTION_$_NAME"
        bucket_name = "my-bucket-name"

        self._generate_dummy_binary_for_template_checksum()

        self.render_config_template(
            path=os.path.abspath(self.working_dir) + "/log/*",
            cloudwatch={
                "name": function_name,
                "bucket": bucket_name,
            },
        )
        functionbeat_proc = self.start_beat(
            logging_args=["-d", "*"],
            extra_args=["export", "function", function_name]
        )

        self.wait_until(
            lambda: self.log_contains("error generating raw template for {}: invalid name".format(function_name))
        )

        exit_code = functionbeat_proc.kill_and_wait()
        assert exit_code != 0

    def _generate_dummy_binary_for_template_checksum(self):
        if os.path.exists("pkg/functionbeat"):
            return

        os.mkdir("pkg")
        with open("pkg/functionbeat", "wb") as f:
            f.write("my dummy functionbeat binary")

    def _get_generated_function_template(self):
        logs = self.get_log_lines()
        function_template_lines = logs[:-2]
        raw_function_temaplate = "".join(function_template_lines)
        function_template = json.loads(raw_function_temaplate)
        return function_template
