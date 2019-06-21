import requests
from urllib.parse import urlsplit
from .content_helper import ContentHelper


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
        self.__generate_definitions__()
        return self.__generate_testcases__()

    def __get_url__(self):
        self.response = requests.get(self.url)
        self.response_content = self.response.json()

    def __get_host__(self):
        self._host = self.__value_or_default__("host", content=self.response_content,
                                               default_value="{0.netloc}".format(urlsplit(self.url)))

    def __get_schemes__(self):
        self._schemes = self.__value_or_default__("schemes", content=self.response_content,
                                                  default_value="{0.scheme}".format(urlsplit(self.url)))

    def __get_base_path__(self):
        self._base_path = self.__value_or_default__("basePath", content=self.response_content)

    def __get_tags__(self):
        _tags = []
        self.testcases = {}
        for tag in self.__value_or_default__("tags", content=self.response_content):
            _tags.append(tag["name"])
            self.testcases[tag["name"]] = []

    def __get_paths__(self):
        self._paths = self.__keys_or_default__("paths", content=self.response_content)

    def __generate_definitions__(self):
        root = "definitions"
        self.definitions = {}
        for definition in self.response_content[root]:
            self.definitions[definition] = {}
            definition_name = definition
            definition_content = self.response_content[root][definition]
            definition_properties = definition_content["properties"]
            properties = definition_properties.keys();
            for property in properties:
                property_data = DefinitionPropertyData(property, definition_properties[property])
                self.definitions[definition_name][property_data.name] = "{" + property_data.type + "}"
        for definition in self.definitions:
            temp = self.__replace_definitions__(self.definitions[definition])
            self.definitions[definition] = temp

    def __replace_definitions__(self, dictionary):
        for k, v in dictionary.items():
            value = str(v)
            if value.find("#/definitions") != -1:
                key = value.split("/")[-1].replace("}", "")
                dictionary[k] = self.definitions[key]
        return dictionary

    def __generate_testcases__(self):
        root = "paths"
        for path in self._paths:
            content = self.response_content[root][path]
            for method in content.keys():
                method_content = self.response_content[root][path][method]
                method_data = HTTPMethodData(method, method_content)

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
                    body = False
                    query_append = True
                    parameter_data = ParameterData(parameter)
                    for scheme in self.__get_iterator__(self._schemes):
                        for content_type in self.__get_iterator__(method_data.content_type):
                            header = {}
                            header["content-type"] = content_type
                            if parameter_data.input == "query" or parameter_data.input == "formData":
                                if parameter_data.input == "formData":
                                    header["content-type"] = "application/x-www-form-urlencoded"
                                if query_append:
                                    data_type = parameter_data.type + "__" + "_".join([parameter_data.minimum,parameter_data.maximum,parameter_data.default])
                                    query += "&" + str(parameter_data.name) + "=" + "{" + data_type + "}"
                                    query_append = False
                            elif parameter_data.input == "body":
                                body = True
                                body_schema = parameter_data.schema
                            elif parameter_data.input == "path":
                                path.replace(parameter_data.name, "{" + parameter_data.type + "}")
                            elif parameter_data.input == "header":
                                header[parameter_data.name] = "{" + parameter_data.type + "}"
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
                            testcase_id = "_".join(
                                [tag, path.replace("/", "_").strip("_"), method_data.name, parameter_data.name, scheme,
                                 content_type.replace("/", "_"),
                                 str(response_code)])
                            testcase_description = "_".join(
                                [method_data.summary, method_data.description, parameter_data.description])
                            url = scheme + "://" + self._host + self._base_path + path + query
                            dirname = self._host + "/" + tag + "/" + self._base_path + path.replace("/",".") + "/" + method_data.name
                            testcase = {
                                "dir": dirname,
                                "file": "test_param_"+ parameter_data.name + ".py",
                                "testcase_id": "test_"+testcase_id.replace("{","").replace("}",""),
                                "description": testcase_description,
                                "url": url.strip("?"),
                                "http_method": method_data.name,
                                "header": header,
                                "body": body,
                                "body_schema": body_schema,
                                "response_code": response_code,
                                "response_schema": method_data.response_schema,
                                "request_enum": parameter_data.enum
                            }
                            self.testcases[tag].append(self.__replace_definitions__(testcase))
                    if parameter_data.required:
                        index = required_parameters.index(parameter_data.name)
                        del (required_parameters[index])

        return self.testcases


class HTTPMethodData(ContentHelper):
    def __init__(self, method_name, method_content):
        self.name = method_name
        self.tags = self.__get_iterator__(self.__value_or_default__(key="tags", content=method_content))
        self.summary = self.__value_or_default__(key="summary", content=method_content)
        self.description = self.__value_or_default__(key="description", content=method_content)
        self.operation_id = self.__value_or_default__(key="operationId", content=method_content)
        self.content_type = self.__value_or_default__(key="produces", content=method_content,
                                                      default_value="application/json")
        self.parameters = self.__value_or_default__(key="parameters", content=method_content)
        self._responses_content = self.__value_or_default__(key="responses", content=method_content)

        try:
            self.response_schema = method_content["responses"]["200"]["schema"]["items"]["$ref"]
        except KeyError:
            self.response_schema = ""

        try:
            self.response_schema = method_content["responses"]["200"]["schema"]["$ref"]
        except KeyError:
            self.response_schema

        try:
            self.schema = method_content["schema"]["$ref"]
        except KeyError:
            self.schema = ""


class ParameterData(ContentHelper):
    def __init__(self, parameter_content):
        self.input = self.__value_or_default__(key="in", content=parameter_content)
        self.name = self.__value_or_default__(key="name", content=parameter_content)
        self.description = self.__value_or_default__(key="description", content=parameter_content)
        self.required = self.__value_or_default__(key="required", content=parameter_content,
                                                  default_value=False)
        self.enum = ""
        try:
            self.schema = parameter_content["schema"]["$ref"]
        except KeyError:
            self.schema = ""
        self.type = self.__value_or_default__(key="type", content=parameter_content)

        if self.type == "array":
            _array_content = parameter_content["items"]
            self._array_type = self.__value_or_default__(key="type", content=_array_content)
            self.schema = self.__value_or_default__(key="$ref", content=_array_content)
            self.type += "_" + self._array_type

        self.format = self.__value_or_default__(key="format", content=parameter_content)
        self.maximum = self.__value_or_default__(key="maximum", content=parameter_content,default_value="*")
        self.minimum = self.__value_or_default__(key="minimum", content=parameter_content,default_value="*")
        self.default = self.__value_or_default__(key="default", content=parameter_content,default_value="*")


class DefinitionPropertyData(ContentHelper):
    def __init__(self, property_name, property_content):
        self.name = property_name
        self.type = self.__value_or_default__(key="type", content=property_content)
        self.enum = self.__value_or_default__(key="enum", content=property_content)
        self._schema = self.__value_or_default__(key="$ref", content=property_content)

        if self._schema != "":
            self.type = self._schema

        if self.type == "array":
            _array_content = property_content["items"]
            self._array_type = self.__value_or_default__(key="type", content=_array_content)
            if self._array_type != "":
                self.type += "_" + self._array_type
            self._array_schema = self.__value_or_default__(key="$ref", content=_array_content)
            if self._array_schema != "":
                self.type = self._array_schema
        if self.enum != "":
            self.type = "_".join(self.enum)
