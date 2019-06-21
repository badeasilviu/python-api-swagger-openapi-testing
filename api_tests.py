from py_tests_spec.py_tests_generator import PyTestsGenerator
from api_spec.specification import Specification

url = "https://petstore.swagger.io/v2/swagger.json"

for spec in Specification:
    api = spec.url(url)
    scenarios = api.build()
    p = PyTestsGenerator(scenarios)
    p.create()