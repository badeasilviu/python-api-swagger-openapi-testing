import os
from string import Template
from shutil import rmtree

from py_tests_spec.input_generator import InputGenerator


class PyTestsGenerator:
    def __init__(self, testcases):
        self.testcases = testcases
        self.root_folder = "tests"

    def __py_test_template__(self,testcase):
        testcase_template = []
        testcase_template.append("\ndef ${testcase_id}():\n")
        testcase_template.append("\t\"\"\"${description}\"\"\"\n")
        testcase_template.append(f"\ttestcase={testcase}\n")
        if testcase["body"]:
            testcase_template.append("\tr = requests.${http_method}(\"${url}\",headers=${header},data=${body_schema})\n")
        else:
            testcase_template.append("\tr = requests.${http_method}(\"${url}\",headers=${header})\n")
        testcase_template.append("\tbasic_check(r)\n")

        return "".join(testcase_template)

    def __cleanup_tests__(self):
        if os.path.exists(self.root_folder):
            rmtree(self.root_folder)

    def create(self, overwrite=True):
        if overwrite:
            self.__cleanup_tests__()
        files_created = []
        file_header = """import requests\nfrom py_tests_spec.py_tests_utils import basic_check\n"""
        for suite in self.testcases:
            for testcase in self.testcases[suite]:
                if "xml" in testcase["header"]["content-type"]:
                    continue
                folder = "/".join([self.root_folder, testcase["dir"]])
                file = "/".join([folder, testcase["file"]])
                if not os.path.exists(folder):
                    os.makedirs(folder, True)
                with open(file, 'a+') as f:
                    if file not in files_created:
                        f.write(file_header)
                    files_created.append(file)
                    replace_dict = {"string": InputGenerator.generate_string(),
                                    "integer": InputGenerator.generate_integer(),
                                    "array_string": InputGenerator.generate_array("string"),
                                    "array_integer": InputGenerator.generate_array("integer")}
                    for t in ["url","body_schema"]:
                        t_template = Template(str(testcase[t]))
                        testcase[t] = t_template.safe_substitute(replace_dict)

                    py_test_scenario = Template(str(self.__py_test_template__(testcase))).safe_substitute(testcase)
                    f.write(py_test_scenario)


