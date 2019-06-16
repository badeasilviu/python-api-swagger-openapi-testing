import requests
from urllib.parse import urlsplit


class ContentHelper:
    def __value_or_default__(self, key, content, default_value=""):
        try:
            return content[key]
        except KeyError:
            return default_value

    def __keys_or_default__(self, key, content, default_value=""):
        try:
            return content[key].keys()
        except (KeyError, TypeError) as e:
            return default_value


class HTTPMethodData(ContentHelper):
    def __init__(self, method_name, method_content):
        self.name = method_name
        self.tags = self.__value_or_default__(key="tags", content=method_content)
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
        try:
            self.schema = parameter_content["schema"]["$ref"]
        except KeyError:
            self.schema = ""
        self.type = self.__value_or_default__(key="type", content=parameter_content)
        if self.type == "array":
            _array_content = parameter_content["items"]
            self._array_type = self.__value_or_default__(key="type",content=_array_content)
            self._array_enum = self.__value_or_default__(key="enum",content=_array_content)
            self.schema = self.__value_or_default__(key="$ref",content=_array_content)
            self.type += "_" + self._array_type
            if self._array_enum != "":
                self.type += "_"+ "_".join(self._array_enum)
        self.format = self.__value_or_default__(key="format", content=parameter_content)
        self.maximum = self.__value_or_default__(key="maximum", content=parameter_content)
        self.minimum = self.__value_or_default__(key="minimum", content=parameter_content)

class PropertyData(ContentHelper):
    def __init__(self,property_name,property_content):
        self.name = property_name
        self.type = self.__value_or_default__(key="type", content=property_content)
        self._enum = self.__value_or_default__(key="enum", content=property_content)
        if self._enum != "":
            self.type += "_" +  "_".join(self._enum)
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


class Swagger(ContentHelper):
    def __init__(self, url):
        self.url = url

    def generate(self):
        self.__get_url__()
        self.__get_host__()
        self.__get_base_path__()
        self.__get_tags__()
        self.__get_schemes__()
        self.__get_paths__()
        self.__generate_definitions__()
        self.__generate_testcases__()

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
        for tag in self.__value_or_default__("tags", content=self.response_content):
            _tags.append(tag["name"])

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
                property_data = PropertyData(property,definition_properties[property])
                self.definitions[definition_name][property_data.name] = "{" + property_data.type + "}"
        for definition in self.definitions:
            temp = self.__replace_definitions__(self.definitions[definition])
            self.definitions[definition] = temp

    def __replace_definitions__(self, dictionary):
        for k,v in dictionary.items():
            value = str(v)
            if value.find("#/definitions") != -1:
                key = value.split("/")[-1].replace("}","")
                dictionary[k] = self.definitions[key]
        return dictionary

    def __generate_testcases__(self):
        self.testcases = []
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
                    iterator = (self._schemes,) if not isinstance(self._schemes, (tuple, list)) else self._schemes
                    for scheme in iterator:
                        for content_type in method_data.content_type:
                            header = {}
                            header["content-type"] = content_type
                            if parameter_data.input == "query" or parameter_data.input == "formData":
                                if parameter_data.input == "formData":
                                    header["content-type"] = "application/x-www-form-urlencoded"
                                if query_append:
                                    if parameter_data.minimum != "" and parameter_data.maximum != "":
                                        data_type = parameter_data.type + "_" + parameter_data.minimum + "_"+ parameter_data.maximum
                                    else:
                                        data_type = parameter_data.type
                                        query += "&" + str(parameter_data.name) + "=" + "{" + data_type + "}"
                                        query_append = False
                            elif parameter_data.input == "body":
                                body = True
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
                            testcase_id = scheme + "_" + path + "_" + method_data.name + "_" + str(
                                content_type).replace("/", "_") + "_" + parameter_data.name + "_" + str(response_code)
                            testcase_description = method_data.summary + "_" + method_data.description + "_" + parameter_data.description
                            url = scheme + "://" + self._host + self._base_path + path + query
                            testcase = {
                                "testcase_id": testcase_id,
                                "description": testcase_description,
                                "url": url,
                                "http_method": method_data.name,
                                "header": header,
                                "body": body,
                                "body_schema": parameter_data.schema,
                                "response_code": response_code,
                                "response_schema" : method_data.response_schema
                            }
                            testcase = self.__replace_definitions__(testcase)
                            self.testcases.append(testcase)
                    if parameter_data.required:
                        index = required_parameters.index(parameter_data.name)
                        del (required_parameters[index])

        print(self.testcases)

swagger_url = "http://petstore.swagger.io/v2/swagger.json"
# swagger_url = "https://raw.githubusercontent.com/logzio/public-api/master/alerts/swagger.json"

s = Swagger(swagger_url)
s.generate()
