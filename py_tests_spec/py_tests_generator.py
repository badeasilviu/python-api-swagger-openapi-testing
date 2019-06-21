import os
from string import Template
from shutil import rmtree

class PyTestsGenerator:
    def __init__(self, testcases):
        self.testcases = testcases
        self.root_folder = "tests"

    def __py_test_template__(self):
        testcase_template = """
def ${testcase_id}():
    \"\"\"${description}\"\"\"
    url = "${url}"
    header = ${header}
    body = ${body_schema}
    response_code = ${response_code}
    response = ${response_schema}
    r = requests.${http_method}(url,header=header,payload=body)
    assert r.status_code == 200
    assert r.json() == response
        """
        return testcase_template

    def __cleanup_tests__(self):
        rmtree(self.root_folder)

    def create(self,overwrite=True):
        if overwrite:
            self.__cleanup_tests__()
        for suite in self.testcases:
            for testcase in self.testcases[suite]:
                folder = "/".join([self.root_folder,testcase["dir"]])
                file = "/".join([folder,testcase["file"]])
                if not os.path.exists(folder):
                    os.makedirs(folder,True)
                with open(file, 'a+') as file:
                    line = Template(self.__py_test_template__()).substitute(testcase)
                    file.write(line)
