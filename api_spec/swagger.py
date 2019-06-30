import requests
from urllib.parse import urlsplit
from api_spec.content_helper import ContentHelper
from dicttoxml import dicttoxml


class Swagger(ContentHelper):
    def __init__(self, url):
        self.url = url

    def build(self):
        self.__get_url__()
        self.__get_host__()
        self.__get_base_path__()
        self.__get_tags__()
        self.__get_schemes__()
        self.__get_paths__()
        self.__get_definitions__()
        print()
    def __get_url__(self):
        self.response = requests.get(self.url)
        self.response_content = self.response.json()

    def __get_host__(self):
        self.host = self.__value_or_default__("host", content=self.response_content,
                                              default_value="{0.netloc}".format(urlsplit(self.url)))

    def __get_schemes__(self):
        self.schemes = self.__value_or_default__("schemes", content=self.response_content,
                                                 default_value="{0.scheme}".format(urlsplit(self.url)))

    def __get_base_path__(self):
        self._base_path = self.__value_or_default__("basePath", content=self.response_content)

    def __get_tags__(self):
        self.tags = []
        for tag in self.__value_or_default__("tags", content=self.response_content):
            self.tags.append(tag["name"])

    def __get_paths__(self):
        paths = self.__value_or_default__("paths", content=self.response_content)
        self.paths = {}
        for name, value in paths.items():
            self.paths[name] = [HTTPMethodData(k, v) for k, v in value.items()]

    def __get_definitions__(self):
        definitions = self.response_content["definitions"]
        self.definitions = {}
        for definition_name, definition_content in definitions.items():
            self.definitions[definition_name] = DefinitionsData(definition_name,definition_content)


class DefinitionsData(ContentHelper):
    def __init__(self, definition, definition_content):
        self.content = definition_content
        self.name = definition
        self.schema_json = {
            "type": definition_content["type"],
            "properties": definition_content["properties"]
        }
        if "xml" in definition_content:
            self.schema_xml = dicttoxml(self.schema_json, custom_root=definition_content["xml"], attr_type=False)
        else:
            self.schema_xml = dicttoxml(self.schema_json, attr_type=False)




class HTTPMethodData(ContentHelper):
    def __init__(self, method, method_content):
        self.name = method
        self.content = method_content
        self.tags = self.__get_iterator__(self.__value_or_default__(key="tags", content=method_content))
        self.summary = self.__value_or_default__(key="summary", content=method_content)
        self.description = self.__value_or_default__(key="description", content=method_content)
        self.operation_id = self.__value_or_default__(key="operationId", content=method_content)
        self.produces = self.__value_or_default__(key="produces", content=method_content,
                                                  default_value="application/json")
        self.consumes = self.__value_or_default__(key="produces", content=method_content,
                                                  default_value="application/json")

        responses_content = self.__value_or_default__(key="responses", content=method_content)
        self.responses = {}
        for response in responses_content:
            schema_content = self.__value_or_default__("schema", content=response)
            self.responses[response] = self.__value_or_default__("$ref", content=schema_content)

        parameters = self.__value_or_default__(key="parameters", content=method_content)
        self.parameters = {}
        for parameter_content in parameters:
            parameter = ParameterData(parameter_content)
            self.parameters[parameter.name] = parameter


class ParameterData(ContentHelper):
    def __init__(self, parameter_content):
        self.content = parameter_content
        self.input = self.__value_or_default__(key="in", content=parameter_content)
        self.name = self.__value_or_default__(key="name", content=parameter_content)
        self.description = self.__value_or_default__(key="description", content=parameter_content)
        self.required = self.__value_or_default__(key="required", content=parameter_content,
                                                  default_value=False)
        self.format = self.__value_or_default__(key="format", content=parameter_content)
        self.maximum = self.__value_or_default__(key="maximum", content=parameter_content, default_value="*")
        self.minimum = self.__value_or_default__(key="minimum", content=parameter_content, default_value="*")
        self.default = self.__value_or_default__(key="default", content=parameter_content, default_value="*")
        self.enum = []
        schema_content = self.__value_or_default__("schema", content=parameter_content)
        if schema_content != "":
            parameter_content = schema_content
        self.schema = self.__value_or_default__("$ref", content=parameter_content)
        self.type = self.__value_or_default__("type", content=parameter_content)
        if self.type == "array":
            array_content = parameter_content["items"]
            self.type = self.__value_or_default__("type", content=array_content)
            self.enum = self.__value_or_default__("enum", content=array_content)
            self.default = self.__value_or_default__("default", content=array_content)
            if "$ref" in array_content:
                self.schema = array_content["$ref"]

class TestData:
    def __init__(self):
        pass
    def __get_testcases__(self):
        root = "paths"
        for path, methods in self.response_content[root].items():
            for method in methods:
                method_data = HTTPMethodData(method, methods[method])

                required_parameters = []
                optional_parameters = []
                for parameter in method_data.parameters:
                    parameter_data = ParameterData(parameter)
                    if parameter_data.required:
                        required_parameters.append(parameter_data.name)
                    else:
                        optional_parameters.append(parameter_data.name)

                query = "?"
                for parameter in method_data.parameters:
                    query_append = True
                    parameter_data = ParameterData(parameter)
                    header = {}
                    resource_path = ""
                    if parameter_data.input == "query" or parameter_data.input == "formData":
                        if parameter_data.input == "formData":
                            header["content-type"] = "application/x-www-form-urlencoded"
                            if query_append:
                                query += "&" + str(parameter_data.name) + "=" + "${" + parameter_data.type + "}"
                                query_append = False
                            elif parameter_data.input == "path":
                                resource_path = path.replace("{" + parameter_data.name + "}",
                                                             "${" + parameter_data.type + "}")
                            elif parameter_data.input == "header":
                                header[parameter_data.name] = "${" + parameter_data.type + "}"
                            else:
                                raise ValueError("parameter input: {} is not supported".format(parameter_data.input))

                            if parameter_data.required:
                                if len(required_parameters) > 1:
                                    response_code = 400
                                else:
                                    response_code = 200
                            else:
                                response_code = 200
                            tag = method_data.tags[0]
                            for scheme in self.__get_iterator__(self.schemes):
                                for content_type in self.__get_iterator__(method_data.produces):
                                    testcase_id = "_".join(
                                        [tag, path.replace("/", "_").strip("_"), method_data.name, parameter_data.name,
                                         scheme,
                                         content_type.replace("/", "_"),
                                         str(response_code)])
                                    testcase_description = "_".join(
                                        [method_data.summary, method_data.description, parameter_data.description])
                                    url = scheme + "://" + self.host + self._base_path + path + query
                                    dirname = self.host + "/" + tag + self._base_path + path.replace("/",
                                                                                                     ".") + "/" + method_data.name
                                    if "content-type" not in header:
                                        header["content-type"] = content_type
                                    testcase = {
                                        "dir": dirname,
                                        "file": "test_param_" + parameter_data.name + ".py",
                                        "testcase_id": "test_" + testcase_id.replace("{", "").replace("}", ""),
                                        "description": testcase_description,
                                        "url": url.strip("?"),
                                        "http_method": method_data.name,
                                        "header": header,
                                        "body": "",
                                        "body_schema": parameter_data.schema,
                                        "response_code": response_code,
                                        "response_schema": self.__value_or_default__(response_code,
                                                                                     content=method_data.responses)
                                    }
                                    self.testcases[tag].append(testcase)
                    if parameter_data.required:
                        index = required_parameters.index(parameter_data.name)
                        del (required_parameters[index])

        return self.testcases
